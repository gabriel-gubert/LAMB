import hashlib
import importlib.resources
import json
import os
import random
import re
import sqlite3
import sys
import yaml
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from functools import partial
from pathlib import Path
from typing import List, Dict, TypedDict, Any, Optional, Tuple, Set

import numpy as np

from markdownify import markdownify as md

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.document_loaders.blob_loaders import Blob
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

import tree_sitter_html as tshtml
from tree_sitter import Language, Parser

from .types import Complexity
from .rate_limited_chat import (
    RateLimitedChatOpenAI,
    RateLimitedOpenAIEmbeddings
)
from .output_templates import (
    ElementsExtraction,
    MappingRow,
    ResolutionResult,
    DirectoryDiscovery
)
from .prompt_templates import (
    get_mapper_extraction_prompt,
    get_general_mapper_resolution_prompt,
    get_lexical_mapper_resolution_prompt,
    get_semantic_mapper_resolution_prompt,
    get_consensus_arbitration_prompt,
    get_directory_discovery_prompt
)
from .logger import (
    log_info,
    log_warn,
    log_error,
    print_agent_state,
    display_rich_matrix,
    display_mapping_table
)


try:
    config_file = importlib.resources.files("lamb").joinpath("languages.yaml")

    with config_file.open("r", encoding="utf-8") as conf_f:
        LINGUIST_CONFIG = yaml.safe_load(conf_f)
except Exception as e:
    log_error(f"Failed Loading \"languages.yaml\": {e}")

    LINGUIST_CONFIG = {}


def _hash_and_clean_chunk_batch(item: dict) -> tuple[str, str, str, str]:
    """Processes a single chunk. Placed at the top-level of the file 
    so it can be serialized and pickled by ProcessPoolExecutor.
    """

    cleaned_text = item["text"].strip() if item.get("text") else ""

    if not cleaned_text:
        return "", "", "", ""

    chunk_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

    return chunk_hash, cleaned_text, item["file_path"], item["version"]


def _calculate_file_strategy(file_path: str) -> dict:
    """Analyzes a single file's size and extension to determine the optimal chunk size."""

    try:
        p = Path(file_path)

        if not p.exists():
            return {"chunk_size": 4000, "chunk_overlap": 200, "batch_grouping": False, "tier": ""}
        
        file_size_bytes = p.stat().st_size

        # Tiny files (< 50 KB): Use standard chunks, no backoff delays needed
        if file_size_bytes < 50_000:
            return {
                "chunk_size": 10000,
                "chunk_overlap": 500
            }
        # Medium files (50 KB - 500 KB): Bump chunk size significantly to save requests
        elif file_size_bytes < 500_000:
            return {
                "chunk_size": 60000,
                "chunk_overlap": 4000
            }
        # Large files (> 500 KB): Maximum safe extraction window to minimize token-per-minute hits
        else:
            return {
                "chunk_size": 120000,
                "chunk_overlap": 8000
            }
    except Exception:
        return {"chunk_size": 4000, "chunk_overlap": 400, "batch_grouping": False, "tier": ""}


def _is_strictly_tree_sitter_html(content: str) -> bool:
    """Uses a formal Tree-sitter grammar AST parser to strictly validate HTML compliance."""

    cleaned = content.strip()

    if not cleaned:
        return False

    try:
        HTML_LANGUAGE = Language(tshtml.language())
        parser = Parser(HTML_LANGUAGE)
        tree = parser.parse(bytes(cleaned, "utf8"))
        root_node = tree.root_node

        if root_node.has_error or root_node.type == "ERROR":
            return False

        has_elements = any(child.type in ("element", "tag", "doctype") for child in root_node.children)

        return has_elements
    except Exception:
        raise RuntimeError(f"[X] Tree-sitter Parser Failed: {e}")


def _split_file(file_path: str = None, content: str = None, ext: str = ".txt", chunk_size: int = 4000, chunk_overlap: int = 400) -> List[str]:
    """Determines splitting logic using the Linguist YAML 'type' field, accepting either a file path or direct string content."""

    if file_path:
        path = Path(file_path)
        ext = path.suffix.lower()

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    elif content is None:
        return []

    detected_type = "prose"

    for _, properties in LINGUIST_CONFIG.items():
        if "extensions" in properties and ext in properties["extensions"]:
            detected_type = properties.get("type", "prose").lower()

            break

    recursive_char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    if detected_type == "programming":
        try:
            parser = LanguageParser()
            blob = Blob.from_data(content, path=file_path or f"filename{ext}")
            ast_docs = parser.lazy_parse(blob)
            final_docs = recursive_char_splitter.split_documents(ast_docs)

            return [doc.page_content for doc in final_docs]
        except Exception as E:
            if file_path:
                log_error(f"Failed Splitting Content from File at \"{file_path}\". Falling Back to Recursive Character Splitter: {E}")
            else:
                log_error(f"Failed Splitting Content. Falling Back to Recursive Character Splitter: {E}")

    if detected_type == "markup":
        try:
            try:
                is_html = _is_strictly_tree_sitter_html(content)
            except Exception as E:
                if file_path:
                    log_error(f"Tree-sitter Failed for {file_path}. Falling Back to RegEx HTML Detection: {E}")
                else:
                    log_error(f"Tree-sitter Failed: {E}. Falling Back to RegEx HTML Detection: {E}")

                is_html = bool(re.search(r'</?\s*[a-zA-Z][^>]*>', content))

            is_markdown = bool(re.search(r'(?m)^(?:#{1,6}\s+.+|(?:={3,}|-{3,})$)', content))

            assert(is_html or is_markdown), f"[X] Content from File at \"{file_path}\" is neither HTML nor Markdown." if file_path else f"[X] Content is neither HTML nor Markdown."

            if is_html:
                markdown_content = md(content)
            else:
                markdown_content = content

            md_header_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3")
                ]
            )

            structural_docs = md_header_splitter.split_text(markdown_content)
            final_docs = recursive_char_splitter.split_documents(structural_docs)

            return [doc.page_content for doc in final_docs]
        except Exception as E:
            if file_path:
                log_error(f"Failed Splitting Content from File at \"{file_path}\". Falling Back to Recursive Character Splitter: {E}")
            else:
                log_error(f"Failed Splitting Content. Falling Back to Recursive Character Splitter: {E}")

    return recursive_char_splitter.split_text(content)


def _process_single_file_split(file_path: str, version: str) -> list[dict]:
    """Top-level worker function executed by ProcessPoolExecutor.
    Since it is global, Python can easily pickle and distribute it.
    """

    try:
        strategy = _calculate_file_strategy(file_path)
        chunks = _split_file(
            file_path=file_path, 
            chunk_size=strategy.get("chunk_size", 4000),
            chunk_overlap=strategy.get("chunk_overlap", 400)
        )

        return [
            {
                "text": chunk,
                "file_path": file_path,
                "version": version
            }
            for chunk in chunks
        ]
    except Exception as E:
        log_error(f"Failed Chunking Artifact at \"{file_path}\": {E}")

        return []


class MapperAgentState(TypedDict):
    run_id: str

    # --- Input Parameters ---
    dir_v1: str
    dir_v2: str

    # --- Discovery Layer ---
    discovery_queue_v1: List[dict]
    discovery_queue_v2: List[dict]
    files_v1: List[str]
    files_v2: List[str]

    # --- Sanitization Layer ---
    files_v1_queue: List[str]
    files_v2_queue: List[str]
    sanitized_files_v1: List[str]
    sanitized_files_v2: List[str]

    # --- Chunking Layer queues ---
    sanitized_files_v1_queue: List[str]
    sanitized_files_v2_queue: List[str]
    raw_chunks_buffer: List[dict]
    chunk_registry: Dict[str, dict]

    # --- Intermediate Processing & Global Deduplication Buffers ---
    deduplication_queue: List[dict]

    # --- Extraction Execution Layer ---
    chunks_v1_queue: List[dict]
    chunks_v2_queue: List[dict]
    extracted_v1: List[dict]
    extracted_v2: List[dict]

    # --- Base Structural Mapping ---
    initial_mappings: List[dict]
    resolution_queue: List[dict]

    # --- Parallel Agent Mapping Scratchpads & Outputs ---
    queue_agent_1: List[dict]
    queue_agent_2: List[dict]
    queue_agent_3: List[dict]
    queue_single: List[dict]
    raw_agent_1: List[dict]
    raw_agent_2: List[dict]
    raw_agent_3: List[dict]
    raw_single: List[dict]

    mappings_agent_1: List[dict]
    mappings_agent_2: List[dict]
    mappings_agent_3: List[dict]

    # --- Consensus Arbitration Layer ---
    base_consensus_mappings: List[dict]
    stalemates_queue: List[dict]
    raw_arbitrated_mappings: List[dict]

    # --- Global Final Output Target ---
    mappings: List[dict]


class MapperAgent:
    def __init__(
            self,
            discoverer: RateLimitedChatOpenAI,
            extractor: RateLimitedChatOpenAI,
            embedder: RateLimitedOpenAIEmbeddings,
            resolver_agent_1: RateLimitedChatOpenAI,
            resolver_agent_2: Optional[RateLimitedChatOpenAI] = None,
            resolver_agent_3: Optional[RateLimitedChatOpenAI] = None,
            multi_agent: bool = False,
            discovery_batch_size: int = 20,
            resolver_batch_size: int = 20,
            verbose: bool = False,
            stage_output_dir: Optional[str | Path] = None,
            database_path: str = "~/.lamb/map_checkpoint.db",
            tmp_dir: str = "~/.lamb/tmp"
        ):
        self._discoverer = discoverer.with_structured_output(DirectoryDiscovery).with_retry(stop_after_attempt=2)
        self._extractor = extractor.with_structured_output(ElementsExtraction).with_retry(stop_after_attempt=2)
        self._embedder = embedder

        self.multi_agent = multi_agent
        self.verbose = verbose

        self._resolver_1 = resolver_agent_1.with_structured_output(ResolutionResult).with_retry(stop_after_attempt=2)
        self._resolver_2 = resolver_agent_2.with_structured_output(ResolutionResult).with_retry(stop_after_attempt=2) if resolver_agent_2 else None
        self._resolver_3 = resolver_agent_3.with_structured_output(ResolutionResult).with_retry(stop_after_attempt=2) if resolver_agent_3 else None

        if self.multi_agent:
            if self.verbose:
                log_info(f"Enabling Multi-Agent Resolution...")

            if not (self._resolver_2 and self._resolver_3):
                if self.verbose:
                    log_info(f"Missing Resolver Agents 2 or 3. Falling back to Single Agent.")

                    self.multi_agent = False

        self.resolver_batch_size = resolver_batch_size
        self.discovery_batch_size = discovery_batch_size

        self.tmp_dir = Path(tmp_dir) if tmp_dir else None

        if self.tmp_dir:
            self.tmp_dir.mkdir(exist_ok=True, parents=True)

        self.output_dir = Path(stage_output_dir) if stage_output_dir else None

        if self.output_dir:
            self.output_dir.mkdir(exist_ok=True, parents=True)

        db_file = Path(database_path)

        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.db_conn = sqlite3.connect(str(db_file), check_same_thread=False)
        self.memory = SqliteSaver(self.db_conn)
        self.graph = self._build_graph()
        self.valid_extensions = self._load_valid_extensions()


    def _save_stage_output(self, stage_name: str, data: Any) -> None:
        """Helper to save the state update of a stage to a JSON file if configured."""

        if not self.output_dir:
            return

        output_path = self.output_dir / f"{stage_name}_output.json"

        if self.verbose:
            log_info(f"Saving {stage_name.replace("_", " ").title()} to \"{output_path}\"...")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, default=str)
        except Exception as e:
            if self.verbose:
                log_error(f"Failed Saving to \"{output_path}\": {e}")


    def _build_graph(self) -> StateGraph:
        """Constructs and compiles the LangGraph state machine with full crash resilience,
        incorporating file-by-file processing, a standalone chunk deduplication node, 
        and a chunk-by-chunk LLM information extraction loop.
        """

        workflow = StateGraph(MapperAgentState)

        # =========================================================================
        # 1. NODE REGISTRATION
        # =========================================================================

        # Discovery Sub-Graph Nodes
        workflow.add_node("init_discovery", self._init_discovery)
        workflow.add_node("discovery_step", self._discovery_step)

        # Chunking Sub-Graph Nodes
        workflow.add_node("prep_sanitization", self._prepare_sanitization_queues)
        workflow.add_node("sanitize_files", self._sanitize_files)
        workflow.add_node("prep_chunking", self._prepare_chunk_queues)
        workflow.add_node("chunk_files", self._chunk_files)
        workflow.add_node("prep_chunk_dedup_queue", self._prepare_chunk_deduplication_queue)
        workflow.add_node("deduplicate_chunks", self._deduplicate_chunks)
        
        # Extraction Sub-Graph Nodes
        workflow.add_node("prep_extraction", self._prepare_extraction_queues)
        workflow.add_node("extract_step", self._extract_step)
        workflow.add_node("deduplicate_elements", self._deduplicate_elements)
        
        # Base Mapping Sub-Graph Nodes
        workflow.add_node("map_initial", self._match_initial)
        workflow.add_node("prep_mapping", self._prepare_mapping_queues)

        # =========================================================================
        # 2. EDGE DEFINITIONS & CONTROL FLOW ROUTING
        # =========================================================================
        
        # --- Discovery Phase Routing ---
        workflow.set_entry_point("init_discovery")
        workflow.add_edge("init_discovery", "discovery_step")
        
        workflow.add_conditional_edges(
            "discovery_step",
            self._should_continue_discovery,
            {
                "discovery_step": "discovery_step", 
                "prep_sanitization": "prep_sanitization"
            }
        )
        
        # --- Queue Prep to Loop Handshake ---
        workflow.add_edge("prep_sanitization", "sanitize_files")
        workflow.add_edge("sanitize_files", "prep_chunking")
        workflow.add_edge("prep_chunking", "chunk_files")
        
        # --- File Chunking Routing Loop ---
        workflow.add_conditional_edges(
            "chunk_files",
            self._should_continue_chunking,
            {
                "chunk_files": "chunk_files",
                "prep_chunk_dedup_queue": "prep_chunk_dedup_queue"
            }
        )
        
        # --- Transition Handshake to Deduplication Loop ---
        workflow.add_edge("prep_chunk_dedup_queue", "deduplicate_chunks")
        
        # --- Incremental Deduplication Routing Loop ---
        workflow.add_conditional_edges(
            "deduplicate_chunks",
            self._should_continue_deduplication,
            {
                "deduplicate_chunks": "deduplicate_chunks",
                "prep_extraction": "prep_extraction"
            }
        )
        workflow.add_edge("prep_extraction", "extract_step")
        
        # --- LLM Extraction Processing Routing Loop ---
        workflow.add_conditional_edges(
            "extract_step",
            self._should_continue_extraction,
            {
                "extract_step": "extract_step", 
                "deduplicate_elements": "deduplicate_elements"
            }
        )
        
        workflow.add_edge("deduplicate_elements", "map_initial")
        workflow.add_edge("map_initial", "prep_mapping")

        # =========================================================================
        # 3. MULTI-AGENT VS SINGLE AGENT TOPOLOGY HOOKS
        # =========================================================================
        if self.multi_agent:
            # Configure Multi-Agent Worker Loop Steps
            workflow.add_node("map_agent_1_step", partial(self._execute_agent_mapping_step, resolver_client=self._resolver_1, prompt=get_general_mapper_resolution_prompt(), agent_label="Agent 1", queue_key="queue_agent_1", raw_key="raw_agent_1"))
            workflow.add_node("map_agent_2_step", partial(self._execute_agent_mapping_step, resolver_client=self._resolver_2, prompt=get_lexical_mapper_resolution_prompt(), agent_label="Agent 2", queue_key="queue_agent_2", raw_key="raw_agent_2"))
            workflow.add_node("map_agent_3_step", partial(self._execute_agent_mapping_step, resolver_client=self._resolver_3, prompt=get_semantic_mapper_resolution_prompt(), agent_label="Agent 3", queue_key="queue_agent_3", raw_key="raw_agent_3"))
            
            workflow.add_node("map_agent_1_finalize", partial(self._finalize_agent_mapping, agent_label="Agent 1", raw_key="raw_agent_1", output_key="mappings_agent_1"))
            workflow.add_node("map_agent_2_finalize", partial(self._finalize_agent_mapping, agent_label="Agent 2", raw_key="raw_agent_2", output_key="mappings_agent_2"))
            workflow.add_node("map_agent_3_finalize", partial(self._finalize_agent_mapping, agent_label="Agent 3", raw_key="raw_agent_3", output_key="mappings_agent_3"))
            
            # Consensus & Arbitration Nodes
            workflow.add_node("check_votes", self._check_consensus_votes)
            workflow.add_node("arbitrate_step", self._arbitrate_stalemate_step)
            workflow.add_node("finalize_consensus", self._finalize_consensus)

            # Connect Parallel Agent Processing Pipelines
            for i in ["1", "2", "3"]:
                workflow.add_edge("prep_mapping", f"map_agent_{i}_step")
                workflow.add_conditional_edges(
                    f"map_agent_{i}_step",
                    partial(self._should_continue_agent_mapping, queue_key=f"queue_agent_{i}", next_step_node=f"map_agent_{i}_step", finalized_node=f"map_agent_{i}_finalize"),
                    {f"map_agent_{i}_step": f"map_agent_{i}_step", f"map_agent_{i}_finalize": f"map_agent_{i}_finalize"}
                )
                workflow.add_edge(f"map_agent_{i}_finalize", "check_votes")
            
            # Tie-Breaking Arbitration Routing
            workflow.add_edge("check_votes", "arbitrate_step")
            workflow.add_conditional_edges(
                "arbitrate_step",
                self._should_continue_arbitration,
                {
                    "arbitrate_step": "arbitrate_step",
                    "finalize_consensus": "finalize_consensus"
                }
            )
            workflow.add_edge("finalize_consensus", END)
        else:
            # Fallback Single Agent Execution
            workflow.add_node("map_single_step", partial(self._execute_agent_mapping_step, resolver_client=self._resolver_1, prompt=get_general_mapper_resolution_prompt(), agent_label="Single Agent", queue_key="queue_single", raw_key="raw_single"))
            workflow.add_node("map_single_finalize", partial(self._finalize_agent_mapping, agent_label="Single Agent", raw_key="raw_single", output_key="mappings"))
            
            workflow.add_edge("prep_mapping", "map_single_step")
            workflow.add_conditional_edges(
                "map_single_step",
                partial(self._should_continue_agent_mapping, queue_key="queue_single", next_step_node="map_single_step", finalized_node="map_single_finalize"),
                {
                    "map_single_step": "map_single_step",
                    "map_single_finalize": "map_single_finalize"
                }
            )
            workflow.add_edge("map_single_finalize", END)

        return workflow.compile(checkpointer=self.memory)

    @staticmethod
    def _is_text_file(filepath: Path) -> bool:
        """Helper to quickly verify if a file is readable text."""

        try:
            with filepath.open('tr', encoding='utf-8') as check_file:
                check_file.read(1024)

            return True
        except Exception:
            return False

    @staticmethod
    def _get_element_key(element: Optional[dict]) -> Tuple[str, str, str, str]:
        """Helper to create a flat, hashable tuple identifier."""

        if not element:
            return ("", "", "", "")

        return (
            element.get("namespace", ""),
            element.get("class_or_interface", ""),
            element.get("member", ""),
            element.get("signature", "")
        )


    def _load_valid_extensions(self) -> Set[str]:
        """Loads and filters extensions from languages.yaml for markup, prose, and programming types."""

        yaml_path = Path(__file__).parent / "languages.yaml"

        if not yaml_path.exists():
            return set()

        if self.verbose:
            log_info(f"Loading \"{yaml_path}\"...")

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            valid_exts = set()

            if isinstance(data, dict):
                for lang_name, lang_info in data.items():
                    lang_type = lang_info.get("type")

                    if lang_type in ("markup", "prose", "programming"):
                        exts = lang_info.get("extensions", [])

                        for ext in exts:
                            if ext:
                                valid_exts.add(ext.lower())

            return valid_exts
        except Exception as e:
            if self.verbose:
                log_error(f"Failed Loading \"languages.yaml\": {e}")

            return set()


    def _gather_directory_samples(self, directory: str) -> List[dict]:
        """Scans directories and creates structural metadata payloads for the LLM to filter."""

        def is_hidden(path: Path) -> bool:
            return path.name.startswith('.') or any(part.startswith('.') for part in path.parts)

        root_path = Path(directory)

        if self.verbose:
            log_info(f"Profiling Root Directory \"{root_path}\"...")

        if not root_path.exists():
            return []

        dirs = [root_path]
        for p in root_path.rglob("*"):
            if p.is_dir() and not is_hidden(p):
                dirs.append(p)

        dir_samples = []
        for d in dirs:
            text_files = []
            all_extensions = []

            for p in d.iterdir():
                if p.is_file() and not is_hidden(p):
                    ext = p.suffix.lower()
                    if ext:
                        all_extensions.append(ext)
                    if self._is_text_file(p):
                        text_files.append(p.name)

            samples = random.sample(text_files, min(len(text_files), 3)) if text_files else []
            top_exts = [item[0] for item in Counter(all_extensions).most_common(3)]

            dir_samples.append({
                "path": str(d.absolute()),
                "top_extensions": top_exts,
                "samples": samples
            })

            if self.verbose:
                print(f"    -> Found Child Directory at \"{dir_samples[-1].get("path", "")}\"", file=sys.stderr)
                print(f"        -> Top-3 File Extension(s): {", ".join(dir_samples[-1].get("top_extensions", []))}", file=sys.stderr)

        return dir_samples


    def _gather_files_from_chosen_directories(self, chosen_paths: List[Path], valid_extensions: Set[str]) -> List[str]:
        """Inspects selected paths and returns individual files matching extension whitelist rules."""

        def is_hidden(path: Path) -> bool:
            return path.name.startswith('.') or any(part.startswith('.') for part in path.parts)

        matched_files = set()

        for path in chosen_paths:
            if self.verbose:
                log_info(f"Collecting Artifact(s) from \"{path}\"...")

            if not path.exists() or is_hidden(path):
                continue

            for p in path.iterdir():
                if p.is_file() and not is_hidden(p):
                    if p.suffix.lower() in valid_extensions:
                        matched_files.add(str(p.absolute()))

        return sorted(list(matched_files))


    def _init_discovery(self, state: MapperAgentState) -> dict:
        """Node: Gathers structural folders and stages them into active state queues."""

        dir_v1 = str(state.get("dir_v1", ""))
        dir_v2 = str(state.get("dir_v2", ""))

        if self.verbose:
            # print_agent_state({"dir_v1": dir_v1, "dir_v2": dir_v2})
            log_info(f"Profiling Root Directory at \"{dir_v1}\" for V1 and Root Directory at \"{dir_v2}\" for V2...")

        return {
            "dir_v1": "",
            "dir_v2": "",
            "discovery_queue_v1": self._gather_directory_samples(dir_v1),
            "discovery_queue_v2": self._gather_directory_samples(dir_v2),
            "files_v1": [],
            "files_v2": []
        }


    def _discovery_step(self, state: MapperAgentState) -> dict:
        """Evaluates a single batched chunk of staged folders through LLM routers."""

        queue_v1 = list(state.get("discovery_queue_v1", []))
        queue_v2 = list(state.get("discovery_queue_v2", []))
        files_v1 = list(state.get("files_v1", []))
        files_v2 = list(state.get("files_v2", []))

        batch_messages = []
        is_v1 = False

        if queue_v1:
            is_v1 = True
            current_batch = [queue_v1.pop(0) for _ in range(min(len(queue_v1), self.discovery_batch_size))]
        elif queue_v2:
            current_batch = [queue_v2.pop(0) for _ in range(min(len(queue_v2), self.discovery_batch_size))]
        else:
            return {}

        prompt_content = json.dumps(current_batch, indent=2)

        batch_messages.append([
            SystemMessage(content=get_directory_discovery_prompt()),
            HumanMessage(content=prompt_content)
        ])

        try:
            llm_results = []

            for message in batch_messages:
                result = self._discoverer.invoke(message)

                llm_results.append(result)

            chosen_paths = []

            for llm_result in llm_results:
                if llm_result and hasattr(llm_result, "directories"):
                    chosen_paths.extend([Path(p) for p in llm_result.directories])
        except Exception as E:
            if self.verbose:
                log_error(f"Failed Calling Discovery Batch: {E}")

            raise E

        new_files = self._gather_files_from_chosen_directories(chosen_paths, self.valid_extensions)

        if is_v1:
            files_v1.extend(new_files)

            return {"discovery_queue_v1": queue_v1, "files_v1": sorted(list(set(files_v1)))}
        else:
            files_v2.extend(new_files)

            return {"discovery_queue_v2": queue_v2, "files_v2": sorted(list(set(files_v2)))}


    def _should_continue_discovery(self, state: MapperAgentState) -> str:
        """Conditional Router checking if directory exploration queues are exhausted."""

        if state.get("discovery_queue_v1") or state.get("discovery_queue_v2"):
            return "discovery_step"

        result = {"files_v1": state.get("files_v1", []), "files_v2": state.get("files_v2", [])}

        self._save_stage_output("collected_artifacts", result)

        if self.verbose:
            print(f"    -> Found {len(state.get('files_v1', []))} Artifact(s) in V1 and {len(state.get('files_v2', []))} Artifact(s) in V2.", file=sys.stderr)
            # print_agent_state(result)

        return "prep_chunking"


    def _prepare_sanitization_queues(self, state: MapperAgentState) -> dict:
        if self.verbose:
            log_info(f"Running Artifact(s) Boilerplate Removal...")

        return {
            "files_v1": [],
            "files_v2": [],
            "files_v1_queue": list(state.get("files_v1", [])),
            "files_v2_queue": list(state.get("files_v2", [])),
            "sanitized_files_v1": [],
            "sanitized_files_v2": []
        }


    def _sanitize_files(self, state: MapperAgentState) -> Dict[str, Any]:
        v1_queue = list(state.get("files_v1_queue", []))
        v2_queue = list(state.get("files_v2_queue", []))

        run_id = state.get("run_id", "default")

        if self.tmp_dir and isinstance(self.tmp_dir, Path):
            cache_dir = self.tmp_dir / str(run_id)
        else:
            cache_dir = Path("~/.lamb/tmp") / str(run_id)

        sanitized_v1_dir = cache_dir / "v1"
        sanitized_v2_dir = cache_dir / "v2"

        sanitized_v1_dir.mkdir(parents=True, exist_ok=True)
        sanitized_v2_dir.mkdir(parents=True, exist_ok=True)

        result = {}

        if v1_queue:
            if self.verbose:
                log_info("Removing Boilerplate from V1 Artifact(s)...")

            counts = Counter()
            v1_cache = []

            for file_path in v1_queue:
                try:
                    path = Path(file_path)
                    content = path.read_text(encoding="utf-8")

                    v1_cache.append((file_path, content))

                    ext = path.suffix.lstrip(".").lower()
                    matched_lang = next((lang for lang in Language if lang.value.lower() == ext or lang.name.lower() == ext), None)
                    scanner = RecursiveCharacterTextSplitter.from_language(language=matched_lang) if matched_lang else RecursiveCharacterTextSplitter(chunk_size=150, chunk_overlap=0)

                    blocks = {c.strip() for c in scanner.split_text(content) if len(c.strip()) >= 30}

                    counts.update(blocks)
                except Exception:
                    continue

            bp_v1 = [block for block, count in counts.items() if count >= 3]

            sanitized_files_v1 = []
            seen_bp = set()

            for file_path, content in v1_cache:
                for bp in bp_v1:
                    if bp in content:
                        if bp in seen_bp:
                            content = content.replace(bp, "")
                        else:
                            seen_bp.add(bp)

                            parts = content.split(bp)
                            content = parts[0] + bp + "".join(parts[1:])

                out_path = sanitized_v1_dir / Path(file_path).name

                out_path.write_text(content, encoding="utf-8")
                sanitized_files_v1.append(str(out_path))

            result["sanitized_files_v1"] = sanitized_files_v1

        if v2_queue:
            if self.verbose:
                log_info("Removing Boilerplate from V2 Artifact(s)...")

            counts = Counter()
            v2_cache = []

            for file_path in v2_queue:
                try:
                    path = Path(file_path)
                    content = path.read_text(encoding="utf-8")

                    v2_cache.append((file_path, content))

                    ext = path.suffix.lstrip(".").lower()
                    matched_lang = next((lang for lang in Language if lang.value.lower() == ext or lang.name.lower() == ext), None)
                    scanner = RecursiveCharacterTextSplitter.from_language(language=matched_lang, chunk_size=150, chunk_overlap=0) if matched_lang else RecursiveCharacterTextSplitter(chunk_size=150, chunk_overlap=0)

                    blocks = {c.strip() for c in scanner.split_text(content) if len(c.strip()) >= 30}

                    counts.update(blocks)
                except Exception:
                    continue

            bp_v2 = [block for block, count in counts.items() if count >= 3]

            sanitized_files_v2 = []
            seen_bp = set()

            for file_path, content in v2_cache:
                for bp in bp_v2:
                    if bp in content:
                        if bp in seen_bp:
                            content = content.replace(bp, "")
                        else:
                            seen_bp.add(bp)

                            parts = content.split(bp)
                            content = parts[0] + bp + "".join(parts[1:])

                out_path = sanitized_v2_dir / Path(file_path).name

                out_path.write_text(content, encoding="utf-8")
                sanitized_files_v2.append(str(out_path))

            result["sanitized_files_v2"] = sanitized_files_v2

        return result


    def _prepare_chunk_queues(self, state: MapperAgentState) -> dict:
        """Runs once after discovery completes to setup the chunking tracking loops
        and initialize the shared processing buffers.
        """

        if self.verbose:
            log_info(f"Running Artifact(s) Chunking...")

        return {
            "sanitized_files_v1": [],
            "sanitized_files_v2": [],
            "sanitized_files_v1_queue": list(state.get("sanitized_files_v1", [])),
            "sanitized_files_v2_queue": list(state.get("sanitized_files_v2", [])),
            "raw_chunks_buffer": []
        }

    def _chunk_files(self, state: MapperAgentState) -> Dict[str, Any]:
        """Pops a batch of files, processes them in parallel across multiple 
        CPU cores using ProcessPoolExecutor, and updates the state buffer.
        """

        v1_queue = list(state.get("sanitized_files_v1_queue", []))
        v2_queue = list(state.get("sanitized_files_v2_queue", []))
        raw_chunks_buffer = list(state.get("raw_chunks_buffer", []))

        if not v1_queue and not v2_queue:
            return {}

        BATCH_SIZE = 100

        batch_files = []
        is_v1 = len(v1_queue) > 0

        if is_v1:
            for _ in range(min(BATCH_SIZE, len(v1_queue))):
                batch_files.append((v1_queue.pop(0), "v1"))
        else:
            for _ in range(min(BATCH_SIZE, len(v2_queue))):
                batch_files.append((v2_queue.pop(0), "v2"))

        try:
            max_workers = len(os.sched_getaffinity(0))
        except AttributeError:
            max_workers = os.cpu_count() or 1

        max_workers = max(1, max_workers)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            file_paths, versions = zip(*batch_files)
            results = list(executor.map(_process_single_file_split, file_paths, versions))

        # results = [
        #     _process_single_file_split(file_path, version)
        #     for file_path, version in batch_files
        # ]

        for (file_path, version), file_chunks in zip(batch_files, results):
            num_chunks = len(file_chunks) if file_chunks else 0
            
            if self.verbose:
                print(f"    -> Split Artifact at \"{file_path}\" into {num_chunks} Chunk(s)...", file=sys.stderr)
            
            if file_chunks:
                raw_chunks_buffer.extend(file_chunks)

        result = {
            "raw_chunks_buffer": raw_chunks_buffer
        }

        if is_v1:
            result["sanitized_files_v1_queue"] = v1_queue
        else:
            result["sanitized_files_v2_queue"] = v2_queue

        return result

    def _should_continue_chunking(self, state: MapperAgentState) -> str:
        """Controls the routing loop processing files into raw chunks."""

        if state.get("sanitized_files_v1_queue") or state.get("sanitized_files_v2_queue"):
            return "chunk_files"

        if self.verbose:
            log_info(f"Split Artifact(s) in {len(state.get("raw_chunks_buffer", []))} Total Chunk(s).")

        return "prep_chunk_dedup_queue"

    def _prepare_chunk_deduplication_queue(self, state: MapperAgentState) -> dict:
        """Runs once after file chunking completes to safely copy raw data blocks
        into an isolated, sacrificial loop processing queue.
        """

        if self.verbose:
            log_info(f"Running Global Chunk(s) Deduplication...")

        return {
            "raw_chunks_buffer": [],
            "deduplication_queue": list(state.get("raw_chunks_buffer", [])),
            "chunk_registry": {}
        }

    def _deduplicate_chunks(self, state: MapperAgentState) -> dict:
        """Pops a batch of items from the queue, processes them in parallel 
        using multiple CPU cores, and updates the registry before checkpointing.
        """

        deduplication_queue = list(state.get("deduplication_queue", []))
        chunk_registry = dict(state.get("chunk_registry", {}))

        if not deduplication_queue:
            return {"deduplication_queue": []}

        BATCH_SIZE = 100

        batch_items = [deduplication_queue.pop(0) for _ in range(min(BATCH_SIZE, len(deduplication_queue)))]

        try:
            max_workers = len(os.sched_getaffinity(0))
        except AttributeError:
            max_workers = os.cpu_count() or 1

        max_workers = max(1, max_workers)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_hash_and_clean_chunk_batch, batch_items))

        for chunk_hash, cleaned_text, file_path, version in results:
            if not chunk_hash:
                continue

            if chunk_hash in chunk_registry:
                if file_path not in chunk_registry[chunk_hash]["sources"]:
                    chunk_registry[chunk_hash]["sources"].append(file_path)
            else:
                chunk_registry[chunk_hash] = {
                    "chunk_text": cleaned_text,
                    "sources": [file_path],
                    "version": version
                }

        return {
            "deduplication_queue": deduplication_queue,
            "chunk_registry": chunk_registry
        }

    def _should_continue_deduplication(self, state: MapperAgentState) -> str:
        """Evaluates if elements remain inside the dedicated loop queue tracker."""

        if len(state.get("deduplication_queue", [])) > 0:
            return "deduplicate_chunks"

        if self.verbose:
            log_info(f"Found {len(state.get("chunk_registry", {}).keys())} Total Unique Chunk(s).")

        return "prep_extraction"

    def _prepare_extraction_queues(self, state: MapperAgentState) -> dict:
        """Greedily aggregates separate unique chunks into maximized token-limit payloads 
        to prevent sending thousands of individual small requests to the LLM.
        """

        chunk_registry = dict(state.get("chunk_registry", {}))

        MAX_BUNDLE_CHARS = 60000

        v1_registry_items = [d for d in chunk_registry.values() if d.get("version") == "v1"]
        v2_registry_items = [d for d in chunk_registry.values() if d.get("version") == "v2"]

        def bundle_registry_items(items: List[dict]) -> List[dict]:
            bundle_queue = []
            current_bundle_text = []
            current_sources = set()
            current_len = 0

            for _, item in enumerate(items):
                text_block = f"---\n\n{item['chunk_text']}\n\n"
                block_len = len(text_block)

                if current_len + block_len > MAX_BUNDLE_CHARS and current_bundle_text:
                    bundle_queue.append({
                        "bundle_text": "".join(current_bundle_text).strip(),
                        "sources": list(current_sources)
                    })

                    current_bundle_text = []
                    current_sources = set()
                    current_len = 0

                current_bundle_text.append(text_block)
                current_sources.update(item["sources"])
                current_len += block_len

            if current_bundle_text:
                bundle_queue.append({
                    "bundle_text": "".join(current_bundle_text).strip(),
                    "sources": list(current_sources)
                })

            return bundle_queue

        chunks_v1_queue = bundle_registry_items(v1_registry_items)
        chunks_v2_queue = bundle_registry_items(v2_registry_items)

        if self.verbose:
            log_info(f"Running API Element(s) Extraction for {len(chunks_v1_queue)} V1 Chunk Bundle(s) and {len(chunks_v2_queue)} V2 Chunk Bundle(s)...")

        return {
            "chunk_registry": {},
            "chunks_v1_queue": chunks_v1_queue,
            "chunks_v2_queue": chunks_v2_queue,
            "extracted_v1": [],
            "extracted_v2": []
        }

    def _extract_step(self, state: MapperAgentState) -> dict:
        """Invokes the extraction LLM on a batch of packed, multi-chunk optimized 
        payload context blocks sequentially before saving a checkpoint.
        """

        v1_queue = list(state.get("chunks_v1_queue", []))
        v2_queue = list(state.get("chunks_v2_queue", []))
        extracted_v1 = list(state.get("extracted_v1", []))
        extracted_v2 = list(state.get("extracted_v2", []))

        is_v1 = len(v1_queue) > 0
        active_queue = v1_queue if is_v1 else v2_queue
        active_extracted = extracted_v1 if is_v1 else extracted_v2

        if not active_queue:
            return {}

        BATCH_SIZE = 100

        batch_items = [active_queue.pop(0) for _ in range(min(BATCH_SIZE, len(active_queue)))]

        for current_bundle in batch_items:
            bundle_text = current_bundle.get("bundle_text", "")

            if not bundle_text:
                continue

            try:
                result = self._extractor.invoke([
                    SystemMessage(content=get_mapper_extraction_prompt()),
                    HumanMessage(content=f"\n```\n{bundle_text}\n```\n")
                ])

                if result and hasattr(result, "elements"):
                    for element in result.elements:
                        active_extracted.append(element.model_dump() if hasattr(element, "model_dump") else element)

                    if self.verbose:
                        print(f"    -> Extracted {len(result.elements)} {"V1" if is_v1 else "V2"} API Element(s) from a Chunk Bundle of {len(bundle_text)} Characters...", file=sys.stderr)
                        

            except Exception as E:
                if self.verbose:
                    log_error(f"API Element(s) Extraction Failed : {E}")

                raise E

        if is_v1:
            return {
                "chunks_v1_queue": v1_queue,
                "extracted_v1": active_extracted
            }
        else:
            return {
                "chunks_v2_queue": v2_queue,
                "extracted_v2": active_extracted
            }

    def _should_continue_extraction(self, state: MapperAgentState) -> str:
        """Conditional router checking if files are left to process."""

        if state.get("chunks_v1_queue") or state.get("chunks_v2_queue"):
            return "extract_step"

        if self.verbose:
            log_info(f"Found {len(state.get("extracted_v1", []))} API Element(s) for V1 and {len(state.get("extracted_v2", []))} API Element(s) for V2.")

        return "deduplicate_elements"

    def _deduplicate_elements(self, state: MapperAgentState) -> dict:
        """Dedicated node that executes once all elements are extracted to deduplicate globally."""

        def deduplicate(elements: List[dict]) -> List[dict]:
            unique_elements = []
            seen_signatures = set()

            for element in elements:
                footprint = (element.get("namespace"), element.get("class_or_interface"), element.get("member"))

                if footprint not in seen_signatures:
                    seen_signatures.add(footprint)
                    unique_elements.append(element)

            return unique_elements

        if self.verbose:
            log_info(f"Running Global API Element(s) Deduplication...")

        extracted_v1 = deduplicate(state.get("extracted_v1", []))
        extracted_v2 = deduplicate(state.get("extracted_v2", []))

        result = {
            "extracted_v1": extracted_v1,
            "extracted_v2": extracted_v2
        }

        self._save_stage_output("extract", result)

        if self.verbose:
            log_info(f"Found {len(extracted_v1)} Unique API Element(s) for V1 and {len(extracted_v2)} Unique API Element(s) for V2.")

        return result

    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Returns a normalized similarity score between 0.0 and 1.0 using sequence matching."""

        if not s1 and not s2:
            return 1.0

        return SequenceMatcher(None, s1, s2).ratio()

    def _compute_similarity_matrix(self, v1_elements: List[dict], v2_elements: List[dict]) -> np.ndarray:
        if self.verbose:
            print("    -> Generating Semantic Similarity Matrix (Embeddings)...", file=sys.stderr)

        v1_summaries = [el.get('summary', '') for el in v1_elements]
        v2_summaries = [el.get('summary', '') for el in v2_elements]
        v1_signatures = [el.get('signature', '') for el in v1_elements]
        v2_signatures = [el.get('signature', '') for el in v2_elements]

        # Summary Embeddings Matrix
        v1_sum_embs = np.array(self._embedder.embed_documents(v1_summaries))
        v2_sum_embs = np.array(self._embedder.embed_documents(v2_summaries))
        v1_sum_norm = np.where(np.linalg.norm(v1_sum_embs, axis=1, keepdims=True) == 0, 1, np.linalg.norm(v1_sum_embs, axis=1, keepdims=True))
        v2_sum_norm = np.where(np.linalg.norm(v2_sum_embs, axis=1, keepdims=True) == 0, 1, np.linalg.norm(v2_sum_embs, axis=1, keepdims=True))
        summary_matrix = np.dot(v1_sum_embs / v1_sum_norm, (v2_sum_embs / v2_sum_norm).T)

        # Full Signature Embeddings Matrix
        v1_sig_embs = np.array(self._embedder.embed_documents(v1_signatures))
        v2_sig_embs = np.array(self._embedder.embed_documents(v2_signatures))
        v1_sig_norm = np.where(np.linalg.norm(v1_sig_embs, axis=1, keepdims=True) == 0, 1, np.linalg.norm(v1_sig_embs, axis=1, keepdims=True))
        v2_sig_norm = np.where(np.linalg.norm(v2_sig_embs, axis=1, keepdims=True) == 0, 1, np.linalg.norm(v2_sig_embs, axis=1, keepdims=True))
        signature_matrix = np.dot(v1_sig_embs / v1_sig_norm, (v2_sig_embs / v2_sig_norm).T)

        n_v1, n_v2 = len(v1_elements), len(v2_elements)
        final_sim_matrix = np.zeros((n_v1, n_v2))

        EPSILON = 1e-6

        for i in range(n_v1):
            el1 = v1_elements[i]
            id1 = ".".join([el1.get(k, '') for k in ['namespace', 'class_or_interface', 'member'] if el1.get(k)])

            for j in range(n_v2):
                el2 = v2_elements[j]
                id2 = ".".join([el2.get(k, '') for k in ['namespace', 'class_or_interface', 'member'] if el2.get(k)])

                # Extract basic raw metrics
                struct_score = self._levenshtein_similarity(id1, id2)
                sig_semantic_score = signature_matrix[i, j]
                sum_semantic_score = summary_matrix[i, j]

                # 1. Primary Weight: Function of structural identity score
                # Squaring it ensures high scores scale up faster than poor ones
                w_id = (struct_score ** 2) * 0.60

                # Calculate remaining space pool left over
                pool_remaining = 1.0 - w_id

                # 2. Secondary Weight: Function of signature strength vs summary strength inside the pool
                sig_ratio = (sig_semantic_score + EPSILON) / (sig_semantic_score + sum_semantic_score + (2 * EPSILON))
                w_sig = pool_remaining * sig_ratio

                # 3. Tertiary Weight: Absolute remainder to maintain 1.0 unity summation
                w_sum = pool_remaining - w_sig

                # Synthesize final score using the continuously adapted weights
                final_sim_matrix[i, j] = (w_id * struct_score) + (w_sig * sig_semantic_score) + (w_sum * sum_semantic_score)

        return final_sim_matrix

    def _convert_sim_matrix_to_json(self, sim_matrix, v1_elements, v2_elements):
        # Output tracking map json construction
        sim_matrix_json = {}

        for i, el1 in enumerate(v1_elements):
            v1_key = ".".join([el1.get(k) for k in ['namespace', 'class_or_interface', 'member'] if el1.get(k)])
            sim_matrix_json[v1_key] = {}

            for j, el2 in enumerate(v2_elements):
                v2_key = ".".join([el2.get(k) for k in ['namespace', 'class_or_interface', 'member'] if el2.get(k)])
                sim_matrix_json[v1_key][v2_key] = sim_matrix[i, j].item()

        return sim_matrix_json

    def _compute_modified_z_matrix(self, sim_matrix: np.ndarray) -> Tuple[np.ndarray, float, float]:
        n_v1, n_v2 = sim_matrix.shape

        if n_v1 == 0 or n_v2 == 0:
            return np.empty((n_v1, n_v2)), 0.0, 0.10

        matrix_flat = sim_matrix.flatten()
        matrix_median = np.median(matrix_flat)
        abs_deviation = np.abs(matrix_flat - matrix_median)
        mad = np.median(abs_deviation)

        # Protective guardrails to prevent zero-division on low-variance or tiny datasets
        if mad > 0.02 and matrix_flat.size >= 25:
            mad_stabilizer = mad
        else:
            mad_stabilizer = 0.10

        # Transform raw similarity space into pure statistical outlier scales
        z_matrix = (0.6745 * (sim_matrix - matrix_median)) / mad_stabilizer

        return z_matrix, matrix_median, mad_stabilizer


    def _initial_semantic_match(self, v1_elements: List[dict], v2_elements: List[dict], z_matrix: np.ndarray) -> Tuple[List[MappingRow], List[dict]]:
        final_rows: List[MappingRow] = []
        resolution_queue = []
        v2_target_map = defaultdict(list)
        v1_candidates_map = {}

        if self.verbose:
            log_info(f"Running Preliminary V1 <-> V2 API Element(s) Matching...")

        n_v1, n_v2 = z_matrix.shape

        if n_v1 == 0 or n_v2 == 0:
            return final_rows, resolution_queue

        # Define invariant statistical rule milestones inside Z-score space
        dynamic_floor = 1.0       # Demands a full standard deviation from noise floor to be considered a candidate
        dynamic_threshold = 3.5   # Universal extreme anomaly marker for high-confidence matches
        dynamic_margin = 1.0      # Demands a full standard deviation gap to prevent ambiguity

        # Step 2: Map out potential target relationships based on above-average Z-scores
        for v1_idx, z_scores in enumerate(z_matrix):
            valid_indices = np.where(z_scores >= dynamic_floor)[0]
            v1_candidates_map[v1_idx] = valid_indices

            for v2_idx in valid_indices:
                v2_target_map[v2_idx].append(v1_idx)

        # Step 3: Determine cardinality and route elements to final rows or the LLM resolution queue
        for v1_idx, z_scores in enumerate(z_matrix):
            v1_data = v1_elements[v1_idx]
            valid_indices = v1_candidates_map[v1_idx]

            if len(valid_indices) == 0:
                resolution_queue.append({"v1_element": v1_data, "potential_targets": []})

                continue

            # Sort candidate targets descending based on their statistical Z-Score strength
            sorted_indices = valid_indices[np.argsort(-z_scores[valid_indices])]
            has_multiple_targets = len(valid_indices) > 1
            any_target_is_shared = any(len(v2_target_map[idx]) > 1 for idx in valid_indices)

            cardinality = Complexity.ONE_TO_ONE

            if has_multiple_targets and any_target_is_shared:
                cardinality = Complexity.MANY_TO_MANY
            elif has_multiple_targets:
                cardinality = Complexity.ONE_TO_MANY
            elif any_target_is_shared:
                cardinality = Complexity.MANY_TO_ONE

            # Collect target candidates alongside their native Z-scores
            candidates = [{"z_score": float(z_scores[idx]), "element": v2_elements[idx]} for idx in sorted_indices]
            top_z_score = candidates[0]['z_score']
            
            # Pure Z-space structural rules
            is_very_high_conf = top_z_score >= dynamic_threshold
            has_clear_gap = len(candidates) == 1 or (top_z_score - candidates[1]['z_score'] > dynamic_margin)

            if is_very_high_conf and has_clear_gap:
                final_rows.append(self._create_mapping_row(v1_data, candidates[0]['element'], Complexity.ONE_TO_ONE))
            elif is_very_high_conf:
                # Retain all contextual targets that safely clear above-average background noise
                intentional_targets = [cand for cand in candidates if cand['z_score'] >= dynamic_floor and top_z_score - cand['z_score'] <= dynamic_margin]

                for cand in intentional_targets:
                    final_rows.append(self._create_mapping_row(v1_data, cand['element'], cardinality))
            else:
                resolution_queue.append({"v1_element": v1_data, "potential_targets": [item["element"] for item in candidates]})

        if self.verbose:
            print(f"    -> Found {len(final_rows)} Direct Matches and {len(resolution_queue)} Complex Cases.", file=sys.stderr)

        return final_rows, resolution_queue

    def _match_initial(self, state: MapperAgentState) -> Dict[str, List[dict]]:
        v1_elements, v2_elements = state.get('extracted_v1', []), state.get('extracted_v2', [])

        if not v1_elements or not v2_elements:
            if self.verbose:
                log_info(f"Skipping Initial Match: ONE OR BOTH VERSIONS HAVE NO ELEMENTS TO MATCH.")

            result = {"initial_mappings": [], "resolution_queue": []}

            self._save_stage_output("map_initial", result)

            return result

        if self.verbose:
            log_info(f"Running Initial Match...")

        sim_matrix = self._compute_similarity_matrix(v1_elements, v2_elements)
        z_matrix, _, _ = self._compute_modified_z_matrix(sim_matrix)
        final_rows, resolution_queue = self._initial_semantic_match(v1_elements, v2_elements, z_matrix)

        if self.verbose:
            display_rich_matrix(sim_matrix, v1_elements, v2_elements, 20, "Semantic Similarity Matrix")
            display_rich_matrix(z_matrix, v1_elements, v2_elements, 20, "Semantic Similarity Z-Matrix (Z-Scores)")
            
        sim_matrix_json = self._convert_sim_matrix_to_json(sim_matrix, v1_elements, v2_elements)
        z_matrix_json = self._convert_sim_matrix_to_json(z_matrix, v1_elements, v2_elements)

        self._save_stage_output("similarity_matrix", sim_matrix_json)
        self._save_stage_output("z_matrix", z_matrix_json)

        result = {
            "initial_mappings": [row.model_dump() if hasattr(row, 'model_dump') else row for row in final_rows],
            "resolution_queue": resolution_queue
        }

        self._save_stage_output("preliminary_mapping", result)

        return result

    def _prepare_mapping_queues(self, state: MapperAgentState) -> dict:
        """Initializes branch-specific staging queues and raw storage accumulators."""

        resolution_queue = state.get("resolution_queue", [])

        return {
            "extracted_v1": [],
            "extracted_v2": [],
            "resolution_queue": [],
            "queue_agent_1": list(resolution_queue) if self.multi_agent else [],
            "queue_agent_2": list(resolution_queue) if self.multi_agent else [],
            "queue_agent_3": list(resolution_queue) if self.multi_agent else [],
            "queue_single": list(resolution_queue),
            "raw_agent_1": [],
            "raw_agent_2": [],
            "raw_agent_3": [],
            "raw_single": []
        }

    def _execute_agent_mapping_step(self, state: MapperAgentState, resolver_client: RateLimitedChatOpenAI, prompt: str, agent_label: str, queue_key: str, raw_key: str) -> dict:
        """Processes a single batch of complex mappings for a specific agent strategy."""

        queue = list(state.get(queue_key, []))
        raw_accumulated = list(state.get(raw_key, []))

        if not queue:
            return {}

        # Extract up to the configured batch size
        batch_size = getattr(self, "resolver_batch_size", 5)
        batch = [queue.pop(0) for _ in range(min(len(queue), batch_size))]

        if self.verbose:
            log_info(f"{agent_label}: Routing Batch of {len(batch)} Complex Cases...")

        try:
            response = resolver_client.invoke([
                SystemMessage(content=prompt),
                HumanMessage(content=f"\n```json\n{json.dumps(batch, indent=2)}\n```\n")
            ])

            if response and hasattr(response, 'resolved_items'):
                for item in response.resolved_items:
                    raw_accumulated.append(item.model_dump() if hasattr(item, 'model_dump') else item)
        except Exception as E:
            if self.verbose:
                log_error(f"Batch Resolution for {agent_label} Failed: {E}")

            raise E

        return {queue_key: queue, raw_key: raw_accumulated}

    def _should_continue_agent_mapping(self, state: MapperAgentState, queue_key: str, next_step_node: str, finalized_node: str) -> str:
        """Determines whether an agent branch needs to continue batching or proceed to finalization."""

        return next_step_node if state.get(queue_key) else finalized_node

    def _finalize_agent_mapping(self, state: MapperAgentState, agent_label: str, raw_key: str, output_key: str) -> dict:
        """Processes raw batch extractions, computes cross-reference structural cardinalities, and exports snapshots."""

        unresolved_rows = state.get(raw_key, [])
        resolved_rows = []

        v1_counts: Counter = Counter()
        v2_counts: Counter = Counter()

        # Compute relational degrees
        for item in unresolved_rows:
            v1_key = self._get_element_key(item.get("v1_element"))
            selected_targets = item.get("selected_targets") or []
            unique_targets = {self._get_element_key(t): t for t in selected_targets}
            
            v1_counts[v1_key] += len(unique_targets)

            for v2_key in unique_targets.keys():
                v2_counts[v2_key] += 1

        # Map to structured cardinality definitions
        for item in unresolved_rows:
            v1_el = item.get("v1_element", {})
            v1_key = self._get_element_key(v1_el)
            reason = item.get("reason", "")
            selected_targets = item.get("selected_targets") or []

            if not v1_counts.get(v1_key, 0) and not selected_targets:
                resolved_rows.append(self._create_mapping_row(v1_el, {}, Complexity.DEPRECATED, reason))

                continue

            unique_targets = {self._get_element_key(t): t for t in selected_targets}

            for v2_key, target in unique_targets.items():
                v1_out_degree, v2_in_degree = v1_counts.get(v1_key, 1), v2_counts.get(v2_key, 1)

                if v1_out_degree > 1 and v2_in_degree > 1:
                    cardinality = Complexity.MANY_TO_MANY
                elif v1_out_degree > 1:
                    cardinality = Complexity.ONE_TO_MANY
                elif v2_in_degree > 1:
                    cardinality = Complexity.MANY_TO_ONE
                else:
                    cardinality = Complexity.ONE_TO_ONE

                resolved_rows.append(self._create_mapping_row(v1_el, target, cardinality, reason))

        # Handle specialized output key adjustments for single agent operations
        if output_key == "mappings":
            result = {
                raw_key: [],
                "mappings": state.get("initial_mappings", []) + [row.model_dump() if hasattr(row, "model_dump") else row for row in resolved_rows]
            }
            stage_label = "map_single"
        else:
            result = {
                raw_key: [],
                output_key: [row.model_dump() if hasattr(row, "model_dump") else row for row in resolved_rows]
            }
            stage_label = f"map_{agent_label.replace(' ', '_').lower()}"

        self._save_stage_output(stage_label, result)

        return result

    def _check_consensus_votes(self, state: MapperAgentState) -> dict:
        """Evaluates agent cross-votes, isolates majorities, and stacks deadlocks into a state queue."""

        maps_1 = list(state.get("mappings_agent_1", []))
        maps_2 = list(state.get("mappings_agent_2", []))
        maps_3 = list(state.get("mappings_agent_3", []))

        if self.verbose:
            for i, maps in enumerate([maps_1, maps_2, maps_3], start=1):
                log_info(f"Mappings from Agent {i}:")

                display_mapping_table(maps)

            log_info("Reviewing Agent(s) Alignment...")

        def get_source_key(m: dict) -> Tuple[str, str, str, str]:
            return (m.get("old_namespace", ""), m.get("old_class_interface", ""), m.get("old_member", ""), m.get("old_signature", ""))

        v1_lookup = {self._get_element_key(el): el for el in state.get("extracted_v1", [])}
        v2_lookup = {self._get_element_key(el): el for el in state.get("extracted_v2", [])}

        by_source = defaultdict(lambda: defaultdict(list))

        for agent_name, agent_maps in zip(["agent_1", "agent_2", "agent_3"], [maps_1, maps_2, maps_3]):
            for m in agent_maps:
                by_source[get_source_key(m)][agent_name].append(m)

        base_consensus_mappings = []
        stalemates = []

        for source_key, assignments in by_source.items():
            bundles = []

            for agent_id in ["agent_1", "agent_2", "agent_3"]:
                agent_maps = assignments[agent_id]

                if not agent_maps:
                    bundles.append(("EMPTY_OR_DEPRECATED", []))

                    continue

                sorted_maps = sorted(agent_maps, key=lambda m: f"{m.get('new_namespace')}||{m.get('new_class_interface')}||{m.get('new_member')}||{m.get('new_signature')}")
                bundle_sig = ":::".join(f"{m.get('new_namespace')}||{m.get('new_class_interface')}||{m.get('new_member')}||{m.get('new_signature')}||{m.get('complexity')}" for m in sorted_maps)

                bundles.append((bundle_sig, agent_maps))

            counter = Counter([b[0] for b in bundles])
            most_common_sig, vote_count = counter.most_common(1)[0]

            if vote_count >= 2:
                winning_maps = next(b[1] for b in bundles if b[0] == most_common_sig)

                base_consensus_mappings.extend(winning_maps)
            else:
                def enrich_proposal(maps: List[dict]) -> List[dict]:
                    return [{
                        "mapping_details": m,
                        "v2_target_element": v2_lookup.get((m.get("new_namespace"), m.get("new_class_interface"), m.get("new_member"), m.get("new_signature")), "DEPRECATED_OR_NO_TARGET")
                    } for m in maps]

                stalemates.append({
                    "source_element": v1_lookup.get(source_key, {}),
                    "agent_1_proposal": enrich_proposal(assignments["agent_1"]),
                    "agent_2_proposal": enrich_proposal(assignments["agent_2"]),
                    "agent_3_proposal": enrich_proposal(assignments["agent_3"])
                })

        return {
            "mappings_agent_1": [],
            "mappings_agent_2": [],
            "mappings_agent_3": [],
            "base_consensus_mappings": base_consensus_mappings,
            "stalemates_queue": stalemates,
            "raw_arbitrated_mappings": []
        }

    def _arbitrate_stalemate_step(self, state: MapperAgentState) -> dict:
        """Processes exactly one batch of ties through the referee model, updating checkpoint blocks."""

        queue = list(state.get("stalemates_queue", []))
        raw_arbitrated = list(state.get("raw_arbitrated_mappings", []))

        if not queue:
            return {}

        batch_size = getattr(self, "resolver_batch_size", 5)
        batch = [queue.pop(0) for _ in range(min(len(queue), batch_size))]

        if self.verbose:
            log_info(f"Processing Stalemate Tie-Breaking Batch of {len(batch)} Complex Cases...")

        try:
            response = self._resolver_1.invoke([
                SystemMessage(content=get_consensus_arbitration_prompt()),
                HumanMessage(content=f"\n```json\n{json.dumps(batch, indent=2)}\n```\n")
            ])

            if response and hasattr(response, 'resolved_items'):
                for item in response.resolved_items:
                    raw_arbitrated.append(item.model_dump() if hasattr(item, 'model_dump') else item)
        except Exception as E:
            if self.verbose:
                log_error(f"Consensus Arbitration Failed: {E}")

            raise E

        return {"stalemates_queue": queue, "raw_arbitrated_mappings": raw_arbitrated}

    def _should_continue_arbitration(self, state: MapperAgentState) -> str:
        """Routes out of arbitration once deadlocks are resolved."""

        return "arbitrate_step" if state.get("stalemates_queue") else "finalize_consensus"

    def _finalize_consensus(self, state: MapperAgentState) -> dict:
        """Assembles base agreements and arbitrated stalemates into final state."""

        base_mappings = list(state.get("base_consensus_mappings", []))
        arbitrated_rows = list(state.get("raw_arbitrated_mappings", []))
        initial_mappings = list(state.get("initial_mappings", []))

        # Process out structural cardinalities from the referee extractions
        resolved_rows = []
        v1_counts: Counter = Counter()
        v2_counts: Counter = Counter()

        for item in arbitrated_rows:
            v1_key = self._get_element_key(item.get("v1_element"))
            selected_targets = item.get("selected_targets") or []
            unique_targets = {self._get_element_key(t): t for t in selected_targets}
            v1_counts[v1_key] += len(unique_targets)

            for v2_key in unique_targets.keys():
                v2_counts[v2_key] += 1

        for item in arbitrated_rows:
            v1_el = item.get("v1_element", {})
            v1_key = self._get_element_key(v1_el)
            reason = item.get("reason", "")
            selected_targets = item.get("selected_targets") or []

            if not v1_counts.get(v1_key, 0) and not selected_targets:
                resolved_rows.append(self._create_mapping_row(v1_el, {}, Complexity.DEPRECATED, reason))

                continue

            unique_targets = {self._get_element_key(t): t for t in selected_targets}

            for v2_key, target in unique_targets.items():
                v1_out_degree, v2_in_degree = v1_counts.get(v1_key, 1), v2_counts.get(v2_key, 1)

                if v1_out_degree > 1 and v2_in_degree > 1:
                    cardinality = Complexity.MANY_TO_MANY
                elif v1_out_degree > 1:
                    cardinality = Complexity.ONE_TO_MANY
                elif v2_in_degree > 1:
                    cardinality = Complexity.MANY_TO_ONE
                else:
                    cardinality = Complexity.ONE_TO_ONE

                resolved_rows.append(self._create_mapping_row(v1_el, target, cardinality, reason))

        result = {
            "base_consensus_mappings": [],
            "raw_arbitrated_mappings": [],
            "initial_mappings": [],
            "mappings": initial_mappings + base_mappings + [row.model_dump() if hasattr(row, "model_dump") else row for row in resolved_rows]
        }

        self._save_stage_output("consensus_mapping", result)

        return result

    def _create_mapping_row(self, v1_data: dict, v2_data: dict, complexity: str = "", notes: str = "") -> MappingRow:
        return MappingRow(
            old_namespace=v1_data.get('namespace',''),
            old_class_interface=v1_data.get('class_or_interface',''),
            old_member=v1_data.get('member',''),
            old_signature=v1_data.get('signature',''),
            new_namespace=v2_data.get('namespace',''),
            new_class_interface=v2_data.get('class_or_interface',''),
            new_member=v2_data.get('member',''),
            new_signature=v2_data.get('signature',''),
            complexity=complexity,
            additional_notes=notes
        )

    def run(self, path_a: str, path_b: str, thread_id: str = "") -> List[dict]:
        if self.verbose:
            log_info(f"Running Mapper Agent...")

        try:
            if thread_id and thread_id.strip():
                config = {"configurable": {"thread_id": thread_id}}
                current_state = self.graph.get_state(config)

                if current_state.next:
                    if self.verbose:
                        log_info(f"Incomplete Checkpoint for \"{thread_id}\". Resuming from Node {current_state.next}.")

                    initial_input = None
                else:
                    if self.verbose:
                        log_info(f"No Checkpoints for \"{thread_id}\". Initiating Run \"{thread_id}\".")

                    initial_input = {
                        "run_id": thread_id,
                        "dir_v1": path_a,
                        "dir_v2": path_b,
                        "discovery_queue_v1": [],
                        "discovery_queue_v2": [],
                        "files_v1": [],
                        "files_v2": [],
                        "files_v1_queue": [],
                        "files_v2_queue": [],
                        "sanitized_files_v1": [],
                        "sanitized_files_v2": [],
                        "sanitized_files_v1_queue": [],
                        "sanitized_files_v2_queue": [],
                        "raw_chunks_buffer": [],
                        "chunk_registry": {},
                        "deduplication_queue": [],
                        "chunks_v1_queue": [],
                        "chunks_v2_queue": [],
                        "extracted_v1": [],
                        "extracted_v2": [] ,
                        "initial_mappings": [],
                        "resolution_queue": [],
                        "queue_agent_1": [],
                        "queue_agent_2": [],
                        "queue_agent_3": [],
                        "queue_single": [],
                        "raw_agent_1": [],
                        "raw_agent_2": [],
                        "raw_agent_3": [],
                        "raw_single": [],
                        "mappings_agent_1": [],
                        "mappings_agent_2": [],
                        "mappings_agent_3": [],
                        "base_consensus_mappings": [],
                        "stalemates_queue": [],
                        "raw_arbitrated_mappings": [],
                        "mappings": []
                    }
            else:
                if self.verbose:
                    log_info(f"No Thread ID. Disabling Checkpoint.")

                initial_input = {"dir_v1": path_a, "dir_v2": path_b}
                config = {}

            final_state = self.graph.invoke(initial_input, config=config)
            mappings = final_state.get('mappings', [])

            if self.verbose:
                display_mapping_table(mappings)

            return mappings
        except Exception as E:
            if self.verbose:
                log_error(f"Mapper Agent Failed: {E}")

            raise E