from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMToolCall(BaseModel):
    """Normalized tool call returned by an LLM provider."""
    call_id: Optional[str] = None
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class LLMStepResult(BaseModel):
    """Result of one orchestration reasoning step from an LLM."""
    tool_calls: List[LLMToolCall] = Field(default_factory=list)
    text_content: Optional[str] = None
    finish_reason: Optional[str] = None
    model_name: str
    provider_name: str


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers (Gemini, Claude, GPT, etc.).
    Decouples LLM-specific SDKs and APIs from the AP Orchestrator.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        timeout: float = 30.0,
        max_tokens: int = 2048,
    ):
        self._api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.max_tokens = max_tokens

    @abstractmethod
    def generate_step(
        self,
        system_instruction: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Callable]] = None,
    ) -> LLMStepResult:
        """Executes a single reasoning step against the LLM, returning selected tool calls or text response."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the provider name identifier (e.g. 'gemini')."""
        pass
