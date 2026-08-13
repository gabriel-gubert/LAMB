import argparse
import ctypes
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from .config_manager import ConfigManager
from .config_schema import ConfigSchema
from .registry_manager import RegistryManager
from .agent_factory import migrator_agent, mapper_agent
from .logger import print_migration_report

def _set_pdeathsig():
    """Linux specific: send SIGTERM to child if parent process dies unexpectedly."""

    try:
        libc = ctypes.CDLL("libc.so.6")

        PR_SET_PDEATHSIG = 1

        libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
    except Exception:
        pass


@contextmanager
def litellm_proxy_context(cm):
    """Context manager to launch the LiteLLM proxy safely in the background
    guaranteeing shutdown on completion or error.
    """

    if not cm.get("general.litellm.enabled", True):
        yield
        return

    litellm_path = shutil.which("litellm")

    if litellm_path:
        cmd = [os.path.abspath(litellm_path)]
    else:
        cmd = [sys.executable, "-m", "litellm.proxy.proxy_cli"]

    host = cm.get("general.litellm.host", "127.0.0.1")
    port = cm.get("general.litellm.port", 4000)
    config_file = cm.get("general.litellm.config_file", None)
    verbose = cm.get("general.verbose", False)

    if host in ("0.0.0.0", "::"):
        print("[/!\\] LiteLLM is binding to ALL Network Interfaces.", file=sys.stderr)

    cmd.extend(["--host", str(host), "--port", str(port)])

    if config_file:
        config_path = Path(config_file).resolve()

        if config_path.is_file():
            cmd.extend(["--config", str(config_path)])
        else:
            raise FileNotFoundError(f"LiteLLM Config File Not Found: {config_file}")

    proxy_process = None

    try:
        if verbose:
            print(f"[*] Starting LiteLLM Proxy on http://{host}:{port}...", file=sys.stderr)

        stdout_dest = None if verbose else subprocess.DEVNULL
        stderr_dest = None if verbose else subprocess.DEVNULL

        kwargs = {}

        if os.name == "posix":
            kwargs["preexec_fn"] = _set_pdeathsig

        proxy_process = subprocess.Popen(
            cmd,
            stdout=stdout_dest,
            stderr=stderr_dest,
            env=os.environ.copy(),
            **kwargs,
        )

        health_url = f"http://{host}:{port}/health/liveliness"
        max_retries = 30
        server_ready = False

        for _ in range(max_retries):
            if proxy_process.poll() is not None:
                break

            try:
                with urllib.request.urlopen(health_url, timeout=1) as resp:
                    if resp.status == 200:
                        server_ready = True

                        break
            except Exception:
                time.sleep(0.5)

        if not server_ready:
            exit_code = proxy_process.poll()

            if exit_code is None:
                proxy_process.terminate()

                try:
                    proxy_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proxy_process.kill()

                raise RuntimeError(f"LiteLLM Proxy Timed Out Starting on http://{host}:{port}.")
            else:
                raise RuntimeError(f"LiteLLM Proxy Process Exited Early with Code {exit_code}.")

        yield

    finally:
        if proxy_process and proxy_process.poll() is None:
            if verbose:
                print("[*] Shutting down LiteLLM Proxy...", file=sys.stderr)

            proxy_process.terminate()

            try:
                proxy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if verbose:
                    print("[/!\\] LiteLLM Proxy DID NOT TERMINATA GRACEFULLY, sending SIGKILL...", file=sys.stderr)

                proxy_process.kill()
                proxy_process.wait()


def parse_configuration_arg(val: str) -> dict:
    val = val.strip()

    try:
        return json.loads(val)
    except json.JSONDecodeError:
        path = Path(val)

        if path.is_file():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                raise ValueError(f"[X] Failed to Read/Parse Configuration File '{val}': {e}.")
        else:
            raise ValueError(f"[X] Invalid JSON String or File Path Not Found: '{val}'.")


def _get_dest_from_flags(flags, kwargs):
    """Helper to determine the attribute name argparse will use for a set of flags."""

    if "dest" in kwargs:
        return kwargs["dest"]

    for flag in flags:
        if flag.startswith('--'):
            return flag.lstrip('-').replace('-', '_')

    return flags[0].replace('-', '_')


def apply_cli_overrides(args: argparse.Namespace, cm: ConfigManager, command: str):
    """
    Dynamically routes parsed arguments to their exact ConfigManager dot-paths
    using the ConfigSchema single source of truth.
    """

    # 1. Apply Global Flags
    for item in ConfigSchema.GLOBAL_CONFIG_FLAGS:
        dest = _get_dest_from_flags(item["flags"], item["kwargs"])
        val = getattr(args, dest, None)

        if val is not None:
            cm.apply_override(item["config_path"], val)

    cmd_schema = ConfigSchema.COMMANDS.get(command)
    if not cmd_schema:
        return

    # 2. Apply Command-Specific Tuning Settings
    for item in cmd_schema.get("config_overrides", []):
        dest = _get_dest_from_flags(item["flags"], item["kwargs"])
        val = getattr(args, dest, None)

        if val is not None:
            cm.apply_override(item["config_path"], val)

    # 3. Apply Agent Configuration Overrides
    agents = cmd_schema.get("agents", [])
    for agent in agents:
        dest = f"configure_{agent.replace('-', '_')}"
        val = getattr(args, dest, None)

        if val is not None:
            try:
                overrides = parse_configuration_arg(val)
                if isinstance(overrides, dict):
                    for k, v in overrides.items():
                        cm.apply_override(f"{agent}.{k}", v)
                else:
                    print(f"[X] Configuration for Agent '{agent.split('.')[-1].title()}' must be a JSON Object/Dictionary.", file=sys.stderr)
                    sys.exit(1)
            except Exception as e:
                print(f"[X] Failed to Parse Configuration for Agent '{agent.split('.')[-1].title()}': {e}.", file=sys.stderr)
                sys.exit(1)


def handle_config(args, cm: ConfigManager):
    """Handles logic for the 'config' subcommand."""

    if args.list:
        for item in cm.list():
            print(item)
        return

    if args.key and args.value:
        scope = "global" if args.global_scope else "local"

        if isinstance(args.value, str):
            if args.value.lower() == 'true':
                args.value = True
            elif args.value.lower() == 'false':
                args.value = False
            else:
                try:
                    if args.value.isdigit() or (args.value.startswith('-') and args.value[1:].isdigit()):
                        args.value = int(args.value)
                    else:
                        args.value = float(args.value)
                except ValueError:
                    pass

        cm.set(args.key, args.value, scope=scope)
        print(f"Set {args.key} to {args.value} in {scope.capitalize()} Configuration File.")
    elif args.key:
        val = cm.get(args.key)
        if val is not None:
            print(val)

def _parse_range_flag(range_str: str, file_content: str) -> str:
    """
    Parses '14:12-14:34', '14:12..34', '14-16', or '14' into the exact highlighted string slice.
    Line and column numbers are 1-indexed.
    """

    if not range_str:
        return ""
        
    range_str = range_str.strip()
    lines = file_content.splitlines()
    total_lines = len(lines)
    
    if total_lines == 0:
        return range_str

    # 1. Match full L:C-L:C or L:C..C format (e.g., 14:12-14:34, 14:12-16:5, 14:12..34)
    match_col_range = re.match(r"^(\d+):(\d+)(?:-|..)(\d+)(?::(\d+))?$", range_str)
    if match_col_range:
        s_line, s_col = int(match_col_range.group(1)), int(match_col_range.group(2))
        
        # If second line isn't specified (e.g. 14:12..34), end line is same as start line
        if match_col_range.group(4) is None:
            e_line = s_line
            e_col = int(match_col_range.group(3))
        else:
            e_line = int(match_col_range.group(3))
            e_col = int(match_col_range.group(4))
            
        # Bound-checking lines
        s_line_idx = max(0, min(s_line - 1, total_lines - 1))
        e_line_idx = max(0, min(e_line - 1, total_lines - 1))
        
        # Single line slice
        if s_line_idx == e_line_idx:
            line_str = lines[s_line_idx]
            s_col_idx = max(0, min(s_col - 1, len(line_str)))
            e_col_idx = max(0, min(e_col, len(line_str)))

            return line_str[s_col_idx:e_col_idx]
        
        # Multiline slice
        selected_lines = []
        # First line remainder
        first_line = lines[s_line_idx]
        selected_lines.append(first_line[max(0, s_col - 1):])
        
        # Middle lines
        for l in range(s_line_idx + 1, e_line_idx):
            selected_lines.append(lines[l])
            
        # Final line prefix
        last_line = lines[e_line_idx]
        selected_lines.append(last_line[:max(0, e_col)])

        return "\n".join(selected_lines)

    # 2. Match line-only ranges (e.g., '14-16' or single line '14')
    match_line_only = re.match(r"^(\d+)(?:-(\d+))?$", range_str)
    if match_line_only:
        s_line = int(match_line_only.group(1))
        e_line = int(match_line_only.group(2)) if match_line_only.group(2) else s_line
        
        s_line_idx = max(0, min(s_line - 1, total_lines - 1))
        e_line_idx = max(0, min(e_line, total_lines))

        return "\n".join(lines[s_line_idx:e_line_idx])

    # 3. Fallback: Treat as a literal substring passed directly by the CLI user
    return range_str


def handle_migrate(args, cm: ConfigManager):
    """Handles logic for the 'migrate' subcommand."""

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            legacy_code_snippet = f.read()
    else:
        legacy_code_snippet = sys.stdin.read()

    mapping_table = None

    if args.alias:
        mapping_table = RegistryManager().get_mapping(args.alias)

    priority_sections = []

    for severity, flag_name in [
        ("CRITICAL", "critical"),
        ("WARNING", "warning"),
        ("INFO", "info"),
        ("DONT_TOUCH", "dont_touch")
    ]:
        flag_vals = getattr(args, flag_name, []) or []

        for range_item in flag_vals:
            if range_item:
                extracted_snippet = _parse_range_flag(range_item, legacy_code_snippet)
                priority_sections.append({
                    "severity": severity,
                    "range_raw": range_item,
                    "snippet": extracted_snippet
                })

    user_comments = getattr(args, "user_comments", "")

    migrator = migrator_agent(config_manager=cm)
    result = migrator.migrate(
        legacy_code_snippet=legacy_code_snippet,
        mapping_table=mapping_table,
        priority_sections=priority_sections,
        user_comments=user_comments
    )

    migrated_code = result.get("migrated_code", "")
    confidence_report = result.get("confidence", {})
    audit_trail = result.get("audit_trail", {})

    if args.report:
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump({
                    "confidence": confidence_report,
                    "audit_trail": audit_trail
                }, f, indent=2)
        except Exception as e:
            print(f"[X] Failed Writing Confidence Report File: {e}", file=sys.stderr)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(migrated_code)

            print(f"Migrated Source Code Successfully Saved to {args.output}.", file=sys.stderr)
        except Exception as e:
            print(f"[X] Failed to Save the Migrated Source Code: {e}.", file=sys.stderr)

            return

    print_migration_report(
        confidence_report=confidence_report,
        audit_trail=audit_trail,
        verbose=args.verbose
    )

    print(migrated_code)


def handle_map(args, cm: ConfigManager):
    """Handles logic for the 'map' subcommand."""

    verbose = cm.get("general.verbose", False)
    mapper = mapper_agent(config_manager=cm)
    result = mapper.run(path_a=args.path_v1, path_b=args.path_v2, thread_id=args.thread_id)

    if args.alias:
        RegistryManager().register(args.alias, result)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4)

            if verbose:
                print(f"Mapping Table Successfully Saved to {args.output}.", file=sys.stderr)
        except Exception as e:
            print(f"[X] {e}", file=sys.stderr)
        return


def main():
    parser = argparse.ArgumentParser(description="LLM-Assisted Code Migration Bot (LAMB)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Build Shared Parser ---
    shared_parser = argparse.ArgumentParser(add_help=False)
    for item in ConfigSchema.GLOBAL_CONFIG_FLAGS:
        shared_parser.add_argument(*item["flags"], **item["kwargs"])

    # --- Build Subparsers ---
    for cmd_name, cmd_data in ConfigSchema.COMMANDS.items():
        parents = [shared_parser] if "agents" in cmd_data else []
        cmd_parser = subparsers.add_parser(cmd_name, parents=parents, help=cmd_data["help"])

        for item in cmd_data.get("args", []):
            cmd_parser.add_argument(*item["flags"], **item["kwargs"])

        if "config_overrides" in cmd_data:
            tuning_group = cmd_parser.add_argument_group(f'{cmd_name.capitalize()} Tuning Settings')
            for item in cmd_data["config_overrides"]:
                tuning_group.add_argument(*item["flags"], **item["kwargs"])

        if "agents" in cmd_data:
            spec_group = cmd_parser.add_argument_group('Agent Configuration Options')
            for agent in cmd_data["agents"]:
                cli_flag = f"--configure-{agent.replace('_', '-')}"
                spec_group.add_argument(cli_flag, type=str, help=f"JSON String or Path to JSON File to Configure the {agent.replace('_', ' ').title()} Agent.")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cm = ConfigManager()
    apply_cli_overrides(args, cm, args.command)

    if args.command in ['migrate', 'map']:
        with litellm_proxy_context(cm):
            if args.command == 'migrate':
                handle_migrate(args, cm)
            elif args.command == 'map':
                handle_map(args, cm)
    elif args.command == 'config':
        handle_config(args, cm)


if __name__ == "__main__":
    main()