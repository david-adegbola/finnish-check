"""A small Claude API client using only the standard library (urllib), for JSON answers.

Settings come from environment variables (or a .env file, loaded by app.py):
    ANTHROPIC_API_KEY   if set, the app calls the API ("live" mode); if not, it runs in MOCK MODE
    LLM_MODEL           default claude-opus-5-5
    LLM_EFFORT          low | medium | high | xhigh | max (default low: this is simple classification)
    LLM_MODE            set to "mock" to force mock mode even when a key is set

How one call works (call_json):
  1. Build a Messages API request with the model, the system prompt, one user message and
     output_config.format = a JSON schema. The API then guarantees the reply is valid JSON in that
     shape ("structured outputs"). There is no temperature setting: API version 2026-10-21 rejects it.
  2. POST it to https://api.anthropic.com/v1/messages with the x-api-key and anthropic-version headers.
  3. Retry on 429 (rate limit), 5xx and network errors, up to max_retries times.
  4. A "refusal" or a cut-off answer ("max_tokens") is an error, not an answer.
  5. Return the parsed JSON plus the model that answered.

Error messages never include the prompt, the ad text or the key.
"""

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
DEFAULT_MODEL = "claude-opus-5-5"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504, 529}
MOCK_LABEL = "[MOCK – not an AI result]"


class LLMError(Exception):
    """The API call failed or returned something unusable."""


@dataclass
class Settings:
    model: str = DEFAULT_MODEL
    api_key: str = field(default="", repr=False)      # repr=False: never printed
    effort: str = "low"
    force_mock: bool = False
    timeout: float = 60.0
    max_retries: int = 2

    @property
    def live(self):
        return bool(self.api_key) and not self.force_mock


def settings_from_env(environ=None):
    env = os.environ if environ is None else environ
    effort = (env.get("LLM_EFFORT") or "low").strip().lower()
    return Settings(
        model=(env.get("LLM_MODEL") or DEFAULT_MODEL).strip(),
        api_key=(env.get("ANTHROPIC_API_KEY") or "").strip(),
        effort=effort if effort in EFFORTS else "low",
        force_mock=(env.get("LLM_MODE") or "").strip().lower() == "mock",
    )


def build_request(settings, system, user, schema, max_tokens):
    """(headers, body) for one Messages API call. Separate so tests can check it without a network."""
    headers = {"content-type": "application/json", "x-api-key": settings.api_key,
               "anthropic-version": API_VERSION}
    body = {
        "model": settings.model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": settings.effort, "format": {"type": "json_schema", "schema": schema}},
    }
    return headers, body


def _post(url, headers, data, timeout):
    """Default transport: (status, response headers, body bytes)."""
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()


def _error_type(raw):
    try:
        return json.loads(raw)["error"]["type"]
    except (ValueError, KeyError, TypeError):
        return "unknown_error"


def call_json(system, user, schema, settings, max_tokens=2048, post=None, sleep=time.sleep):
    """Ask the model; return {"data": parsed JSON, "model": str}. post() is replaced in tests."""
    if not settings.live:
        raise LLMError("No API key is set, so the app is in mock mode.")
    post = post or _post
    headers, body = build_request(settings, system, user, schema, max_tokens)
    data = json.dumps(body).encode("utf-8")
    for attempt in range(settings.max_retries + 1):
        try:
            status, response_headers, raw = post(API_URL, headers, data, settings.timeout)
        except (urllib.error.URLError, OSError):
            status, response_headers, raw = None, {}, b""
        if status == 200:
            break
        retryable = status is None or status in RETRY_STATUSES     # None = network error
        if not retryable or attempt == settings.max_retries:
            reason = "network error" if status is None else f"HTTP {status} {_error_type(raw)}"
            raise LLMError(f"Claude API call failed: {reason}.")
        retry_after = {k.lower(): v for k, v in response_headers.items()}.get("retry-after")
        sleep(min(float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt, 60))

    message = json.loads(raw)
    if message.get("stop_reason") in ("refusal", "max_tokens"):
        raise LLMError(f"The model's answer is unusable ({message['stop_reason']}).")
    text = next((block["text"] for block in message.get("content", []) if block.get("type") == "text"), None)
    try:
        return {"data": json.loads(text), "model": message.get("model", settings.model)}
    except (TypeError, ValueError) as error:
        raise LLMError("The model's answer wasn't valid JSON.") from error
