import json
import sys
from typing import Dict, Any, List

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

import numpy as np

def print_agent_state(state: dict, title: str = "Mapper Agent State", n: int = 5):
    """
    Prints the LangGraph state to the CLI with formatting and colors.
    If the state dictionary is too big, it truncates it to show only
    the first N elements and the last N elements.
    Recursively truncates any properties that are lists.
    """

    console = Console()

    # --- Recursive Helper Function ---
    def truncate_recursive(item):
        if isinstance(item, dict):
            # Recursively process all dictionary values
            return {k: truncate_recursive(v) for k, v in item.items()}
        
        elif isinstance(item, list):
            # If the list is larger than the boundaries, truncate the middle
            if len(item) > 2 * n:
                truncated_list = []
                # Add first n elements (recursively processed)
                for x in item[:n]:
                    truncated_list.append(truncate_recursive(x))
                
                # Add placeholder indicating the number of hidden elements
                truncated_list.append(f"... ({len(item) - 2 * n} ELEMENTS HIDDEN) ...")
                
                # Add last n elements (recursively processed)
                for x in item[-n:]:
                    truncated_list.append(truncate_recursive(x))
                return truncated_list
            else:
                # List is short enough, but still process elements recursively
                return [truncate_recursive(x) for x in item]
        
        return item

    # 1. Truncate the top-level dictionary keys if necessary
    if len(state) > 2 * n:
        state_list = list(state.items())
        truncated_state = {}
        for k, v in state_list[:n]:
            truncated_state[k] = v
        truncated_state["... (truncated)"] = f"{len(state) - 2 * n} elements hidden"
        for k, v in state_list[-n:]:
            truncated_state[k] = v
        state_to_print = truncated_state
    else:
        state_to_print = state

    # 2. Apply recursive list truncation to the state dictionary copy
    processed_state = truncate_recursive(state_to_print)

    # 3. Print the processed state using Rich
    state_json = json.dumps(processed_state, indent=2, default=str)
    syntax = Syntax(state_json, "json", theme="monokai", line_numbers=True)

    panel = Panel(
        syntax,
        title=f"[bold blue]{title}[/bold blue]",
        border_style="bright_blue",
        expand=False
    )

    console.print(panel)

def display_rich_matrix(sim_matrix, v1_elements, v2_elements, n: int = 5, title="Semantic Similarity Matrix"):
    """
    Displays the similarity matrix using a grayscale heatmap for cell values
    and a professional monochromatic blue theme for the structure.
    If the matrix is too big, it truncates it to show only the first N
    elements and the last N elements.
    """
    console = Console()
    brand_blue = "#005A9B"

    # --- MIN-MAX MATRIX NORMALIZATION BLOCK ---
    # Captures any matrix configuration (raw or pure Z-score) and maps it cleanly
    matrix_min = float(np.min(sim_matrix))
    matrix_max = float(np.max(sim_matrix))
    matrix_range = matrix_max - matrix_min
    
    # Avoid zero division if every cell inside the matrix holds the exact same score
    if matrix_range == 0:
        matrix_range = 1e-6
    # ------------------------------------------

    # Determine column truncation
    col_truncated = len(v2_elements) > 2 * n
    if col_truncated:
        v2_cols = list(v2_elements[:n]) + [{"member": "..."}] + list(v2_elements[-n:])
        col_indices = list(range(n)) + [None] + list(range(len(v2_elements) - n, len(v2_elements)))
    else:
        v2_cols = list(v2_elements)
        col_indices = list(range(len(v2_elements)))

    table = Table(
        title=title, 
        title_style=f"bold {brand_blue}",
        border_style=brand_blue,
        header_style=f"bold {brand_blue}",
        pad_edge=False
    )

    table.add_column("Legacy / Modern", style=f"bold {brand_blue}", no_wrap=True)
    for el in v2_cols:
        table.add_column((el.get('member') or el.get('class_or_interface') or el.get('namespace') or "")[:8], justify="center")

    # Determine row truncation
    row_truncated = len(v1_elements) > 2 * n
    if row_truncated:
        row_indices = list(range(n)) + [None] + list(range(len(v1_elements) - n, len(v1_elements)))
    else:
        row_indices = list(range(len(v1_elements)))

    is_first_row = True
    for r_idx in row_indices:
        if r_idx is None:
            table.add_row("...")
            is_first_row = False
            continue

        v1_name = (v1_elements[r_idx].get('member') or v1_elements[r_idx].get('class_or_interface') or v1_elements[r_idx].get('namespace') or "")[:15]
        row_data = [Text(v1_name, style=f"bold {brand_blue}")]

        for c_idx in col_indices:
            if c_idx is None:
                row_data.append(Text("...", justify="center") if is_first_row else Text(""))
                continue
                
            score = sim_matrix[r_idx][c_idx]
            
            # Linearly scale the score to an exact 0.0 - 1.0 normalization window
            normalized_score = (score - matrix_min) / matrix_range
            
            # Compute v and apply clip guardrails to ensure it sits safely inside [0, 255]
            v = int(np.clip(normalized_score * 255, 0, 255))
            
            cell_text = Text(f"{score:.2f}", style=f"black on rgb({v},{v},{v})")
            row_data.append(cell_text)

        table.add_row(*row_data)
        is_first_row = False

    console.print(table)

def display_mapping_table(mappings: list[dict], n: int = 5):
    """
    Displays the final API migration mapping including namespaces,
    using a professional monochromatic theme.
    If the mapping list is too big, it truncates it to show only
    the first N elements and the last N elements.
    """

    console = Console()

    if not mappings:
        console.print("[bold red]No mappings found to display.[/bold red]")

        return

    header_style = "bold #00599C"
    table = Table(
        title="API Migration Mapping Table",
        title_style=header_style,
        border_style="#005A9B",
        header_style=header_style,
        show_lines=True,
    )

    table.add_column("Legacy Path (V1)", ratio=2)
    table.add_column("Modern Path (V2)", ratio=2)
    table.add_column("Complexity", ratio=2)
    table.add_column("Migration Notes", ratio=1)

    style_map = {
        "1:1": "green",
        "1:N": "orange3",
        "N:1": "blue",
        "N:N": "orange3",
        "AMBIGUOUS": "yellow",
        "DEPRECATED": "red",
    }

    if len(mappings) > 2 * n:
        mappings_to_show = list(mappings[:n]) + [None] + list(mappings[-n:])
    else:
        mappings_to_show = mappings

    for row in mappings_to_show:
        if row is None:
            table.add_row("...")
            continue

        v1_namespace = f"[dim]{row.get('old_namespace', 'N/A')}[/dim]"
        v1_member = ".".join([val for val in [row.get('old_class_interface', ''), f"[bold]{row.get('old_member', '')}[/bold]" if row.get('old_member') else ""] if val])
        v1_sig = f"[dim i]{row.get('old_signature', '')}[/dim i]"
        v1_display = f"{v1_namespace}\n{v1_member}\n{v1_sig}"

        if not row.get("new_member"):
            v2_display = ""
        else:
            v2_namespace = f"[dim]{row.get('new_namespace', 'N/A')}[/dim]"
            v2_member = ".".join([val for val in [row.get('new_class_interface', ''), f"[bold]{row.get('new_member', '')}[/bold]" if row.get('new_member') else ""] if val])
            v2_sig = f"[dim i]{row.get('new_signature', '')}[/dim i]"
            v2_display = f"{v2_namespace}\n{v2_member}\n{v2_sig}"

        complexity_val = str(row.get("complexity", "1:1")).strip().upper()
        row_style = style_map.get(complexity_val, "default")
        complexity_text = Text(complexity_val, style=row_style)

        notes = row.get("additional_notes", "")
        notes_text = Text(notes, style=f"italic {row_style}" if row_style != "default" else "italic")

        table.add_row(v1_display, v2_display, complexity_text, notes_text)

    console.print(table)

def print_migration_report(confidence_report: Dict[str, Any], audit_trail: Dict[str, Any], verbose: bool = False) -> None:
        """
        Prints a structured summary of applied rules, confidence scores, line ranges,
        code snippets, and diagnostics to stderr.
        """

        rule_scores: List[Dict[str, Any]] = confidence_report.get("rule_scores", [])
        global_score: float = confidence_report.get("score", 0.0)
        global_level: str = confidence_report.get("level", "UNKNOWN")

        print("\n===========================================================", file=sys.stderr)
        print("                MIGRATION CONFIDENCE REPORT                ", file=sys.stderr)
        print("===========================================================", file=sys.stderr)
        print(f"Global Confidence Score : {global_score * 100:.1f}% ({global_level})", file=sys.stderr)
        print(f"Total Rules Evaluated   : {len(rule_scores)}", file=sys.stderr)
        print(f"Language                : {audit_trail.get('language', 'N/A')}", file=sys.stderr)
        print(f"Attempts Executed       : {audit_trail.get('total_attempts_executed', 1)}", file=sys.stderr)
        print("-----------------------------------------------------------", file=sys.stderr)

        if rule_scores:
            print("\n--- APPLIED RULES & SNIPPET BREAKDOWN ---", file=sys.stderr)

            for r in rule_scores:
                rule_id = r.get("rule_id", "N/A")
                score = r.get("score", 0.0) * 100
                level = r.get("level", "N/A")
                status = r.get("status", "N/A")
                in_snip = r.get("input_snippet", "").strip()
                out_snip = r.get("output_snippet", "").strip()
                rng = r.get("range", {})
                diag = r.get("diagnostics", {})

                if rng:
                    range_str = f"L{rng.get('start_line')}:{rng.get('start_column')} -> L{rng.get('end_line')}:{rng.get('end_column')}"
                else:
                    range_str = "N/A"

                print(f"\n[Rule #{rule_id}] Score: {score:.1f}% | Level: {level} | Status: {status}", file=sys.stderr)
                print(f"  Range          : {range_str}", file=sys.stderr)
                print(f"  Input Snippet  : {in_snip}", file=sys.stderr)
                print(f"  Output Snippet : {out_snip}", file=sys.stderr)

                if diag:
                    cov = diag.get("schema_coverage_ratio", 0.0) * 100
                    logprob_mass = diag.get("snippet_logprob_mass", 0.0) * 100
                    tokens = diag.get("tokens_in_snippet", 0)
                    matched = diag.get("matched_target_symbols", [])
                    leftover = diag.get("leftover_legacy_symbols", [])

                    print(f"  Coverage Ratio : {cov:.1f}%", file=sys.stderr)
                    print(f"  Logprob Mass   : {logprob_mass:.1f}% ({tokens} tokens)", file=sys.stderr)
                    if matched:
                        print(f"  Matched Targets: {', '.join(matched)}", file=sys.stderr)
                    if leftover:
                        print(f"  Leftover    : {', '.join(leftover)}", file=sys.stderr)

        if verbose:
            print("\n--- FULL AUDIT REPORT JSON ---", file=sys.stderr)
            print(json.dumps(confidence_report, indent=2), file=sys.stderr)

        print("===========================================================\n", file=sys.stderr)