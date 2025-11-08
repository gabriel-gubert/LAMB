from importlib import resources
from abc import ABC, abstractmethod
from .lamb_vba_parser import LambVbaParser
import json
import requests

class BaseLamb(ABC):
    """
    A generic, model-agnostic base class for handling code migration.

    This class provides the core logic for rule extraction and orchestrates
    the migration process. It is designed to be subclassed by specific agents
    that implement the API calls for different LLMs.
    """


    def __init__(self, model = 'base', verbose = False):
        mapping_table = resources.files('lamb.data').joinpath('map.json')

        with mapping_table.open('r', encoding = 'utf-8') as f:
            self.mapping_table = json.load(f)

        self.model = model
        self.verbose = verbose

        # The comment_length_threshold defines the maximum number of
        # characters a comment from the rules table can have before it is considered
        # "too long". If a comment exceeds this length, it will be sent to the LLM
        # for summarization before being included in the final migration prompt.

        self.comment_length_threshold = 2048

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Abstract method to generate a response from an LLM.
        Subclasses must implement this to call a specific LLM API.

        Args:
            prompt (str): The complete prompt to send to the LLM.
        Returns:
            str: The LLM's response.
        """

        raise NotImplementedError('Subclasses must implement the generic "generate" method.')


    def extract_migration_rules(self, legacy_code_snippet: str) -> list[str]:
        """
        Analyzes a code snippet against mapping tables to generate a list of specific migration rules for an LLM prompt.

        Args:
            legacy_code_snippet (str): The legacy code to analyze.
        Returns:
            list[str]: A list of formatted migration rules.
        """

        def summarize(text: str) -> str:
            summarization_prompt = f"""You are an expert VBA developer specializing in migrating scripts and tools from an old version to a new version. Your sole function is to process the provided technical documentation about a specific API object or method and generate a summary focused **exclusively on the differences** between its implementation in the old and new versions.

**Instructions:**
1.  **Focus on Comparison:** Generate a summary that clearly outlines the differences, behavioral changes, deprecations, and new functionalities between the legacy and current versions of the API element described in the text.
2.  **Structure the Output:** To ensure clarity, organize your summary using the following markdown headings:
    * `## Overview`: A one-sentence description of the API's purpose.
    * `## Old Implementation`: A brief on its usage and behavior in the old version.
    * `## New Implementation`: A brief on its usage and behavior in the new version.
    * `## Key Differences & Migration Notes`: A bulleted list detailing the specific changes a developer must know to migrate code.
3.  **Retain Code and Examples:** You must copy all source code blocks and inline code snippets verbatim into the appropriate section of your summary.
4.  **Final Response:** Your response must consist **only** of the final, structured summary. Do not add any conversational text like "Here is your summary."

**Text to Process:**

{text}
"""

            return self.generate(prompt = summarization_prompt)

        lamb_vba_parser = LambVbaParser(legacy_code_snippet)
        identifiers = lamb_vba_parser.get_identifiers()
        rules = set()
        num_entries = len(self.mapping_table['Objects'])

        for i in range(num_entries):
            old_namespace = self.mapping_table['Namespace'][i]
            old_object = self.mapping_table['Object'][i]
            old_member = self.mapping_table['Member'][i]
            old_signature = self.mapping_table['Signature'][i]
            new_namespace = self.mapping_table['New Namespace'][i]
            new_object = self.mapping_table['New Object'][i]
            new_member = self.mapping_table['New Member'][i]
            new_signature = self.mapping_table['New Signature']
            notes = self.mapping_table['Notes']

            # rule = f'- legacy object `{moved_object}` was moved to a new location and can now be found inside framework `{new_framework}` and/or typelib `{new_typelib}`.'

            if old_object and old_object in identifiers:
                rule = ''

                if new_object == old_object:
                    availability = 'current'
                else:
                    availability = 'legacy'

                if availability == 'legacy':
                    rule = f'- Legacy object `{old_object}` is obsolete.'

                    if new_object:
                        rule += f' It was replaced by object `{new_object}`'

                        if new_namespace:
                            rule += f' which can be found inside namespace `{new_namespace}`.'
                        else:
                            rule += '.'
                    else:
                        rule += f' It has no direct replacement.'
                elif availability == 'current':
                    rule = f'- Legacy object `{old_object}` still exists in the current version.'

                    if new_namespace:
                        rule += f' It can be found inside namespace `{new_namespace}`.'

                    if new_object and new_object != old_object:
                        rule += f' However, it was renamed to `{new_object}`.'

                rules.add(rule)

            if old_member and old_member in identifiers:
                rule = ''

                if new_member:
                    rule += f'- Legacy member `{old_member}` in legacy namespace `{old_namespace}` was replaced by method `{new_member}` in namespace `{new_namespace}`.'
                else:
                    rule += f'- Legacy member `{old_member}` in legacy namespace `{old_namespace}` does not have a counterpart in the current version.'

                rules.add(rule)

                if notes:
                    if len(notes) > self.comment_length_threshold:
                        notes = summarize(notes)

                    rule += f' Additional notes from the documentation, which may or may not influence the way this migration rule is applied, say the following:\n\n\"{notes}\"\n\n'

        return list(rules)


    def migrate(self, legacy_code_snippet: str) -> str:
        rules = self.extract_migration_rules(legacy_code_snippet)

        formatted_rules = '\n'.join(rules) if rules else 'No specific migration rules were found. Migrate based on general knowledge.'

        migration_prompt = f"""
**Role**: You are an expert VBA developer specializing in migrating scripts and tools from an old version to a new version. Your task is to act as an intelligent code migrator, translating legacy legacy scripts to their modern current equivalents.

**Context**: You will be given a snippet of legacy code and a set of `Applicable Migration Rules`. These rules have been extracted directly from the official legacy and current API documentations and are your primary source of truth. They MUST be prioritized over any general knowledge you may have.

**Instructions**:
1.  Translate the legacy code logic to its current equivalent.
2.  Strictly apply all provided migration rules. For example, if a rule says a legacy method is replaced by a current method, you must perform that replacement, if applicable to that piece of code.
3.  If a rule indicates a legacy object is obsolete and has no direct replacement, add a new comment in the current code at the relevant line, like this: `' TODO: Current object "ObsoleteObjectName" is obsolete and requires manual review.`
{'4. Your entire response MUST be a single markdown code block containing the migrated VBA code. Within the code, add comments directly above or next to any line you modified from the original legacy code. Each comment must explain what was changed and why. Moreover, briefly explain the main changes to the code in a single paragraph after the code block. Do not add any introductory text or summaries before or after the code block.' if self.verbose else '4.  Your entire response MUST be a single markdown code block containing the migrated VBA code. Do not add any introductory text, explanations, or summaries before or after the code block.'}

---

### **TASK**

**Legacy Code to Migrate:**

{legacy_code_snippet}

**Applicable Migration Rules:**

{formatted_rules}

**Migrated Code:**

"""

        migrated_code = self.generate(prompt = migration_prompt)

        return migrated_code


class vLLMLamb(BaseLamb):
    def __init__(self,
        model: str = 'meta-llama/Meta-Llama-3-8B-Instruct',
        host: str = '127.0.0.1',
        port: int = 8000,
        verbose: bool = False
    ):
        super().__init__(model = model, verbose = verbose)

        self.host = host
        self.port = port

    def generate(self, prompt: str) -> str:
        headers = {
            'Content-Type': 'application/json'
        }
        json = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }

        try:
            response = requests.post(f'http://{self.host}:{self.port}/v1/chat/completions', headers = headers, json = json)

            response.raise_for_status()

            data = response.json()
            generated_text = data['choices'][0]['message']['content'].strip()

            return generated_text
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f'{e}') from e


class OpenAILamb(BaseLamb):
    def __init__(self,
        model: str = 'o3-mini',
        api_key: str = '',
        verbose: bool = False
    ):
        super().__init__(model = model, verbose = verbose)

        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        json = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }

        try:
            response = requests.post('https://api.openai.com/v1/chat/completions', headers = headers, json = json)

            response.raise_for_status()

            data = response.json()
            generated_text = data['choices'][0]['message']['content'].strip()

            return generated_text
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f'{e}') from e
