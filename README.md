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

---

## Exhaustive Configuration Reference

Every setting in LAMB can be defined in the TOML files or overridden via CLI flags.

### 1. Global & Tuning Settings

These settings control the application's verbosity and internal algorithm thresholds.

| TOML Key Path | CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `general.verbose` | `--verbose` | Boolean | `None` | Enables detailed logging for prompt payloads and agent reasoning. |
| `tasks.migration.summarization_threshold` | `--summarization-threshold` | Integer | `2048` | Max character length of legacy documentation before the summarizer agent is invoked. |
| `tasks.mapping.multi_agent` | `--multi-agent` | Boolean | `True` | Whether or not to use multiple agent consensus. |
| `tasks.mapping.confidence_threshold` | `--confidence-threshold` | Float | `0.92` | Minimum similarity score required to auto-map elements without the resolution agent. |
| `tasks.mapping.confidence_floor` | `--confidence-floor` | Float | `0.65` | Minimum similarity score required not to discard an element as a potential mapping target. |
| `tasks.mapping.ambiguous_margin` | `--ambiguous-margin` | Float | `0.05` | Score margin that triggers the resolution agent to decide between competing mappings. |
| `tasks.mapping.resolver_batch_size` | `--resolver-batch-size` | Integer | `20` | Number of conflicts passed to the resolution agent in a single LLM prompt. |

### 2. Shared LLM & Generation Parameters

These parameters configure the primary LLM connection and generation behavior for all agents.

| TOML Key Path (under `tasks.default`) | General CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `model` | `--model` | String | `gpt-4o` | Model ID (e.g., `gpt-4o`, `o3-mini`). |
| `api_key` | `--api-key` | String | `None` | Authentication key. |
| `base_url` | `--base-url` | String | `None` | Custom endpoint URL for local APIs. |
| `organization` | `--organization` | String | `None` | Organization ID for API requests. |
| `temperature` | `--temperature` | Float | `0.7` | Sampling temperature (0.0 to 1.0). |
| `max_tokens` | `--max-tokens` | Integer | `None` | Maximum tokens generated in the response. |
| `top_p` | `--top-p` | Float | `None` | Nucleus sampling probability mass. |
| `frequency_penalty` | `--frequency-penalty` | Float | `None` | Penalty for token frequency (prevents repetition). |
| `presence_penalty` | `--presence-penalty` | Float | `None` | Penalty for token presence (encourages new topics). |
| `n` | `--n` | Integer | `1` | Number of chat completions to generate. |
| `seed` | `--seed` | Integer | `None` | Integer for deterministic sampling. |
| `stop` | `--stop` | List | `None` | List of strings to stop generation. |
| `logprobs` | `--logprobs` | Boolean | `None` | Whether to return log probabilities. |
| `top_logprobs` | `--top-logprobs` | Integer | `None` | Number of logprobs to return. |
| `logit_bias` | `--logit-bias` | Dict | `None` | Modify likelihood of specific tokens. |

### 3. Embedding Specific Parameters

Used specifically by the **Embedding Agent** during the mapping phase.

| TOML Key Path (under `tasks.embedding`) | CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `model` | `--embedding-model` | String | `text-embedding-3-small` | Embedding model ID. |
| `dimensions` | `--embedding-dimensions` | Integer | `None` | Explicitly set output dimensions. |
| `chunk_size` | `--embedding-chunk-size` | Integer | `1000` | Number of texts to embed in a single batch. |
| `skip_empty` | `--embedding-skip-empty` | Boolean | `False` | Drop empty strings from the input. |
| `show_progress_bar` | `--embedding-show-progress-bar` | Boolean | `False` | Track large bulk embeddings. |

### 4. Connection & Advanced Kwargs

Low-level settings for connection handling and tokenization.

| TOML Key Path (under `tasks.default`) | CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `timeout` | `--timeout` | Integer | `None` | API request timeout in seconds. |
| `max_retries` | `--max-retries` | Integer | `2` | Maximum retry attempts for failed API calls. |
| `streaming` | `--streaming` | Boolean | `False` | Enable real-time token streaming. |
| `tiktoken_enabled` | `--tiktoken-enabled` | Boolean | `True` | Enable local token counting. |
| `tiktoken_model_name` | `--tiktoken-model-name` | String | `None` | Override for token counting model. |
| `model_kwargs` | N/A | Dict | `None` | Extra parameters for the provider. |
| `default_headers` | N/A | Dict | `None` | Custom HTTP headers. |
| `default_query` | N/A | Dict | `None` | Custom URL query parameters. |

---

## Agent-Specific Overrides

To optimize for cost or reasoning, you can target individual agents. Every parameter in sections 2, 3, and 4 can be prefixed with the agent name.

#### Map Command Agents

* **`--extraction-<param>`**: Configuration for code structural data extraction.
* **`--embedding-<param>`**: Configuration for vectorization (uses embedding defaults).
* **`--resolution-<param>`**: Configuration for the conflict-resolution logic.

#### Migrate Command Agents

* **`--detection-<param>`**: Configuration for legacy pattern identification.
* **`--summarization-<param>`**: Configuration for document compression.
* **`--migration-<param>`**: Configuration for the core generation agent.

---

## Advanced Usage Example

```bash
lamb migrate -f core.cpp --alias v2_map \
  --model gpt-4o-mini \
  --migration-model o1 \
  --migration-seed 42 \
  --summarization-temperature 0.0 \
  --summarization-stop "['END']"

```

---

## Citation

If you use **LAMB** in your research, please cite the following paper:

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
```