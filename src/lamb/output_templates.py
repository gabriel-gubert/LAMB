from typing import List

from pydantic import BaseModel, Field

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
    additional_notes: str = Field(default="", description="Markdown compliant notes for complex migrations or deprecations. Empty if direct match.")

class ResolvedItem(BaseModel):
    v1_element: APIElement = Field(
        ..., 
        description="The original legacy element being evaluated."
    )
    decision: str = Field(
        ..., 
        description="The classification of the mapping relationship."
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