"""The only place that talks to Gemini.

generate_json returns a parsed Pydantic object, or None when there is no key,
the call fails, the response is blocked or empty. Callers then use their
non-AI fallback, so the demo never breaks.
"""
import logging

from pydantic import BaseModel

from .. import settings

log = logging.getLogger("with_us.ai")
TOKENS = {"input": 0, "output": 0, "calls": 0}
_client = None


def available() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate_json(system: str, contents: list, schema: type[BaseModel], temperature: float = 0.2):
    if not available():
        return None
    try:
        from google.genai import types

        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=temperature,
            ),
        )
        usage = getattr(response, "usage_metadata", None)
        if usage:
            TOKENS["input"] += usage.prompt_token_count or 0
            TOKENS["output"] += usage.candidates_token_count or 0
        TOKENS["calls"] += 1
        parsed = response.parsed
        if parsed is None and response.text:
            parsed = schema.model_validate_json(response.text)
        return parsed
    except Exception as exc:  # network, quota, safety block, bad JSON
        log.warning("Gemini call failed, using fallback: %s %s", type(exc).__name__,
                    getattr(exc, "code", "") or "")
        return None


def image_part(data: bytes, mime_type: str):
    from google.genai import types

    return types.Part.from_bytes(data=data, mime_type=mime_type)
