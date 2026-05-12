import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

def print_agent_state(state: dict, title: str = "Mapper Agent State"):
    """
    Prints the LangGraph state to the CLI with formatting and colors.
    """

    console = Console()
    state_json = json.dumps(state, indent=2, default=str)
    syntax = Syntax(state_json, "json", theme="monokai", line_numbers=True)

    panel = Panel(
        syntax,
        title=f"[bold blue]{title}[/bold blue]",
        border_style="bright_blue",
        expand=False
    )

    console.print(panel)

def display_rich_matrix(sim_matrix, v1_elements, v2_elements):
    """
    Displays the similarity matrix using a grayscale heatmap for cell values
    and a professional monochromatic blue theme for the structure.
    """

    console = Console()

    brand_blue = "#005A9B"

    table = Table(
        title="Semantic Similarity Matrix", 
        title_style=f"bold {brand_blue}",
        border_style=brand_blue,
        header_style=f"bold {brand_blue}",
        pad_edge=False
    )

    table.add_column("Legacy \ Modern", style=f"bold {brand_blue}", no_wrap=True)
    for el in v2_elements:
        table.add_column(el.get('member', '??')[:8], justify="center")

    for i, row in enumerate(sim_matrix):
        v1_name = v1_elements[i].get('member', '??')[:15]
        row_data = [Text(v1_name, style=f"bold {brand_blue}")]

        for score in row:
            v = int(score * 255)
            cell_text = Text(f"{score:.2f}", style=f"black on rgb({v},{v},{v})")

            row_data.append(cell_text)

        table.add_row(*row_data)

    console.print(table)

def display_mapping_table(mappings: list[dict]):
    """
    Displays the final API migration mapping including namespaces, 
    using a professional monochromatic theme.
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
        show_lines=True
    )

    table.add_column("Legacy Path (V1)", ratio=2)
    table.add_column("Modern Path (V2)", ratio=2)
    table.add_column("Migration Notes", ratio=1, style="italic")

    for row in mappings:
        v1_namespace = f"[dim]{row.get('old_namespace', 'N/A')}[/dim]"
        v1_member = f"{row.get('old_class_interface', '')}.[bold]{row.get('old_member', '')}[/bold]"
        v1_sig = f"[dim i]{row.get('old_signature', '')}[/dim i]"
        v1_display = f"{v1_namespace}\n{v1_member}\n{v1_sig}"
        
        if not row.get('new_member'):
            v2_display = "[bold red]DEPRECATED / REMOVED[/bold red]"
        else:
            v2_namespace = f"[dim]{row.get('new_namespace', 'N/A')}[/dim]"
            v2_member = f"{row.get('new_class_interface', '')}.[bold]{row.get('new_member', '')}[/bold]"
            v2_sig = f"[dim i]{row.get('new_signature', '')}[/dim i]"
            v2_display = f"{v2_namespace}\n{v2_member}\n{v2_sig}"

        notes = row.get('additional_notes', "")

        if "[1:N]" in notes or "[N:N]" in notes:
            notes_text = Text(notes, style="orange3")
        elif "[DEPRECATED]" in notes:
            notes_text = Text(notes, style="red")
        elif "[AMBIGUOUS]" in notes:
            notes_text = Text(notes, style="yellow")
        else:
            notes_text = Text(notes)

        table.add_row(v1_display, v2_display, notes_text)

    console.print(table)