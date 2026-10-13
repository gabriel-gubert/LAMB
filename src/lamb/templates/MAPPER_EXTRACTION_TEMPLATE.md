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

* **namespace**: The full package, namespace, or module path. Must be a clean, unformatted string. Use a sensible default or leave empty if completely absent.
* **class_or_interface**: The name of the containing class, interface, struct, trait, or enum. Must be a clean, unformatted string. Leave this blank ONLY for standalone top-level elements that genuinely lack a parent container. If you are extracting the container itself, place its name here.
* **member**: The name of the specific function, method, constant, macro, or variant. Must be a clean, unformatted string. Leave this blank `""` if the current record represents the container itself.
* **signature**: The full technical signature (including name, modifiers, parameters, return types, or HTTP verbs). For elements without complex signatures (like global constants or enum variants), copy the exact declaration line. Strip any Markdown/Markup container markers while preserving all native programming language syntax.
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

```markdown
# Module: api.v1.auth

Global API authentication service configuration and identity management protocol interface. For full architectural specifications, view the [Authentication Architecture Guide](https://docs.example.com/api/v1/auth/architecture).

## Constants

### `TOKEN_EXPIRATION_SECONDS`
```python
TOKEN_EXPIRATION_SECONDS: int = 3600
```

The global Time-To-Live (TTL) duration in seconds for generated session tokens across all OAuth2 workers.

* **Default Value:** `3600` (1 hour)
* **Scope:** Cluster-wide session store state

---

## Classes

# Class: AuthClient

Primary HTTP authentication interface interacting with identity tokens. Implements the [`IBaseAuthClient`](https://www.google.com/url?sa=E&source=gmail&q=https://docs.example.com/api/v1/interfaces/IBaseAuthClient) abstract protocol contract.

### Method: `login`

```python
@observe_telemetry
async def login(credentials: Dict[str, str]) -> AuthToken
```

Authenticates a user against the central identity provider using standard credentials payload.

#### Parameters:

* `credentials`: A dictionary structure containing the identity payload parameters:
* `username`: The unique user handle or email string.
* `password`: The raw plain-text password string.

#### Returns:

* `AuthToken`: An active session token object representing the verified session identity.

#### Raises:

* `AuthenticationError`: Raised when credentials verification fails against the backing database layer.
```

**Output:**

```json
[
    {
        "namespace": "api.v1.auth",
        "class_or_interface": "",
        "member": "TOKEN_EXPIRATION_SECONDS",
        "signature": "TOKEN_EXPIRATION_SECONDS: int = 3600",
        "summary": "The global Time-To-Live (TTL) duration in seconds for generated session tokens across all OAuth2 workers.\n\n* **Default Value:** `3600` (1 hour)\n* **Scope:** Cluster-wide session store state"
    },
    {
        "namespace": "api.v1.auth",
        "class_or_interface": "AuthClient",
        "member": "",
        "signature": "Class: AuthClient",
        "summary": "Primary HTTP authentication interface interacting with identity tokens. Implements the [`IBaseAuthClient`](https://docs.example.com/api/v1/interfaces/IBaseAuthClient) abstract protocol contract."
    },
    {
        "namespace": "api.v1.auth",
        "class_or_interface": "AuthClient",
        "member": "login",
        "signature": "@observe_telemetry\nasync def login(credentials: Dict[str, str]) -> AuthToken",
        "summary": "Authenticates a user against the central identity provider using standard credentials payload.\n\n#### Parameters:\n* `credentials`: A dictionary structure containing the identity payload parameters:\n  * `username`: The unique user handle or email string.\n  * `password`: The raw plain-text password string.\n\n#### Returns:\n* `AuthToken`: An active session token object representing the verified session identity.\n\n#### Raises:\n* `AuthenticationError`: Raised when credentials verification fails against the backing database layer."
    }
]
```

---

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