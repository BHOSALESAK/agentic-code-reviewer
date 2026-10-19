import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(RuntimeError):
    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient


@dataclass
class UsageRecord:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class StructuredResult(Generic[T]):
    value: T
    usage: UsageRecord


class StructuredLLMProvider(ABC):
    def __init__(self, *, max_retries: int = 2, backoff_seconds: float = 0.05):
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.usage = UsageRecord()

    def complete_structured(self, prompt: str, response_model: type[T]) -> StructuredResult[T]:
        last_error: LLMProviderError | None = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            self.usage.requests += 1
            try:
                raw = self._complete_once(prompt, response_model)
                value = self._validate(raw, response_model)
                self.usage.input_tokens += len(prompt.split())
                self.usage.output_tokens += len(value.model_dump_json().split())
                self.usage.latency_ms.append((time.perf_counter() - started) * 1000)
                return StructuredResult(value, self.usage)
            except LLMProviderError as exc:
                last_error = exc
            except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
                last_error = LLMProviderError(f"structured response validation failed: {type(exc).__name__}")
            if last_error is None or not last_error.transient or attempt == self.max_retries:
                break
            time.sleep(self.backoff_seconds * (2**attempt))
        raise last_error or LLMProviderError("LLM request failed")

    @staticmethod
    def _validate(raw: Any, response_model: type[T]) -> T:
        if isinstance(raw, str):
            raw = json.loads(raw)
        return response_model.model_validate(raw)

    @abstractmethod
    def _complete_once(self, prompt: str, response_model: type[T]) -> Any:
        raise NotImplementedError
