from .langchain_blueprints import *

def get_shared_parameters(blueprints: list[dict]) -> list[dict]:
    """
    Combines multiple blueprints into a unique list of parameters 
    formatted for argparse.
    """

    unique_params = {}

    for bp in blueprints:
        for key in bp.keys():
            if key not in unique_params:
                # Get the type from our registry, default to str if unknown
                param_type = PARAM_TYPES.get(key, str)

                unique_params[key] = {
                    "param": key,
                    "type": param_type,
                    "help": f"Configure the {key} parameter"
                }

    return list(unique_params.values())

class ConfigSchema:
    SHARED_PARAMETERS = get_shared_parameters([
        CHATOPENAI_DEFAULT_BLUEPRINT,
        OPENAIEMBEDDINGS_DEFAULT_BLUEPRINT
    ])

    GLOBAL_CONFIG_FLAGS = [
        {"flags": ["--verbose"], "kwargs": {"action": "store_true", "default": None, "help": "Enable verbose output"}, "config_path": "general.verbose"}
    ]

    COMMANDS = {
        "config": {
            "help": "Manage configuration (git-style)",
            "args": [
                {"flags": ["--global"], "kwargs": {"action": "store_true", "dest": "global_scope", "help": "Edit global config"}},
                {"flags": ["--list"], "kwargs": {"action": "store_true", "help": "List all configurations"}},
                {"flags": ["key"], "kwargs": {"nargs": "?", "help": "Config key (e.g., tasks.migration.model)"}},
                {"flags": ["value"], "kwargs": {"nargs": "?", "help": "Value to set"}}
            ]
        },
        "migrate": {
            "help": "Migrate code snippet",
            "args": [
                {"flags": ["-f", "--file"], "kwargs": {"help": "Legacy code file (defaults to stdin)"}},
                {"flags": ["-o", "--output"], "kwargs": {"help": "Path to save the migrated code (e.g., code_v2.cpp)"}},
                {"flags": ["--alias"], "kwargs": {"required": True, "help": "Mapping table alias to use"}}
            ],
            "config_overrides": [
                {"flags": ["--summarization-threshold"], "kwargs": {"type": int, "help": "Override token threshold for summarization"}, "config_path": "tasks.migration.summarization_threshold"}
            ],
            "agents": ["migration", "summarization", "detection"]
        },
        "map": {
            "help": "Generate a mapping table from two versions of a library/SDK/API based on documentation",
            "args": [
                {"flags": ["path_v1"], "kwargs": {"help": "Path to the legacy (v1) codebase/documentation directory"}},
                {"flags": ["path_v2"], "kwargs": {"help": "Path to the current (v2) codebase/documentation directory"}},
                {"flags": ["--alias"], "kwargs": {"required": True, "help": "Alias to register the mapping table under"}},
                {"flags": ["-o", "--output"], "kwargs": {"help": "Path to save the generated mapping (e.g., map.json)"}},
            ],
            "config_overrides": [
                {"flags": ["--multi-agent"], "kwargs": {"action": "store_true", "default": None, "help": "Enable multi-agent consensus resolution"}, "config_path": "tasks.mapping.multi_agent"},
                {"flags": ["--no-multi-agent"], "kwargs": {"action": "store_false", "default": None, "help": "Disable multi-agent consensus resolution (single agent)"}, "config_path": "tasks.mapping.multi_agent"},
                {"flags": ["--confidence-floor"], "kwargs": {"type": float, "help": "Override mapping confidence floor"}, "config_path": "tasks.mapping.confidence_floor"},
                {"flags": ["--confidence-threshold"], "kwargs": {"type": float, "help": "Override mapping confidence threshold"}, "config_path": "tasks.mapping.confidence_threshold"},
                {"flags": ["--ambiguous-margin"], "kwargs": {"type": float, "help": "Override ambiguous mapping margin"}, "config_path": "tasks.mapping.ambiguous_margin"},
                {"flags": ["--resolver-batch-size"], "kwargs": {"type": int, "help": "Override resolver agent batch size"}, "config_path": "tasks.mapping.resolver_batch_size"}
            ],
            "agents": ["extraction", "embedding", "general_resolution", "lexical_resolution", "semantic_resolution"]
        }
    }