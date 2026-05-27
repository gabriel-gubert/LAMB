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
- For each element, identify the following components:

* **namespace**: The full package, namespace, or module path.
* **class_or_interface**: The name of the containing class, interface, or struct. Use "Global" if none.
* **member**: The name of the specific function, method, constant, or endpoint.
* **signature**: The full technical signature (including name, parameters, return types, or HTTP verbs).
* **summary**: The textual documentation extracted from the source text. You must adhere strictly to the following constraints when generating this value:
1. **Copy-Paste Extraction:** Act exclusively as a direct extraction tool to harvest all docstrings, comments, and raw text.
2. **No Extraneous Text:** Do not generate, summarize, or add any introductory text, concluding remarks, or explanations. Do not include any text or commentary that does not exist inside the original documentation artifact.
3. **Strict Markdown Format:** Convert the extracted text strictly into Markdown. Transform any non-Markdown markup languages (such as HTML tags, XML, or Javadoc-style annotations) into their exact Markdown equivalents.
4. **Structural Completeness:** Do not settle for a single sentence. Use Markdown headers, bulleted lists, tables, and bold text to structurally preserve and synthesize the full scope of behavior exactly as written (including parameters, side effects, error handling, and business logic).
5. **Explicit Info Only:** Only include information explicitly stated in the source text, ensuring the final output is a clean, fully compliant Markdown block.

### OUTPUT FORMATTING
Output a flat list of objects in the format below:

```json
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

### EXAMPLES

**Input:**

```html
<div class="namespace">ForgeEngine.Core</div>
<main class="class-doc">
    <h1>Class: PhysicsBody</h1>
    <p>Represents a rigid physical object within the game world simulator.</p>
    
    <div class="method-doc">
        <h3>Method: ApplyImpulse</h3>
        <p>Syntax: <code>public void ApplyImpulse(Vector3 force, bool ignoreMass = false)</code></p>
        <div class="description">
            Applies an instantaneous force vector directly to the center of mass of the physics object.
            <p><b>Note:</b> This will modify the linear velocity vector immediately and wake up the body if it is currently sleeping.</p>
            
            <h4>Parameters:</h4>
            <ul>
                <li><code>force</code>: The directional impulse force vector expressed in Newtons per second.</li>
                <li><code>ignoreMass</code>: If set to true, velocity changes bypass the mass properties of the entity, acting as a direct velocity change.</li>
            </ul>
            
            <h4>Exceptions:</h4>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Condition</th>
                </tr>
                <tr>
                    <td>InvalidOperationException</td>
                    <td>Thrown if the target physics body has not been initialized or is marked static.</td>
                </tr>
            </table>
        </div>
    </div>
</main>

```

**Output:**

```json
[
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "PhysicsBody",
    "member": "ApplyImpulse",
    "signature": "public void ApplyImpulse(Vector3 force, bool ignoreMass = false)",
    "summary": "Applies an instantaneous force vector directly to the center of mass of the physics object.\n\n**Note:** This will modify the linear velocity vector immediately and wake up the body if it is currently sleeping.\n\n#### Parameters:\n* `force`: The directional impulse force vector expressed in Newtons per second.\n* `ignoreMass`: If set to true, velocity changes bypass the mass properties of the entity, acting as a direct velocity change.\n\n#### Exceptions:\n| Type | Condition |\n| :--- | :--- |\n| InvalidOperationException | Thrown if the target physics body has not been initialized or is marked static. |"
  }
]
```

### INPUT DATA
""".strip()


def get_general_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert Systems Architect mapping Legacy API elements to a New version. Analyze the semantic relationship and functional intent between the legacy source and the potential candidates. You must select the correct target(s) and classify the relationship logic.

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```json
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

```json
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

```json
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

```json
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

```json
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

```json
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

def get_lexical_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert Systems Architect specializing in Strict Type Safety and API Contract Mapping. Your objective is to map Legacy API elements to a New version by analyzing raw signatures, parameter constraints, structural hierarchies, and formal code contracts. You prioritize strict structural fit over loose semantic matching.

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```json
{{
  "v1_element": {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }},
  "potential_targets": [ {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }} ]
}}
```

**DECISION CLASSIFICATIONS:**
*   1:1 - A single clean structural layout fit exists. Add exactly ONE target to 'selected_targets'.
*   1:N - The parameter list or return payload types have been decomposed or split across distinct system boundaries. Add MULTIPLE targets to 'selected_targets'.
*   N:1 - Multiple tight legacy interfaces consolidate down to a unified generic typed method. Add exactly ONE target to 'selected_targets'.
*   N:N - Complete structural reorganization of parameters and types across multiple interfaces. Add MULTIPLE targets to 'selected_targets'.
*   AMBIGUOUS - Multiple targets offer a structurally identical signature type footprint, making a deterministic automated selection impossible without external state context. Add the top 2 candidates.
*   DEPRECATED - No targets match the fundamental data contract types, or the underlying technical capability is unsupported by the new framework. Leave 'selected_targets' empty [].

**CRITICAL RULES:**
*   **Contract-First Thinking:** Evaluate return types, parameter count, and namespace hierarchies before reading the textual 'summary'.
*   For the 'reason' field, output ONLY valid Markdown focusing on data contract transformations, type compatibility, or casting requirements.
*   If the decision is a straightforward 1:1 match by signature or exact type logic, output an empty string "" for the 'reason'.
*   If 'potential_targets' is empty, the decision MUST be DEPRECATED.

### OUTPUT FORMATTING
You must return a list of objects in the format below:

```json
[
  {{
    "v1_element": {{ ... }},
    "decision": "1:1|1:N|N:1|N:N|AMBIGUOUS|DEPRECATED",
    "selected_targets": [ {{ ... }} ],
    "reason": "Markdown text or empty string"
  }}
]

```

### EXAMPLES

**Input:**

```json
{{
  "v1_element": {{
    "namespace": "com.legacy.math",
    "class_or_interface": "Calculator",
    "member": "Compute",
    "signature": "Compute(val: int, rate: float): double",
    "summary": "Executes core matrix math using raw numerical inputs."
  }},
  "potential_targets": [
    {{
      "namespace": "org.modern.numeric",
      "class_or_interface": "Engine",
      "member": "Evaluate",
      "signature": "Evaluate(x: Int32, y: Float64): Float64",
      "summary": "Processes internal calculations."
    }}
  ]
}}

```

**Output:**

```json
{{
  "v1_element": {{
    "namespace": "com.legacy.math",
    "class_or_interface": "Calculator",
    "member": "Compute",
    "signature": "Compute(val: int, rate: float): double",
    "summary": "Executes core matrix math using raw numerical inputs."
  }},
  "decision": "1:1",
  "selected_targets": [
    {{
      "namespace": "org.modern.numeric",
      "class_or_interface": "Engine",
      "member": "Evaluate",
      "signature": "Evaluate(x: Int32, y: Float64): Float64",
      "summary": "Processes internal calculations."
    }}
  ],
  "reason": ""
}}

```

### INPUT DATA
""".strip()

def get_semantic_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert Domain-Driven Design (DDD) Architect mapping Legacy API components to a modernized framework. Your objective is to map elements by evaluating behavioral semantics, functional side-effects, docstring intention, and business goals. You look past signature transformations to ensure domain operations match up seamlessly.

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```json
{{
  "v1_element": {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }},
  "potential_targets": [ {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }} ]
}}
```

**DECISION CLASSIFICATIONS:**
*   1:1 - The exact same business intent/functional side-effect is handled by a new modern endpoint. Add exactly ONE target to 'selected_targets'.
*   1:N - The old routine handled a combination of business actions that have now been correctly isolated into decoupled bounded domains. Add MULTIPLE targets to 'selected_targets'.
*   N:1 - Redundant, overlapping legacy operational hooks have been unified under a single cohesive domain method. Add exactly ONE target to 'selected_targets'.
*   N:N - High-level structural modernization of cross-cutting logic workflows. Add MULTIPLE targets to 'selected_targets'.
*   AMBIGUOUS - The system intent splits across different architectural targets, requiring a deeper functional decision review. Add the top 2 candidate targets.
*   DEPRECATED - The underlying business capability or design pattern is no longer relevant or safe in the modern target architecture. Leave 'selected_targets' empty [].

**CRITICAL RULES:**
*   **Behavior-First Thinking:** Analyze the 'summary' and structural names for intent. Namespaces and type footprints change constantly during a rewrite—look at *what the code actually accomplishes*.
*   For the 'reason' field, output ONLY valid Markdown explicitly documenting the architectural shift, domain decoupling pattern, or business rationale for your decisions.
*   If the decision represents an identical, un-decoupled behavioral mapping transition, output an empty string "" for the 'reason'.
*   If 'potential_targets' is empty, the decision MUST be DEPRECATED.

### OUTPUT FORMATTING
You must return a list of objects in the format below:

```json
[
  {{
    "v1_element": {{ ... }},
    "decision": "1:1|1:N|N:1|N:N|AMBIGUOUS|DEPRECATED",
    "selected_targets": [ {{ ... }} ],
    "reason": "Markdown text or empty string"
  }}
]
```

### EXAMPLES

**Input:**

```json
{{
  "v1_element": {{
    "namespace": "com.legacy.store",
    "class_or_interface": "CartManager",
    "member": "Finalize",
    "signature": "Finalize(cartId: String): Void",
    "summary": "Locks user cart, runs inventory validation checking, saves billing history state, and fires shipping events."
  }},
  "potential_targets": [
    {{
      "namespace": "org.modern.checkout",
      "class_or_interface": "OrderService",
      "member": "PlaceOrder",
      "signature": "PlaceOrder(id: UUID): OrderResult",
      "summary": "Initiates purchase transactional workflows."
    }},
    {{
      "namespace": "org.modern.logistics",
      "class_or_interface": "FulfillmentHub",
      "member": "ScheduleDelivery",
      "signature": "ScheduleDelivery(orderId: UUID): Void",
      "summary": "Queues physical distribution pipelines for an order."
    }}
  ]
}}
```

**Output:**

```json
{{
  "v1_element": {{
    "namespace": "com.legacy.store",
    "class_or_interface": "CartManager",
    "member": "Finalize",
    "signature": "Finalize(cartId: String): Void",
    "summary": "Locks user cart, runs inventory validation checking, saves billing history state, and fires shipping events."
  }},
  "decision": "1:N",
  "selected_targets": [
    {{
      "namespace": "org.modern.checkout",
      "class_or_interface": "OrderService",
      "member": "PlaceOrder",
      "signature": "PlaceOrder(id: UUID): OrderResult",
      "summary": "Initiates purchase transactional workflows."
    }},
    {{
      "namespace": "org.modern.logistics",
      "class_or_interface": "FulfillmentHub",
      "member": "ScheduleDelivery",
      "signature": "ScheduleDelivery(orderId: UUID): Void",
      "summary": "Queues physical distribution pipelines for an order."
    }}
  ],
  "reason": "The monolithic `Finalize` command violated single-responsibility patterns. **Domain Decoupling:**\\n- Order state transitions are routed to `OrderService`.\\n- Downstream side-effects are decoupled into the asynchronous context of `FulfillmentHub`."
}}
```

### INPUT DATA
""".strip()

def get_consensus_arbitration_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert system conflict arbitrator. 3 parallel mapping agents have produced distinct, conflicting architectural proposals for migrating a codebase component from V1 to V2. Review all proposals, evaluate semantic accuracy, and choose the most precise target outcome.

### INSTRUCTIONS & GUIDELINES
You will receive a list of deadlocked stalemates. Each stalemate contains a clean `source_element` (V1 metadata) and three competing strategic bundles: `agent_1_proposal`, `agent_2_proposal`, and `agent_3_proposal`.

Each proposal contains an array of items representing that agent's complete structural verdict. Each item provides:
- `mapping_details`: The metadata and complexity asserted by the agent.
- `v2_target_element`: The full original V2 metadata for that target, or the string "DEPRECATED_OR_NO_TARGET".

**CRITICAL RULES:**
*   **Evaluate Holistically**: Compare the strategies. One agent might suggest a single replacement (1:1), another might suggest splitting the logic across two targets (1:N), and a third might assert the component was erased entirely (DEPRECATED).
*   **Reasoning Understanding**: Review the `additional_notes` within each `mapping_details` block to understand the underlying architectural reasoning provided by each individual agent.
*   **Preserve Bundle Integrity**: You are voting on the best *strategy*. If you choose a 1:N proposal, you must include **all** V2 target elements provided within that specific agent's proposal bundle inside your `selected_targets` list. Do not mix and match items between different agents.
*   **Handling Deprecations**: If you determine that the agent proposing `{Complexity.DEPRECATED}` has the most accurate architectural strategy, set your `decision` field to `{Complexity.DEPRECATED}` and leave the `selected_targets` list completely empty.
*   **Semantic Contract**: Prioritize the proposal that best preserves the functional intent, data contracts, and type relationships of the source element.

**DECISION CLASSIFICATIONS:**
*   {Complexity.ONE_TO_ONE} - Clear single replacement element.
*   {Complexity.ONE_TO_MANY} - Functionality split across multiple targets.
*   {Complexity.MANY_TO_ONE} - Consolidated into a shared target.
*   {Complexity.MANY_TO_MANY} - Complex architectural reorganization.
*   {Complexity.AMBIGUOUS} - Multiple paths looked valid; you are picking the structurally superior one.
*   {Complexity.DEPRECATED} - No valid replacement component exists in V2.

### OUTPUT FORMATTING
You must return a list of objects exactly structured matching the JSON format below:

```json
[
  {{
    "v1_element": {{
      "namespace": "string",
      "class_or_interface": "string",
      "member": "string",
      "signature": "string"
    }},
    "decision": "{"|".join([
        Complexity.ONE_TO_ONE, 
        Complexity.ONE_TO_MANY, 
        Complexity.MANY_TO_ONE, 
        Complexity.MANY_TO_MANY, 
        Complexity.AMBIGUOUS, 
        Complexity.DEPRECATED])}",
    "selected_targets": [
      {{
        "namespace": "string",
        "class_or_interface": "string",
        "member": "string",
        "signature": "string"
      }}
    ],
    "reason": "Markdown text explaining the arbitration choice comprehensively."
  }}
]
```


### EXAMPLES

**Input:**

```json
{{
  "source_element": {{
    "namespace": "Legacy.Crypto",
    "class_or_interface": "Cipher",
    "member": "EncryptData",
    "signature": "EncryptData(string raw)",
    "summary": "Encrypts a raw string using default system algorithms."
  }},
  "agent_1_proposal": [
    {{
      "mapping_details": {{ "complexity": "{Complexity.ONE_TO_MANY}", "new_member": "EncryptAES" }},
      "v2_target_element": {{ "namespace": "Secure.Crypto", "class_or_interface": "AESEngine", "member": "EncryptAES", "signature": "EncryptAES(byte[] payload)" }}
    }},
    {{
      "mapping_details": {{ "complexity": "{Complexity.ONE_TO_MANY}", "new_member": "StringToBytes" }},
      "v2_target_element": {{ "namespace": "Secure.Utils", "class_or_interface": "Conv", "member": "StringToBytes", "signature": "StringToBytes(string s)" }}
    }}
  ],
  "agent_2_proposal": [
    {{
      "mapping_details": {{ "complexity": "{Complexity.DEPRECATED}", "new_member": "" }},
      "v2_target_element": "DEPRECATED_OR_NO_TARGET"
    }}
  ],
  "agent_3_proposal": [
    {{
      "mapping_details": {{ "complexity": "{Complexity.ONE_TO_ONE}", "new_member": "EncryptTripleDES" }},
      "v2_target_element": {{ "namespace": "Secure.Crypto", "class_or_interface": "DESEngine", "member": "EncryptTripleDES", "signature": "EncryptTripleDES(string raw)" }}
    }}
  ]
}}
```

**Output:**

```json
[
  {{
    "v1_element": {{
      "namespace": "Legacy.Crypto",
      "class_or_interface": "Cipher",
      "member": "EncryptData",
      "signature": "EncryptData(string raw)"
    }},
    "decision": "{Complexity.ONE_TO_MANY}",
    "selected_targets": [
      {{ "namespace": "Secure.Crypto", "class_or_interface": "AESEngine", "member": "EncryptAES", "signature": "EncryptAES(byte[] payload)" }},
      {{ "namespace": "Secure.Utils", "class_or_interface": "Conv", "member": "StringToBytes", "signature": "StringToBytes(string s)" }}
    ],
    "reason": "The monolithic V1 encryption routine was decomposed into an explicit string-to-byte pre-processing utility alongside an upgraded AES encryption algorithm wrapper in V2."
  }}
]
```

### INPUT DATA
""".strip()