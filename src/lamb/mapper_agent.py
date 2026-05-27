import os
import json
import numpy as np
from collections import Counter

from typing import List, TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .types import Complexity
from .output_templates import ElementsExtraction, MappingRow, ResolutionResult
from .prompt_templates import get_mapper_extraction_prompt, get_general_mapper_resolution_prompt, get_lexical_mapper_resolution_prompt, get_semantic_mapper_resolution_prompt, get_consensus_arbitration_prompt
from .logger import print_agent_state, display_rich_matrix, display_mapping_table

class MapperAgentState(TypedDict):
    dir_v1: str
    dir_v2: str
    files_v1: List[str]
    files_v2: List[str]
    extracted_v1: List[dict]
    extracted_v2: List[dict]
    initial_mappings: List[dict]
    resolution_queue: List[dict]
    mappings_agent_1: List[dict]
    mappings_agent_2: List[dict]
    mappings_agent_3: List[dict]
    mappings: List[dict]

class MapperAgent:
    def __init__(
            self,
            extractor: ChatOpenAI,
            embedder: OpenAIEmbeddings,
            resolver_agent_1: ChatOpenAI,
            resolver_agent_2: ChatOpenAI = None,
            resolver_agent_3: ChatOpenAI = None,
            multi_agent: bool = True,
            confidence_floor: float = 0.65,
            confidence_threshold: float = 0.95,
            ambiguous_margin: float = 0.15,
            resolver_batch_size: int = 20,
            verbose: bool = False
        ):
        self._extractor = extractor.with_structured_output(ElementsExtraction).with_retry(stop_after_attempt=2)
        self._embedder = embedder

        self.multi_agent = multi_agent

        self._resolver_1 = resolver_agent_1.with_structured_output(ResolutionResult).with_retry(stop_after_attempt=2)
        self._resolver_2 = resolver_agent_2.with_structured_output(ResolutionResult).with_retry(stop_after_attempt=2) if resolver_agent_2 else None
        self._resolver_3 = resolver_agent_3.with_structured_output(ResolutionResult).with_retry(stop_after_attempt=2) if resolver_agent_3 else None

        if self.multi_agent and (not self._resolver_2 or not self._resolver_3):
            if verbose:
                print("[!] Multi-agent resolution enabled but resolver agents 2 or 3 are missing. Falling back to single-agent.")

            self.multi_agent = False
        else:
            if verbose:
                print("[!] Multi-agent resolution enabled.")

        self.confidence_floor = confidence_floor
        self.confidence_threshold = confidence_threshold
        self.ambiguous_margin = ambiguous_margin
        self.resolver_batch_size = resolver_batch_size
        self.verbose = verbose

        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Constructs and compiles the LangGraph state machine."""

        workflow = StateGraph(MapperAgentState)

        workflow.add_node("discover", self._discover_files)
        workflow.add_node("extract", self._extract_elements)
        workflow.add_node("map_initial", self._match_initial)
        
        if self.multi_agent:
            workflow.add_node("map_agent_1", self._generate_mapping_agent_1)
            workflow.add_node("map_agent_2", self._generate_mapping_agent_2)
            workflow.add_node("map_agent_3", self._generate_mapping_agent_3)
            workflow.add_node("consensus", self._resolve_consensus)

            workflow.set_entry_point("discover")

            workflow.add_edge("discover", "extract")
            workflow.add_edge("extract", "map_initial")
            workflow.add_edge("map_initial", "map_agent_1")
            workflow.add_edge("map_initial", "map_agent_2")
            workflow.add_edge("map_initial", "map_agent_3")
            workflow.add_edge("map_agent_1", "consensus")
            workflow.add_edge("map_agent_2", "consensus")
            workflow.add_edge("map_agent_3", "consensus")
            workflow.add_edge("consensus", END)
        else:
            workflow.add_node("map_single", self._generate_mapping_single)

            workflow.set_entry_point("discover")

            workflow.add_edge("discover", "extract")
            workflow.add_edge("extract", "map_initial")
            workflow.add_edge("map_initial", "map_single")
            workflow.add_edge("map_single", END)

        return workflow.compile(checkpointer=self.memory)

    def _discover_files(self, state: MapperAgentState):
        def is_text_file(filepath: str) -> bool:
            try:
                with open(filepath, 'tr', encoding='utf-8') as check_file:
                    check_file.read(1024)

                return True
            except Exception:
                return False

        def get_all_text_files(directory: str) -> List[str]:
            found_files = []

            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for file in files:
                    if not file.startswith('.'):
                        filepath = os.path.join(root, file)

                        if is_text_file(filepath):
                            found_files.append(filepath)

            return found_files

        dir_v1 = state.get("dir_v1", "")
        dir_v2 = state.get("dir_v2", "")

        if self.verbose:
            print_agent_state({"dir_v1": dir_v1, "dir_v2": dir_v2}, title="Current State: Discovery")
            print(f"[*] Discovering files in v1: {dir_v1} and v2: {dir_v2}")

        files_v1 = get_all_text_files(dir_v1)
        files_v2 = get_all_text_files(dir_v2)

        if self.verbose:
            print(f"    - Found {len(files_v1)} text files in v1 and {len(files_v2)} in v2.")

        return {
            "files_v1": files_v1,
            "files_v2": files_v2
        }


    def _extract_elements(self, state: MapperAgentState):
        def process_files(file_paths: List[str]) -> List[dict]:
            all_elements = []

            for file_path in file_paths:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()

                    if not content: continue

                    result = self._extractor.invoke([
                        SystemMessage(content=get_mapper_extraction_prompt()),
                        HumanMessage(content=f"\n```\n{content}\n```\n")
                    ])

                    if result and result.elements:
                        all_elements.extend([el.model_dump() for el in result.elements])
                except Exception as e:
                    if self.verbose:
                        print(f"    [Warning] Failed at {file_path}: {e}")

            return all_elements

        files_v1 = state.get("files_v1", [])
        files_v2 = state.get("files_v2", [])

        if self.verbose:
            print_agent_state({"files_v1": files_v1, "files_v2": files_v2}, title="Current State: Extraction")
            print("[*] Extracting structural elements from files...")

        extracted_v1 = process_files(files_v1)
        extracted_v2 = process_files(files_v2)

        if self.verbose:
            print(f"    - Extracted {len(extracted_v1)} elements from v1 and {len(extracted_v2)} from v2.")

        return {
            "extracted_v1": extracted_v1,
            "extracted_v2": extracted_v2
        }

    def _match_initial(self, state: MapperAgentState):
        v1_elements = state.get('extracted_v1', [])
        v2_elements = state.get('extracted_v2', [])

        if not v1_elements or not v2_elements:
            if self.verbose:
                print("    - Skipping initial match: one or both versions have no elements.")
            return {"initial_mappings": [], "resolution_queue": []}

        if self.verbose:
            print_agent_state({"extracted_v1": v1_elements, "extracted_v2": v2_elements}, title="Current State: Mapping")
            print(f"[*] Starting Initial Semantic Match (V1: {len(v1_elements)} elements, V2: {len(v2_elements)} elements)...")

        # 1. Compute Similarity Matrix
        sim_matrix = self._compute_similarity_matrix(v1_elements, v2_elements)

        # 2. Initial Semantic Matching (Direct vs Complex)
        final_rows, resolution_queue = self._initial_semantic_match(v1_elements, v2_elements, sim_matrix)

        return {
            "initial_mappings": [row.model_dump() for row in final_rows],
            "resolution_queue": resolution_queue
        }

    def _generate_mapping_agent_1(self, state: MapperAgentState):
        resolution_queue = state.get("resolution_queue", [])
        if not resolution_queue:
            return {"mappings_agent_1": []}

        if self.verbose:
            print(f"\n[Agent 1] Resolving {len(resolution_queue)} complex items using General strategy...")
        
        resolved_rows = self._resolve_complex_mappings(resolution_queue, self._resolver_1, get_general_mapper_resolution_prompt())
        return {"mappings_agent_1": [row.model_dump() for row in resolved_rows]}

    def _generate_mapping_agent_2(self, state: MapperAgentState):
        resolution_queue = state.get("resolution_queue", [])
        if not resolution_queue:
            return {"mappings_agent_2": []}

        if self.verbose:
            print(f"\n[Agent 2] Resolving {len(resolution_queue)} complex items using Lexical strategy...")
        
        resolved_rows = self._resolve_complex_mappings(resolution_queue, self._resolver_2, get_lexical_mapper_resolution_prompt())
        return {"mappings_agent_2": [row.model_dump() for row in resolved_rows]}

    def _generate_mapping_agent_3(self, state: MapperAgentState):
        resolution_queue = state.get("resolution_queue", [])
        if not resolution_queue:
            return {"mappings_agent_3": []}

        if self.verbose:
            print(f"\n[Agent 3] Resolving {len(resolution_queue)} complex items using Semantic strategy...")
        
        resolved_rows = self._resolve_complex_mappings(resolution_queue, self._resolver_3, get_semantic_mapper_resolution_prompt())
        return {"mappings_agent_3": [row.model_dump() for row in resolved_rows]}

    def _resolve_complex_mappings(self, resolution_queue: List[dict], resolver_client, prompt: str) -> List[MappingRow]:
        total_items = len(resolution_queue)

        if self.verbose:
            print(f"  -> Routing {total_items} items to LLM in batches of {self.resolver_batch_size}...")

        resolved_rows: List[MappingRow] = []

        for i in range(0, total_items, self.resolver_batch_size):
            batch = resolution_queue[i : i + self.resolver_batch_size]

            response = resolver_client.invoke([
                SystemMessage(content=prompt),
                HumanMessage(content=f"\n```json\n{json.dumps(batch, indent=2)}\n```\n")
            ])

            if response and hasattr(response, 'resolved_items'):
                for item in response.resolved_items:
                    v1_data = item.v1_element.model_dump()

                    # Handle Deprecation
                    if item.decision in [Complexity.DEPRECATED] or not item.selected_targets:
                        resolved_rows.append(
                            self._create_mapping_row(v1_data, {}, item.decision, item.reason)
                        )
                    # Handle 1:N and N:N
                    elif item.decision in [Complexity.ONE_TO_MANY, Complexity.MANY_TO_MANY]:
                        for target in item.selected_targets:
                            resolved_rows.append(
                                self._create_mapping_row(v1_data, target.model_dump(), item.decision, item.reason)
                            )
                    # Handle 1:1, N:1, and Ambiguous
                    elif item.decision in [Complexity.ONE_TO_ONE, Complexity.MANY_TO_ONE, Complexity.AMBIGUOUS]:
                        target = item.selected_targets[0]

                        resolved_rows.append(
                            self._create_mapping_row(v1_data, target.model_dump(), item.decision, item.reason)
                        )

        return resolved_rows

    def _resolve_consensus(self, state: MapperAgentState):
        maps_1 = state.get("mappings_agent_1", [])
        maps_2 = state.get("mappings_agent_2", [])
        maps_3 = state.get("mappings_agent_3", [])
        initial_mappings = state.get("initial_mappings", [])
        extracted_v1 = state.get("extracted_v1", [])
        extracted_v2 = state.get("extracted_v2", [])

        if self.verbose:
            print(f"\n[*] Mappings from Agent 1:")
            display_mapping_table(maps_1)
            print(f"\n[*] Mappings from Agent 2:")
            display_mapping_table(maps_2)
            print(f"\n[*] Mappings from Agent 3:")
            display_mapping_table(maps_3)
            print(f"\n[*] Reviewing alignments across separate agents...")

        def get_source_key(m: dict) -> tuple:
            return (m.get("old_namespace"), m.get("old_class_interface"), m.get("old_member"), m.get("old_signature"))

        # Create a lookup for clean, unmapped V1 source elements
        v1_lookup = {
            (el.get("namespace"), el.get("class_or_interface"), el.get("member"), el.get("signature")): el
            for el in extracted_v1
        }

        # Create a lookup for clean, original V2 target elements
        v2_lookup = {
            (el.get("namespace"), el.get("class_or_interface"), el.get("member"), el.get("signature")): el
            for el in extracted_v2
        }

        all_sources = set()
        by_source = {}

        for m in maps_1 + maps_2 + maps_3:
            key = get_source_key(m)
            all_sources.add(key)
            if key not in by_source:
                by_source[key] = {"agent_1": [], "agent_2": [], "agent_3": []}

        for m in maps_1: by_source[get_source_key(m)]["agent_1"].append(m)
        for m in maps_2: by_source[get_source_key(m)]["agent_2"].append(m)
        for m in maps_3: by_source[get_source_key(m)]["agent_3"].append(m)

        consensus_mappings = []
        stalemates = []

        for source_key, assignments in by_source.items():
            bundles = []

            for agent_id in ["agent_1", "agent_2", "agent_3"]:
                agent_maps = assignments[agent_id]
                
                if not agent_maps:
                    bundles.append(("EMPTY_OR_DEPRECATED", []))
                    continue

                # Sort mappings deterministically to create a unique bundle signature
                sorted_maps = sorted(agent_maps, key=lambda m: f"{m.get('new_namespace')}||{m.get('new_class_interface')}||{m.get('new_member')}||{m.get('new_signature')}")
                
                # The bundle signature includes all targets and the overall complexity to ensure structural integrity
                bundle_sig_parts = [f"{m.get('new_namespace')}||{m.get('new_class_interface')}||{m.get('new_member')}||{m.get('new_signature')}||{m.get('complexity')}" for m in sorted_maps]
                bundle_sig = ":::".join(bundle_sig_parts)
                
                bundles.append((bundle_sig, agent_maps))

            # Count the bundle signatures
            counter = Counter([b[0] for b in bundles])
            most_common_sig, vote_count = counter.most_common(1)[0]

            if vote_count >= 2:
                # We have a consensus on the entire bundle. Find the first agent that proposed this winning bundle.
                winning_maps = next(b[1] for b in bundles if b[0] == most_common_sig)
                consensus_mappings.extend(winning_maps)
            else:
                # 3-way tie stalemate. Enrich all proposals and send the entire strategic context to the referee.
                def enrich_proposal(maps):
                    enriched = []
                    for m in maps:
                        v2_key = (m.get("new_namespace"), m.get("new_class_interface"), m.get("new_member"), m.get("new_signature"))
                        v2_el = v2_lookup.get(v2_key)
                        
                        enriched.append({
                            "mapping_details": m,
                            "v2_target_element": v2_el if v2_el else "DEPRECATED_OR_NO_TARGET"
                        })
                    return enriched

                source_context = v1_lookup.get(source_key, {})

                stalemates.append({
                    "source_element": source_context,
                    "agent_1_proposal": enrich_proposal(assignments["agent_1"]),
                    "agent_2_proposal": enrich_proposal(assignments["agent_2"]),
                    "agent_3_proposal": enrich_proposal(assignments["agent_3"])
                })

        if stalemates:
            if self.verbose:
                print(f"  -> Found {len(stalemates)} deadlock stalemates. Resolving via referee pass...")

            response = self._resolver_1.invoke([
                SystemMessage(content=get_consensus_arbitration_prompt()),
                HumanMessage(content=f"\n```json\n{json.dumps(stalemates, indent=2)}\n```\n")
            ])

            if response and hasattr(response, 'resolved_items'):
                for item in response.resolved_items:
                    v1_data = item.v1_element.model_dump()

                    if item.selected_targets:
                        for target in item.selected_targets:
                            consensus_mappings.append(
                                self._create_mapping_row(v1_data, target.model_dump(), item.decision, item.reason).model_dump()
                            )
                    else:
                        consensus_mappings.append(
                            self._create_mapping_row(v1_data, {}, item.decision, item.reason).model_dump()
                        )

        return {"mappings": initial_mappings + consensus_mappings}

    def _compute_similarity_matrix(self, v1_elements: List[dict], v2_elements: List[dict]) -> np.ndarray:
        if self.verbose:
            print("  -> Generating Semantic Embeddings...")

        def generate_embedding_text(el: dict) -> str:
            return f"Namespace: {el.get('namespace','')} | Class: {el.get('class_or_interface','')} | Member: {el.get('member','')} | Signature: {el.get('signature','')} | Summary: {el.get('summary','')}"

        v1_texts = [generate_embedding_text(el) for el in v1_elements]
        v2_texts = [generate_embedding_text(el) for el in v2_elements]

        v1_embs = self._embedder.embed_documents(v1_texts)
        v2_embs = self._embedder.embed_documents(v2_texts)

        if self.verbose:
            print("  -> Running Vector Math for Direct Matches...")

        v1_arr, v2_arr = np.array(v1_embs), np.array(v2_embs)

        v1_norm = np.linalg.norm(v1_arr, axis=1, keepdims=True)
        v2_norm = np.linalg.norm(v2_arr, axis=1, keepdims=True)
        v1_norm[v1_norm == 0], v2_norm[v2_norm == 0] = 1, 1

        v1_normalized, v2_normalized = v1_arr / v1_norm, v2_arr / v2_norm

        sim_matrix = np.dot(v1_normalized, v2_normalized.T)

        if self.verbose:
            display_rich_matrix(sim_matrix, v1_elements, v2_elements)

        return sim_matrix

    def _initial_semantic_match(self, v1_elements: List[dict], v2_elements: List[dict], sim_matrix: np.ndarray):
        final_rows: List[MappingRow] = []
        resolution_queue = []

        for v1_idx, scores in enumerate(sim_matrix):
            v1_data = v1_elements[v1_idx]

            valid_indices = np.where(scores >= self.confidence_floor)[0]
            if len(valid_indices) == 0:
                resolution_queue.append({"v1_element": v1_data, "potential_targets": []})

                continue

            sorted_indices = valid_indices[np.argsort(-scores[valid_indices])]
            candidates = [{"score": float(scores[idx]), "element": v2_elements[idx]} for idx in sorted_indices]

            top_score = candidates[0]['score']
            is_very_high_conf = top_score >= self.confidence_threshold
            has_clear_gap = len(candidates) == 1 or (top_score - candidates[1]['score'] > self.ambiguous_margin)

            if is_very_high_conf and has_clear_gap:
                final_rows.append(self._create_mapping_row(v1_data, candidates[0]['element'], Complexity.ONE_TO_ONE))
            else:
                resolution_queue.append({"v1_element": v1_data, "potential_targets": [item["element"] for item in candidates]})

        if self.verbose:
            print(f"    - Found {len(final_rows)} direct matches and {len(resolution_queue)} complex cases.")

        return final_rows, resolution_queue

    def _generate_mapping_single(self, state: MapperAgentState):
        resolution_queue = state.get("resolution_queue", [])
        initial_mappings = state.get("initial_mappings", [])
        
        if not resolution_queue:
            return {"mappings": initial_mappings}

        if self.verbose:
            print(f"\n[Single Agent] Resolving {len(resolution_queue)} complex items...")
        
        resolved_rows = self._resolve_complex_mappings(resolution_queue, self._resolver_1, get_general_mapper_resolution_prompt())
        all_mappings = initial_mappings + [row.model_dump() for row in resolved_rows]
        
        return {"mappings": all_mappings}

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

    def run(self, path_a: str, path_b: str, thread_id: str = "1") -> List[dict]:
        initial_state = {
            "dir_v1": path_a,
            "dir_v2": path_b,
        }

        config = {"configurable": {"thread_id": thread_id}}

        if self.verbose:
            print(f"Invoking Mapper Agent with paths: {path_a} and {path_b}")

        try:
            final_state = self.graph.invoke(initial_state, config=config)

            mappings = final_state.get('mappings', [])

            if self.verbose:
                display_mapping_table(mappings)

            return mappings
        except Exception as e:
            error_msg = f"An error occurred while running the Mapper Agent: {e}"

            if self.verbose:
                print(error_msg)

            return []