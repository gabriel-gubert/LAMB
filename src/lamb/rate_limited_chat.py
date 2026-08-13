import time
import threading
from typing import Any, List, Tuple, Dict
import tiktoken
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

class RateLimitedChatOpenAI(ChatOpenAI):
    """
    A self-contained, rate-limited wrapper around LangChain's ChatOpenAI.
    Enforces Requests Per Minute (RPM) and Tokens Per Minute (TPM) 
    locally within the instance itself. Fully thread-safe.
    """

    requests_per_minute: float = 0.0
    tokens_per_minute: int = 0

    _token_history: List[Tuple[float, int]] = []
    _lock: threading.Lock = None

    def __init__(self, requests_per_minute: float = 0.0, tokens_per_minute: int = 0, **kwargs):
        super().__init__(**kwargs)

        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self._token_history = []
        self._lock = threading.Lock()

    def _clean_and_get_usage(self, current_time: float) -> int:
        """Clears records older than 60s and returns the active token sum."""

        self._token_history = [
            (t, count) for t, count in self._token_history 
            if current_time - t < 60
        ]

        return sum(count for _, count in self._token_history)

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        """
        Intercepts the standard invoke call to enforce TPM and RPM limits.
        """

        if self.tokens_per_minute > 0:
            if isinstance(input, list):
                text_to_encode = " ".join([msg.content for msg in input if hasattr(msg, "content")])
            elif hasattr(input, "content"):
                text_to_encode = input.content
            else:
                text_to_encode = str(input)

            try:
                encoding = tiktoken.encoding_for_model(self.model_name)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")

            input_tokens = len(encoding.encode(text_to_encode))

            while True:
                now = time.time()

                with self._lock:
                    current_tpm_usage = self._clean_and_get_usage(now)

                    if current_tpm_usage + input_tokens <= self.tokens_per_minute:
                        self._token_history.append((now, input_tokens))

                        break

                time.sleep(0.25)

        start_time = time.time()

        result = super().invoke(input, config=config, **kwargs)

        current_time = time.time()
        elapsed_time = current_time - start_time

        token_usage = result.response_metadata.get("token_usage", {})
        actual_total = token_usage.get("total_tokens", 0)
        actual_input = token_usage.get("prompt_tokens", 0)
        actual_output = token_usage.get("completion_tokens", actual_total - actual_input)

        if self.tokens_per_minute > 0 and actual_output > 0:
            with self._lock:
                self._token_history.append((current_time, actual_output))
                tokens_used_in_window = self._clean_and_get_usage(current_time)

            if tokens_used_in_window > self.tokens_per_minute:
                overshoot_ratio = tokens_used_in_window / self.tokens_per_minute
                tpm_wait_time = 60.0 * (overshoot_ratio - 1.0)
            else:
                tpm_wait_time = (actual_total / self.tokens_per_minute) * 60.0
        else:
            tpm_wait_time = 0.0

        rpm_wait_time = 60.0 / self.requests_per_minute if self.requests_per_minute > 0.0 else 0.0
        target_wait_time = max(rpm_wait_time, tpm_wait_time)

        if target_wait_time > 0.0:
            remaining_delay = target_wait_time - elapsed_time

            if remaining_delay > 0.0:
                time.sleep(remaining_delay)

        return result

class RateLimitedOpenAIEmbeddings(OpenAIEmbeddings):
    """
    A self-contained, rate-limited wrapper around LangChain's OpenAIEmbeddings.
    Enforces Requests Per Minute (RPM) and Tokens Per Minute (TPM) 
    locally within the instance itself. Fully thread-safe.
    """

    requests_per_minute: float = 0.0
    tokens_per_minute: int = 0

    _token_history: List[Tuple[float, int]] = []
    _lock: threading.Lock = None

    def __init__(self, requests_per_minute: float = 0.0, tokens_per_minute: int = 0, **kwargs):
        super().__init__(**kwargs)

        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self._token_history = []
        self._lock = threading.Lock()

    def _clean_and_get_usage(self, current_time: float) -> int:
        """Clears records older than 60s and returns the active token sum."""
        self._token_history = [
            (t, count) for t, count in self._token_history 
            if current_time - t < 60
        ]
        return sum(count for _, count in self._token_history)

    def _get_encoding(self) -> tiktoken.Encoding:
        """Helper to safely fetch the tiktoken encoding."""
        model_name = getattr(self, "model", "text-embedding-3-small")
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    def _wait_for_tpm_capacity(self, estimated_tokens: int) -> None:
        """Blocks execution until the required token capacity is available in the 60s window."""
        if self.tokens_per_minute <= 0:
            return

        while True:
            now = time.time()
            with self._lock:
                current_tpm_usage = self._clean_and_get_usage(now)
                if current_tpm_usage + estimated_tokens <= self.tokens_per_minute:
                    self._token_history.append((now, estimated_tokens))
                    break
            time.sleep(0.25)

    def _apply_rate_limit_delay(self, start_time: float, total_tokens: int) -> None:
        """Enforces remaining RPM and TPM delays after the embedding request completes."""
        elapsed_time = time.time() - start_time

        # Calculate TPM delay
        if self.tokens_per_minute > 0 and total_tokens > 0:
            current_time = time.time()
            with self._lock:
                tokens_used_in_window = self._clean_and_get_usage(current_time)

            if tokens_used_in_window > self.tokens_per_minute:
                overshoot_ratio = tokens_used_in_window / self.tokens_per_minute
                tpm_wait_time = 60.0 * (overshoot_ratio - 1.0)
            else:
                tpm_wait_time = (total_tokens / self.tokens_per_minute) * 60.0
        else:
            tpm_wait_time = 0.0

        # Calculate RPM delay
        rpm_wait_time = 60.0 / self.requests_per_minute if self.requests_per_minute > 0.0 else 0.0
        
        target_wait_time = max(rpm_wait_time, tpm_wait_time)

        if target_wait_time > 0.0:
            remaining_delay = target_wait_time - elapsed_time
            if remaining_delay > 0.0:
                time.sleep(remaining_delay)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Intercepts document batch embedding requests to enforce rate limits.
        """
        encoding = self._get_encoding()
        input_tokens = sum(len(encoding.encode(text)) for text in texts)

        self._wait_for_tpm_capacity(input_tokens)

        start_time = time.time()
        result = super().embed_documents(texts)
        self._apply_rate_limit_delay(start_time, input_tokens)

        return result

    def embed_query(self, text: str) -> List[float]:
        """
        Intercepts single query embedding requests to enforce rate limits.
        """
        encoding = self._get_encoding()
        input_tokens = len(encoding.encode(text))

        self._wait_for_tpm_capacity(input_tokens)

        start_time = time.time()
        result = super().embed_query(text)
        self._apply_rate_limit_delay(start_time, input_tokens)

        return result