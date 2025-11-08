import asyncio
from pathlib import Path
from typing import Any, List, Mapping, Optional

import tomli
from jupyter_ai_magics import BaseProvider
from langchain.llms.base import LLM

from lamb.lamb import BaseLamb, vLLMLamb, OpenAILamb


class _LambLLM(LLM):
    client: BaseLamb

    @property
    def _llm_type(self) -> str:
        return 'lamb_migration_agent'

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        migrated_code = self.client.migrate(v1_code_snippet=prompt)

        return migrated_code

    async def _acall(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        loop = asyncio.get_running_loop()

        migrated_code = await loop.run_in_executor(
            None,
            lambda: self.client.migrate(v1_code_snippet=prompt)
        )

        return migrated_code

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {'model': self.client.model}


class LambProvider(BaseProvider, _LambLLM):
    id = 'LAMB'
    name = 'LAMB'
    model_id_key = 'model'
    models = ['vllm', 'openai']

    def __init__(self, **kwargs: Any):
        config_path = Path.home() / '.config' / 'LAMB' / 'LAMB.toml'
        settings = {
            'vllm': {
                'model': 'meta-llama/Meta-Llama-3-8B-Instruct',
                'host': '127.0.0.1',
                'port': 8000,
                'verbose': False
            },
            'openai': {
                'model': 'o3-mini',
                'api_key': '',
                'verbose': False
            }
        }

        if config_path.is_file():
            try:
                with open(config_path, 'rb') as f:
                    config = tomli.load(f)
                    settings.update(config)
            except (IOError, tomli.TOMLDecodeError) as e:
                print(f'Warning: Couldn\'t load LAMB\'s Configuration File in {config_path}: {e}')

        try:
            model_id = kwargs.get('model_id')

            match model_id:
                case 'vllm':
                    client_instance = vLLMLamb(
                        model = settings['vllm']['model'],
                        host = settings['vllm']['host'],
                        port = settings['vllm']['port'],
                        verbose = settings['vllm']['verbose']
                    )
                case 'openai':
                    client_instance = OpenAILamb(
                        model = settings['openai']['model'],
                        api_key = settings['openai']['api_key'],
                        verbose = settings['openai']['verbose']
                    )
                case _:
                    raise ValueError(f'Unsupported Model {model_id}.')
        except Exception as e:
            raise ConnectionError(
                f'Failed to initialize LAMB Client. Check your LAMB\'s Configuration File in {config_path}. Error: {e}'
            ) from e

        super().__init__(client = client_instance, **kwargs)