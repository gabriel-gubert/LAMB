import json
from collections import defaultdict
from dataclasses import is_dataclass, asdict
from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from .logger import log_info, log_warn, log_error
from .rate_limited_chat import RateLimitedChatOpenAI
from .smart_parser import SmartParser, ASTSyntaxError
from .confidence import (
    DynamicConfidenceEvaluator, 
    TokenLogprob, 
    GlobalConfidenceReport
)
from .output_templates import (
    MappingRow,
    ExternalVariableInference,
    MigrationPlanSchema,
    MigrationOutputSchema
)
from .prompt_templates import (
    get_summarization_prompt,
    get_migration_planner_prompt,
    get_migration_prompt,
)
from .types import (
    Complexity,
    MigrationRule,
    MatchMapping
)


def to_json(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    elif is_dataclass(obj) and not isinstance(obj, type):
        return to_json(asdict(obj))
    elif isinstance(obj, dict):
        return {k: to_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json(item) for item in obj]
    return obj


class MigrationState(TypedDict):
    language: str
    legacy_code: str
    current_code: str
    previous_code: Optional[str]
    mapping_table: Dict[str, List[Any]]
    user_comments: Optional[str]
    identifiers: List[str]
    fully_qualified_identifiers: List[str]
    external_contexts: Dict[str, ExternalVariableInference]
    rules: List[MigrationRule]
    plan: str
    applied_rules: List[dict]
    current_logprobs: Optional[List[TokenLogprob]]
    latest_signals: List[Dict[str, Any]]
    changelog: List[Dict[str, Any]]
    validation_error: Optional[str]
    attempt: int
    max_attempts: int
    confidence_report: Optional[GlobalConfidenceReport]
    history: List[Dict[str, Any]]
    priority_sections: Optional[List[dict]]


class MigratorAgent:
    def __init__(
        self,
        migrator: RateLimitedChatOpenAI,
        summarizer: RateLimitedChatOpenAI,
        detector: RateLimitedChatOpenAI,
        analyzer: RateLimitedChatOpenAI,
        inferer: RateLimitedChatOpenAI,
        planner: Optional[RateLimitedChatOpenAI] = None,
        summarization_threshold: int = 2048,
        verbose: bool = False,
        max_attempts: int = 3,
    ):
        self.migrator = migrator.with_structured_output(MigrationOutputSchema, include_raw=True).with_retry(stop_after_attempt=2)
        self.planner = planner.with_structured_output(MigrationPlanSchema).with_retry(stop_after_attempt=2) if planner else None
        self.summarizer = summarizer
        self.summarization_threshold = summarization_threshold
        self.detector = detector
        self.analyzer = analyzer
        self.inferer = inferer
        self._parser_timeline: List[SmartParser] = []
        self.max_attempts = max_attempts
        self.verbose = verbose

        if self.verbose:
            log_info(f"Initializing Agent... (Max Attempts: {self.max_attempts}, Character Threshold: {self.summarization_threshold})")

        self.graph = self._build_graph()


    def _build_graph(self):
        if self.verbose:
            log_info(f"Building Workflow Graph...")

        workflow = StateGraph(MigrationState)

        workflow.add_node("parse", self.parse_code)
        workflow.add_node("extract", self.extract_rules)
        workflow.add_node("plan", self.plan_migration)
        workflow.add_node("migrate", self.generate_migration)
        workflow.add_node("validate", self.validate_code)

        workflow.set_entry_point("parse")
        workflow.add_edge("parse", "extract")
        workflow.add_edge("extract", "plan")
        workflow.add_edge("plan", "migrate")
        workflow.add_edge("migrate", "validate")

        workflow.add_conditional_edges(
            "validate",
            self._decide_next_step,
            {
                "retry": "migrate",
                "end": END
            }
        )

        return workflow.compile()

    # -----------------------------------------------------------------------
    # Graph Helpers
    # -----------------------------------------------------------------------

    def _summarize(self, text: str) -> str:
        if self.verbose:
            log_info(f"Summarizing Notes Exceeding Character Threshold ({len(text)} Characters)...")
        return self.summarizer.invoke([
            SystemMessage(content=get_summarization_prompt()),
            HumanMessage(content=f"\n```\n{text}\n```\n")
        ]).content


    def _decide_next_step(self, state: MigrationState) -> str:
        validation_error = state.get("validation_error")
        attempt = state.get("attempt", 0)
        max_attempts = state.get("max_attempts", 3)

        if validation_error and attempt < max_attempts:
            if self.verbose:
                log_warn(f"Retrying Migration... (Attempt {attempt} of {max_attempts})")
            return "retry"

        if self.verbose:
            if validation_error:
                log_error(f"Terminating Workflow... (Maximum Limit Reached: {attempt} of {max_attempts})")
            else:
                log_info(f"Finalizing Workflow...")

        return "end"

    # -----------------------------------------------------------------------
    # Graph Nodes
    # -----------------------------------------------------------------------

    def parse_code(self, state: MigrationState) -> dict:
        if self.verbose:
            log_info(f"Parsing Source Code & External Variable Usage Patterns...")

        legacy_code = state.get("legacy_code", state["current_code"])

        parser = SmartParser(legacy_code, detector=self.detector, analyzer=self.analyzer, inferer=self.inferer, verbose=self.verbose)
        parser.parse()

        self._parser_timeline.append(parser)

        identifiers = list(parser.get_identifiers())
        fully_qualified_identifiers = list(parser.get_fully_qualified_identifiers())
        external_contexts = parser.get_external_variable_contexts()

        if self.verbose:
            log_info(f"Detected Language is '{parser.language}'. Detected {len(external_contexts)} Non-Local Variable Context(s).")
            log_info(f"Found {len(identifiers)} Symbols and {len(fully_qualified_identifiers)} Fully-Qualified Symbols.")

        return {
            "current_code": parser.code,
            "previous_code": parser.code,
            "language": parser.language,
            "identifiers": identifiers,
            "fully_qualified_identifiers": fully_qualified_identifiers,
            "external_contexts": external_contexts
        }


    def extract_rules(self, state: MigrationState) -> dict:
        if self.verbose:
            log_info(f"Extracting And Mapping Rules...")

        table = state["mapping_table"]
        identifiers = set(state.get("identifiers", []))

        num_entries = len(table)

        if not num_entries:
            if self.verbose:
                log_warn(f"Empty Mapping Table. No Rules Extracted.")

            return {"rules": []}

        columns = list(MappingRow.model_fields.keys())

        matched_rows = []

        for i in range(num_entries):
            row = {col: table[i].get(col, '') for col in columns}

            if row['old_class_interface'] in identifiers or row['old_member'] in identifiers:
                notes = row.get('additional_notes', '')

                if notes and len(notes) > self.summarization_threshold:
                    row['additional_notes'] = self._summarize(notes)
                
                matched_rows.append(row)

        if not matched_rows:
            if self.verbose:
                log_warn(f"No Source Code Identifiers Matched... No Rules Extracted.")

            return {"rules": []}

        grouped_by_old = defaultdict(list)
        grouped_by_new = defaultdict(list)

        for row in matched_rows:
            old_key = (row['old_namespace'], row['old_class_interface'], row['old_member'])
            new_key = (row['new_namespace'], row['new_class_interface'], row['new_member'])
            grouped_by_old[old_key].append(row)
            grouped_by_new[new_key].append(row)

        rules = []
        for rule_id, (old_key, matches) in enumerate(grouped_by_old.items(), start=1):
            old_ns, old_cls, old_mem = old_key

            is_deprecated_rule = False

            for match in matches:
                match_complexity = match.get('complexity', '')
                match_complexity = str(match_complexity.value if isinstance(match_complexity, Complexity) else match_complexity).upper().strip()
                
                has_no_target = not any([match['new_namespace'], match['new_class_interface'], match['new_member']])

                if match_complexity == Complexity.DEPRECATED.value or has_no_target:
                    is_deprecated_rule = True

                    break

            if is_deprecated_rule:
                complexity = Complexity.DEPRECATED
            else:
                unique_targets = {
                    (match['new_namespace'], match['new_class_interface'], match['new_member']) 
                    for match in matches
                }

                is_n_to_1 = any(len(grouped_by_new[t]) > 1 for t in unique_targets)

                if len(unique_targets) == 1 and not is_n_to_1:
                    complexity = Complexity.ONE_TO_ONE
                elif len(unique_targets) > 1 and not is_n_to_1:
                    complexity = Complexity.ONE_TO_MANY
                elif len(unique_targets) == 1 and is_n_to_1:
                    complexity = Complexity.MANY_TO_ONE
                else:
                    complexity = Complexity.MANY_TO_MANY

            for match in matches:
                match_complexity = match.get('complexity', '')

                if isinstance(match_complexity, Complexity):
                    pass
                elif isinstance(match_complexity, str) and match_complexity.strip():
                    complexity_value = match_complexity.strip()

                    try:
                        match_complexity = Complexity(complexity_value)
                    except ValueError:
                        try:
                            match_complexity = Complexity[complexity_value.upper()]
                        except KeyError:
                            match_complexity = complexity_value
                else:
                    match_complexity = None

                if match_complexity and match_complexity != complexity:
                    match_complexity_value = str(match_complexity.value if isinstance(match_complexity, Complexity) else match_complexity)

                    if self.verbose:
                        log_warn(f"Complexity Diverged from Mapping Table for Rule #{rule_id} (`{old_ns}.{old_cls}`): Mapping Table has '{match_complexity_value}', got '{complexity.value}'.")

            match_mappings = [
                MatchMapping(
                    old_namespace=match['old_namespace'],
                    old_class_interface=match['old_class_interface'],
                    old_member=match['old_member'],
                    old_signature=match['old_signature'],
                    new_namespace=match['new_namespace'],
                    new_class_interface=match['new_class_interface'],
                    new_member=match['new_member'],
                    new_signature=match['new_signature'],
                    additional_notes=match['additional_notes']
                )
                for match in matches
            ]

            rule = MigrationRule(
                rule_id=rule_id,
                complexity=complexity,
                old_namespace=old_ns,
                old_class_interface=old_cls,
                old_member=old_mem,
                matches=match_mappings
            )

            rules.append(rule)

        if self.verbose:
            log_info(f"Generated {len(rules)} Rule Block(s) From {len(matched_rows)} Rows.")

        return {"rules": rules}


    def plan_migration(self, state: MigrationState) -> dict:
        if self.verbose:
            log_info(f"Generating Migration Plan...")

        rules = state["rules"]
        user_comments = state.get("user_comments", "")
        priority_sections = state.get("priority_sections", [])

        priority_summary = ""
        if priority_sections:
            items = []
            for p in priority_sections:
                if p['severity'] == 'DONT_TOUCH':
                    items.append(f"- [DONT_TOUCH / IMMUTABLE] Range `{p['range_raw']}`: `{p['snippet']}` (MUST REMAIN VERBATIM)")
                else:
                    items.append(f"- [{p['severity']}] Range `{p['range_raw']}`: `{p['snippet']}`")
            
            priority_summary = "\n".join(items)

        formatted_rules = "\n\n".join([rule.serialize() for rule in rules])

        system_prompt, user_prompt = get_migration_planner_prompt(
            language=state.get("language", "generic"),
            legacy_code_snippet=state["current_code"],
            formatted_rules=formatted_rules if rules else "No Matching Rule(s).",
            priority_summary=priority_summary,
            user_comments=user_comments
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        plan_data: MigrationPlanSchema = self.planner.invoke(messages)

        formatted_plan = f"Overview: {plan_data.overview}\n\n"
        for step in plan_data.steps:
            formatted_plan += f"{step.step_number}. [{step.cardinality}] {step.title}: {step.description}\n"

        if self.verbose:
            log_info(f"Planned {len(plan_data.steps)} Total Steps.")

        return {"plan": formatted_plan}


    def generate_migration(self, state: MigrationState) -> dict:
        attempt = state.get("attempt", 0) + 1

        if self.verbose:
            log_info(f"Migrating Source Code... (Attempt {attempt})")

        rules = state["rules"]
        legacy_code = state["legacy_code"]
        current_code = state["current_code"]
        language = state.get("language", "python")
        plan = state.get("plan", "")
        user_comments = state.get("user_comments", "")
        priority_sections = state.get("priority_sections", [])
        validation_error = state.get("validation_error", "")

        formatted_rules = "\n\n".join([rule.serialize() for rule in rules]) if rules else 'No Matching Rule(s).'

        priority_summary = ""

        if priority_sections:
            items = []

            for p in priority_sections:
                if p['severity'] == 'DONT_TOUCH':
                    items.append(f"- [DONT_TOUCH / IMMUTABLE] Range `{p['range_raw']}`: `{p['snippet']}` (MUST REMAIN VERBATIM)")
                else:
                    items.append(f"- [{p['severity']}] Range `{p['range_raw']}`: `{p['snippet']}`")

            priority_summary = "\n".join(items)

        system_prompt, user_prompt = get_migration_prompt(
            language=language,
            legacy_code_snippet=legacy_code,
            formatted_rules=formatted_rules,
            migration_plan=plan,
            user_comments=user_comments,
            priority_summary=priority_summary,
            validation_error=validation_error or ""
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response_dict = self.migrator.invoke(messages)
        raw_message = response_dict["raw"]
        result: MigrationOutputSchema = response_dict["parsed"]

        migrated_code = result.migrated_code
        applied_rules = []
        for applied_rule in result.applied_rules:
            for rule in rules:
                if rule.rule_id == applied_rule.rule_id:
                    applied_rules.append(
                        {
                            "applied_rule": rule,
                            "operations": applied_rule.operations,
                            "input_snippet": applied_rule.input_snippet,
                            "output_snippet": applied_rule.output_snippet
                        }
                    )

        raw_text = raw_message.content if isinstance(raw_message.content, str) else ""
        token_logprobs: List[TokenLogprob] = []

        if hasattr(raw_message, "response_metadata") and "logprobs" in raw_message.response_metadata and raw_message.response_metadata["logprobs"]:
            content_logprobs = raw_message.response_metadata["logprobs"].get("content", [])
            
            # 1. Build cumulative byte map for raw LLM token stream
            raw_tokens_with_offsets = []
            curr_raw_byte = 0

            for item in content_logprobs:
                if "logprob" in item and "token" in item:
                    tok_str = item["token"]
                    tok_bytes = len(tok_str.encode("utf8"))
                    start_b = curr_raw_byte
                    end_b = start_b + tok_bytes
                    curr_raw_byte = end_b
                    
                    raw_tokens_with_offsets.append({
                        "token": tok_str,
                        "logprob": item["logprob"],
                        "start_byte": start_b,
                        "end_byte": end_b
                    })

            # 2. Convert migrated_code into its exact JSON-escaped representation
            # json.dumps(x)[1:-1] turns literal '\n' into '\\n' and '"' into '\"'
            escaped_migrated_code = json.dumps(migrated_code)[1:-1]
            
            escaped_bytes = escaped_migrated_code.encode("utf8")
            raw_bytes = raw_text.encode("utf8")
            
            start_in_raw = raw_bytes.find(escaped_bytes)

            # Fallback: if JSON string dumping still misses by 1 character, search for key prefix
            if start_in_raw == -1:
                key_prefix = '"migrated_code": "'.encode("utf8")
                key_pos = raw_bytes.find(key_prefix)

                if key_pos != -1:
                    start_in_raw = key_pos + len(key_prefix)

            if start_in_raw != -1:
                end_in_raw = start_in_raw + len(escaped_bytes)
                migrated_code_utf8_len = len(migrated_code.encode("utf8"))

                # 3. Filter tokens that fall within the escaped code boundaries
                for tok in raw_tokens_with_offsets:
                    if tok["end_byte"] > start_in_raw and tok["start_byte"] < end_in_raw:
                        # Re-base offsets to 0 matching start of migrated_code
                        raw_offset_start = max(0, tok["start_byte"] - start_in_raw)
                        raw_offset_end = min(len(escaped_bytes), tok["end_byte"] - start_in_raw)
                        
                        # Scale byte position to unescaped migrated_code bounds
                        scale = migrated_code_utf8_len / len(escaped_bytes) if len(escaped_bytes) > 0 else 1.0
                        aligned_start = int(raw_offset_start * scale)
                        aligned_end = int(raw_offset_end * scale)

                        token_logprobs.append(
                            TokenLogprob(
                                token=tok["token"],
                                logprob=tok["logprob"],
                                start_byte=aligned_start,
                                end_byte=aligned_end
                            )
                        )
            else:
                if self.verbose:
                    log_warn(f"Could Not Exact-Match Migrated Code Byte Offsets In Raw LLM Stream.")

        changelog_entry = {
            "attempt": attempt,
            "rules_applied_count": len(applied_rules),
            "applied_rules": applied_rules,
            "had_user_comments": bool(user_comments.strip()),
            "validation_passed": False
        }

        updated_changelog = state.get("changelog", []) + [changelog_entry]

        if self.verbose:
            log_info(f"Completed Source Code Migration (Attempt {attempt}). Got {len(token_logprobs)} Structured Token Logprob(s) & Emitted {len(applied_rules)} Applied Rule Mapping(s).")

        return {
            "previous_code": current_code,
            "current_code": migrated_code,
            "applied_rules": applied_rules,
            "current_logprobs": token_logprobs,
            "attempt": attempt,
            "validation_error": None,
            "changelog": updated_changelog
        }


    def validate_code(self, state: MigrationState) -> dict:
        """
        Validates code by evaluating applied rule snippets directly against exact substring offsets 
        in current_code, token logprobs, schema rule compliance, and inspecting for syntax errors.
        """

        attempt = state.get("attempt", 1)

        if self.verbose:
            log_info(f"Validating Migrated Source Code... (Attempt {attempt})")

        language = state["language"]
        current_code = state["current_code"]
        mapping_table = state["mapping_table"]
        applied_rules = state.get("applied_rules", [])
        current_logprobs = state.get("current_logprobs")

        # 1. Parse Current Code strictly to detect syntax errors
        curr_parser = SmartParser(
            current_code,
            detector=self.detector,
            analyzer=self.analyzer,
            inferer=self.inferer,
            language=language,
            verbose=self.verbose
        )

        curr_parser.parse()
        self._parser_timeline.append(curr_parser)

        # 2. Evaluate Rule Snippets & Code Syntax
        confidence_report: GlobalConfidenceReport = DynamicConfidenceEvaluator.evaluate_migration_rules(
            applied_rules=applied_rules,
            migrated_code=current_code,
            all_syntax_errors=curr_parser.get_syntax_errors(),
            mapping_table=mapping_table,
            attempts_taken=attempt,
            token_logprobs=current_logprobs,
            verbose=self.verbose
        )

        snapshot = {
            "attempt": attempt,
            "code": current_code,
            "confidence": confidence_report,
            "applied_rules_count": len(applied_rules)
        }

        updated_history = state.get("history", []) + [snapshot]
        changelog = state.get("changelog", [])

        if self.verbose:
            log_info(f"Confidence Score (Attempt {attempt}): {confidence_report.score:.2f}")

        # 3. Handle Validation Errors & Feedback Generation
        errors: List[str] = []

        if confidence_report.score == 0.0:
            syntax_errs: List[ASTSyntaxError] = curr_parser.get_syntax_errors()
            if syntax_errs:
                syntax_msg = "\n".join(
                    [f"- Line {err.range.start_line}, Column {err.range.start_column}: {err.message}" for err in syntax_errs]
                )
                errors.append(f"Syntax Errors:\n{syntax_msg}")
            else:
                errors.append("Rule Snippet Validation Failure or Code Divergence.")

        leftover_symbols = confidence_report.diagnostics.leftover_legacy_symbols if confidence_report.diagnostics else []
        if leftover_symbols:
            errors.append(f"Legacy Symbols Detected: {', '.join(leftover_symbols)}")

        if errors:
            if changelog:
                changelog[-1]["validation_passed"] = False

            combined_error_msg = f"Validation Failure (Attempt {attempt}):\n" + "\n".join(errors)

            if self.verbose:
                log_error(combined_error_msg)

            return {
                "validation_error": combined_error_msg,
                "confidence_report": confidence_report,
                "history": updated_history
            }

        if changelog:
            changelog[-1]["validation_passed"] = True

        if self.verbose:
            log_info(f"Validation Succeeded (Attempt {attempt}).")

        return {
            "validation_error": None,
            "current_code": current_code,
            "changelog": changelog,
            "confidence_report": confidence_report,
            "history": updated_history
        }


    def migrate(
            self,
            legacy_code_snippet: str, 
            mapping_table: dict, 
            priority_sections: Optional[List[dict]] = None, 
            user_comments: Optional[str] = ""
    ) -> Dict[str, Any]:
        """
        Executes code migration pipeline and returns a structured dictionary output.
        """

        if self.verbose:
            log_info(f"Starting Source Code Migration Workflow...")

        self._parser_timeline.clear()

        initial_state = {
            "language": "",
            "legacy_code": legacy_code_snippet,
            "current_code": legacy_code_snippet,
            "previous_code": legacy_code_snippet,
            "mapping_table": mapping_table,
            "user_comments": user_comments,
            "identifiers": [],
            "fully_qualified_identifiers": [],
            "external_contexts": {},
            "rules": [],
            "plan": "",
            "applied_rules": [],
            "changelog": [],
            "latest_signals": [],
            "validation_error": None,
            "confidence_report": None,
            "history": [],
            "attempt": 0,
            "max_attempts": self.max_attempts,
            "priority_sections": priority_sections or []
        }

        final_state = self.graph.invoke(initial_state)

        # Best-State Trajectory Selection
        history = final_state.get("history", [])
        if history:
            best_snapshot = max(
                history, 
                key=lambda x: x["confidence"].score if isinstance(x["confidence"], GlobalConfidenceReport) else 0.0
            )
            selected_code = best_snapshot["code"]
            selected_confidence = asdict(best_snapshot["confidence"]) if isinstance(best_snapshot["confidence"], GlobalConfidenceReport) else best_snapshot["confidence"]
            best_attempt_num = best_snapshot["attempt"]
            
            if self.verbose:
                log_info(f"Selecting Optimal Trajectory Result... Selected Attempt {best_attempt_num} with Confidence Score {selected_confidence.get('score', 0.0):.2f}.")
        else:
            selected_code = final_state["current_code"]
            raw_report = final_state.get("confidence_report")
            selected_confidence = asdict(raw_report) if isinstance(raw_report, GlobalConfidenceReport) else (raw_report or {})
            best_attempt_num = final_state.get("attempt", 1)
            
            if self.verbose:
                log_warn(f"No Trajectory History Found... Selecting Final Output.")

        output = {
            "migrated_code": selected_code,
            "confidence": selected_confidence,
            "audit_trail": {
                "language": final_state.get("language"),
                "total_attempts_executed": final_state.get("attempt"),
                "selected_best_attempt": best_attempt_num,
                "migration_plan": final_state.get("plan"),
                "changelog": final_state.get("changelog"),
                "priority_sections_processed": final_state.get("priority_sections")
            }
        }

        return to_json(output)