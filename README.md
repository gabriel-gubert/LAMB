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
lamb config tasks.migration.migration.model gemini-1.5-flash

```

---

## Configuration Architecture

LAMB features a granular, cascading configuration system. Settings are resolved in the following priority order (1 being the highest):

1. **CLI Flags & Overrides:**
   - Agent Configuration Options (`--configure-<agent>`)
   - Command Tuning Settings / Overrides (e.g., `--summarization-threshold`, `--multi-agent`, `--resolver-batch-size`)
   - Global Config Flags (e.g., `--verbose`, `--litellm-port`)
2. **Local Config File:** `./.lambconfig.toml` (Project-specific)
3. **Global Config File:** `~/.lamb/config.toml` (User-wide)

Within configuration files, agent parameters cascade hierarchically:
`tasks.<agent>` (e.g., `tasks.migration.migration`) &rarr; `tasks.default` &rarr; `general`.

---

## Exhaustive Configuration Reference

Every setting in LAMB can be defined in TOML configuration files or overridden via CLI flags.

### 1. Global Configuration Flags

These flags control global application behavior and proxy networking across commands.

| TOML Key Path | CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `general.verbose` | `--verbose` | Boolean | `None` | Enable Verbose Output. |
| `general.litellm.host` | `--litellm-host` | String | `"127.0.0.1"` | Override LiteLLM Proxy Host IP. |
| `general.litellm.port` | `--litellm-port` | Integer | `4000` | Override LiteLLM Proxy Port. |
| `general.litellm.config_file` | `--litellm-config-file` | String | `None` | Path to Custom LiteLLM Proxy YAML Config File. |
| `general.litellm.enabled` | `--disable-litellm` | Boolean | `True` | Disable LiteLLM Proxy globally. |

### 2. Command Reference & Tuning Settings

#### `lamb migrate`

Migrate Source Code from a Source Version to a Target Version of a Library/SDK/API based on a Mapping Table.

**Command Arguments:**

| Argument / Flag | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `-f`, `--file` | String | No | `stdin` | Legacy Code File (defaults to stdin). |
| `-o`, `--output` | String | No | `stdout` | Output Path to the Migrated Code (e.g., `./code_v2.cpp`). |
| `--alias` | String | **Yes** | — | Alias of the Mapping Table Alias to use. |
| `--critical` | List[String] | No | `[]` | List of highlight ranges (e.g., `'14:12-14:34'` `'14-18'` `'foo()'`) tagged as CRITICAL priority. |
| `--warning` | List[String] | No | `[]` | List of highlight ranges (e.g., `'14:12-14:34'` `'14-18'` `'bar()'`) tagged as WARNING priority. |
| `--info` | List[String] | No | `[]` | List of highlight ranges (e.g., `'14:12-14:34'` `'14-18'` `'baz()'`) tagged as INFO priority. |
| `--dont-touch` | List[String] | No | `[]` | List of protected ranges (e.g., `'14:12-14:34'` `'14-18'` `'qux()'`) tagged as DONT_TOUCH priority to prevent modification. |
| `--user-comments` | String | No | `""` | Custom developer migration instructions or notes. |

**Tuning Settings (Config Overrides):**

| TOML Key Path | CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `tasks.migration.summarization_threshold` | `--summarization-threshold` | Integer | `2048` | Override Token Threshold for Summarization. |
| `tasks.migration.max_attempts` | `--max-attempts` | Integer | `3` | Override Maximum Number of Migration Attempts. |
| `tasks.migration.report` | `--report` | String | `None` | File path to save the migration confidence and audit report JSON. |
| `tasks.migration.logprobs` | `--logprobs` | Boolean | `False` | Uses model log probabilities to improve score calculations. |

#### `lamb map`

Generate the Mapping Table from a Source Version to a Target Version of a Library/SDK/API based on Codebase/Documentation.

**Command Arguments:**

| Argument / Flag | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path_v1` | String | **Yes** | — | Path to the Source Version Codebase/Documentation Root Directory. |
| `path_v2` | String | **Yes** | — | Path to the Target Version Codebase/Documentation Root Directory. |
| `--alias` | String | **Yes** | — | Alias for the Mapping Table. |
| `--thread-id` | String | No | `""` | Identificator for the CURRENT Mapper Agent Run. Used to SAVE/LOAD LangGraph's Checkpoints TO/FROM the SQLite 3 Database File. |
| `-o`, `--output` | String | No | `None` | Output Path of the Mapping Table (e.g., `./SynthNetLib.json`). |

**Tuning Settings (Config Overrides):**

| TOML Key Path | CLI Flag | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `tasks.mapping.multi_agent` | `--multi-agent` | Boolean | `False` | Enable Multi-Agent Consensus Resolution. |
| `tasks.mapping.multi_agent` | `--no-multi-agent` | Boolean | `False` | Disable Multi-Agent Consensus Resolution. |
| `tasks.mapping.resolver_batch_size` | `--resolver-batch-size` | Integer | `20` | Override Resolver Agent Batch Size. |
| `tasks.mapping.discovery_batch_size` | `--discovery-batch-size` | Integer | `20` | Override the Discovery Agent Batch Size. |
| `tasks.mapping.stage_output_dir` | `--stage-output-dir` | String | `None` | Override Stage Output Directory. |
| `tasks.mapping.checkpoint_database_path` | `--checkpoint-database-path` | String | `"~/.lamb/map_checkpoint.db"` | Override the Path to the SQLite 3 Database File to use for LangGraph's Checkpoints. |
| `tasks.mapping.tmp_dir` | `--tmp-dir` | String | `"~/.lamb/tmp"` | Override the Path to the TEMP File Directory. |

#### `lamb config`

Manage configuration (git-style).

**Command Arguments:**

| Argument / Flag | Type | Required | Description |
| --- | --- | --- | --- |
| `--global` | Flag | No | Edit Global Configuration File (`~/.lamb/config.toml`). |
| `--list` | Flag | No | List ALL Key-Value Configuration Pairs from both Global and Local Configuration Files. |
| `key` | String | No | Configuration Key (e.g., `tasks.migration.migration.model`). |
| `value` | String | No | Configuration Value (e.g., `"gemini-1.5-flash"`). |

---

## Agent Configuration Options

Each command supports configuring its constituent agents via kebab-case `--configure-<agent>` CLI flags, which accept either an inline JSON string or a path to a JSON file.

### Migrate Command Agents

* **`--configure-migration`**: JSON string or path to JSON file to configure the Migration agent (`tasks.migration.migration`).
* **`--configure-summarization`**: JSON string or path to JSON file to configure the Summarization agent (`tasks.migration.summarization`).
* **`--configure-detection`**: JSON string or path to JSON file to configure the Detection agent (`tasks.migration.detection`).

### Map Command Agents

* **`--configure-extraction`**: JSON string or path to JSON file to configure the Extraction agent (`tasks.mapping.extraction`).
* **`--configure-discovery`**: JSON string or path to JSON file to configure the Discovery agent (`tasks.mapping.discovery`).
* **`--configure-embedding`**: JSON string or path to JSON file to configure the Embedding agent (`tasks.mapping.embedding`).
* **`--configure-general-resolution`**: JSON string or path to JSON file to configure the General Resolution agent (`tasks.mapping.general_resolution`).
* **`--configure-lexical-resolution`**: JSON string or path to JSON file to configure the Lexical Resolution agent (`tasks.mapping.lexical_resolution`).
* **`--configure-semantic-resolution`**: JSON string or path to JSON file to configure the Semantic Resolution agent (`tasks.mapping.semantic_resolution`).

---

## TOML Configuration Reference (LLM & Agent Parameters)

In addition to CLI flags, agents can be configured via TOML configuration files (`.lambconfig.toml` or `~/.lamb/config.toml`). Default settings apply under `[tasks.default]`, while individual agents are configured under their respective sections (e.g., `[tasks.migration.migration]` or `[tasks.mapping.embedding]`).

LAMB instantiates agents using custom wrappers around LangChain components:
- **`RateLimitedChatOpenAI`** (extends [`ChatOpenAI`](https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html)) for chat and code generation agents.
- **`RateLimitedOpenAIEmbeddings`** (extends [`OpenAIEmbeddings`](https://python.langchain.com/api_reference/openai/embeddings/langchain_openai.embeddings.base.OpenAIEmbeddings.html)) for the mapping embedding agent (`[tasks.mapping.embedding]`).

### 1. LangChain Native Parameters

All standard LangChain parameters for `ChatOpenAI` (e.g., `model`, `temperature`, `api_key`, `base_url`, `organization`, `max_tokens`, `timeout`, `max_retries`, etc.) and `OpenAIEmbeddings` (e.g., `model`, `dimensions`, `chunk_size`, etc.) are natively supported and passed directly to the underlying LangChain classes. 

Please refer to LangChain's official documentation for parameter references and configuration options:
* [LangChain `ChatOpenAI` Documentation](https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html)
* [LangChain `OpenAIEmbeddings` Documentation](https://python.langchain.com/api_reference/openai/embeddings/langchain_openai.embeddings.base.OpenAIEmbeddings.html)

### 2. Custom LAMB Rate-Limiting & Proxy Parameters

LAMB extends LangChain's components via [`src/lamb/rate_limited_chat.py`](src/lamb/rate_limited_chat.py) with thread-safe client-side rate limiting and proxy integration:

| TOML Key Path (under `tasks.default` or agent section) | Type | Default | Description |
| --- | --- | --- | --- |
| `requests_per_minute` | Float | `0.0` | Maximum Requests Per Minute (RPM) allowed. When `> 0.0`, client-side rate limiting enforces delays between calls to avoid exceeding the RPM budget. Disabled if `0.0`. |
| `tokens_per_minute` | Integer | `0` | Maximum Tokens Per Minute (TPM) allowed. When `> 0`, client-side rate limiting tracks token usage across a rolling 60-second window (estimating input tokens via `tiktoken` and adding actual usage from response metadata) and pauses execution when the limit is approached or exceeded. Disabled if `0`. |
| `use_litellm` | Boolean | `true` | When `true`, automatically configures `base_url` and fallback credentials to route requests through the local LiteLLM proxy (`http://<litellm_host>:<litellm_port>/v1`). Set to `false` to communicate directly with custom or provider endpoints. |

---

## Advanced Usage Example

### Using CLI Flags

```bash
lamb migrate -f core.cpp --alias v2_map \
  --verbose \
  --summarization-threshold 4096 \
  --configure-migration '{"model": "o1", "seed": 42, "requests_per_minute": 30.0}' \
  --configure-summarization '{"temperature": 0.0, "tokens_per_minute": 50000}'
```

### Using TOML Configuration

```toml
[general]
verbose = true

[tasks.default]
model = "gpt-4o-mini"
requests_per_minute = 60.0
tokens_per_minute = 100000

[tasks.migration]
summarization_threshold = 4096
max_attempts = 3

[tasks.migration.migration]
model = "o1"
temperature = 0.2

[tasks.migration.summarization]
temperature = 0.0
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