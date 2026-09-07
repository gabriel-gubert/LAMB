from typing import TypeVar, Type

from .config_manager import ConfigManager
from .mapper_agent import MapperAgent
from .migrator_agent import MigratorAgent
from .rate_limited_chat import RateLimitedChatOpenAI, RateLimitedOpenAIEmbeddings

T = TypeVar('T') 

def create_openai_component(
    component_class: Type[T],
    config_manager: 'ConfigManager',
    task_key: str,
    override_kwargs: dict = None
) -> T:
    """
    Unified factory function to create any OpenAI-based LangChain component
    (e.g., RateLimitedChatOpenAI, RateLimitedOpenAIEmbeddings) using a cascaded fallback strategy.
    Hierarchy: tasks.{task_key} -> tasks.default -> general.
    """

    settings = {}

    general_cfg = config_manager.get("general")

    if isinstance(general_cfg, dict):
        for k, v in general_cfg.items():
            if k != "verbose" and v is not None:
                settings[k] = v

    default_cfg = config_manager.get("tasks.default")

    if isinstance(default_cfg, dict):
        for k, v in default_cfg.items():
            if v is not None:
                settings[k] = v

    task_cfg = config_manager.get(f"tasks.{task_key}")

    if isinstance(task_cfg, dict):
        for k, v in task_cfg.items():
            if v is not None:
                settings[k] = v

    if override_kwargs:
        settings.update(override_kwargs)

    use_litellm = settings.pop("use_litellm", True)

    if use_litellm:
        litellm_host = config_manager.get("general.litellm.host", "127.0.0.1")
        litellm_port = config_manager.get("general.litellm.port", 4000)

        settings["base_url"] = f"http://{litellm_host}:{litellm_port}/v1"

        if not settings.get("api_key"):
            settings["api_key"] = "sk-litellm-local-proxy"
    else:
        if settings.get("base_url") and not settings.get("api_key"):
            settings["api_key"] = "vllm-local-endpoint"

    valid_keys = set()

    try:
        for name, field in component_class.model_fields.items():
            valid_keys.add(name)

            if field.alias:
                valid_keys.add(field.alias)

            val_alias = getattr(field, 'validation_alias', None)

            if isinstance(val_alias, str):
                valid_keys.add(val_alias)
            elif hasattr(val_alias, 'choices'):
                for choice in val_alias.choices:
                    if isinstance(choice, str):
                        valid_keys.add(choice)
                    elif isinstance(choice, list) and choice and isinstance(choice[0], str):
                        valid_keys.add(choice[0])
    except AttributeError:
        for name, field in component_class.__fields__.items():
            valid_keys.add(name)

            if field.alias:
                valid_keys.add(field.alias)

    kwargs = {
        k: v for k, v in settings.items()
        if v is not None and k in valid_keys
    }

    if "model_kwargs" in settings and "model_kwargs" in valid_keys:
        kwargs["model_kwargs"] = settings["model_kwargs"]

    return component_class(**kwargs)

def migrator_agent(config_manager: ConfigManager) -> MigratorAgent:
    """
    Factory function to create a LambAgent instance from a ConfigManager.
    Supports local vLLM deployments and extensive ChatOpenAI settings.
    Enforces logprobs=True for the migrator component.
    """

    migrator = create_openai_component(
        RateLimitedChatOpenAI,
        config_manager,
        "migration.migration",
        override_kwargs={
            "logprobs": True
        }
    )

    return MigratorAgent(
        migrator=migrator,
        summarizer=create_openai_component(RateLimitedChatOpenAI, config_manager, "migration.summarization"),
        detector=create_openai_component(RateLimitedChatOpenAI, config_manager, "migration.detection"),
        analyzer=create_openai_component(RateLimitedChatOpenAI, config_manager, "migration.analysis"),
        inferer=create_openai_component(RateLimitedChatOpenAI, config_manager, "migration.inference"),
        planner=create_openai_component(RateLimitedChatOpenAI, config_manager, "migration.planning"),
        summarization_threshold=config_manager.get("tasks.migration.summarization_threshold", 2048),
        max_attempts=config_manager.get("tasks.migration.max_attempts", 3),
        verbose=config_manager.get("general.verbose", False)
    )

def mapper_agent(config_manager: ConfigManager) -> MapperAgent:
    """
    Factory function to create a MapperAgent instance from a ConfigManager.
    Supports local vLLM deployments and extensive ChatOpenAI settings.
    """

    multi_agent = config_manager.get("tasks.mapping.multi_agent", False)

    resolver_agent_1 = create_openai_component(RateLimitedChatOpenAI, config_manager, "mapping.general_resolution")
    resolver_agent_2 = None
    resolver_agent_3 = None

    if multi_agent:
        resolver_agent_2 = create_openai_component(RateLimitedChatOpenAI, config_manager, "mapping.lexical_resolution")
        resolver_agent_3 = create_openai_component(RateLimitedChatOpenAI, config_manager, "mapping.semantic_resolution")

    return MapperAgent(
        discoverer=create_openai_component(RateLimitedChatOpenAI, config_manager, "mapping.discovery"),
        extractor=create_openai_component(RateLimitedChatOpenAI, config_manager, "mapping.extraction"),
        embedder=create_openai_component(RateLimitedOpenAIEmbeddings, config_manager, "mapping.embedding"),
        resolver_agent_1=resolver_agent_1,
        resolver_agent_2=resolver_agent_2,
        resolver_agent_3=resolver_agent_3,
        multi_agent=multi_agent,
        discovery_batch_size=config_manager.get("tasks.mapping.discovery_batch_size", 20),
        resolver_batch_size=config_manager.get("tasks.mapping.resolver_batch_size", 20),
        stage_output_dir=config_manager.get("tasks.mapping.stage_output_dir", None),
        database_path=config_manager.get("tasks.mapping.checkpoint_database_path", "~/.lamb/map_checkpoint.db"),
        tmp_dir=config_manager.get("tasks.mapping.tmp_dir", "~/.lamb/tmp"),
        verbose=config_manager.get("general.verbose", False)
    )