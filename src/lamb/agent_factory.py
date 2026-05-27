from typing import TypeVar, Type, Any, Dict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .migrator_agent import MigratorAgent
from .mapper_agent import MapperAgent
from .config_manager import ConfigManager
from .langchain_blueprints import CHATOPENAI_DEFAULT_BLUEPRINT, OPENAIEMBEDDINGS_DEFAULT_BLUEPRINT

T = TypeVar('T') 

def create_openai_component(
    component_class: Type[T],
    config_manager: 'ConfigManager',
    task_key: str,
    defaults_blueprint: Dict[str, Any]
) -> T:
    """
    Unified factory function to create any OpenAI-based LangChain component
    (e.g., ChatOpenAI, OpenAIEmbeddings) using a cascaded fallback strategy.
    Hierarchy: tasks.{task_key} -> tasks.default -> general -> Hardcoded Default.
    """

    def get_setting(param: str, hardcoded_fallback: Any = None):
        """Retrieves a setting by checking configurations in priority order."""

        paths_to_check = [
            f"tasks.{task_key}.{param}",
            f"tasks.default.{param}",
            f"general.{param}"
        ]

        for path in paths_to_check:
            value = config_manager.get(path)

            if value is not None:
                return value

        return hardcoded_fallback

    # 1. Retrieve all settings based on the provided blueprint
    settings = {
        param: get_setting(param, fallback)
        for param, fallback in defaults_blueprint.items()
    }

    # 2. Handle specific deployment edge cases (like local vLLM)
    if settings.get("base_url") and not settings.get("api_key"):
        settings["api_key"] = "vllm-local-endpoint"

    # 3. Validate requirements
    if not settings.get("api_key"):
        model_name = settings.get("model", "unknown-model")

        raise ValueError(
            f"Missing API Key: Model '{model_name}' for task '{task_key}' requires an 'api_key'. "
            "Please check your 'tasks' or 'general' configuration sections."
        )

    # 4. Construct kwargs, strictly filtering out None values
    kwargs = {k: v for k, v in settings.items() if v is not None}

    # 5. Instantiate and return the provided class
    return component_class(**kwargs)

def migrator_agent(config_manager: ConfigManager) -> MigratorAgent:
    """
    Factory function to create a LambAgent instance from a ConfigManager.
    Supports local vLLM deployments and extensive ChatOpenAI settings.
    """

    return MigratorAgent(
        migrator=create_openai_component(ChatOpenAI, config_manager, "migration", CHATOPENAI_DEFAULT_BLUEPRINT),
        summarizer=create_openai_component(ChatOpenAI, config_manager, "summarization", CHATOPENAI_DEFAULT_BLUEPRINT),
        detector=create_openai_component(ChatOpenAI, config_manager, "detection", CHATOPENAI_DEFAULT_BLUEPRINT),
        summarization_threshold=config_manager.get("tasks.migration.summarization_threshold", 2048),
        verbose=config_manager.get("general.verbose", False)
    )

def mapper_agent(config_manager: ConfigManager) -> MapperAgent:
    """
    Factory function to create a MapperAgent instance from a ConfigManager.
    Supports local vLLM deployments and extensive ChatOpenAI settings.
    """

    multi_agent = config_manager.get("tasks.mapping.multi_agent", False)

    resolver_agent_1 = create_openai_component(ChatOpenAI, config_manager, "general_resolution", CHATOPENAI_DEFAULT_BLUEPRINT)
    resolver_agent_2 = None
    resolver_agent_3 = None

    if multi_agent:
        resolver_agent_2 = create_openai_component(ChatOpenAI, config_manager, "lexical_resolution", CHATOPENAI_DEFAULT_BLUEPRINT)
        resolver_agent_3 = create_openai_component(ChatOpenAI, config_manager, "semantic_resolution", CHATOPENAI_DEFAULT_BLUEPRINT)

    return MapperAgent(
        extractor=create_openai_component(ChatOpenAI, config_manager, "extraction", CHATOPENAI_DEFAULT_BLUEPRINT),
        embedder=create_openai_component(OpenAIEmbeddings, config_manager, "embedding", OPENAIEMBEDDINGS_DEFAULT_BLUEPRINT),
        resolver_agent_1=resolver_agent_1,
        resolver_agent_2=resolver_agent_2,
        resolver_agent_3=resolver_agent_3,
        multi_agent=multi_agent,
        confidence_floor=config_manager.get("tasks.mapping.confidence_floor", 0.65),
        confidence_threshold=config_manager.get("tasks.mapping.confidence_threshold", 0.92),
        ambiguous_margin=config_manager.get("tasks.mapping.ambiguous_margin", 0.05),
        resolver_batch_size=config_manager.get("tasks.mapping.resolver_batch_size", 20),
        verbose=config_manager.get("general.verbose", False)
    )