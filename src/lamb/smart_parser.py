import sys
from dataclasses import dataclass
from enum import Enum
from typing import Set, List, Dict, Any, Optional, Tuple

import tree_sitter_language_pack as tslp
from tree_sitter import Parser, Node

from langchain_core.messages import SystemMessage, HumanMessage

from .rate_limited_chat import RateLimitedChatOpenAI
from .output_templates import (
    Language,
    ParserResult,
    ExternalVariableInference,
    TypeInferenceResult
)
from .prompt_templates import (
    get_language_prompt,
    get_parse_prompt,
    get_type_inference_prompt,
)


# =========================================================================
# ENUMS & DATACLASSES
# =========================================================================

@dataclass
class ASTRange:
    """
    Represents full source location bounds across lines, columns, and raw bytes.
    Line numbers are 1-indexed; column offsets and byte ranges are 0-indexed.
    """
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_byte: int
    end_byte: int


@dataclass
class ASTSyntaxError:
    """
    Represents a granular syntax error detected during Tree-Sitter parsing.
    """
    error_id: int
    node_type: str
    scope_name: str
    message: str
    range: ASTRange
    node_text: str


class SmartParser:
    def __init__(
        self, 
        code: str,
        detector: RateLimitedChatOpenAI,
        analyzer: RateLimitedChatOpenAI,
        inferer: RateLimitedChatOpenAI,
        language: Optional[str] = None,
        verbose: bool = False
    ):
        self.code = code
        self.language = language
        self.verbose = verbose

        self.detector = detector.with_structured_output(Language).with_retry(stop_after_attempt=2)
        self.analyzer = analyzer.with_structured_output(ParserResult).with_retry(stop_after_attempt=2)
        self.inferer = inferer.with_structured_output(TypeInferenceResult).with_retry(stop_after_attempt=2)

        self.tree = None

        self.symbols: Set[str] = set()
        self.fully_qualified_symbols: Set[str] = set()

        self.external_usage_contexts: Dict[str, TypeInferenceResult] = {}

        self.parser = None
        self._is_parsed = False

    # =========================================================================
    # LOGGING HELPERS
    # =========================================================================

    def _log_info(self, message: str) -> None:
        if self.verbose:
            print(f"[*] {message}", file=sys.stderr)

    def _log_warn(self, message: str) -> None:
        if self.verbose:
            print(f"[/!\\] {message}", file=sys.stderr)

    def _log_error(self, message: str) -> None:
        if self.verbose:
            print(f"[X] {message}", file=sys.stderr)

    # =========================================================================
    # PARSING & EXTRACTORS
    # =========================================================================

    def _detect_language(self) -> str:
        available_languages = list(tslp.available_languages())
        self._log_info("Detecting Programming Language Via LLM...")

        messages = [
            SystemMessage(content=get_language_prompt(available_languages)),
            HumanMessage(content=f"\n```\n{self.code}\n```\n")
        ]

        try:
            response = self.detector.invoke(messages)
            detected_lang = response.language.value.strip().lower()
            self._log_info(f"Detected Programming Language: '{detected_lang}'.")
            return detected_lang
        except Exception as E:
            self._log_error(f"Failed Programming Language Detection (Fallback To `python`): {E}")
            return "python"

    def _ensure_language_installed(self) -> bool:
        if not self.language:
            self.language = self._detect_language()

        if tslp.has_language(self.language):
            return True

        self._log_warn(f"Language '{self.language}' Grammar Not Found.")

        try:
            self._log_info(f"Downloading Tree-Sitter Grammar For '{self.language}'...")
            tslp.download([self.language])
            self._log_info(f"Successfully Installed Grammar For '{self.language}'.")
            return True
        except Exception as e:
            self._log_error(f"Tree-Sitter Language Grammar Download Failed: {e}")

        return False

    def parse(self) -> bool:
        if self._is_parsed:
            return True

        self._log_info("Initiating SmartParser Parsing Sequence...")

        if not self._ensure_language_installed():
            self._log_error(f"Cannot Parse Code: Grammar For '{self.language}' Unavailable.")
            return False

        try:
            language_obj = tslp.get_language(self.language)
            self.parser = Parser(language_obj)
            self.tree = self.parser.parse(bytes(self.code, "utf8"))
            self._log_info(f"Tree-Sitter AST Construction Complete For '{self.language}'.")

            self._extract_type_identifiers_via_llm()
            self._analyze_external_variable_usages_via_llm()

            self._is_parsed = True
            self._log_info("SmartParser Parsing Sequence Completed Successfully.")
            return True

        except Exception as e:
            self._log_error(f"Failed Parsing {self.language}: {e}")
            return False

    def _extract_type_identifiers_via_llm(self):
        self._log_info("Extracting Type Identifiers Via LLM...")
        prompt = get_parse_prompt()

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"\n```\n{self.code}\n```\n")
        ]

        try:
            response = self.analyzer.invoke(messages)

            for item in response.identifiers:
                self.symbols.add(item.name)
                if item.fully_qualified_name:
                    self.fully_qualified_symbols.add(item.fully_qualified_name)

            self._log_info(
                f"LLM Identifier Extraction: Found {len(self.symbols)} Bare Symbol(s) "
                f"And {len(self.fully_qualified_symbols)} Fully-Qualified Symbol(s)."
            )

        except Exception as e:
            self._log_error(f"LLM Type Identifier Extraction Failed: {e}")

    def get_identifiers(self) -> Set[str]:
        if not self._is_parsed:
            self.parse()

        return self.symbols

    def get_fully_qualified_identifiers(self) -> Set[str]:
        if not self._is_parsed:
            self.parse()

        return self.fully_qualified_symbols

    def get_external_variable_contexts(self) -> Dict[str, ExternalVariableInference]:
        if not self._is_parsed:
            self.parse()

        return self.external_usage_contexts

    def _analyze_external_variable_usages_via_llm(self, mapping_table: Optional[List[Any]] = None):
        """
        Uses LLM reasoning to identify undeclared external variables and infer 
        their types based on usage patterns and an optional schema mapping table.
        """
        self._log_info("Analyzing External Variable Usage Contexts Via LLM...")
        prompt = get_type_inference_prompt(mapping_table)

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"\n```\n{self.code}\n```\n")
        ]

        try:
            response = self.inferer.invoke(messages)

            self.external_usage_contexts = {
                var_info.variable_name: var_info
                for var_info in response.external_variables
            }

            self._log_info(f"External Variable Inference: Analyzed {len(self.external_usage_contexts)} Non-Local Context(s).")

        except Exception as e:
            self._log_error(f"LLM External Variable Type Inference Failed: {e}")

    def infer_type_from_schema(self, var_name: str, mapping_table: List[Any]) -> Dict[str, Any]:
        """
        Triggers LLM-based type inference against a schema mapping table 
        and returns the result dictionary for the target variable.
        """
        if not self._is_parsed:
            self.parse()

        self._log_info(f"Inferring Schema Type For Variable '{var_name}'...")
        self._analyze_external_variable_usages_via_llm(mapping_table=mapping_table)

        ctx = self.external_usage_contexts.get(var_name)

        if not ctx:
            self._log_warn(f"Variable '{var_name}' Not Found In External Usage Contexts.")
            return {"status": "UNKNOWN", "candidate_class": None}

        return {
            "status": ctx.status,
            "candidate_class": ctx.inferred_type,
            "schema_type": ctx.schema_type,
        }

    def get_syntax_errors(self) -> List[ASTSyntaxError]:
        """
        Traverses the AST to extract granular syntax errors pinpointed 
        at the exact leaf node or missing token location.
        """
        if not self._is_parsed:
            self.parse()

        if not self.tree or not self.tree.root_node:
            self._log_warn("AST Unavailable For Syntax Error Inspection.")
            return []

        self._log_info("Inspecting AST For Syntax Errors...")
        errors: List[ASTSyntaxError] = []
        error_counter = 1

        def find_leaf_errors(node: Node) -> List[Node]:
            if not node.children or node.is_missing:
                if node.is_missing or node.type == "ERROR" or (node.parent and node.parent.type == "ERROR"):
                    return [node]
                return []

            leaf_errors = []
            for child in node.children:
                leaf_errors.extend(find_leaf_errors(child))

            if not leaf_errors and (node.type == "ERROR" or node.is_missing):
                return [node]

            return leaf_errors

        def traverse(node: Node):
            nonlocal error_counter

            if node.is_missing or node.type == "ERROR":
                exact_err_nodes = find_leaf_errors(node)

                for err_node in exact_err_nodes:
                    token_text = err_node.text.decode('utf8') if err_node.text else ''
                    
                    if err_node.is_missing:
                        msg = f"Missing Token: '{err_node.type}'"
                    else:
                        msg = f"Unexpected Token '{token_text}'"

                    parent = err_node.parent
                    while parent and parent.type == "ERROR":
                        parent = parent.parent
                    
                    scope_name = f"{parent.type}_scope" if parent else "global"

                    errors.append(
                        ASTSyntaxError(
                            error_id=error_counter,
                            node_type=err_node.type,
                            scope_name=scope_name,
                            message=msg,
                            range=self._node_to_range(err_node),
                            node_text=token_text
                        )
                    )
                    error_counter += 1

                return

            for child in node.children:
                traverse(child)

        traverse(self.tree.root_node)

        if errors:
            self._log_warn(f"Found {len(errors)} Syntax Error(s).")
        else:
            self._log_info("No Syntax Errors Found.")

        return errors

    @staticmethod
    def _node_to_range(node: Node) -> ASTRange:
        """Converts a Tree-Sitter Node's spatial boundaries into an ASTRange instance."""
        return ASTRange(
            start_line=node.start_point[0] + 1,
            start_column=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1],
            start_byte=node.start_byte,
            end_byte=node.end_byte
        )