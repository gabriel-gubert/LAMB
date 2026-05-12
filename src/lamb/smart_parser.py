from typing import Set
import tree_sitter_language_pack as tslp
from tree_sitter import Parser
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .prompt_templates import get_dynamic_detection_prompt

class SmartParser:
    def __init__(self, code: str, detector: ChatOpenAI):
        """
        Args:
            code: The raw code snippet.
            detector: An instantiated LangChain ChatOpenAI object.
        """

        self.code = code
        self.detector = detector

        self.language = None
        self.tree = None
        self.identifiers = set()

        self.parser = Parser()
        self._is_parsed = False

    def _detect_language(self) -> str:
        """Dynamically identifies the language using an LLM and the live grammar list."""

        supported_langs = tslp.available_languages()

        messages = [
            SystemMessage(content=get_dynamic_detection_prompt(supported_langs)),
            HumanMessage(content=f"\n```\n{self.code}\n```\n")
        ]

        try:
            response = self.detector.invoke(messages)
            detected = response.content.strip().lower()

            return detected
        except Exception as e:
            return "python"

    def _ensure_language_installed(self) -> bool:
        """Dynamic installation logic."""

        if not self.language:
            self.language = self._detect_language()

        if tslp.has_language(self.language):
            return True

        print(f"\n[Parser] Language '{self.language}' grammar not found.")

        choice = input(f"Do you want to download the tree-sitter parser for {self.language}? (y/n): ")

        if choice.lower() == 'y':
            try:
                print(f"Downloading {self.language}...")

                tslp.download([self.language])

                return True
            except Exception as e:
                print(f"Download failed: {e}")

        return False

    def parse(self) -> bool:
        """
        Executes the full parsing pipeline and populates the class properties.
        Returns True if successful, False otherwise.
        """

        if self._is_parsed:
            return True

        if not self._ensure_language_installed():
            return False

        try:
            # 1. Setup the parser
            language_obj = tslp.get_language(self.language)
            self.parser.set_language(language_obj)

            # 2. Parse the code and populate self.tree
            self.tree = self.parser.parse(bytes(self.code, "utf8"))
            
            # 3. Extract and populate self.identifiers
            query = language_obj.query("(identifier) @id")
            captures = query.captures(self.tree.root_node)
            self.identifiers = {node.text.decode('utf8') for node, _ in captures}
            
            self._is_parsed = True

            return True

        except Exception as e:
            print(f"Error parsing {self.language}: {e}")

            return False

    def get_identifiers(self) -> Set[str]:
        """Returns the cached set of identifiers, triggering parsing if necessary."""

        if not self._is_parsed:
            self.parse()
            
        return self.identifiers