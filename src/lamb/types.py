from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import List, Optional


class Complexity(StrEnum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"
    AMBIGUOUS = "AMBIGUOUS"
    DEPRECATED = "DEPRECATED"


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
class MatchMapping:
    old_namespace: str = ""
    old_class_interface: str = ""
    old_member: str = ""
    old_signature: str = ""
    new_namespace: str = ""
    new_class_interface: str = ""
    new_member: str = ""
    new_signature: str = ""
    additional_notes: str = ""


@dataclass
class MigrationRule:
    rule_id: int
    complexity: Complexity
    old_namespace: str
    old_class_interface: str
    old_member: str = ""
    matches: List[MatchMapping] = field(default_factory=list)

    def serialize(self) -> str:
        target_identity = f"`{self.old_namespace}.{self.old_class_interface}`"
        if self.old_member:
            target_identity += f" -> `{self.old_member}`"

        comp_val = self.complexity.value if hasattr(self.complexity, 'value') else str(self.complexity)
        rule_block = f"Rule ID: {self.rule_id} | Cardinality: [{comp_val}] | Target: {target_identity}\n"

        for m in self.matches:
            has_target = any([m.new_namespace, m.new_class_interface, m.new_member])

            if self.complexity == Complexity.DEPRECATED or not has_target:
                rule_block += "- Target Destination: DEPRECATED / REMOVED (No replacement entity in target version)\n"
            else:
                dest = f"`{m.new_namespace}.{m.new_class_interface}`"
                if m.new_member:
                    dest += f" -> `{m.new_member}`"
                rule_block += f"- Target Destination: {dest}\n"

            if m.old_signature or m.new_signature:
                rule_block += f"  - Signature: `{m.old_signature}` -> `{m.new_signature}`\n"

            additional_notes = m.additional_notes
            if additional_notes:
                rule_block += f"  - Additional Notes: {additional_notes}\n"

        return rule_block.strip()


@dataclass
class ASTRange:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_byte: int
    end_byte: int


@dataclass
class ASTSyntaxError:
    error_id: int
    node_type: str
    scope_name: str
    message: str
    range: ASTRange
    node_text: str


@dataclass
class TokenLogprob:
    token: str
    logprob: float
    start_byte: int
    end_byte: int


@dataclass
class SnippetDiagnostics:
    syntax_errors: List[ASTSyntaxError] = field(default_factory=list)
    leftover_legacy_symbols: List[str] = field(default_factory=list)
    matched_target_symbols: List[str] = field(default_factory=list)
    schema_coverage_ratio: float = 0.0
    snippet_logprob_mass: float = 0.80
    tokens_in_snippet: int = 0


@dataclass
class RuleConfidenceScore:
    rule_id: int
    description: str
    operations: str
    range: ASTRange
    score: float
    level: ConfidenceLevel
    status: EvaluationStatus
    reason: str
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
    reason: str
    rule_scores: List[RuleConfidenceScore] = field(default_factory=list)
    diagnostics: Optional[GlobalDiagnostics] = None