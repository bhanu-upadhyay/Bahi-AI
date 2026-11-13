import logging
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from app.services.agents.providers.base import BaseLLMProvider, LLMStepResult, LLMToolCall

logger = logging.getLogger("bahi_ai.agents.providers.gemini")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementing function calling and structured orchestration
    using the official Google GenAI Python SDK (`google-genai`).
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.5-flash-lite",
        timeout: float = 30.0,
        max_tokens: int = 2048,
    ):
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            timeout=timeout,
            max_tokens=max_tokens,
        )
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key is missing or empty. Configure LLM_API_KEY.")

        # Instantiate official Google GenAI Client with explicit key
        try:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=int(self.timeout * 1000)),
            )
        except Exception as e:
            # Redact key in case SDK surfaces it in initialization errors
            safe_err = str(e).replace(self._api_key, "[REDACTED_API_KEY]")
            raise RuntimeError(f"Failed to initialize Gemini Client: {safe_err}")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _sanitize_error(self, err: Exception) -> str:
        """Removes any occurrence of the raw API key from error strings."""
        msg = str(err)
        if self._api_key and self._api_key in msg:
            msg = msg.replace(self._api_key, "[REDACTED_API_KEY]")
        return msg

    def generate_step(
        self,
        system_instruction: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Callable]] = None,
    ) -> LLMStepResult:
        """Executes a single reasoning turn against Gemini using structured function calling."""
        try:
            # Build GenerateContentConfig with tools and system instruction
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=self.max_tokens,
                temperature=0.1,
            )
            if tools:
                config.tools = tools

            # Convert message dicts to SDK Contents
            contents: List[types.Content] = []
            for m in messages:
                role = m.get("role", "user")
                if "parts" in m and isinstance(m["parts"], list):
                    parts = []
                    for p in m["parts"]:
                        if isinstance(p, types.Part):
                            parts.append(p)
                        elif isinstance(p, dict):
                            if "text" in p:
                                parts.append(types.Part.from_text(text=p["text"]))
                            elif "function_call" in p:
                                fc = p["function_call"]
                                parts.append(
                                    types.Part(
                                        function_call=types.FunctionCall(
                                            name=fc["name"],
                                            args=fc.get("args", {}),
                                        )
                                    )
                                )
                            elif "function_response" in p:
                                fr = p["function_response"]
                                parts.append(
                                    types.Part.from_function_response(
                                        name=fr["name"],
                                        response=fr["response"],
                                    )
                                )
                        elif isinstance(p, str):
                            parts.append(types.Part.from_text(text=p))
                    contents.append(types.Content(role=role, parts=parts))
                elif "text" in m:
                    contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=m["text"])],
                        )
                    )

            # Dispatch call to Gemini
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            tool_calls: List[LLMToolCall] = []
            if response.function_calls:
                for fc in response.function_calls:
                    tool_calls.append(
                        LLMToolCall(
                            tool_name=fc.name,
                            arguments=dict(fc.args or {}),
                        )
                    )

            text_content = response.text if hasattr(response, "text") and response.text else None

            return LLMStepResult(
                tool_calls=tool_calls,
                text_content=text_content,
                finish_reason="TOOL_CALL" if tool_calls else "STOP",
                model_name=self.model_name,
                provider_name=self.provider_name,
            )

        except Exception as e:
            safe_msg = self._sanitize_error(e)
            logger.error(f"[GeminiProvider] Error during generate_step: {safe_msg}")
            raise RuntimeError(f"Gemini generation error: {safe_msg}")

