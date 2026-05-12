from .types import Complexity

def get_dynamic_detection_prompt(supported_langs: list[str] = None) -> str:
    """
    Generates a prompt containing the actual supported tree-sitter names.
    This ensures the LLM picks a valid key for tslp.get_language().
    """

    lang_list_str = ", ".join(supported_langs)

    return f"""
### ROLE & OBJECTIVE
You are a code classifier. Identify the programming language of the snippet below.

### INSTRUCTIONS & GUIDELINES
Choose ONLY from this list: [{lang_list_str}].

### OUTPUT FORMATTING
You MUST respond with ONLY the exact canonical name used by tree-sitter.
Do not include quotes, markdown formatting, or explanations.

### EXAMPLES

**Input:**

```
class DataProcessor:
    def __init__(self, data):
        self.data = data

    def clean(self):
        return [d.strip() for d in self.data if d]
```

**Output:** python

---

**Input:**

```
interface User {{
  id: number;
  name: string;
}}

const greet = (user: User): string => {{
  return `Hello, ${{user.name}}!`;
}};
```

**Output:** typescript

---

**Input:**

```
#include <stdio.h>
#include <stdlib.h>

int main() {{
    int *ptr = malloc(sizeof(int) * 5);
    if (ptr == NULL) return 1;
    free(ptr);
    return 0;
}}
```

**Output:** c

### INPUT DATA
""".strip()


def get_summarization_prompt() -> str:
    """Constructs the summarization prompt for API documentation."""
    return """
### ROLE & OBJECTIVE
You are an expert developer specializing in migrating scripts and tools from an old version to a new version. Your sole function is to process the provided technical documentation about a specific API object or method and generate a summary focused **exclusively on the differences** between its implementation in the old and new versions.

### INSTRUCTIONS & GUIDELINES
*   **Focus on Comparison:** Generate a summary that clearly outlines the differences, behavioral changes, deprecations, and new functionalities between the legacy and current versions of the API element described in the text.
*   **Retain Code and Examples:** You must copy all source code blocks and inline code snippets verbatim into the appropriate section of your summary.

### OUTPUT FORMATTING
*   **Structure the Output:** To ensure clarity, organize your summary using the following markdown headings:
    * `## Overview`: A one-sentence description of the API's purpose.
    * `## Old Implementation`: A brief on its usage and behavior in the old version.
    * `## New Implementation`: A brief on its usage and behavior in the new version.
    * `## Key Differences & Migration Notes`: A bulleted list detailing the specific changes a developer must know to migrate code.
*   **Final Response:** Your response must consist **only** of the final, structured summary. Do not add any conversational text like "Here is your summary."

### EXAMPLES
None.

### INPUT DATA
""".strip()


def get_migration_prompt(language: str, legacy_code_snippet: str, formatted_rules: str, verbose: bool) -> str:
    """Constructs the full migration prompt with conditional instructions."""
    
    instruction_4 = (
        "*   Your entire response MUST be a single markdown code block containing the migrated code. "
        "Within the code, add comments directly above or next to any line you modified from the original legacy code. "
        "Each comment must explain what was changed and why. Moreover, briefly explain the main changes to the code "
        "in a single paragraph after the code block. Do not add any introductory text or summaries before or after the code block."
        if verbose else
        "*   Your entire response MUST be a single markdown code block containing the migrated code. "
        "Do not add any introductory text, explanations, or summaries before or after the code block."
    )

    return f"""
### ROLE & OBJECTIVE
You are an expert developer specializing in migrating scripts and tools from an old version to a new version. Your task is to act as an intelligent code migrator, translating legacy legacy scripts to their modern current equivalents.

### INSTRUCTIONS & GUIDELINES
You will be given a snippet of legacy code and a set of `Applicable Migration Rules`. These rules have been extracted directly from the official legacy and current API documentations and are your primary source of truth. They MUST be prioritized over any general knowledge you may have.

*   Translate the legacy code logic to its current equivalent.
*   Strictly apply all provided migration rules. For example, if a rule says a legacy method is replaced by a current method, you must perform that replacement, if applicable to that piece of code.
*   If a rule indicates a legacy object is obsolete and has no direct replacement, add a new comment in the current code at the relevant line, like this: `' TODO: Current object "ObsoleteObjectName" is obsolete and requires manual review.`

### OUTPUT FORMATTING
{instruction_4}

### EXAMPLES
None.

### INPUT DATA
**Legacy Code to Migrate:**

```{language}
{legacy_code_snippet}
```

**Applicable Migration Rules:**

{formatted_rules}
""".strip()


def get_mapper_extraction_prompt():
    return """
### ROLE & OBJECTIVE
Analyze the provided file content and extract all structural API elements into a flat list of objects. 

### INSTRUCTIONS & GUIDELINES
- Extract classes, interfaces, structs, methods, properties, exported constants, functions, and REST API routes.
- Focus on public-facing contracts; ignore internal helper functions or private variables.
- Maintain technical precision in the signature to ensure accurate semantic matching.

### OUTPUT FORMATTING
Output a flat list of objects in the format below:

```python
[
  {
    "namespace": str,
    "class_or_interface": str, 
    "member": str, 
    "signature": str, 
    "summary": str 
  }
]
```

For each element, identify the following components:
*   **namespace**: The full package, namespace, or module path.
*   **class_or_interface**: The name of the containing class, interface, or struct. Use "Global" if none.
*   **member**: The name of the specific function, method, constant, or endpoint.
*   **signature**: The full technical signature (including name, parameters, return types, or HTTP verbs).
*   **summary**: A comprehensive extraction of all documentation (docstrings, comments, raw text) provided strictly and solely in Markdown format. You must transform any non-Markdown markup languages (such as HTML tags, XML, or Javadoc-style annotations) into their proper Markdown equivalents. Do not settle for a single sentence; use Markdown headers, bulleted lists, tables, and bold text to synthesize the full scope of behavior, including parameters, side effects, error handling, and business logic. Only include information explicitly stated in the source text, ensuring the final output is a clean, fully compliant Markdown block.
### EXAMPLES

```python
[
  {
    "namespace": "com.auth.service",
    "class_or_interface": "UserManager",
    "member": "validate_session",
    "signature": "validate_session(token: str) -> bool",
    "summary": "### Session Validation Logic\nVerifies the integrity and expiration of a JWT session token.\n- **Validation Steps**: Decodes the header, checks the signature against the public key, and verifies the `exp` claim.\n- **Returns**: `True` if valid; `False` if expired or malformed.\n- **Exceptions**: May throw `ConnectionError` if the Auth server is unreachable.\n"
  },
  {
    "namespace": "org.api.orders",
    "class_or_interface": "Global",
    "member": "POST /checkout",
    "signature": "async function createOrder(cart: CartItem[]): Promise<Order>",
    "summary": "### Order Creation Endpoint\nProcesses the final checkout for a user shopping cart.\n- **Logic**: Iterates through `CartItem` array to verify inventory levels.\n- **Persistence**: Creates a new record in the `Orders` table with a 'Pending' status.\n- **Side Effects**: Triggers a notification to the fulfillment service and clears the user's local session cache.\n"
  },
  {
    "namespace": "System.Data.Client",
    "class_or_interface": "IDbConnection",
    "member": "ConnectionString",
    "signature": "public string ConnectionString {{ get; set; }}",
    "summary": "### Connection Configuration\nGets or sets the string used to open a database connection.\n- **Format**: Expected to contain provider-specific keys (e.g., `Server`, `Database`, `User ID`).\n- **Security**: Must be encrypted at rest. Setting this property while the connection is open will throw an `InvalidOperationException`.\n"
  },
  {
    "namespace": "graphics::engine::vulkan",
    "class_or_interface": "Renderer",
    "member": "SubmitFrame",
    "signature": "void SubmitFrame(const FrameData* data, uint32_t timeout_ms)",
    "summary": "### Frame Submission Pipeline\nSubmits the recorded command buffers to the graphics queue for hardware execution.\n- **Synchronization**: Uses a fence to ensure the GPU has finished processing the previous frame before writing new data.\n- **Memory Management**: The `FrameData` pointer must remain valid until the submission call returns.\n- **Performance**: High-frequency call; should be invoked on the main render thread to minimize latency.\n"
  }
]
```

### INPUT DATA
""".strip()


def get_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert Systems Architect mapping Legacy API elements to a New version. Analyze the semantic relationship and functional intent between the legacy source and the potential candidates. You must select the correct target(s) and classify the relationship logic.

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```python
{{
  "v1_element": {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }},
  "potential_targets": [ {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }} ]
}}
```

**DECISION CLASSIFICATIONS:**
*   {Complexity.ONE_TO_ONE} - A clear, single replacement exists. Add exactly ONE target to 'selected_targets'.
*   {Complexity.ONE_TO_MANY} - The legacy element's functionality was split or expanded into multiple modern calls. Add MULTIPLE targets to 'selected_targets'.
*   {Complexity.MANY_TO_ONE} - Multiple legacy elements are being consolidated into this single modern element. Add exactly ONE target to 'selected_targets'.
*   {Complexity.MANY_TO_MANY} - A complex structural reorganization where multiple legacy elements map to a suite of new elements. Add MULTIPLE targets to 'selected_targets'.
*   {Complexity.AMBIGUOUS} - Multiple targets seem equally valid, but the source should logically only map to one. Add the top 2 candidates to 'selected_targets'.
*   {Complexity.DEPRECATED} - The legacy element has no valid replacement among the candidates or has been removed from the ecosystem. Leave 'selected_targets' empty [].

**CRITICAL RULES:**
*   For the 'reason' field, output ONLY valid Markdown.
*   Use the 'reason' field strictly to provide migration instructions for 1:N/N:N cases, explain consolidation for N:1, describe the conflict in AMBIGUOUS cases, or detail the DEPRECATED status.
*   Use the 'reason' field to explicitly provide at least one valid technical reason for the inclusion of each item in 'selected_targets' in the mapping, explaining how it relates to the original legacy element.
*   If the decision is a straightforward 1:1, output an empty string "" for the 'reason'. Do NOT use "N/A", "None", or "Unchanged".
*   If 'potential_targets' is empty, the decision MUST be DEPRECATED.

### OUTPUT FORMATTING
You must return a list of objects in the format below:

```python
[
  {{
    "v1_element": {{ ... }},
    "decision": "{"|".join([
        Complexity.ONE_TO_ONE, 
        Complexity.ONE_TO_MANY, 
        Complexity.MANY_TO_ONE, 
        Complexity.MANY_TO_MANY, 
        Complexity.AMBIGUOUS, 
        Complexity.DEPRECATED])}",
    "selected_targets": [ {{ ... }} ],
    "reason": "Markdown text or empty string"
  }}
]
```

### EXAMPLES

**Input:**

```python
{{
  "v1_element": {{
    "namespace": "com.legacy.io",
    "class_or_interface": "FileSystem",
    "member": "GetFreeSpace",
    "signature": "GetFreeSpace(path: String): Long",
    "summary": "Returns the number of unallocated bytes in the partition."
  }},
  "potential_targets": [
    {{
      "namespace": "org.modern.storage",
      "class_or_interface": "VolumeManager",
      "member": "QueryAvailableBytes",
      "signature": "QueryAvailableBytes(mountPoint: Path): UInt64",
      "summary": "Returns available storage capacity for the specified path."
    }}
  ]
}}
```

**Output:**

```python
{{
  "v1_element": {{
    "namespace": "com.legacy.io",
    "class_or_interface": "FileSystem",
    "member": "GetFreeSpace",
    "signature": "GetFreeSpace(path: String): Long",
    "summary": "Returns the number of unallocated bytes in the partition."
  }},
  "decision": "1:1",
  "selected_targets": [
    {{
      "namespace": "org.modern.storage",
      "class_or_interface": "VolumeManager",
      "member": "QueryAvailableBytes",
      "signature": "QueryAvailableBytes(mountPoint: Path): UInt64",
      "summary": "Returns available storage capacity for the specified path."
    }}
  ],
  "reason": ""
}}
```

---

**Input:**

```python
{{
  "v1_element": {{
    "namespace": "com.legacy.auth",
    "class_or_interface": "UserClient",
    "member": "UpdateUserAndPermissions",
    "signature": "UpdateUserAndPermissions(userId: string, data: Bundle)",
    "summary": "Updates both the user profile information and their access scopes in a single transaction."
  }},
  "potential_targets": [
    {{
      "namespace": "org.modern.identity",
      "class_or_interface": "ProfileService",
      "member": "UpdateBio",
      "signature": "UpdateBio(id: UUID, payload: ProfileDto)",
      "summary": "Updates user-specific metadata and biographical information."
    }},
    {{
      "namespace": "org.modern.identity",
      "class_or_interface": "AccessControl",
      "member": "GrantScopes",
      "signature": "GrantScopes(id: UUID, scopes: List<String>)",
      "summary": "Applies security scopes and permission sets to a specific identity."
    }}
  ]
}}
```

**Output:**

```python
{{
  "v1_element": {{
    "namespace": "com.legacy.auth",
    "class_or_interface": "UserClient",
    "member": "UpdateUserAndPermissions",
    "signature": "UpdateUserAndPermissions(userId: string, data: Bundle)",
    "summary": "Updates both the user profile information and their access scopes in a single transaction."
  }},
  "decision": "1:N",
  "selected_targets": [
    {{
      "namespace": "org.modern.identity",
      "class_or_interface": "ProfileService",
      "member": "UpdateBio",
      "signature": "UpdateBio(id: UUID, payload: ProfileDto)",
      "summary": "Updates user-specific metadata and biographical information."
    }},
    {{
      "namespace": "org.modern.identity",
      "class_or_interface": "AccessControl",
      "member": "GrantScopes",
      "signature": "GrantScopes(id: UUID, scopes: List<String>)",
      "summary": "Applies security scopes and permission sets to a specific identity."
    }}
  ],
  "reason": "The legacy monolithic call has been decoupled for better security auditing. **Migration Path:**\\n1. Update identity data via `ProfileService`.\\n2. Update permissions via `AccessControl`."
}}
```

### INPUT DATA
""".strip()