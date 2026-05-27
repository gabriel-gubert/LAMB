import argparse
import json
import sys
from .config_manager import ConfigManager
from .config_schema import ConfigSchema
from .registry_manager import RegistryManager
from .agent_factory import migrator_agent, mapper_agent

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

    # 3. Apply Agent Cascading for LLM Parameters
    agents = cmd_schema.get("agents", [])

    for agent in agents:
        for llm_param in ConfigSchema.SHARED_PARAMETERS:
            param_name = llm_param["param"]
            
            # Retrieve values mapped by argparse
            specific_val = getattr(args, f"{agent}_{param_name}", None)
            general_val = getattr(args, param_name, None)
            
            # Apply strict Specific > General > Default precedence
            if specific_val is not None:
                cm.apply_override(f"tasks.{agent}.{param_name}", specific_val)
            elif general_val is not None:
                cm.apply_override(f"tasks.{agent}.{param_name}", general_val)
                cm.apply_override(f"tasks.default.{param_name}", general_val)


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

        print(f"Set {args.key} to {args.value} in {scope} config.")
    elif args.key:
        val = cm.get(args.key)

        if val is not None:
            print(val)


def handle_migrate(args, cm: ConfigManager):
    """Handles logic for the 'migrate' subcommand."""

    if args.file:
        with open(args.file, 'r') as f:
            legacy_code_snippet = f.read()
    else:
        legacy_code_snippet = sys.stdin.read()

    if args.alias:
        mapping_table = RegistryManager().get_mapping(args.alias)

    migrator = migrator_agent(config_manager=cm)
    result = migrator.migrate(legacy_code_snippet=legacy_code_snippet, mapping_table=mapping_table)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)

            print(f"Migrated code successfully saved to: {args.output}")
        except Exception as e:
            print(f"Error saving the migrated code: {e}", file=sys.stderr)

            return

    print(result)


def handle_map(args, cm: ConfigManager):
    """Handles logic for the 'map' subcommand."""

    mapper = mapper_agent(config_manager=cm)
    result = mapper.run(path_a=args.path_v1, path_b=args.path_v2)

    if args.alias:
        RegistryManager().register(args.alias, result)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4)

            print(f"Full mapping table successfully saved to: {args.output}")
        except Exception as e:
            print(f"Error saving mapping table: {e}", file=sys.stderr)

        return

def main():
    parser = argparse.ArgumentParser(description="LLM-Assisted Code Migration Bot (LAMB)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Build Shared Parser ---
    shared_parser = argparse.ArgumentParser(add_help=False)
    
    # Add Global Config Flags
    for item in ConfigSchema.GLOBAL_CONFIG_FLAGS:
        shared_parser.add_argument(*item["flags"], **item["kwargs"])

    # Add Shared LLM Parameters
    for param_def in ConfigSchema.SHARED_PARAMETERS:
        cli_flag = f"--{param_def['param'].replace('_', '-')}"
        shared_parser.add_argument(cli_flag, type=param_def["type"], help=f"Default {param_def['help']} for all tasks")

    # --- Build Subparsers ---
    for cmd_name, cmd_data in ConfigSchema.COMMANDS.items():
        # Inherit shared parser only if it utilizes agents (e.g., skip for 'config')
        parents = [shared_parser] if "agents" in cmd_data else []
        cmd_parser = subparsers.add_parser(cmd_name, parents=parents, help=cmd_data["help"])

        # Add Standard Arguments
        for item in cmd_data.get("args", []):
            cmd_parser.add_argument(*item["flags"], **item["kwargs"])

        # Add Tuning Settings
        if "config_overrides" in cmd_data:
            tuning_group = cmd_parser.add_argument_group(f'{cmd_name.capitalize()} Tuning Settings')

            for item in cmd_data["config_overrides"]:
                tuning_group.add_argument(*item["flags"], **item["kwargs"])

        # Add Specific Agent Overrides
        if "agents" in cmd_data:
            spec_group = cmd_parser.add_argument_group('Specific Agent Overrides')

            for agent in cmd_data["agents"]:
                for param_def in ConfigSchema.SHARED_PARAMETERS:
                    cli_flag = f"--{agent}-{param_def['param'].replace('_', '-')}"
                    spec_group.add_argument(cli_flag, type=param_def["type"], help=f"{param_def['help']} specifically for {agent} agent")

    # --- Parse & Execute ---
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cm = ConfigManager()

    apply_cli_overrides(args, cm, args.command)

    if args.command == 'config':
        handle_config(args, cm)
    elif args.command == 'migrate':
        handle_migrate(args, cm)
    elif args.command == 'map':
        handle_map(args, cm)


if __name__ == "__main__":
    main()