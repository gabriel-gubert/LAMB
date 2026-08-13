from typing import Any, Optional, List, Tuple
from .types import Complexity

def get_language_prompt(supported_langs: list[str] = None) -> str:
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

def get_parse_prompt() -> str:
    return f"""
### ROLE & OBJECTIVE
You are an expert static code analysis engine. Your goal is to extract all code symbols—including type identifiers, function calls, method invocations, and property accesses—encountered or explicitly/implicitly referenced in the provided code snippet, and infer their fully qualified names (FQNs) wherever possible.

### INSTRUCTIONS & GUIDELINES
1. **Target Entities & Categories (`kind`):**
   - `'TYPE'`: Primitive types, user-defined classes, interfaces, structs, enums, type aliases, generics/type parameters, imported types, and type annotations.
   - `'FUNCTION'`: Standalone or global function declarations and function calls (e.g., `print()`, `process_data()`).
   - `'METHOD'`: Member methods invoked on objects or classes (e.g., `user.get_id()`, `df.head()`).
   - `'PROPERTY'`: Attributes, fields, or properties accessed on objects or classes (e.g., `user.name`, `arr.length`).
2. **Short Name (`name`):** 
   - Extract strictly the unqualified simple identifier (e.g., `QueryEngine` NOT `Database::Core::QueryEngine`, `cout` NOT `std::cout`, `DataFrame` NOT `pd.DataFrame`).
   - Do not include scope resolution operators (`::`), module qualifiers, package prefixes, or object references in `name`.
3. **Fully Qualified Name (`fully_qualified_name`):** 
   - Standardize all fully qualified names to use **dot notation (`.`) as the universal delimiter** across all programming languages (e.g., convert C++ `Database::Core::QueryEngine::executeQuery` to `Database.Core.QueryEngine.executeQuery`, and `std::endl` to `std.endl`).
   - Deduce the FQN based on imports, standard library conventions, or package/namespace declarations in the snippet.
   - If an exact FQN cannot be inferred with high confidence, set `fully_qualified_name` to `null` or the simple `name`.
4. **Exclude Pure Local Variables:** Do not include local variable assignments, parameter declarations, or function/method definitions unless they represent property accesses or function/method calls.

### OUTPUT FORMATTING

```json
{{
  "identifiers": [
{    {
      "name": "Short symbol name (e.g., 'QueryEngine')",
      "kind": "'TYPE' | 'FUNCTION' | 'METHOD' | 'PROPERTY'",
      "fully_qualified_name": "Normalized dot-separated FQN or null (e.g., 'Database.Core.QueryEngine')"
    }}
  ]
}}

### EXAMPLES

**Example 1: Python Data Processing Script**

**Input:**

```python
import pandas as pd
from typing import List, Optional
from mymodule.models import UserProfile

def process_users(users: List[UserProfile], default_id: Optional[int]) -> pd.DataFrame:
    raw_data = [u.to_dict() for u in users]
    df: pd.DataFrame = pd.DataFrame(raw_data)
    print(f"Total rows: {{df.shape[0]}}")
    return df

```

**Output:**

```json
{{
  "identifiers": [
    {{
      "name": "List",
      "kind": "TYPE",
      "fully_qualified_name": "typing.List"
    }},
    {{
      "name": "UserProfile",
      "kind": "TYPE",
      "fully_qualified_name": "mymodule.models.UserProfile"
    }},
    {{
      "name": "Optional",
      "kind": "TYPE",
      "fully_qualified_name": "typing.Optional"
    }},
    {{
      "name": "int",
      "kind": "TYPE",
      "fully_qualified_name": "builtins.int"
    }},
    {{
      "name": "DataFrame",
      "kind": "TYPE",
      "fully_qualified_name": "pandas.core.frame.DataFrame"
    }},
    {{
      "name": "process_users",
      "kind": "FUNCTION",
      "fully_qualified_name": "process_users"
    }},
    {{
      "name": "to_dict",
      "kind": "METHOD",
      "fully_qualified_name": "mymodule.models.UserProfile.to_dict"
    }},
    {{
      "name": "DataFrame",
      "kind": "FUNCTION",
      "fully_qualified_name": "pandas.DataFrame"
    }},
    {{
      "name": "print",
      "kind": "FUNCTION",
      "fully_qualified_name": "builtins.print"
    }},
    {{
      "name": "shape",
      "kind": "PROPERTY",
      "fully_qualified_name": "pandas.DataFrame.shape"
    }}
  ]
}}

```

---

**Example 2: Java Service Method**

**Input:**

```java
package com.example.service;

import java.util.Map;
import com.example.model.Order;

public class OrderProcessor {{
    private final Map<String, Order> activeOrders;

    public OrderProcessor(Map<String, Order> orders) {{
        this.activeOrders = orders;
    }}

    public int getOrderCount() {{
        return this.activeOrders.size();
    }}
}}

```

**Output:**

```json
{{
  "identifiers": [
    {{
      "name": "OrderProcessor",
      "kind": "TYPE",
      "fully_qualified_name": "com.example.service.OrderProcessor"
    }},
    {{
      "name": "Map",
      "kind": "TYPE",
      "fully_qualified_name": "java.util.Map"
    }},
    {{
      "name": "String",
      "kind": "TYPE",
      "fully_qualified_name": "java.lang.String"
    }},
    {{
      "name": "Order",
      "kind": "TYPE",
      "fully_qualified_name": "com.example.model.Order"
    }},
    {{
      "name": "int",
      "kind": "TYPE",
      "fully_qualified_name": "int"
    }},
    {{
      "name": "getOrderCount",
      "kind": "METHOD",
      "fully_qualified_name": "com.example.service.OrderProcessor.getOrderCount"
    }},
    {{
      "name": "activeOrders",
      "kind": "PROPERTY",
      "fully_qualified_name": "com.example.service.OrderProcessor.activeOrders"
    }},
    {{
      "name": "size",
      "kind": "METHOD",
      "fully_qualified_name": "java.util.Map.size"
    }}
  ]
}}

```

---

**Example 3: TypeScript Request Handler**

**Input:**

```typescript
import {{ Request, Response }} from 'express';

interface AuthenticatedRequest extends Request {{
  userRole: string;
}}

export function handleRequest(req: AuthenticatedRequest, res: Response): void {{
  const role = req.userRole;
  res.status(200).send({{ role: role }});
}}

```

**Output:**

```json
{{
  "identifiers": [
    {{
      "name": "Request",
      "kind": "TYPE",
      "fully_qualified_name": "express.Request"
    }},
    {{
      "name": "Response",
      "kind": "TYPE",
      "fully_qualified_name": "express.Response"
    }},
    {{
      "name": "AuthenticatedRequest",
      "kind": "TYPE",
      "fully_qualified_name": "AuthenticatedRequest"
    }},
    {{
      "name": "string",
      "kind": "TYPE",
      "fully_qualified_name": "string"
    }},
    {{
      "name": "void",
      "kind": "TYPE",
      "fully_qualified_name": "void"
    }},
    {{
      "name": "userRole",
      "kind": "PROPERTY",
      "fully_qualified_name": "AuthenticatedRequest.userRole"
    }},
    {{
      "name": "handleRequest",
      "kind": "FUNCTION",
      "fully_qualified_name": "handleRequest"
    }},
    {{
      "name": "status",
      "kind": "METHOD",
      "fully_qualified_name": "express.Response.status"
    }},
    {{
      "name": "send",
      "kind": "METHOD",
      "fully_qualified_name": "express.Response.send"
    }}
  ]
}}

```

---

**Example 4: C++ Database Query Routine**

**Input:**

```cpp
#include <iostream>
#include <vector>
#include <string>

namespace Database {{
namespace Core {{
    class QueryEngine {{
    public:
        std::vector<std::string> executeQuery(const std::string& sql);
    }};
}}
}}

void logAndQuery(Database::Core::QueryEngine& engine, const std::string& sql) {{
    std::clog << sql << std::endl;
    engine.executeQuery(sql);
}}

```

**Output:**

```json
{{
  "identifiers": [
    {{
      "name": "QueryEngine",
      "kind": "TYPE",
      "fully_qualified_name": "Database.Core.QueryEngine"
    }},
    {{
      "name": "vector",
      "kind": "TYPE",
      "fully_qualified_name": "std.vector"
    }},
    {{
      "name": "string",
      "kind": "TYPE",
      "fully_qualified_name": "std.string"
    }},
    {{
      "name": "logAndQuery",
      "kind": "FUNCTION",
      "fully_qualified_name": "logAndQuery"
    }},
    {{
      "name": "executeQuery",
      "kind": "METHOD",
      "fully_qualified_name": "Database.Core.QueryEngine.executeQuery"
    }},
    {{
      "name": "clog",
      "kind": "PROPERTY",
      "fully_qualified_name": "std.clog"
    }},
    {{
      "name": "endl",
      "kind": "PROPERTY",
      "fully_qualified_name": "std.endl"
    }}
  ]
}}

```

### INPUT DATA
""".strip()

def get_type_inference_prompt(mapping_table: Optional[List[Any]] = None) -> str:
    schema_str = f"\nMapping Table / Schema Context:\n{mapping_table}\n" if mapping_table else "\nMapping Table / Schema Context: None provided.\n"

    return f"""
### ROLE & OBJECTIVE
You are a precise static code analysis engine specializing in type inference. Your goal is to identify variables in the provided code snippet that have no local declaration or assignment, record how they are used, and identify their type STRICTLY based on evidence from the code or the provided mapping schema.

### INTRUCTIONS & GUIDELINES
1. **NO HALLUCINATIONS / GUESSING:** Do NOT invent, assume, or guess generic type names (e.g., do NOT invent names like `ApiClient`, `UserRepository`, or `ILogger` unless those exact names appear in the code's annotations/comments or in the provided Mapping Table).
2. **Sources for `inferred_type`:**
   - **From Mapping Schema:** Match accessed attributes and invoked methods against `old_member` or `new_member` in the Mapping Table, and extract `old_class_interface` or `new_class_interface`.
   - **From Code:** Use a type name ONLY if it explicitly appears in the snippet (e.g., inline docstrings, type annotations, JSDoc comments, casting expressions, or class references).
   - **If Neither Applies:** Set `inferred_type` to `null`.
3. **Status Rules:**
   - `'INFERRED'`: An explicit type name was matched via the code or schema.
   - `'AMBIGUOUS'`: The usage context matched multiple candidate classes in the schema.
   - `'UNRESOLVED'`: Usage attributes/methods were extracted, but no explicit type name exists in the code or mapping schema.
   - `'UNKNOWN'`: The variable is used, but has no identifiable attribute/method accesses.
4. **`schema_type`:** Set to `'LEGACY'` or `'NEW'` if matched via the Mapping Table, otherwise `null`.
{schema_str}

### OUTPUT FORMATTING
Adhere strictly to the JSON schema specified by the structured output definition.

### EXAMPLES

**Example 1: Grounded Match via Legacy Mapping Schema**

**Mapping Table / Schema Context:**
`[{{"old_class_interface": "com.legacy.CustomerService", "old_member": "fetchCustomerById", "new_class_interface": "com.v2.AccountClient", "new_member": "getAccount"}}]`

**Input Code:**

```javascript
async function handleCheckout(service, customerId) {{
  const record = await service.fetchCustomerById(customerId);
  return record;
}}

```

**Output:**

```json
{{
  "external_variables": [
    {{
      "variable_name": "service",
      "accessed_attributes": [],
      "invoked_methods": ["fetchCustomerById"],
      "status": "INFERRED",
      "inferred_type": "com.legacy.CustomerService",
      "schema_type": "LEGACY"
    }}
  ]
}}

```

---

**Example 2: Grounded Match via New Mapping Schema**

**Mapping Table / Schema Context:**
`[{{"old_class_interface": "v1.LegacyStorage", "old_member": "put_data", "new_class_interface": "v2.S3Adapter", "new_member": "upload_file"}}]`

**Input Code:**

```python
def export_report(storage, report_data):
    storage.upload_file(report_data)

```

**Output:**

```json
{{
  "external_variables": [
    {{
      "variable_name": "storage",
      "accessed_attributes": [],
      "invoked_methods": ["upload_file"],
      "status": "INFERRED",
      "inferred_type": "v2.S3Adapter",
      "schema_type": "NEW"
    }}
  ]
}}

```

---

**Example 3: Unmatched Usage Against Provided Mapping Schema**

**Mapping Table / Schema Context:**
`[{{"old_class_interface": "com.legacy.AuthService", "old_member": "verifyToken", "new_class_interface": "com.v2.IdentityClient", "new_member": "authenticate"}}]`

**Input Code:**

```python
def process_data(client, payload):
    token = client.get_auth_token()
    user_id = payload.user.id
    return client.send_request(user_id, token)

```

**Output:**

```json
{{
  "external_variables": [
    {{
      "variable_name": "client",
      "accessed_attributes": [],
      "invoked_methods": ["get_auth_token", "send_request"],
      "status": "UNRESOLVED",
      "inferred_type": null,
      "schema_type": null
    }},
    {{
      "variable_name": "payload",
      "accessed_attributes": ["user", "id"],
      "invoked_methods": [],
      "status": "UNRESOLVED",
      "inferred_type": null,
      "schema_type": null
    }}
  ]
}}

```

---

**Example 4: Ambiguous Schema Match across Multiple Mappings**

**Mapping Table / Schema Context:**
`[{{"old_class_interface": "IUserStore", "old_member": "delete", "new_class_interface": "IV2Store", "new_member": "remove"}}, {{"old_class_interface": "ICacheProvider", "old_member": "delete", "new_class_interface": "IRedisCache", "new_member": "purge"}}]`

**Input Code:**

```typescript
function cleanup(store) {{
  store.delete("session_key");
}}

```

**Output:**

```json
{{
  "external_variables": [
    {{
      "variable_name": "store",
      "accessed_attributes": [],
      "invoked_methods": ["delete"],
      "status": "AMBIGUOUS",
      "inferred_type": null,
      "schema_type": "LEGACY"
    }}
  ]
}}

```

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

def get_migration_planner_prompt(
    language: str,
    legacy_code_snippet: str,
    formatted_rules: str,
    priority_summary: str = "",
    user_comments: str = ""
) -> Tuple[str, str]:
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

    system_prompt = f"""
### ROLE & OBJECTIVE
You are a Lead Software Architect planning a code migration for {language} code. Analyze the legacy code, schema rules, priority highlights, protected code sections, and developer instructions to create an actionable refactoring plan.

### INSTRUCTIONS & GUIDELINES
{priority_instructions_block}

#### Schema Transformation & Cardinality
- **1:1 Mapping:** Plan direct renames or signature updates.
- **1:N Mapping:** Plan splitting single legacy calls into multiple sequential target function invocations.
- **N:1 Mapping:** Plan consolidating multiple legacy operations into a single unified API call.
- **N:N Mapping:** Plan full refactoring for complex signature shifts and contextual restructuring.

### EXAMPLES

**Input:**

### TARGET LANGUAGE
python

### MIGRATION RULES TO APPLY
Rule ID: 1 | Cardinality: [1:1] | Target: `v1.net.Client` -> `connect_raw`
- Target Destination: `v2.net.Client` -> `connect`
  - Signature: `connect_raw(host: str, port: int)` -> `connect(config: ConnectionConfig)`

### DEVELOPER PRIORITY HIGHLIGHTS
- [DONT_TOUCH / IMMUTABLE] Range `2:1-2:38`: `client.connect_raw("localhost", 8080)` (MUST REMAIN VERBATIM)

### LEGACY CODE SNIPPET TO PLAN MIGRATION FOR
```python
client = Client()
client.connect_raw("localhost", 8080)
```

**Output:**

```json
{{
  "overview": "Refactor Client initialization while maintaining strict verbatim preservation on DONT_TOUCH lines.",
  "steps": [
    {{
      "step_number": 1,
      "title": "Preserve Immutable Section Verbatim",
      "description": "Leave line 2 (`client.connect_raw(\"localhost\", 8080)`) completely untouched and preserved verbatim as requested by DONT_TOUCH constraints, despite available migration rules.",
      "cardinality": "1:1",
      "target_symbols": ["client.connect_raw"]
    }}
  ]
}}
```

""".strip()

    user_instructions_block = ""
    if user_comments.strip():
        user_instructions_block = f"""
### ADDITIONAL NOTES/INSTRUCTIONS
"{user_comments.strip()}"
"""

    priority_block = ""
    if priority_summary.strip():
        priority_block = f"""
### DEVELOPER PRIORITY HIGHLIGHTS
{priority_summary.strip()}
"""

    user_prompt = f"""
### TARGET LANGUAGE
{language}

### MIGRATION RULES TO APPLY
{formatted_rules}
{priority_block}

### LEGACY CODE SNIPPET TO PLAN MIGRATION FOR
{legacy_code_snippet}

{user_instructions_block}
""".strip()

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

    system_prompt = f"""
### ROLE & OBJECTIVE
You are an expert Automated Code Transformation Engine for {language}. Your sole objective is to execute the step-by-step refactoring strategy provided in the MIGRATION PLAN and produce valid, clean, production-ready code.

### INSTRUCTIONS & GUIDELINES

#### Plan Execution & Code Generation
- **Strict Step Execution:** Follow the sequence outlined in the MIGRATION PLAN precisely. Do not skip steps, reorder operations, or introduce unplanned architectural shifts.
- **Rule Tracking & Snippet Edge Cases:** For every migration rule applied, record its integer `rule_id`, the exact `input_snippet` from the legacy code, and the corresponding `output_snippet` produced in the migrated code.
  - **Deprecations / Removals:** If a rule causes a legacy code snippet to be completely deleted or removed without a replacement, set `output_snippet` to an empty string `""`.
  - **Additions / Injections:** If a rule requires inserting new code that has no direct equivalent in the legacy code snippet, set `input_snippet` to an empty string `""`.
- **Clean Code Standard:** Output ONLY clean, executable {language} code. Do NOT add inline code comments, block comments, or docstrings to the generated output unless specifically instructed in the plan.
- **Syntax Integrity:** Ensure the final generated snippet is 100% syntactically valid, complete, and fully executable in {language}.

{dont_touch_instructions}

### EXAMPLES

**Input:**

### TARGET LANGUAGE
python

### MIGRATION RULES TO APPLY
Rule ID: 1 | Cardinality: [1:1] | Target: `v1.net.Client` -> `connect_raw`
- Target Destination: `v2.net.Client` -> `connect`
  - Signature: `connect_raw(host: str, port: int)` -> `connect(config: ConnectionConfig)`

### MIGRATION PLAN
1. Refactor Client instantiation to V2 schema.
2. Preserve Line 2 verbatim as requested by DONT_TOUCH constraints.

### DEVELOPER PRIORITY HIGHLIGHTS
- [DONT_TOUCH / IMMUTABLE] Range `2:1-2:38`: `client.connect_raw("localhost", 8080)` (Must remain verbatim)

### LEGACY CODE SNIPPET TO MIGRATE
```python
client = Client()
client.connect_raw("localhost", 8080)
```

**Output:**

```json
{{
  "migrated_code": "client = v2.net.Client()\nclient.connect_raw(\"localhost\", 8080)",
  "applied_rules": [
    {{
      "rule_id": 1,
      "input_snippet": "client = Client()",
      "output_snippet": "client = v2.net.Client()"
    }}
  ]
}}
```

---

**Input:**

### TARGET LANGUAGE
python

### MIGRATION RULES TO APPLY
Rule ID: 1 | Cardinality: [1:1] | Target: `v1.log.Logger` -> `info`
- Target Destination: `v2.log.Logger` -> `info`
  - Signature: `info(msg: str) -> None` -> `info(message: str) -> None`

Rule ID: 2 | Cardinality: [1:1] | Target: `v1.config.Config` -> `get`
- Target Destination: `v2.config.AppConfig` -> `get_setting`
  - Signature: `get(key: str) -> Any` -> `get_setting(key_name: str) -> Any`

### MIGRATION PLAN
1. Refactor Logger instantiation and logging call to V2.
2. Update Config access to use AppConfig.get_setting.

### DEVELOPER PRIORITY HIGHLIGHTS
* [WARNING] Range `1:1-3:30`: Standard API migration

### LEGACY CODE SNIPPET TO MIGRATE
```python
cfg = Config()
logger = Logger()
logger.info(cfg.get("app_name"))
```

**Output:**

```json
{{
  "migrated_code": "cfg = v2.config.AppConfig()\nlogger = v2.log.Logger()\nlogger.info(cfg.get_setting(\"app_name\"))",
  "applied_rules": [
    {{
      "rule_id": 1,
      "input_snippet": "logger = Logger()\nlogger.info(cfg.get(\"app_name\"))",
      "output_snippet": "logger = v2.log.Logger()\nlogger.info(cfg.get_setting(\"app_name\"))"
    }},
    {{
      "rule_id": 2,
      "input_snippet": "cfg = Config()\ncfg.get(\"app_name\")",
      "output_snippet": "cfg = v2.config.AppConfig()\ncfg.get_setting(\"app_name\")"
    }}
  ]
}}
```

---

**Input:**

### TARGET LANGUAGE
python

### MIGRATION RULES TO APPLY
Rule ID: 1 | Cardinality: DEPRECATED | Target: `v1.cache.clear_legacy_cache`
- Target Destination: DEPRECATED / REMOVED
  - Additional Notes: Cache lifecycle is handled automatically in V2.

Rule ID: 2 | Cardinality: [1:1] | Target: `v1.db.connect`
- Target Destination: `v2.db.connect`
  - Signature: `connect(uri: str)` -> `connect(uri: str, opts: ClientOptions)`
  - Additional Notes: Must instantiate `opts = v2.db.ClientOptions()` prior to connection if not present.

### MIGRATION PLAN
1. Remove deprecated `clear_legacy_cache()` call.
2. Inject required `opts = v2.db.ClientOptions()` configuration object.
3. Update `connect()` call to pass the new `opts` instance.

### DEVELOPER PRIORITY HIGHLIGHTS
* [WARNING] Range `1:1-3:25`: Deprecated call removal and signature update

### LEGACY CODE SNIPPET TO MIGRATE
```python
clear_legacy_cache()
db = connect("postgres://localhost:5432/db")
```

**Output:**

```json
{{
  "migrated_code": "opts = v2.db.ClientOptions()\ndb = v2.db.connect(\"postgres://localhost:5432/db\", opts)",
  "applied_rules": [
    {{
      "rule_id": 1,
      "input_snippet": "clear_legacy_cache()",
      "output_snippet": ""
    }},
    {{
      "rule_id": 2,
      "input_snippet": "db = connect(\"postgres://localhost:5432/db\")",
      "output_snippet": "opts = v2.db.ClientOptions()\ndb = v2.db.connect(\"postgres://localhost:5432/db\", opts)"
    }}
  ]
}}
```
""".strip()

    user_instructions_block = ""
    if user_comments.strip():
        user_instructions_block = f"""
### ADDITIONAL NOTES/INSTRUCTIONS
{user_comments.strip()}
"""

    priority_block = ""
    if priority_summary.strip():
        priority_block = f"""
### DEVELOPER PRIORITY HIGHLIGHTS
{priority_summary.strip()}
"""

    plan_block = ""
    if migration_plan.strip():
        plan_block = f"""
### MIGRATION PLAN
{migration_plan.strip()}
"""

    error_retry_block = ""
    if validation_error.strip():
        error_retry_block = f"""
### PREVIOUS ATTEMPT SYNTAX / VALIDATION ERROR (FIX THIS)
The previous migration attempt failed validation with the following error:
"{validation_error.strip()}"
Correct this error completely in the new generated code.
"""

    user_prompt = f"""
### TARGET LANGUAGE
{language}

### MIGRATION RULES TO APPLY
{formatted_rules}
{plan_block}
{priority_block}

### LEGACY CODE SNIPPET TO MIGRATE
{legacy_code_snippet}
{user_instructions_block}
{error_retry_block}
""".strip()

    return system_prompt, user_prompt

def get_mapper_extraction_prompt():
    return """
### ROLE & OBJECTIVE

Analyze the provided file content and exhaustively extract ALL structural API elements into a flat list of objects. This is an agnostic extraction: you must capture everything including containers (classes, interfaces, enums, structs, traits), internal members (methods, properties, fields, enum variants), and global/standalone constructs (functions, variables, constants, macros, type aliases, modules, and REST API routes).

**CRITICAL:** Completely ignore any Table of Contents (ToC), structural navigation indexes, or front-matter outlines. Do not take Table of Contents information into account at all. If the provided text chunk contains only a Table of Contents or other non-functional "trash" information with no actual API declarations, you must return an empty list `[]`.

### INSTRUCTIONS & GUIDELINES

* **Exhaustion Mandate:** Every single exported declaration, identifier, or documented block in the source text must map to at least one entry in your output. Do not summarize, truncate, or omit anything.
* **Table of Contents Exclusion:** Do not treat Table of Contents entries, page listings, or section headers from an index as API elements. If the input contains nothing but a Table of Contents, return an empty list `[]`.
* **Extract Both Containers and Members:** For any structural container (like a class, struct, trait, or enum), you must generate one entry for the container itself, and separate entries for each of its internal components or members.
* **Container Placement Rule:** When outputting the entry for a container itself (e.g., a class, struct, or enum declaration), place its identifier in the `class_or_interface` key and leave the `member` key empty `""`.
* **Standalone/Global Rule:** For standalone global constructs that do not belong to a container (like a global function, top-level constant, macro, or independent type alias), leave `class_or_interface` blank and place its identifier in the `member` key.
* Focus on public-facing contracts; ignore internal helper functions or private variables unless they are part of the exported surface.
* Maintain technical precision in the signature to ensure accurate semantic matching.

### FIELD EXTRACTION RULES

* **namespace**: The full package, namespace, or module path. Use a sensible default or leave empty if completely absent.
* **class_or_interface**: The name of the containing class, interface, struct, trait, or enum. Leave this blank ONLY for standalone top-level elements that genuinely lack a parent container. If you are extracting the container itself, place its name here.
* **member**: The name of the specific function, method, constant, macro, or variant. Leave this blank `""` if the current record represents the container itself.
* **signature**: The full technical signature (including name, modifiers, parameters, return types, or HTTP verbs). For elements without complex signatures (like global constants or enum variants), copy the exact declaration line.
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
<api-surface>
    <namespace>ForgeEngine.Core</namespace>
    
    <nav class="toc">
        <h2>Table of Contents</h2>
        <ol>
            <li><a href="#max-velocity">Constant: MAX_VELOCITY</a></li>
            <li><a href="#entity-id">Typedef: EntityId</a></li>
            <li>
                <a href="#physics-body">Class: PhysicsBody</a>
                <ul>
                    <li><a href="#apply-impulse">Method: ApplyImpulse</a></li>
                </ul>
            </li>
            <li><a href="#force-mode">Enum: ForceMode</a></li>
        </ol>
    </nav>

    <constant-doc id="max-velocity">
        <name>MAX_VELOCITY</name>
        <syntax>public const float MAX_VELOCITY = 299.792f;</syntax>
        <summary>The absolute maximum speed limit imposed on any physical body vector within the simulator.</summary>
    </constant-doc>

    <typedef-doc id="entity-id">
        <name>EntityId</name>
        <syntax>using EntityId = System.UInt64;</syntax>
        <summary>A unique unsigned 64-bit integer tracking lifecycle allocations across clusters.</summary>
    </typedef-doc>

    <class-doc>
        <h1 id="physics-body">Class: PhysicsBody</h1>
        <p>Represents a rigid physical object within the game world simulator.</p>
        
        <method-doc>
            <h3 id="apply-impulse">Method: ApplyImpulse</h3>
            <p>Syntax: <code>public void ApplyImpulse(Vector3 force)</code></p>
            <p>Applies an instantaneous force vector directly to the center of mass.</p>
        </method-doc>
    </class-doc>

    <enum-doc>
        <h1 id="force-mode">Enum: ForceMode</h1>
        <p>Specifies how to evaluate a force application mapping vector.</p>
        
        <variant>
            <name>Impulse</name>
            <syntax>ForceMode.Impulse = 0</syntax>
            <summary>Apply an instant force impulse using its mass properties.</summary>
        </variant>
        <variant>
            <name>VelocityChange</name>
            <syntax>ForceMode.VelocityChange = 1</syntax>
            <summary>Apply a direct velocity change, bypassing mass values completely.</summary>
        </variant>
    </enum-doc>
</api-surface>
```

**Output:**

```json
[
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "",
    "member": "MAX_VELOCITY",
    "signature": "public const float MAX_VELOCITY = 299.792f;",
    "summary": "The absolute maximum speed limit imposed on any physical body vector within the simulator."
  },
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "",
    "member": "EntityId",
    "signature": "using EntityId = System.UInt64;",
    "summary": "A unique unsigned 64-bit integer tracking lifecycle allocations across clusters."
  },
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "PhysicsBody",
    "member": "",
    "signature": "Class: PhysicsBody",
    "summary": "Represents a rigid physical object within the game world simulator."
  },
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "PhysicsBody",
    "member": "ApplyImpulse",
    "signature": "public void ApplyImpulse(Vector3 force)",
    "summary": "Applies an instantaneous force vector directly to the center of mass."
  },
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "ForceMode",
    "member": "",
    "signature": "Enum: ForceMode",
    "summary": "Specifies how to evaluate a force application mapping vector."
  },
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "ForceMode",
    "member": "Impulse",
    "signature": "ForceMode.Impulse = 0",
    "summary": "Apply an instant force impulse using its mass properties."
  },
  {
    "namespace": "ForgeEngine.Core",
    "class_or_interface": "ForceMode",
    "member": "VelocityChange",
    "signature": "ForceMode.VelocityChange = 1",
    "summary": "Apply a direct velocity change, bypassing mass values completely."
  }
]
```

---

**Input:**

```
# Documentation Index

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
   - [Installation](#installation)
   - [Authentication](#authentication)
3. [ForgeEngine.Core Namespace](#forgeengine-core)
   - [Constant: MAX_VELOCITY](#max-velocity)
   - [Typedef: EntityId](#entity-id)
4. [Architecture & Classes](#architecture-overview)
   - [Class: PhysicsBody](#physics-body)
   - [Method: PhysicsBody.ApplyImpulse](#apply-impulse)
   - [Enum: ForceMode](#force-mode)
5. [Appendix](#appendix)
   - [Glossary](#glossary)
   - [Changelog](#changelog)
```

**Output:**

```json
[]
```

---

**Input:**

```cpp
namespace Game::Networking {
    /** @brief The default connection port used by the subsystem. */
    inline constexpr int DEFAULT_PORT = 8080;

    /** @brief High-level socket wrapper handling server packet streams. */
    class NetworkSocket {
    public:
        /** Disconnects the socket session safely. */
        void close();

        /** * @brief Sends a raw payload across the network channel.
         * @param data Pointer to the buffer array.
         */
        bool send(const char* data);

        /** * @brief Sends a structured system packet.
         * @param packet Reference to the target packet payload.
         */
        bool send(const Packet& packet);
    };
}
```

**Output:**

```json
[
  {
    "namespace": "Game::Networking",
    "class_or_interface": "",
    "member": "DEFAULT_PORT",
    "signature": "inline constexpr int DEFAULT_PORT = 8080;",
    "summary": "The default connection port used by the subsystem."
  },
  {
    "namespace": "Game::Networking",
    "class_or_interface": "NetworkSocket",
    "member": "",
    "signature": "class NetworkSocket",
    "summary": "High-level socket wrapper handling server packet streams."
  },
  {
    "namespace": "Game::Networking",
    "class_or_interface": "NetworkSocket",
    "member": "close",
    "signature": "void close()",
    "summary": "Disconnects the socket session safely."
  },
  {
    "namespace": "Game::Networking",
    "class_or_interface": "NetworkSocket",
    "member": "send",
    "signature": "bool send(const char* data)",
    "summary": "Sends a raw payload across the network channel.\n\n#### Parameters:\n* `data`: Pointer to the buffer array."
  },
  {
    "namespace": "Game::Networking",
    "class_or_interface": "NetworkSocket",
    "member": "send",
    "signature": "bool send(const Packet& packet)",
    "summary": "Sends a structured system packet.\n\n#### Parameters:\n* `packet`: Reference to the target packet payload."
  }
]
```

---

**Input:**

```python
# Module: storage.cache

MAX_CACHE_ITEMS: int = 500
# The upper threshold limit of structural items allowed in the active cache memory store.

class CacheManager:
    # Manages hot-swappable in-memory data records.

    @property
    def is_empty(self) -> bool:
        # Returns True if the internal store contains zero active records.
        pass

    @observe_metrics
    async def evict_expired(self, force: bool = False) -> int:
        # Asynchronously purges stale entries from the tracking collection.
        # Returns the count of deleted elements.
        pass
```

**Output:**

```json
[
  {
    "namespace": "storage.cache",
    "class_or_interface": "",
    "member": "MAX_CACHE_ITEMS",
    "signature": "MAX_CACHE_ITEMS: int = 500",
    "summary": "The upper threshold limit of structural items allowed in the active cache memory store."
  },
  {
    "namespace": "storage.cache",
    "class_or_interface": "CacheManager",
    "member": "",
    "signature": "class CacheManager",
    "summary": "Manages hot-swappable in-memory data records."
  },
  {
    "namespace": "storage.cache",
    "class_or_interface": "CacheManager",
    "member": "is_empty",
    "signature": "@property\ndef is_empty(self) -> bool",
    "summary": "Returns True if the internal store contains zero active records."
  },
  {
    "namespace": "storage.cache",
    "class_or_interface": "CacheManager",
    "member": "evict_expired",
    "signature": "@observe_metrics\nasync def evict_expired(self, force: bool = False) -> int",
    "summary": "Asynchronously purges stale entries from the tracking collection.\nReturns the count of deleted elements."
  }
]
```

---

**Input:**

```rust
//! module: core::pipeline

/// Global version flag identifier for the execution pipeline.
pub const PIPELINE_VERSION: &str = "2.4.0";

/// Defines a standardized behavioral protocol for data processing transformations.
pub trait TransformPipeline<T> {
    /// Transforms the inner data payload structure.
    fn process(&self, input: T) -> Result<T, String>;
}

/// Represents the explicit status state of an arbitrary processing sequence.
pub enum Status {
    /// The step finished with no warnings.
    Success,
    /// The step encountered a terminal abort criteria condition.
    Failure { code: u32, error: String },
}
```

**Output:**

```json
[
  {
    "namespace": "core::pipeline",
    "class_or_interface": "",
    "member": "PIPELINE_VERSION",
    "signature": "pub const PIPELINE_VERSION: &str = \"2.4.0\";",
    "summary": "Global version flag identifier for the execution pipeline."
  },
  {
    "namespace": "core::pipeline",
    "class_or_interface": "TransformPipeline",
    "member": "",
    "signature": "pub trait TransformPipeline<T>",
    "summary": "Defines a standardized behavioral protocol for data processing transformations."
  },
  {
    "namespace": "core::pipeline",
    "class_or_interface": "TransformPipeline",
    "member": "process",
    "signature": "fn process(&self, input: T) -> Result<T, String>",
    "summary": "Transforms the inner data payload structure."
  },
  {
    "namespace": "core::pipeline",
    "class_or_interface": "Status",
    "member": "",
    "signature": "pub enum Status",
    "summary": "Represents the explicit status state of an arbitrary processing sequence."
  },
  {
    "namespace": "core::pipeline",
    "class_or_interface": "Status",
    "member": "Success",
    "signature": "Success",
    "summary": "The step finished with no warnings."
  },
  {
    "namespace": "core::pipeline",
    "class_or_interface": "Status",
    "member": "Failure",
    "signature": "Failure { code: u32, error: String }",
    "summary": "The step encountered a terminal abort criteria condition."
  }
]
```

### INPUT DATA
""".strip()


def get_general_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert systems architect mapping legacy API elements to their new version counterparts. Analyze the semantic relationship and functional intent between the legacy source element in V1 and the potential target candidates in V2. You must select the correct target(s).

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```json
{{
  "v1_element": {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }},
  "potential_targets": [ {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }} ]
}}
```

**CRITICAL RULES:**
* For the 'reason' field, output ONLY valid Markdown.
* Use the 'reason' field to explicitly provide at least one valid technical reason for your selections, explaining how the chosen target(s) functionally relate to the original legacy element.
* If `selected_targets` contains multiple elements because you are unsure (AMBIGUOUS), use the 'reason' field to describe the specific conflict or similarity between the choices.
* If `selected_targets` is left empty (DEPRECATED), use the 'reason' field to detail the lack of an available replacement or its removal status.
* If there is exactly one clear, straightforward mapping in `selected_targets`, output an empty string "" for the 'reason'. Do NOT use "N/A", "None", or "Unchanged".

### OUTPUT FORMATTING
You must return a list of objects in the format below:

```json
[
  {{
    "v1_element": {{ ... }},
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
    }},
    {{
      "namespace": "org.modern.analytics",
      "class_or_interface": "TelemetryLogger",
      "member": "TrackDiskMetrics",
      "signature": "TrackDiskMetrics(event: LogEvent): Void",
      "summary": "Pushes low-level system diagnostic observations to the telemetry cloud backend."
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
  "selected_targets": [
    {{
      "namespace": "org.modern.storage",
      "class_or_interface": "VolumeManager",
      "member": "QueryAvailableBytes",
      "signature": "QueryAvailableBytes(mountPoint: Path): UInt64",
      "summary": "Returns available storage capacity for the specified path."
    }}
  ],
  "reason": "`VolumeManager.QueryAvailableBytes` is the direct structural equivalent for `FileSystem.GetFreeSpace`. Both operations accept a file system path string/object identifier and return an unsigned numerical value representing the unallocated storage block capacity within that specific partition boundary."
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
    }},
    {{
      "namespace": "org.modern.crypto",
      "class_or_interface": "PasswordHasher",
      "member": "GenerateSecureSalt",
      "signature": "GenerateSecureSalt(): String",
      "summary": "Generates a cryptographically strong random salt string for registration flows."
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
  "reason": "The monolithic transactional functionality of `UserClient.UpdateUserAndPermissions` is completely refactored across `ProfileService.UpdateBio` and `AccessControl.GrantScopes`. Replicating the legacy operation requires invoking `ProfileService` to modify the biographical user payload metadata alongside a distinct invocation of `AccessControl` to append the required application security authorization scopes."
}}
```

### INPUT DATA
""".strip()

def get_lexical_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert systems architect specializing in strict type safety and API contract mapping. Your objective is to map legacy API elements to their new version counterparts by analyzing raw signatures, parameter constraints, structural hierarchies, and formal code contracts from the source V1 element and the potential target V2 elements. You prioritize strict structural fit over loose semantic matching. You must select the correct target(s) and reevaluate the relationship logic (complexity).

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```json
{{
  "v1_element": {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }},
  "potential_targets": [ {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }} ]
}}
```

**CRITICAL RULES:**
* Evaluate return types, parameter count, and namespace hierarchies before reading the textual 'summary'.
* For the 'reason' field, output ONLY valid Markdown focusing on data contract transformations, type compatibility, or casting requirements.
* If there is exactly one clear, straightforward match by signature or exact type logic in `selected_targets`, output an empty string "" for the 'reason'.
* If `selected_targets` is left empty due to no matches or empty candidates, the item is implicitly treated as DEPRECATED. Use the 'reason' field to detail the lack of an available replacement or its removal status.

### OUTPUT FORMATTING
You must return a list of objects in the format below:

```json
[
  {{
    "v1_element": {{ ... }},
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
    }},
    {{
      "namespace": "org.modern.ui",
      "class_or_interface": "DisplayWidget",
      "member": "RenderGraph",
      "signature": "RenderGraph(data: Matrix): Void",
      "summary": "Draws the coordinate grid lines and plotting nodes onto the user interface canvas."
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
  "selected_targets": [
    {{
      "namespace": "org.modern.numeric",
      "class_or_interface": "Engine",
      "member": "Evaluate",
      "signature": "Evaluate(x: Int32, y: Float64): Float64",
      "summary": "Processes internal calculations."
    }}
  ],
  "reason": "`Engine.Evaluate` represents the direct algorithmic equivalent for `Calculator.Compute`. Both components ingest the primary numerical data values to execute low-level arithmetic calculations, whereas `DisplayWidget.RenderGraph` handles decoupled user interface rendering tasks."
}}
```

### INPUT DATA
""".strip()

def get_semantic_mapper_resolution_prompt():
    return f"""
### ROLE & OBJECTIVE
You are an expert Domain-Driven Design (DDD) Architect mapping legacy API components to their new version counterparts. Your objective is to map elements by evaluating behavioral semantics, functional side-effects, docstring intention, and business goals from both V1 elements and their corresponding target elements in V2. You look past signature transformations to ensure domain operations match up seamlessly. You must select the correct target(s) by evaluating the relationship logic between them.

### INSTRUCTIONS & GUIDELINES
You will receive a list of objects. Each object follows this structure:

```json
{{
  "v1_element": {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }},
  "potential_targets": [ {{ "namespace": str, "class_or_interface": str, "member": str, "signature": str, "summary": str }} ],
}}
```

**CRITICAL RULES:**
* Analyze the 'summary' and structural names for intent. Namespaces and type footprints change constantly during a rewrite—look at *what the code actually accomplishes*.
* For the 'reason' field, output ONLY valid Markdown explicitly documenting the architectural shift, domain decoupling pattern, or business rationale for your selections.
* If `selected_targets` contains an identical, un-decoupled behavioral mapping transition with exactly one element, output an empty string "" for the 'reason'.
* If `selected_targets` is left empty due to no matches or empty candidates, the item is implicitly treated as DEPRECATED. Use the 'reason' field to detail the lack of an available replacement or its removal status.

### OUTPUT FORMATTING
You must return a list of objects in the format below:

```json
[
  {{
    "v1_element": {{ ... }},
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
    }},
    {{
      "namespace": "org.modern.marketing",
      "class_or_interface": "NewsletterEngine",
      "member": "SubscribeEmail",
      "signature": "SubscribeEmail(email: String): Boolean",
      "summary": "Registers a target email address into the automated promotional recurring campaign mailing lists."
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
  "reason": "The compound transactional behaviors embedded within `CartManager.Finalize` have been unbundled across distinct subdomains. The state verification and purchase processing map directly to `OrderService.PlaceOrder`, while the shipping side-effects map to the specialized logistics pipeline managed by `FulfillmentHub.ScheduleDelivery`."
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


def get_directory_discovery_prompt() -> str:
    return """
### ROLE & OBJECTIVE
You are an expert repository analyzer. Your goal is to identify directories in a codebase that contain either:
1. Final, built/compiled API or library reference documentation artifacts (e.g., static HTML, built manuals, production-ready reference assets). Do NOT select directories containing the raw uncompiled documentation source files.
2. If no dedicated, final reference documentation directories exist, fall back to directories containing the primary production source code files for that API/library.

### CRITICAL EXCLUSION RULES
You must strictly ignore and exclude any directories or files that match the following criteria:
- **No Uncompiled Documentation Source Files:** Completely ignore directories dedicated to storing raw, uncompiled documentation markup/source files (e.g., raw markdown source structures, Sphinx `.rst` source trees, Doxygen configuration/source structures) if they are separate from the final deployment artifacts.
- **No Onboarding/Learning Content:** Completely ignore "getting started", "tutorials", "guides", "examples", "walkthroughs", "howto", or "help" directories/files.
- **No Narrative or Educational Prose:** Explicitly reject directories containing introductory prose, architecture overviews, conceptual explanations, "quickstarts", "readmes", or step-by-step onboarding guides.
- **No Non-Production Code:** Do not select test directories (`tests/`, `specs/`), build outputs (`dist/`, `build/`), configuration-only directories, benchmark scripts, or third-party dependencies (`node_modules/`, `vendor/`).

### STRUCTURAL SIGNIFIERS FOR PURE REFERENCE
Prioritize directories that exhibit signs of structured, machine-generated, or strictly organized final API layouts:
- Paths containing structural or distribution terms: `/api/`, `/reference/`, `/generated/`, `_apidoc/`, `/v1/`, `/html/`, `/site/`.
- Filenames matching code entities or final artifacts: e.g., `index.html`, `classes.html`, `functions.json`, `endpoints.yaml`, `class_*.md`, or files named directly after code modules.

### INSTRUCTIONS & GUIDELINES
1. Review the input JSON list containing directory absolute paths, top file extensions, and random file samples.
2. Evaluate candidates against the Objective, Exclusion Rules, and Structural Signifiers.
3. Prioritize finalized documentation deployment artifacts (such as HTML or JSON references) over raw documentation source directories.
4. If a documentation directory contains a mix of reference files and narrative/tutorial files, treat it as "polluted" and reject the entire directory if its primary purpose is instructional. Fall back to the core production source code instead.
5. Output your final answer as a JSON object matching the format shown in the examples below.

### EXAMPLES

**Input:**

```json
[
  {
    "path": "/workspace/project/docs/api_reference",
    "top_extensions": [".md"],
    "samples": ["authentication.md", "endpoints.md", "class_client.md"]
  },
  {
    "path": "/workspace/project/docs/tutorials",
    "top_extensions": [".md"],
    "samples": ["getting_started.md", "01_basic_setup.md"]
  },
  {
    "path": "/workspace/project/src",
    "top_extensions": [".py"],
    "samples": ["main.py"]
  }
]
```

**Output:**

```json
{
  "directories": [
    "/workspace/project/docs/api_reference"
  ]
}
```

---

**Input:**

```json
[
  {
    "path": "/workspace/project/examples/guides",
    "top_extensions": [".py"],
    "samples": ["simple_client.py", "quickstart.py"]
  },
  {
    "path": "/workspace/project/lib/core",
    "top_extensions": [".py"],
    "samples": ["connection.py", "router.py"]
  },
  {
    "path": "/workspace/project/tests",
    "top_extensions": [".py"],
    "samples": ["test_connection.py"]
  }
]
```

**Output:**

```json
{
  "directories": [
    "/workspace/project/lib/core"
  ]
}
```

---

**Input:**

```json
[
  {
    "path": "/workspace/project/docs",
    "top_extensions": [".md"],
    "samples": ["README.md", "introduction.md", "tutorial.md", "api_index.md"]
  },
  {
    "path": "/workspace/project/src/api",
    "top_extensions": [".py"],
    "samples": ["endpoints.py", "controllers.py"]
  }
]
```

**Output:**

```json
{
  "directories": [
    "/workspace/project/src/api"
  ]
}
```

---

**Input:**

```json
[
  {
    "path": "/workspace/project/docs/src/reference",
    "top_extensions": [".rst"],
    "samples": ["api_root.rst", "modules.rst"]
  },
  {
    "path": "/workspace/project/docs/build/html",
    "top_extensions": [".html", ".js"],
    "samples": ["index.html", "genindex.html", "api_client.html"]
  }
]
```

**Output:**

```json
{
  "directories": [
    "/workspace/project/docs/build/html"
  ]
}
```

### INPUT DATA
""".strip()