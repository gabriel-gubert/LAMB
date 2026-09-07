class ConfigSchema:
    GLOBAL_CONFIG_FLAGS = [
        {
            "flags": ["--verbose"],
            "kwargs": {"action": "store_true", "default": None, "help": "Enable Verbose Output."},
            "config_path": "general.verbose"
        },
        {
            "flags": ["--litellm-host"],
            "kwargs": {"type": str, "help": "Override LiteLLM Proxy Host IP (defaults to \"127.0.0.1\")."},
            "config_path": "general.litellm.host"
        },
        {
            "flags": ["--litellm-port"],
            "kwargs": {"type": int, "help": "Override LiteLLM Proxy Port (defaults to 4000)."},
            "config_path": "general.litellm.port"
        },
        {
            "flags": ["--litellm-config-file"],
            "kwargs": {"type": str, "help": "Path to Custom LiteLLM Proxy YAML Config File."},
            "config_path": "general.litellm.config_file"
        },
        {
            "flags": ["--disable-litellm"],
            "kwargs": {"action": "store_false", "dest": "litellm_enabled", "default": None, "help": "Disable LiteLLM Proxy globally."},
            "config_path": "general.litellm.enabled"
        }
    ]

    COMMANDS = {
        "config": {
            "help": "Manage configuration (git-style)",
            "args": [
                {"flags": ["--global"], "kwargs": {"action": "store_true", "dest": "global_scope", "help": "Edit Global Configuration File."}},
                {"flags": ["--list"], "kwargs": {"action": "store_true", "help": "List ALL Key-Value Configuration Pairs from both Global and Local Configuration Files."}},
                {"flags": ["key"], "kwargs": {"nargs": "?", "help": "Configuration Key (e.g., tasks.migration.migration.model)."}},
                {"flags": ["value"], "kwargs": {"nargs": "?", "help": "Configuration Value (e.g. \"gemini-1.5-flash\")."}}
            ]
        },
        "migrate": {
            "help": "Migrate Source Code from a Source Version to a Target Version of a Library/SDK/API based on a Mapping Table.",
            "args": [
                {"flags": ["-f", "--file"], "kwargs": {"help": "Legacy Code File (defaults to stdin)."}},
                {"flags": ["-o", "--output"], "kwargs": {"help": "Output Path to the Migrated Code (e.g., \"./code_v2.cpp\")."}},
                {"flags": ["--alias"], "kwargs": {"required": True, "help": "Alias of the Mapping Table Alias to use."}},
                {"flags": ["--critical"], "kwargs": {"nargs": "+", "type": str, "default": [], "help": "List of highlight ranges (e.g., '14:12-14:34' '14-18' 'foo()') tagged as CRITICAL priority."}},
                {"flags": ["--warning"], "kwargs": {"nargs": "+", "type": str, "default": [], "help": "List of highlight ranges (e.g., '14:12-14:34' '14-18' 'bar()') tagged as WARNING priority."}},
                {"flags": ["--info"], "kwargs": {"nargs": "+", "type": str, "default": [], "help": "List of highlight ranges (e.g., '14:12-14:34' '14-18' 'baz()') tagged as INFO priority."}},
                {"flags": ["--dont-touch"], "kwargs": {"nargs": "+", "type": str, "default": [], "help": "List of protected ranges (e.g., '14:12-14:34' '14-18' 'qux()') tagged as DONT_TOUCH priority to prevent modification."}},
                {"flags": ["--user-comments"], "kwargs": {"type": str, "default": "", "help": "Custom developer migration instructions or notes."}}
            ],
            "config_overrides": [
                {"flags": ["--summarization-threshold"], "kwargs": {"type": int, "help": "Override Token Threshold for Summarization"}, "config_path": "tasks.migration.summarization_threshold"},
                {"flags": ["--max-attempts"], "kwargs": {"type": int, "help": "Override Maximum Number of Migration Attempts"}, "config_path": "tasks.migration.max_attempts"},
                {"flags": ["--report"], "kwargs": {"type": str, "help": "File path to save the migration confidence and audit report JSON"}, "config_path": "tasks.migration.report"}
            ],
            "agents": [
                "tasks.migration.migration",
                "tasks.migration.summarization",
                "tasks.migration.detection"
            ]
        },
        "map": {
            "help": "Generate the Mapping Table from a Source Version to a Target Version of a Library/SDK/API based on Codebase/Documentation.",
            "args": [
                {"flags": ["path_v1"], "kwargs": {"help": "Path to the Source Version Codebase/Documentation Root Directory."}},
                {"flags": ["path_v2"], "kwargs": {"help": "Path to the Target Version Codebase/Documentation Root Directory."}},
                {"flags": ["--alias"], "kwargs": {"required": True, "help": "Alias for the Mapping Table."}},
                {"flags": ["--thread-id"], "kwargs": {"type": str, "default": "", "help": "Identificator for the CURRENT Mapper Agent Run. Used to SAVE/LOAD LangGraph's Checkpoints TO/FROM the SQLite 3 Database File."}},
                {"flags": ["-o", "--output"], "kwargs": {"help": "Output Path of the Mapping Table (e.g., \"./SynthNetLib.json\")."}},
            ],
            "config_overrides": [
                {"flags": ["--multi-agent"], "kwargs": {"action": "store_true", "default": None, "help": "Enable Multi-Agent Consensus Resolution."}, "config_path": "tasks.mapping.multi_agent"},
                {"flags": ["--no-multi-agent"], "kwargs": {"action": "store_false", "default": None, "help": "Disable Multi-Agent Consensus Resolution."}, "config_path": "tasks.mapping.multi_agent"},
                {"flags": ["--resolver-batch-size"], "kwargs": {"type": int, "default": 20, "help": "Override Resolver Agent Batch Size."}, "config_path": "tasks.mapping.resolver_batch_size"},
                {"flags": ["--discovery-batch-size"], "kwargs": {"type": int, "default": 20, "help": "Override the Discovery Agent Batch Size."}, "config_path": "tasks.mapping.discovery_batch_size"},
                {"flags": ["--stage-output-dir"], "kwargs": {"help": "Override Stage Output Directory."}, "config_path": "tasks.mapping.stage_output_dir"},
                {"flags": ["--checkpoint-database-path"], "kwargs": {"help": "Override the Path to the SQLite 3 Database File to use for LangGraph's Checkpoints. Defaults to \"~/.lamb/map_checkpoint.db\"."}, "config_path": "tasks.mapping.checkpoint_database_path"},
                {"flags": ["--tmp-dir"], "kwargs": {"help": "Override the Path to the TEMP File Directory. Defaults to \"~/.lamb/tmp\"."}, "config_path": "tasks.mapping.tmp_dir"}
            ],
            "agents": [
                "tasks.mapping.extraction",
                "tasks.mapping.discovery",
                "tasks.mapping.embedding",
                "tasks.mapping.general_resolution",
                "tasks.mapping.lexical_resolution",
                "tasks.mapping.semantic_resolution"
            ]
        }
    }