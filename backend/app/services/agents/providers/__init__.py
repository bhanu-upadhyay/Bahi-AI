import logging
from typing import Optional

from app.core.config import settings as default_settings
from app.services.agents.providers.base import BaseLLMProvider, LLMStepResult, LLMToolCall
from app.services.agents.providers.gemini_provider import GeminiProvider

logger = logging.getLogger("bahi_ai.agents.providers")


def get_llm_provider(settings=None) -> Optional[BaseLLMProvider]:
    """Factory creating the configured LLM provider instance.
    Returns None if API key is unconfigured or provider is disabled,
    triggering graceful deterministic rule-based fallback.
    """
    cfg = settings or default_settings
    provider_name = (cfg.LLM_PROVIDER or "gemini").lower()
    api_key = cfg.LLM_API_KEY or ""

    if not api_key:
        logger.info("[LLMProviderFactory] LLM_API_KEY not configured. Falling back to deterministic rule-based mode.")
        return None

    if provider_name == "gemini":
        try:
            return GeminiProvider(
                api_key=api_key,
                model_name=cfg.LLM_MODEL or "gemini-3.5-flash-lite",
                timeout=float(cfg.LLM_TIMEOUT or 30.0),
                max_tokens=int(cfg.LLM_MAX_TOKENS or 2048),
            )
        except Exception as e:
            logger.warning(f"[LLMProviderFactory] Could not initialize Gemini provider: {e}. Will use rule-based fallback.")
            return None

    logger.warning(f"[LLMProviderFactory] Unsupported LLM provider '{provider_name}'. Falling back to rule-based.")
    return None


__all__ = [
    "BaseLLMProvider",
    "LLMStepResult",
    "LLMToolCall",
    "GeminiProvider",
    "get_llm_provider",
]
