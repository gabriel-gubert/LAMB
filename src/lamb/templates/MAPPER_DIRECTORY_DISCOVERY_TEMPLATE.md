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