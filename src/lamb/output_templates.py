from enum import Enum
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import tree_sitter_language_pack as tslp

# ---------------------------------------------------------------------------
# 1. API Extraction & Discovery Schemas
# ---------------------------------------------------------------------------

class APIElement(BaseModel):
    namespace: str = Field(default="", description="Namespace, package, or module name.")
    class_or_interface: str = Field(default="", description="Class, Interface, or Struct name.")
    member: str = Field(default="", description="Method, function, property, or constant name.")
    signature: str = Field(default="", description="Full signature (e.g., param types, return type, URL path).")
    summary: str = Field(default="", description="Brief description of behavior.")


class ElementsExtraction(BaseModel):
    elements: List[APIElement]


class MappingRow(BaseModel):
    old_namespace: str = Field(default="")
    old_class_interface: str = Field(default="")
    old_member: str = Field(default="")
    old_signature: str = Field(default="")
    new_namespace: str = Field(default="")
    new_class_interface: str = Field(default="")
    new_member: str = Field(default="")
    new_signature: str = Field(default="")
    complexity: str = Field(default="")
    additional_notes: str = Field(
        default="", 
        description="Markdown compliant notes for complex migrations or deprecations. Empty if direct match."
    )


class ResolvedItem(BaseModel):
    v1_element: APIElement = Field(
        ..., 
        description="The original legacy element being evaluated."
    )
    selected_targets: List[APIElement] = Field(
        default_factory=list, 
        description=(
            "The selected target(s). 1 item for 1:1 or N:1. "
            "Multiple items for 1:N or N:N. "
            "Top 3 choices for ambiguous mappings. Empty list if deprecated."
        )
    )
    reason: str = Field(
        default="", 
        description=(
            "Detailed Markdown notes explaining why specific target elements "
            "were selected for the legacy element. For each item in "
            "selected_targets, the model must provide at least one valid technical reason for its "
            "inclusion in the final mapping."
        )
    )


class ResolutionResult(BaseModel):
    resolved_items: List[ResolvedItem]


class DirectoryDiscovery(BaseModel):
    directories: List[str] = Field(
        ...,
        description="List of absolute paths to directories most likely to contain API reference documentation or source code."
    )


AvailableLanguages = Enum(
    "AvailableLanguages",
    {lang: lang for lang in tslp.available_languages()}
)

class Language(BaseModel):
    language: AvailableLanguages = Field(
        description="The target programming language identifier supported by tree-sitter."
    )


class SymbolIdentifier(BaseModel):
    name: str = Field(
        description="The literal name of the symbol as referenced in the code (e.g., 'List', 'process_users', 'DataFrame', 'activeOrders')."
    )
    kind: str = Field(
        description="The category of the symbol: 'TYPE', 'FUNCTION', 'METHOD', or 'PROPERTY'."
    )
    fully_qualified_name: Optional[str] = Field(
        default=None,
        description="The inferred fully qualified name of the symbol, if applicable (e.g., 'java.util.List', 'pandas.DataFrame')."
    )


class ParserResult(BaseModel):
    identifiers: List[SymbolIdentifier] = Field(
        default_factory=list,
        description="A comprehensive list of all types, functions, methods, and properties encountered or referenced in the code snippet."
    )


class ExternalVariableInference(BaseModel):
    variable_name: str = Field(
        description="The name of the external/undeclared variable."
    )
    accessed_attributes: List[str] = Field(
        default_factory=list,
        description="Attributes or properties accessed on this variable (e.g., ['id', 'name'])."
    )
    invoked_methods: List[str] = Field(
        default_factory=list,
        description="Methods called on this variable (e.g., ['get_status', 'save'])."
    )
    status: str = Field(
        description="Inference status: 'INFERRED', 'AMBIGUOUS', 'UNKNOWN', or 'UNRESOLVED'."
    )
    inferred_type: Optional[str] = Field(
        default=None,
        description="The inferred class/interface name or fully qualified type."
    )
    schema_type: Optional[str] = Field(
        default=None,
        description="If a mapping schema was provided, indicates 'LEGACY' or 'NEW' match."
    )


class TypeInferenceResult(BaseModel):
    external_variables: List[ExternalVariableInference] = Field(
        default_factory=list,
        description="List of all undeclared external variables and their inferred types/usage contexts."
    )


class RefactoringStep(BaseModel):
    step_number: int = Field(description="Sequential step number.")
    title: str = Field(description="Short title of the refactoring step.")
    description: str = Field(description="Detailed explanation of code changes.")
    cardinality: Literal["1:1", "1:N", "N:1", "N:N"] = Field(description="Mapping type applied.")
    target_symbols: List[str] = Field(description="Symbols or functions affected by this step.")


class MigrationPlanSchema(BaseModel):
    overview: str = Field(description="High-level architectural summary of the migration.")
    steps: List[RefactoringStep] = Field(description="Ordered refactoring steps.")


class AppliedRuleMapping(BaseModel):
    rule_id: int = Field(
        ...,
        description="The unique numerical ID of the migration rule that was applied."
    )
    input_snippet: str = Field(
        ...,
        description="The exact snippet or line from the legacy source code affected by this rule."
    )
    output_snippet: str = Field(
        ...,
        description="The exact transformed snippet or line generated in the migrated code by this rule."
    )


class MigrationOutputSchema(BaseModel):
    migrated_code: str = Field(
        ..., 
        description="The complete, valid, executable refactored code without markdown code block fences."
    )
    applied_rules: List[AppliedRuleMapping] = Field(
        default_factory=list, 
        description="Granular mappings tracking each applied rule ID alongside its source input snippet and transformed output snippet."
    )