# LAMB

**L**LM-**A**ssisted Code **M**igration **B**ot

## The Migration Challenge

Migrating code between API versions is complex and error-prone due to breaking changes in namespaces, object models, and framework architectures. **LAMB** automates this by combining deterministic code analysis with the reasoning power of specialized LLM agents. 

LAMB creates mapping tables between codebases and uses those ground-truth rules to safely migrate legacy code to modern standards without hallucination.

---

## Installation

LAMB is packaged using a modern Python `src` layout. To install the tool globally or within your virtual environment, run the following from the root directory:

```bash
git clone https://github.com/gabriel-gubert/LAMB.git
cd LAMB
pip install -e .
```

Once installed, the `lamb` command will be available globally in your terminal.

---

## Quick Start

### 1. Generate a Mapping Table
Analyze a legacy and modern codebase to generate a conflict-free mapping table.
```bash
lamb map ./legacy_api_v1 ./modern_api_v2 --output map.json --alias my_api_alias
```

### 2. Migrate Legacy Code
Use the registered mapping table to translate legacy code, reading from a file and piping to a new file.
```bash
lamb migrate -f legacy_script.py --alias my_api_alias > modern_script.py
```

### 3. Manage Configuration
View and edit your settings seamlessly from the command line.
```bash
lamb config --list
lamb config --global general.verbose true
```

---

## Configuration Architecture

LAMB features a highly granular, 4-tier cascading configuration system. Settings are resolved in the following priority order (1 being the highest):

1. **Specific Agent CLI Flags:** (e.g., `--migration-model o1`)
2. **General CLI Flags:** (e.g., `--model gpt-4o`)
3. **Local Config File:** `./.lambconfig.toml` (Project-specific)
4. **Global Config File:** `~/.lamb/config.toml` (User-wide)

### File Format
Configuration files use standard TOML format. Here is a fully loaded example:

```toml
[general]
verbose = true

[tasks.default]
model = "gpt-4o"
temperature = 0.7
max_tokens = 2048

[tasks.mapping]
confidence_threshold = 0.95

[tasks.migration]
summarization_threshold = 1000

# Overriding a specific sub-agent
[tasks.summarization]
model = "gpt-4o-mini"
temperature = 0.3
```

---

## Exhaustive Configuration Reference

Every single setting in LAMB can be defined in the TOML files or overridden via CLI flags.

### 1. Global & Tuning Settings
These settings control the application's verbosity and internal algorithm thresholds.

| TOML Key Path | CLI Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `general.verbose` | `--verbose` | Boolean | `None` | Enables detailed logging for prompt payloads and agent reasoning. |
| `tasks.migration.summarization_threshold` | `--summarization-threshold` | Integer | `2048` | Max character length of legacy documentation before the summarizer agent is invoked. |
| `tasks.mapping.confidence_threshold` | `--confidence-threshold` | Float | `0.92` | Minimum similarity score required to auto-map elements without the resolution agent. |
| `tasks.mapping.ambiguous_margin` | `--ambiguous-margin` | Float | `0.05` | Score margin that triggers the resolution agent to decide between competing mappings. |
| `tasks.mapping.resolver_batch_size` | `--resolver-batch-size` | Integer | `20` | Number of conflicts passed to the resolution agent in a single LLM prompt. |

### 2. Shared LLM Parameters
These core parameters configure the LLM connection. When used as **General CLI Flags** (e.g., `--model`), they apply to *all* agents invoked by the current command.

| TOML Key Path (Default) | General CLI Flag | Type | Description |
| :--- | :--- | :--- | :--- |
| `tasks.default.model` | `--model` | String | Model ID (e.g., `gpt-4o`, `o3-mini`, `llama-3`). |
| `tasks.default.temperature` | `--temperature` | Float | Sampling temperature (0.0 to 1.0). |
| `tasks.default.max_tokens` | `--max-tokens` | Integer | Maximum tokens generated in the response. |
| `tasks.default.timeout` | `--timeout` | Integer | API request timeout in seconds. |
| `tasks.default.max_retries` | `--max-retries` | Integer | Maximum retry attempts for failed API calls. |
| `tasks.default.api_key` | `--api-key` | String | Authentication key (use "EMPTY" for local vLLM). |
| `tasks.default.base_url` | `--base-url` | String | Custom endpoint URL for local APIs (e.g., `http://127.0.0.1:8000/v1`). |

### 3. Agent-Specific Overrides
For extreme precision, you can target individual agents within a command to optimize for cost, speed, or reasoning capabilities. 

Substitute `<param>` with any of the 7 Shared LLM Parameters above (e.g., `--[agent]-model`, `--[agent]-temperature`, `--[agent]-base-url`). 

If using TOML, place these under the `[tasks.<agent_name>]` section.

#### Map Command Agents
* **`--extraction-<param>`**: Controls the agent responsible for reading source code and extracting structural data.
* **`--embedding-<param>`**: Controls the agent responsible for vectorizing the extracted logic.
* **`--resolution-<param>`**: Controls the agent responsible for resolving complex, ambiguous mapping conflicts.

#### Migrate Command Agents
* **`--detection-<param>`**: Controls the agent that identifies legacy patterns within the target file.
* **`--summarization-<param>`**: Controls the agent that compresses massive documentation strings to save context window space.
* **`--migration-<param>`**: Controls the core generation agent responsible for safely writing the modern code block.

---

## Advanced Usage Example

Here is an example of leveraging the cascading CLI to optimize a migration run:

```bash
lamb migrate -f core.cpp --alias v2_map \
  --model gpt-4o-mini \
  --migration-model o1 \
  --summarization-temperature 0.0 \
  --summarization-threshold 500
```
**What this command does:**
1. Sets the default model to the fast/cheap `gpt-4o-mini` for the overall run (used by the detection agent).
2. Overrides the core migration agent to use the high-reasoning `o1` model for safety.
3. Overrides the summarizer agent's temperature to `0.0` for highly deterministic text compression.
4. Lowers the summarization threshold to `500` characters, forcing the summarizer to run more frequently.

### Citation

If you use **LAMB** in your research or wish to refer to the methodology described in our work, please cite the following paper:

```bibtex
@inproceedings{Gubert2026,
  author    = {Gubert, Gabriel Vitor Klaumann and Kugele, Stefan and Georges, Munir},
  title     = {A Hybrid LLM-Guided Approach to Code Migration Using API-Derived Rules},
  booktitle = {2026 IEEE/ACM Third International Conference on AI Foundation Models and Software Engineering (FORGE '26)},
  year      = {2026},
  pages     = {5},
  location  = {Rio de Janeiro, Brazil},
  publisher = {ACM},
  address   = {New York, NY, USA},
  doi       = {10.1145/3793655.3793734},
  url       = {https://doi.org/10.1145/3793655.3793734}
}