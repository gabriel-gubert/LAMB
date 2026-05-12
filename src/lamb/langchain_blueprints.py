PARAM_TYPES = {
    # Core Identity & Authentication
    "model": str, 
    "api_key": str, 
    "base_url": str, 
    "organization": str,
    
    # Generation & Embedding Parameters
    "temperature": float, 
    "max_tokens": int, 
    "top_p": float,
    "frequency_penalty": float, 
    "presence_penalty": float, 
    "n": int,
    "stop": list,               # Supports List[str]
    "seed": int,
    "logprobs": bool,           # Boolean flag
    "top_logprobs": int,        # Number of logprobs
    "logit_bias": dict,         # Dictionary {token_id: bias}
    "dimensions": int,
    "chunk_size": int, 
    "skip_empty": bool,
    "show_progress_bar": bool,  # Boolean flag for embeddings
    
    # Execution & Connection Parameters
    "timeout": int, 
    "max_retries": int, 
    "streaming": bool,
    
    # Advanced & Low-Level Kwargs
    "model_kwargs": dict,       # Extra parameters dictionary
    "default_headers": dict,    # Header dictionary
    "default_query": dict,      # Query parameter dictionary
    "tiktoken_enabled": bool, 
    "tiktoken_model_name": str  # String override
}

CHATOPENAI_DEFAULT_BLUEPRINT = {
    # Core Identity & Authentication
    "model": "gpt-4o",
    "api_key": None,
    "base_url": None,
    "organization": None,
    
    # Generation Parameters
    "temperature": 0.7,
    "max_tokens": None,          # None allows the model to use its maximum context window
    "top_p": None,
    "frequency_penalty": None,
    "presence_penalty": None,
    "n": 1,                      # Number of chat completions to generate
    "stop": None,                # List of strings to stop generation
    "seed": None,                # Integer for deterministic sampling
    "logprobs": None,            # Boolean to return log probabilities
    "top_logprobs": None,        # Integer specifying how many logprobs to return
    "logit_bias": None,          # Dictionary to modify the likelihood of specified tokens
    
    # Execution & Connection Parameters
    "streaming": False,
    "max_retries": 2,
    "timeout": None,
    
    # Advanced & Low-Level Kwargs
    "model_kwargs": None,        # Dictionary for any extra kwargs not covered above
    "default_headers": None,     # Custom HTTP headers
    "default_query": None,       # Custom URL query parameters
    "tiktoken_model_name": None  # Override for token counting
}

OPENAIEMBEDDINGS_DEFAULT_BLUEPRINT = {
    # Core Identity & Authentication
    "model": "text-embedding-3-small",
    "api_key": None,
    "base_url": None,
    "organization": None,
    
    # Embedding Specific Parameters
    "dimensions": None,          # Explicitly set output dimensions (supported by v3 models)
    "chunk_size": 1000,          # Number of texts to embed in a single batch
    "skip_empty": False,         # Boolean to drop empty strings from the input
    
    # Execution & Connection Parameters
    "max_retries": 2,
    "timeout": None,
    "show_progress_bar": False,  # Useful for tracking large bulk embeddings
    
    # Advanced & Low-Level Kwargs
    "model_kwargs": None,        # Dictionary for any extra kwargs
    "default_headers": None,     # Custom HTTP headers
    "default_query": None,       # Custom URL query parameters
    "tiktoken_enabled": True,    # Boolean to enable local token counting
    "tiktoken_model_name": None  # Override for token counting
}