import asyncio
from typing import Any, List, Mapping, Optional

from jupyter_ai_magics.providers import BaseProvider
from langchain_core.language_models.llms import LLM

import pandas as pd

from ..migrator_agent import MigratorAgent
from ..mapper_agent import MapperAgent
from ..agent_factory import migrator_agent, mapper_agent
from ..config_manager import ConfigManager
from ..registry_manager import RegistryManager


class _LambLLM(LLM):
    client: MigratorAgent

    @property
    def _llm_type(self) -> str:
        return 'lamb_migrator_agent'

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        parts = prompt.strip().split()

        if len(parts) < 2:
            return """
Error: MigratorAgent requires two directory paths. Usage:

%%ai LAMB <LIBRARY_ALIAS> 
<INPUT_CODE>

Registered libraries: {libraries}
""".format(libraries=", ".join(RegistryManager().get_all_aliases().keys())).strip()

        mapping_table = RegistryManager().get_mapping(parts[0])
        input_code = parts[1]

        migrated_code = self.client.migrate(legacy_code_snippet=input_code, mapping_table=mapping_table)

        return migrated_code

    async def _acall(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        loop = asyncio.get_running_loop()

        migrated_code = await loop.run_in_executor(
            None,
            lambda: self._call(prompt, stop, **kwargs)
        )

        return migrated_code

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {'model': 'lamg-agent-v1'}


class MigratorAgentProvider(BaseProvider, _LambLLM):
    id = 'LAMB_MIGRATOR'
    name = 'LAMB Migrator Agent'
    
    def __init__(self, **kwargs: Any):
        config_manager = ConfigManager()

        super().__init__(client=migrator_agent(config_manager=config_manager), **kwargs)


class _MapperLLM(LLM):
    client: MapperAgent

    @property
    def _llm_type(self) -> str:
        return 'lamb_mapper_agent'

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        parts = prompt.strip().split()

        if len(parts) < 3:
            return "Error: Usage: %%ai LAMB_MAPPER <LIBRARY_ALIAS> <PATH_V1> <PATH_V2>"
        
        result = self.client.run(path_a=parts[1], path_b=parts[2])
        
        mappings = result.get("mappings", [])
        
        if not mappings:
            return "No mappings found."

        RegistryManager().register(parts[0], mappings)

        return _get_pretty_table(pd.DataFrame(mappings))

    async def _acall(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            lambda: self._call(prompt, stop, **kwargs)
        )

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {'model': 'lamb-mapper-agent-v1'}


class MapperAgentProvider(BaseProvider, _MapperLLM):
    id = 'LAMB_MAPPER'
    name = 'LAMB Mapper Agent'

    def __init__(self, **kwargs: Any):
        config_manager = ConfigManager()

        super().__init__(client=mapper_agent(config_manager=config_manager), **kwargs)

def _get_pretty_table(df):
    if len(df) <= 10:
        return df.to_html()

    head = df.head(5)
    tail = df.tail(5)

    spacer = pd.DataFrame({col: ["..."] for col in df.columns}, index=[0])

    combined = pd.concat([head, spacer, tail], ignore_index=True)

    return combined.to_html(index=False)