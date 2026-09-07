import json
from pathlib import Path
from typing import Dict, Union


class RegistryManager:
    def __init__(self):
        self.base_dir = Path.home() / ".lamb"
        self.mappings_dir = self.base_dir / "mappings"
        self.registry_file = self.base_dir / "registry.json"

        self.mappings_dir.mkdir(parents=True, exist_ok=True)

        if not self.registry_file.exists():
            with open(self.registry_file, 'w') as f:
                json.dump({}, f)


    def register(self, alias: str, mapping_data: Union[str, Dict]):
        data = json.loads(mapping_data) if isinstance(mapping_data, str) else mapping_data
        target_path = self.mappings_dir / f"{alias}.json"

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        registry = self.get_all_aliases()
        registry[alias] = str(target_path)

        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=4)

        return target_path


    def get_mapping(self, alias: str) -> Dict:
        path = self.get_all_aliases().get(alias)

        if not path or not Path(path).exists():
            raise ValueError(f"Alias '{alias}' not found.")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


    def get_all_aliases(self) -> Dict:
        with open(self.registry_file, 'r') as f:
            return json.load(f)