from typing import Any, Optional, List, Tuple
from pathlib import Path

def get_template(file_name: str) -> str:
    """
    Reads and returns a prompt from a Markdown file.
    """

    prompt_path = Path(__file__).parent / "templates" / file_name

    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path.resolve()}")
        
    return prompt_path.read_text(encoding="utf-8").strip()


def get_language_prompt(supported_langs: list[str] = None) -> str:
    lang_list_str = ", ".join(supported_langs)

    return get_template("MIGRATION_LANGUAGE_TEMPLATE.md").format(lang_list_str=lang_list_str).strip()


def get_parse_prompt() -> str:
    return get_template("MIGRATION_PARSE_TEMPLATE.md").strip()


def get_type_inference_prompt(mapping_table: Optional[List[Any]] = None) -> str:
    schema_str = f"\nMapping Table / Schema Context:\n{mapping_table}\n" if mapping_table else "\nMapping Table / Schema Context: None provided.\n"

    return get_template("MIGRATION_TYPE_INFERENCE_TEMPLATE.md").format(schema_str=schema_str).strip()


def get_summarization_prompt() -> str:
    return get_template("MIGRATION_SUMMARIZATION_TEMPLATE.md").strip()


def get_migration_planner_prompt(
    language: str,
    legacy_code_snippet: str,
    formatted_rules: str,
    priority_summary: str = "",
    user_comments: str = ""
) -> Tuple[str, str]:
    # 1. Prepare dynamic conditional blocks
    has_priorities = bool(priority_summary.strip())

    priority_instructions_block = ""
    if has_priorities:
        priority_instructions_block = """
#### Code Preservation & Protection Boundaries (`DONT_TOUCH`)
- **Strict Character-Level Granularity:** Any code region tagged as `DONT_TOUCH` / `IMMUTABLE` applies STRICTLY and ONLY to the exact text within the specified character or line range. 
- **Scope Isolation:** Do NOT treat a `DONT_TOUCH` tag on a specific symbol, token, or line as an immutable constraint on its enclosing function, block, or scope. Surrounding code outside the specified range REMAIN FULLY EDITABLE.
- **Strict Boundary Preservation:** Text within the exact character range must remain completely verbatim as a complete copy of the original snippet, regardless of whether migration rules apply to those sections. Do NOT plan line insertions, edits, moves, deletions, stubs, or wrapper code around these protected bounds.

#### Execution Priority Hierarchy
- **CRITICAL Priority:**
    - *Focus:* Breaking changes, security updates, core architectural changes, or removed API elements.
    - *Order:* MUST be planned as the earliest sequential steps (Step 1, Step 2, etc.) prior to standard refactoring.
    - *Requirement:* Every `CRITICAL` item requires zero-regression plan steps with explicit target symbol definitions.
- **WARNING Priority:**
    - *Focus:* Standard schema migrations, non-breaking method renames, signature updates, or property access refactorings.
    - *Order:* Planned immediately following all `CRITICAL` priorities.
- **INFO Priority:**
    - *Focus:* Optional enhancements, non-breaking type annotation additions, comment updates, or code cleanliness refactorings.
    - *Order:* Planned last as minor refinements.
"""

    user_instructions_block = ""
    if user_comments.strip():
        user_instructions_block = f'### ADDITIONAL NOTES/INSTRUCTIONS\n"{user_comments.strip()}"'

    priority_block = ""
    if priority_summary.strip():
        priority_block = f"### DEVELOPER PRIORITY HIGHLIGHTS\n{priority_summary.strip()}"

    # 2. Load Markdown templates
    system_template = get_template("MIGRATION_PLANNER_SYSTEM_TEMPLATE.md")
    user_template = get_template("MIGRATION_PLANNER_USER_TEMPLATE.md")

    # 3. Format templates with inputs
    system_prompt = system_template.format(
        language=language,
        priority_instructions_block=priority_instructions_block
    ).strip()

    user_prompt = user_template.format(
        language=language,
        formatted_rules=formatted_rules,
        priority_block=priority_block,
        legacy_code_snippet=legacy_code_snippet,
        user_instructions_block=user_instructions_block
    ).strip()

    return system_prompt, user_prompt


def get_migration_prompt(
    language: str,
    legacy_code_snippet: str,
    formatted_rules: str,
    migration_plan: str = "",
    user_comments: str = "",
    priority_summary: str = "",
    validation_error: str = ""
) -> Tuple[str, str]:
    has_priorities = bool(priority_summary.strip())

    dont_touch_instructions = ""
    if has_priorities:
        dont_touch_instructions = """
#### Code Preservation & Protection Boundaries (`DONT_TOUCH`)
- **Strict Character-Level Granularity:** Any code region tagged as `DONT_TOUCH` / `IMMUTABLE` applies STRICTLY and ONLY to the exact text within the specified character or line range.
- **Scope Isolation:** Do NOT treat a `DONT_TOUCH` tag on a specific symbol, token, or line as an immutable constraint on its enclosing function, block, or scope. Surrounding code outside the specified range REMAIN FULLY EDITABLE.
- **Strict Boundary Preservation:** Any code region tagged as `DONT_TOUCH` / `IMMUTABLE` must remain a complete verbatim copy of the original code snippet in the generated output, even if migration rules apply to those sections. Do NOT alter, move, reindent out of scope, delete, or inject stubs, shims, adapters, or wrapper code around these protected ranges.
"""

    user_instructions_block = ""
    if user_comments.strip():
        user_instructions_block = f'### ADDITIONAL NOTES/INSTRUCTIONS\n\n"{user_comments.strip()}"'

    priority_block = ""
    if priority_summary.strip():
        priority_block = f'### DEVELOPER PRIORITY HIGHLIGHTS\n\n{priority_summary.strip()}'

    plan_block = ""
    if migration_plan.strip():
        plan_block = f'### MIGRATION PLAN\n\n{migration_plan.strip()}'

    error_retry_block = ""
    if validation_error.strip():
        error_retry_block = f'### PREVIOUS ATTEMPT SYNTAX / VALIDATION ERROR (FIX THIS)\n\nThe previous migration attempt failed validation with the following error:\n\n"{validation_error.strip()}"\n\nCorrect this error completely in the new generated code.'

    system_template = get_template("MIGRATION_SYSTEM_TEMPLATE.md")
    user_template = get_template("MIGRATION_USER_TEMPLATE.md")

    system_prompt = system_template.format(
        language=language,
        dont_touch_instructions=dont_touch_instructions
    ).strip()

    user_prompt = user_template.format(
        language=language,
        formatted_rules=formatted_rules,
        plan_block=plan_block,
        priority_block=priority_block,
        legacy_code_snippet=legacy_code_snippet,
        user_instructions_block=user_instructions_block,
        error_retry_block=error_retry_block
    ).strip()

    return system_prompt, user_prompt


def get_mapper_extraction_prompt() -> str:   
    return get_template("MAPPER_EXTRACTION_TEMPLATE.md")


def get_general_mapper_resolution_prompt():
    return get_template("MAPPER_RESOLUTION_TEMPLATE.md")


def get_lexical_mapper_resolution_prompt():
    return get_template("MAPPER_LEXICAL_RESOLUTION_TEMPLATE.md")


def get_semantic_mapper_resolution_prompt():
    return get_template("MAPPER_SEMANTIC_RESOLUTION_TEMPLATE.md")


def get_consensus_arbitration_prompt():
    return get_template("MAPPER_CONSENSUS_ARBITRATION_TEMPLATE.md")


def get_directory_discovery_prompt() -> str:
    return get_template("MAPPER_DIRECTORY_DISCOVERY_TEMPLATE.md")