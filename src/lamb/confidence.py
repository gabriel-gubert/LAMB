import math
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Set, Optional, Union, Dict, Any, Tuple

from .smart_parser import ASTSyntaxError, ASTRange
from .output_templates import AppliedRuleMapping


# =========================================================================
# ENUMS & REPORT DATACLASSES
# =========================================================================

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    ZERO = "ZERO (Syntax Errors Detected / Divergence)"


class EvaluationStatus(str, Enum):
    AUTO_APPROVED = "AUTO-APPROVED"
    NEEDS_MANUAL_REVIEW = "NEEDS MANUAL REVIEW"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


@dataclass
class TokenLogprob:
    """Represents a token's log probability alongside its byte offsets in generated code."""
    token: str
    logprob: float
    start_byte: int
    end_byte: int


@dataclass
class SnippetDiagnostics:
    leftover_legacy_symbols: List[str] = field(default_factory=list)
    matched_target_symbols: List[str] = field(default_factory=list)
    schema_coverage_ratio: float = 0.0
    snippet_logprob_mass: float = 0.80
    tokens_in_snippet: int = 0


@dataclass
class RuleConfidenceScore:
    rule_id: int
    operation: str
    range: ASTRange
    score: float
    level: ConfidenceLevel
    status: EvaluationStatus
    input_snippet: str
    output_snippet: str
    diagnostics: SnippetDiagnostics


@dataclass
class GlobalDiagnostics:
    attempts_taken: int
    retry_penalty_factor: float
    total_rules_applied: int
    total_syntax_errors: int
    syntax_errors: List[ASTSyntaxError] = field(default_factory=list)
    leftover_legacy_symbols: List[str] = field(default_factory=list)
    matched_target_symbols: List[str] = field(default_factory=list)


@dataclass
class GlobalConfidenceReport:
    score: float
    level: ConfidenceLevel
    status: EvaluationStatus
    rule_scores: List[RuleConfidenceScore] = field(default_factory=list)
    diagnostics: Optional[GlobalDiagnostics] = None


# =========================================================================
# EVALUATOR CLASS
# =========================================================================

class DynamicConfidenceEvaluator:
    """
    Computes global and rule-snippet granular confidence scores. 
    Uses the parser strictly to inspect the presence of syntax errors.
    """

    @staticmethod
    def _dempster_combine(m1: float, m2: float) -> float:
        return m1 + m2 - (m1 * m2)

    @classmethod
    def _calculate_snippet_logprob_mass(
        cls, 
        snippet_range: ASTRange, 
        token_logprobs: Optional[List[TokenLogprob]]
    ) -> Tuple[float, int]:
        """
        Filters tokens that fall within the byte span of the rule's output snippet 
        and calculates snippet-specific logprob evidence mass using geometric mean.
        """
        if not token_logprobs:
            return 0.75, 0

        snippet_tokens = [
            t.logprob for t in token_logprobs
            if t.start_byte >= snippet_range.start_byte and t.end_byte <= snippet_range.end_byte
        ]

        if not snippet_tokens:
            return 0.75, 0

        geom_mean_prob = math.exp(sum(snippet_tokens) / len(snippet_tokens))
        return round(geom_mean_prob * 0.85, 3), len(snippet_tokens)

    @staticmethod
    def _ranges_overlap(r1: ASTRange, r2: ASTRange) -> bool:
        """Checks whether two byte ranges overlap."""
        return not (r1.end_byte <= r2.start_byte or r1.start_byte >= r2.end_byte)

    @staticmethod
    def _locate_snippet_exact_range(migrated_code: str, snippet: str) -> Optional[ASTRange]:
        """
        Locates the exact byte, line, and column range of a snippet within migrated_code.
        Returns None if snippet does not exist in migrated_code (Divergence).
        """
        snippet_clean = snippet.strip()
        if not snippet_clean or snippet_clean not in migrated_code:
            return None

        # Byte offsets
        code_bytes = migrated_code.encode("utf8")
        snip_bytes = snippet_clean.encode("utf8")
        start_byte = code_bytes.find(snip_bytes)
        end_byte = start_byte + len(snip_bytes)

        # Line and Column offsets (1-indexed lines, 0-indexed columns)
        char_idx = migrated_code.find(snippet_clean)
        start_line = migrated_code[:char_idx].count('\n') + 1
        
        last_nl = migrated_code[:char_idx].rfind('\n')
        start_column = char_idx if last_nl == -1 else char_idx - (last_nl + 1)

        end_line = start_line + snippet_clean.count('\n')
        snip_last_nl = snippet_clean.rfind('\n')
        if snip_last_nl != -1:
            end_column = len(snippet_clean) - (snip_last_nl + 1)
        else:
            end_column = start_column + len(snippet_clean)

        return ASTRange(
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
            start_byte=start_byte,
            end_byte=end_byte
        )

    @classmethod
    def score_single_rule(
        cls,
        rule_mapping: AppliedRuleMapping,
        migrated_code: str,
        all_syntax_errors: List[ASTSyntaxError],
        old_symbols: Set[str],
        new_symbols: Set[str],
        retry_decay: float,
        token_logprobs: Optional[List[TokenLogprob]] = None,
        verbose: bool = True
    ) -> RuleConfidenceScore:
        """
        Evaluates an individual AppliedRuleMapping snippet directly against migrated_code.
        """
        # 1. Exact string assertion inside migrated_code
        snippet_range = cls._locate_snippet_exact_range(migrated_code, rule_mapping.output_snippet)

        if not snippet_range:
            if verbose:
                print(
                    f"[/!\\] Divergence Detected For Rule ID {rule_mapping.rule_id}: "
                    f"Output Snippet '{rule_mapping.output_snippet[:40]}...' Not Found In Migrated Code.",
                    file=sys.stderr
                )
            
            fallback_range = ASTRange(
                start_line=1, start_column=0, end_line=1, end_column=1,
                start_byte=0, end_byte=1
            )
            return RuleConfidenceScore(
                rule_id=rule_mapping.rule_id,
                operation="DIVERGENCE_ERROR",
                range=fallback_range,
                score=0.0,
                level=ConfidenceLevel.ZERO,
                status=EvaluationStatus.REJECTED,
                input_snippet=rule_mapping.input_snippet,
                output_snippet=rule_mapping.output_snippet,
                diagnostics=SnippetDiagnostics(
                    leftover_legacy_symbols=[],
                    matched_target_symbols=[],
                    schema_coverage_ratio=0.0,
                    snippet_logprob_mass=0.0,
                    tokens_in_snippet=0
                )
            )

        # 2. Check for intersecting syntax errors
        rule_syntax_errors = [
            err for err in all_syntax_errors
            if cls._ranges_overlap(err.range, snippet_range)
        ]

        if rule_syntax_errors:
            err_msg = rule_syntax_errors[0].message
            return RuleConfidenceScore(
                rule_id=rule_mapping.rule_id,
                operation="SYNTAX_ERROR",
                range=snippet_range,
                score=0.0,
                level=ConfidenceLevel.ZERO,
                status=EvaluationStatus.REJECTED,
                input_snippet=rule_mapping.input_snippet,
                output_snippet=rule_mapping.output_snippet,
                diagnostics=SnippetDiagnostics(
                    leftover_legacy_symbols=[],
                    matched_target_symbols=[],
                    schema_coverage_ratio=0.0,
                    snippet_logprob_mass=0.0,
                    tokens_in_snippet=0
                )
            )

        # 3. Compliance Check: Inspect symbols in input and output snippets
        out_tokens = set(rule_mapping.output_snippet.replace("(", " ").replace(")", " ").replace(".", " ").split())
        in_tokens = set(rule_mapping.input_snippet.replace("(", " ").replace(")", " ").replace(".", " ").split())

        leftover_legacy = in_tokens.intersection(old_symbols).intersection(out_tokens)
        matched_targets = out_tokens.intersection(new_symbols)

        if leftover_legacy and not matched_targets:
            legacy_ceiling = max(0.10, 0.40 - (len(leftover_legacy) * 0.15))
        else:
            legacy_ceiling = 1.0

        # Observer 1: Target Schema Compliance Ratio
        target_ratio = (len(matched_targets) / len(new_symbols)) if new_symbols else 1.0
        m1_schema = 0.85 * target_ratio

        # Observer 2: Granular Snippet Token Logprob Evidence Mass
        m2_logprob, token_count = cls._calculate_snippet_logprob_mass(
            snippet_range=snippet_range,
            token_logprobs=token_logprobs
        )

        # Dempster-Shafer Combination
        m_combined = cls._dempster_combine(m1_schema, m2_logprob)

        final_score = min(legacy_ceiling, m_combined * retry_decay)
        final_score = round(final_score, 3)

        if final_score >= 0.85:
            level = ConfidenceLevel.HIGH
            status = EvaluationStatus.AUTO_APPROVED
        elif final_score >= 0.60:
            level = ConfidenceLevel.MEDIUM
            status = EvaluationStatus.NEEDS_MANUAL_REVIEW
        else:
            level = ConfidenceLevel.LOW
            status = EvaluationStatus.FLAGGED

        return RuleConfidenceScore(
            rule_id=rule_mapping.rule_id,
            operation="RULE_APPLIED",
            range=snippet_range,
            score=final_score,
            level=level,
            status=status,
            input_snippet=rule_mapping.input_snippet,
            output_snippet=rule_mapping.output_snippet,
            diagnostics=SnippetDiagnostics(
                leftover_legacy_symbols=list(leftover_legacy),
                matched_target_symbols=list(matched_targets),
                schema_coverage_ratio=round(target_ratio, 3),
                snippet_logprob_mass=m2_logprob,
                tokens_in_snippet=token_count
            )
        )

    @classmethod
    def evaluate_migration_rules(
        cls,
        applied_rules: List[AppliedRuleMapping],
        migrated_code: str,
        all_syntax_errors: List[ASTSyntaxError],
        mapping_table: List[Union[Dict[str, Any], Any]],
        attempts_taken: int,
        token_logprobs: Optional[List[TokenLogprob]] = None,
        verbose: bool = True
    ) -> GlobalConfidenceReport:
        """
        Evaluates confidence scores strictly for applied rule snippets and overall code syntax.
        """
        # GATE 1: Global syntax error rejection
        if all_syntax_errors:
            error_rule_scores = [
                RuleConfidenceScore(
                    rule_id=err.error_id,
                    operation="SYNTAX_ERROR",
                    range=err.range,
                    score=0.0,
                    level=ConfidenceLevel.ZERO,
                    status=EvaluationStatus.REJECTED,
                    input_snippet="[SYNTAX ERROR]",
                    output_snippet=err.node_text,
                    diagnostics=SnippetDiagnostics(
                        leftover_legacy_symbols=[],
                        matched_target_symbols=[],
                        schema_coverage_ratio=0.0,
                        snippet_logprob_mass=0.0,
                        tokens_in_snippet=0
                    )
                )
                for err in all_syntax_errors
            ]

            return GlobalConfidenceReport(
                score=0.0,
                level=ConfidenceLevel.ZERO,
                status=EvaluationStatus.REJECTED,
                rule_scores=error_rule_scores,
                diagnostics=GlobalDiagnostics(
                    attempts_taken=attempts_taken,
                    retry_penalty_factor=round(max(0.60, 1.0 - ((attempts_taken - 1) * 0.10)), 2),
                    total_rules_applied=len(applied_rules),
                    total_syntax_errors=len(all_syntax_errors),
                    syntax_errors=all_syntax_errors,
                    leftover_legacy_symbols=[],
                    matched_target_symbols=[]
                )
            )

        # Extract symbols from mapping table
        old_symbols: Set[str] = set()
        new_symbols: Set[str] = set()

        for record in mapping_table:
            if isinstance(record, dict):
                old_ns = record.get("old_namespace", "") or ""
                old_cls = record.get("old_class_interface", "") or ""
                old_mem = record.get("old_member", "") or ""
                new_ns = record.get("new_namespace", "") or ""
                new_cls = record.get("new_class_interface", "") or ""
                new_mem = record.get("new_member", "") or ""
            else:
                old_ns = getattr(record, "old_namespace", "") or ""
                old_cls = getattr(record, "old_class_interface", None) or ""
                old_mem = getattr(record, "old_member", None) or ""
                new_ns = getattr(record, "new_namespace", "") or ""
                new_cls = getattr(record, "new_class_interface", None) or ""
                new_mem = getattr(record, "new_member", None) or ""

            if old_cls: old_symbols.add(str(old_cls))
            if old_mem: old_symbols.add(str(old_mem))
            if new_cls: new_symbols.add(str(new_cls))
            if new_mem: new_symbols.add(str(new_mem))

            old_path = ".".join(filter(None, [str(old_ns), str(old_cls), str(old_mem)]))
            new_path = ".".join(filter(None, [str(new_ns), str(new_cls), str(new_mem)]))

            if old_path: old_symbols.add(old_path)
            if new_path: new_symbols.add(new_path)

        retry_decay = max(0.60, 1.0 - ((attempts_taken - 1) * 0.10))

        rule_scores: List[RuleConfidenceScore] = []
        all_leftover_legacy: Set[str] = set()
        all_matched_targets: Set[str] = set()

        for rule in applied_rules:
            r_score = cls.score_single_rule(
                rule_mapping=rule,
                migrated_code=migrated_code,
                all_syntax_errors=all_syntax_errors,
                old_symbols=old_symbols,
                new_symbols=new_symbols,
                retry_decay=retry_decay,
                token_logprobs=token_logprobs,
                verbose=verbose
            )
            rule_scores.append(r_score)

            all_leftover_legacy.update(r_score.diagnostics.leftover_legacy_symbols)
            all_matched_targets.update(r_score.diagnostics.matched_target_symbols)

        if not rule_scores:
            global_score = 1.0
        else:
            avg_score = sum(r.score for r in rule_scores) / len(rule_scores)

            if all_leftover_legacy:
                global_ceiling = max(0.10, 0.40 - (len(all_leftover_legacy) * 0.15))
            else:
                global_ceiling = 1.0

            global_score = min(global_ceiling, avg_score)

        global_score = round(global_score, 3)

        if global_score >= 0.85:
            global_level = ConfidenceLevel.HIGH
            global_status = EvaluationStatus.AUTO_APPROVED
        elif global_score >= 0.60:
            global_level = ConfidenceLevel.MEDIUM
            global_status = EvaluationStatus.NEEDS_MANUAL_REVIEW
        else:
            global_level = ConfidenceLevel.LOW
            global_status = EvaluationStatus.FLAGGED

        return GlobalConfidenceReport(
            score=global_score,
            level=global_level,
            status=global_status,
            rule_scores=rule_scores,
            diagnostics=GlobalDiagnostics(
                attempts_taken=attempts_taken,
                retry_penalty_factor=round(retry_decay, 2),
                total_rules_applied=len(rule_scores),
                total_syntax_errors=0,
                syntax_errors=[],
                leftover_legacy_symbols=list(all_leftover_legacy),
                matched_target_symbols=list(all_matched_targets)
            )
        )