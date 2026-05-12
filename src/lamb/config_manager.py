import toml
from pathlib import Path
from typing import Any

class ConfigManager:
    """
    Manages configuration with a hierarchy similar to git config:
    Global: ~/.lambconfig.toml
    Local:  ./config.toml
    """

    def __init__(self):
        self.global_path = Path.home() / ".lamb" / "config.toml"
        self.local_path = Path(".lambconfig.toml")
        self.config = self._load_cascaded_config()

        self.global_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_path.touch(exist_ok=True)


    def apply_override(self, key_path: str, value: Any):
        """
        In-memory override of a configuration value. 
        Does not persist to TOML files.
        """

        keys = key_path.split('.')
        current = self.config

        for key in keys[:-1]:
            current = current.setdefault(key, {})

        if isinstance(value, str):
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)

        current[keys[-1]] = value

    def _load_cascaded_config(self) -> dict:
        """Merges global and local configs (local takes precedence)."""

        combined = {}

        # Load Global (~/.lamb/config.toml)
        if self.global_path.exists():
            combined.update(toml.load(self.global_path))

        # Load Local (./.lambconfig.toml)
        if self.local_path.exists():
            local_cfg = toml.load(self.local_path)

            for section, values in local_cfg.items():
                if section in combined and isinstance(values, dict):
                    combined[section].update(values)
                else:
                    combined[section] = values

        return combined

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a value using dot notation (e.g., 'tasks.default.model').
        """

        keys = key_path.split('.')
        val = self.config

        try:
            for key in keys:
                val = val[key]

            return val
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any, scope: str = "local"):
        """
        Sets a value in the config file.
        Scope can be 'local' or 'global'.
        """

        target_path = self.local_path if scope == "local" else self.global_path

        cfg = toml.load(target_path) if target_path.exists() else {}

        keys = key_path.split('.')
        current = cfg

        for key in keys[:-1]:
            current = current.setdefault(key, {})

        current[keys[-1]] = value

        with open(target_path, "w", encoding="utf-8") as f:
            toml.dump(cfg, f)

        self.config = self._load_cascaded_config()

    def list(self):
        """Returns the entire configuration as a flat list of key-value pairs."""

        items = []

        def flatten(d, prefix=''):
            for k, v in d.items():
                new_key = f"{prefix}.{k}" if prefix else k

                if isinstance(v, dict):
                    flatten(v, new_key)
                else:
                    items.append(f"{new_key}={v}")

        flatten(self.config)

        return items