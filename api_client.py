"""
api_client.py
─────────────
WHY THIS FILE EXISTS:
  Every agent needs to call the Anthropic API.
  Centralising the call here means:
    1. All agents share ONE retry / error-handling logic.
    2. All agents are automatically logged (token counts, latency).
    3. Changing the model happens in ONE place, not in 5 agent files.
    4. Mock mode is toggled here — agents never need to know.

MOCK MODE:
  Set the environment variable BEFORE importing this module:
    MOCK_MODE=1 python orchestrator.py
  OR pass --mock to orchestrator.py (it sets os.environ first).

  The check is done INSIDE call_claude() — not at import time —
  so that orchestrator.py can set os.environ["MOCK_MODE"] before
  the first call is made.
"""

import os
import time
import anthropic
from logger import log_call

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _is_mock() -> bool:
    """
    Check mock mode at CALL TIME, not at import time.
    This allows orchestrator.py to set os.environ["MOCK_MODE"]
    before the first agent call, even after this module is imported.
    """
    return os.environ.get("MOCK_MODE", "").lower() in ("1", "true", "yes")


def call_claude(
    agent_name: str,
    step: str,
    system: str,
    user: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2048,
) -> str:
    """
    Single-turn API call with full logging.
    Transparently dispatches to mock_client when MOCK_MODE is set.
    """
    # ── Mock dispatch — checked at call time, not import time
    if _is_mock():
        from mock_client import call_claude_mock
        return call_claude_mock(agent_name, step, system, user, model, max_tokens)

    # ── Real API call
    client = get_client()
    t0 = time.time()
    success = True
    prompt_tokens = 0
    completion_tokens = 0
    result = ""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        prompt_tokens     = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        result            = response.content[0].text

    except Exception as e:
        success = False
        result  = f"ERROR: {e}"

    latency = time.time() - t0
    log_call(agent_name, step, prompt_tokens, completion_tokens,
             latency, success, notes="" if success else result[:120])
    return result
