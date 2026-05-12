from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .prompt_templates import get_summarization_prompt, get_migration_prompt
from .smart_parser import SmartParser

class MigrationState(TypedDict):
    current_code: str
    mapping_table: dict
    identifiers: List[str]
    rules: List[str]

class MigratorAgent:
    """
    A LangGraph-powered agent that handles code migration by orchestrating 
    different LLMs in a cyclic graph for parsing, summarization, and generation.
    """

    def __init__(self, 
        migrator: ChatOpenAI,
        summarizer: ChatOpenAI,
        detector: ChatOpenAI,
        summarization_threshold: int = 2048,
        verbose: bool = False,
    ):
        self.detector = detector
        self.summarizer = summarizer
        self.migrator = migrator
        self.summarization_threshold = summarization_threshold
        self.verbose = verbose

        self.graph = self._build_graph()

    def _build_graph(self):
        """Constructs and compiles the LangGraph state machine."""

        workflow = StateGraph(MigrationState)

        workflow.add_node("parse", self.parse_code)
        workflow.add_node("extract", self.extract_rules)
        workflow.add_node("migrate", self.generate_migration)

        workflow.set_entry_point("parse")

        workflow.add_edge("parse", "extract")
        workflow.add_edge("extract", "migrate")
        workflow.add_edge("migrate", "end")

        return workflow.compile()

    def _summarize(self, text: str) -> str:
        """Helper method to summarize lengthy documentation notes."""

        return self.summarizer.invoke([
            SystemMessage(content=get_summarization_prompt()),
            HumanMessage(content=f"\n```\n{text}\n```\n")
        ]).content

    def parse_code(self, state: MigrationState) -> dict:
        """Parses the current iteration of the code to find identifiers."""

        parser = SmartParser(state["current_code"], detector=self.detector)
        parser.parse()

        return {
            "language": parser.language,
            "identifiers": parser.get_identifiers()
        }

    def extract_rules(self, state: MigrationState) -> dict:
        """Matches identifiers against the mapping table to extract rules."""

        mapping_table = state["mapping_table"]
        identifiers = state["identifiers"]
        rules = set()

        num_entries = len(mapping_table.get('Object', []))
        if not num_entries:
            return {"rules": []}

        columns = [
            'Namespace', 'Object', 'Member', 'Signature',
            'New Namespace', 'New Object', 'New Member', 'New Signature', 'Notes'
        ]

        row_iterator = zip(*(mapping_table.get(col, [''] * num_entries) for col in columns))

        for (old_ns, old_obj, old_mem, old_sig, 
            new_ns, new_obj, new_mem, new_sig, notes) in row_iterator:

            # Evaluate Object Rules
            if old_obj and old_obj in identifiers:
                if new_obj == old_obj:
                    rule = f"- Legacy object `{old_obj}` still exists in the current version."
                    if new_ns:
                        rule += f" It can be found inside namespace `{new_ns}`."
                else:
                    rule = f"- Legacy object `{old_obj}` is obsolete."
                    if new_obj:
                        rule += f" It was replaced by object `{new_obj}`"
                        rule += f" which can be found inside namespace `{new_ns}`." if new_ns else "."
                    else:
                        rule += " It has no direct replacement."
                rules.add(rule)

            # Evaluate Member Rules
            if old_mem and old_mem in identifiers:
                if new_mem:
                    rule = f"- Legacy member `{old_mem}` in legacy namespace `{old_ns}` was replaced by method `{new_mem}` in namespace `{new_ns}`."
                else:
                    rule = f"- Legacy member `{old_mem}` in legacy namespace `{old_ns}` does not have a counterpart in the current version."

                if notes:
                    if len(notes) > self.summarization_threshold:
                        notes = self._summarize(notes)
                    rule += f'\n\nAdditional notes from the documentation:\n\n"{notes}"\n\n'
                rules.add(rule)

        return {"rules": list(rules)}

    def generate_migration(self, state: MigrationState) -> dict:
        """Feeds the code and rules to the LLM to generate the updated code."""

        rules = state["rules"]
        current_code = state["current_code"]
        language = state["language"]

        formatted_rules = '\n'.join(rules) if rules else 'No specific rules found.'

        prompt = get_migration_prompt(
            language=language,
            legacy_code_snippet=current_code,
            formatted_rules=formatted_rules,
            verbose=self.verbose
        )

        migrated_code = self.migrator.invoke(prompt).content

        return {"current_code": migrated_code}

    def migrate(self, legacy_code_snippet: str, mapping_table: dict) -> str:
        initial_state = {
            "language": "",
            "current_code": legacy_code_snippet,
            "mapping_table": mapping_table,
            "identifiers": [],
            "rules": []
        }

        final_state = self.graph.invoke(initial_state)

        return final_state["current_code"]
