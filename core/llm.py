"""A small client for Claude, using only the standard library (urllib), for JSON answers.

It can reach Claude two ways:
    ANTHROPIC_API_KEY    directly, through Anthropic's Messages API
    OPENROUTER_API_KEY   through OpenRouter (openrouter.ai), which forwards the request to Claude
If neither key is set, the app runs in MOCK MODE. Other settings (environment variables or .env):
    LLM_MODEL    default claude-opus-5-5. For OpenRouter the name is converted automatically
                 ("claude-haiku-5-5" -> "anthropic/claude-haiku-5.5"); a name with "/" is used as it is.
    LLM_EFFORT   low | medium | high | xhigh | max (default low; Anthropic API only)
    LLM_MODE     set to "mock" to force mock mode even when a key is set

How one call works (call_json):
  1. Build the request with the model, the system prompt, one user message and a JSON schema. The service
     then guarantees the reply is valid JSON in that shape ("structured outputs"). No temperature is sent:
     the current Claude models reject it.
  2. POST it, with the key in a header.
  3. Retry on 429 (rate limit), 5xx and network errors, up to max_retries times.
  4. A refusal or a cut-off answer is an error, not an answer.
  5. Return the parsed JSON plus the model that answered.

Error messages never include the prompt, the ad text or the key.
"""

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2026-10-21"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "claude-opus-5-5"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504, 529}
MOCK_LABEL = "[MOCK – not an AI result]"


class LLMError(Exception):
    """The API call failed or returned something unusable."""


@dataclass
class Settings:
    provider: str = "anthropic"                      # "anthropic" or "openrouter"
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
    openrouter_key = (env.get("OPENROUTER_API_KEY") or "").strip()
    effort = (env.get("LLM_EFFORT") or "low").strip().lower()
    return Settings(
        provider="openrouter" if openrouter_key else "anthropic",
        model=(env.get("LLM_MODEL") or DEFAULT_MODEL).strip(),
        api_key=openrouter_key or (env.get("ANTHROPIC_API_KEY") or "").strip(),
        effort=effort if effort in EFFORTS else "low",
        force_mock=(env.get("LLM_MODE") or "").strip().lower() == "mock",
    )


def openrouter_model(name):
    """Anthropic's model names in OpenRouter's style: "claude-haiku-5-5" -> "anthropic/claude-haiku-5.5"."""
    if "/" in name:
        return name
    return "anthropic/" + re.sub(r"-(\d+)-(\d+)$", r"-\1.\2", name)


def build_request(settings, system, user, schema, max_tokens):
    """(url, headers, body) for one call. Separate so tests can check it without a network."""
    if settings.provider == "openrouter":
        headers = {"content-type": "application/json", "authorization": f"Bearer {settings.api_key}"}
        body = {
            "model": openrouter_model(settings.model),
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "answer", "strict": True, "schema": schema}},
            # Only providers that support the JSON schema, and that don't store or train on the data
            "provider": {"require_parameters": True, "data_collection": "deny"},
        }
        return OPENROUTER_URL, headers, body
    headers = {"content-type": "application/json", "x-api-key": settings.api_key,
               "anthropic-version": ANTHROPIC_VERSION}
    body = {
        "model": settings.model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": settings.effort, "format": {"type": "json_schema", "schema": schema}},
    }
    return ANTHROPIC_URL, headers, body


def answer_text(settings, message):
    """The JSON text of a successful reply, or LLMError. The two services shape replies differently."""
    if settings.provider == "openrouter":
        choice = (message.get("choices") or [{}])[0]
        if choice.get("finish_reason") in ("length", "content_filter"):
            raise LLMError(f"The model's answer is unusable ({choice['finish_reason']}).")
        return (choice.get("message") or {}).get("content")
    if message.get("stop_reason") in ("refusal", "max_tokens"):
        raise LLMError(f"The model's answer is unusable ({message['stop_reason']}).")
    return next((block["text"] for block in message.get("content", []) if block.get("type") == "text"), None)


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
        error = json.loads(raw)["error"]
        return str(error.get("type") or error.get("code") or "unknown_error")
    except (ValueError, KeyError, TypeError, AttributeError):
        return "unknown_error"


def call_json(system, user, schema, settings, max_tokens=4096, post=None, sleep=time.sleep):
    """Ask the model; return {"data": parsed JSON, "model": str}. post() is replaced in tests."""
    if not settings.live:
        raise LLMError("No API key is set, so the app is in mock mode.")
    post = post or _post
    url, headers, body = build_request(settings, system, user, schema, max_tokens)
    data = json.dumps(body).encode("utf-8")
    for attempt in range(settings.max_retries + 1):
        try:
            status, response_headers, raw = post(url, headers, data, settings.timeout)
        except (urllib.error.URLError, OSError):
            status, response_headers, raw = None, {}, b""
        if status == 200:
            break
        retryable = status is None or status in RETRY_STATUSES     # None = network error
        if not retryable or attempt == settings.max_retries:
            reason = "network error" if status is None else f"HTTP {status} {_error_type(raw)}"
            raise LLMError(f"{settings.provider} API call failed: {reason}.")
        retry_after = {k.lower(): v for k, v in response_headers.items()}.get("retry-after")
        sleep(min(float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt, 60))

    message = json.loads(raw)
    text = answer_text(settings, message)
    try:
        return {"data": json.loads(text), "model": message.get("model", settings.model)}
    except (TypeError, ValueError) as error:
        raise LLMError("The model's answer wasn't valid JSON.") from error
