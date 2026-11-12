"""
Thin wrapper around the LLM provider so the rest of the app never talks
to an SDK directly. Default provider is Groq (free tier); Mistral is still
available by setting LLM_PROVIDER=mistral in .env.

Includes simple client-side throttling and retry-with-backoff on 429
(rate limit) responses.

.env settings:
    LLM_PROVIDER=groq            # or: mistral
    GROQ_API_KEY=...             # from console.groq.com
    GROQ_MODEL=llama-3.3-70b-versatile
    MISTRAL_API_KEY=...          # only if LLM_PROVIDER=mistral
    MISTRAL_MODEL=mistral-small-latest
    LLM_MIN_INTERVAL=2.0         # seconds between requests
    LLM_MAX_RETRIES=5
"""

import os
import random
import threading
import time

from dotenv import load_dotenv

load_dotenv()  # make sure .env is loaded even if this module is imported first

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

# Groq model options: "llama-3.3-70b-versatile" (smarter) or
# "llama-3.1-8b-instant" (faster, higher limits). Check console.groq.com for
# the current list.
DEFAULT_MODELS = {
    "groq": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    "mistral": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
}
DEFAULT_MODEL = DEFAULT_MODELS.get(PROVIDER, DEFAULT_MODELS["groq"])

MIN_INTERVAL = float(os.getenv("LLM_MIN_INTERVAL", "2.0"))
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "5"))

_client = None
_throttle_lock = threading.Lock()
_last_call = 0.0


def get_client():
    global _client
    if _client is not None:
        return _client

    if PROVIDER == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file "
                "(create one at console.groq.com)."
            )
        from groq import Groq

        _client = Groq(api_key=api_key)
    elif PROVIDER == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set. Add it to your .env file.")
        from mistralai import Mistral

        _client = Mistral(api_key=api_key)
    else:
        raise RuntimeError(f"Unknown LLM_PROVIDER '{PROVIDER}'. Use 'groq' or 'mistral'.")
    return _client


def _wait_for_slot() -> None:
    """Block until at least MIN_INTERVAL has passed since the last request."""
    global _last_call
    with _throttle_lock:
        wait = MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _is_rate_limit(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) == 429:
        return True
    text = str(exc).lower()
    return "429" in text and "rate" in text


def _retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None) or getattr(exc, "raw_response", None)
    headers = getattr(response, "headers", None)
    if headers:
        value = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _complete(client, model: str, temperature: float, messages: list) -> str:
    if PROVIDER == "mistral":
        response = client.chat.complete(model=model, temperature=temperature, messages=messages)
    else:
        response = client.chat.completions.create(model=model, temperature=temperature, messages=messages)
    return response.choices[0].message.content


def chat(system_prompt: str, user_prompt: str, model: str | None = None, temperature: float = 0.3) -> str:
    """Single-turn call: one system prompt + one user prompt -> text response."""
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(MAX_RETRIES + 1):
        _wait_for_slot()
        try:
            return _complete(client, model or DEFAULT_MODEL, temperature, messages)
        except Exception as exc:
            if not _is_rate_limit(exc) or attempt == MAX_RETRIES:
                raise
            # Exponential backoff with jitter, honoring Retry-After if sent.
            delay = _retry_after(exc) or min(2 ** attempt * 2, 30)
            time.sleep(delay + random.uniform(0, 1))