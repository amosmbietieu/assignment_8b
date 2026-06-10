"""
logger.py
─────────
WHY THIS FILE EXISTS:
  The assignment explicitly says "Log everything. Analyze your log files."
  Every agent call — prompt sent, tokens used, response received, latency —
  must be captured in a structured, queryable format.

  We use JSONL (one JSON object per line) because:
    - It can be streamed (no need to load entire file into memory)
    - Each line is independently parseable
    - Easy to grep, filter, analyze with pandas

  The LogAnalyzer class produces the summary statistics for the dashboard
  and the write-up section "Log Analysis".
"""

import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("logs/agent_calls.jsonl")


def ensure_log_dir():
    LOG_PATH.parent.mkdir(exist_ok=True)


def log_call(agent_name: str, step: str, prompt_tokens: int,
             completion_tokens: int, latency_s: float,
             success: bool, notes: str = ""):
    """
    Write one structured log entry.

    FIELDS EXPLAINED:
      agent_name     : which agent made this call (e.g. "DataScout")
      step           : human-readable description of what was being done
      prompt_tokens  : tokens sent to the API (costs money, affects latency)
      completion_tokens: tokens received (the model's answer)
      latency_s      : wall-clock seconds for this API call
      success        : did the agent complete without error?
      notes          : any qualitative observation (e.g. "refusal triggered")
    """
    ensure_log_dir()
    entry = {
        "ts":                datetime.now(timezone.utc).isoformat(),
        "agent":             agent_name,
        "step":              step,
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
        "latency_s":         round(latency_s, 3),
        "success":           success,
        "notes":             notes,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


class LogAnalyzer:
    """
    Reads the JSONL log and computes summary statistics.
    Used by the dashboard and write-up generator.
    """

    def __init__(self, path: Path = LOG_PATH):
        self.path = path
        self.entries = self._load()

    def _load(self):
        if not self.path.exists():
            return []
        entries = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def total_tokens(self) -> int:
        return sum(e["total_tokens"] for e in self.entries)

    def total_latency(self) -> float:
        return sum(e["latency_s"] for e in self.entries)

    def calls_per_agent(self) -> dict:
        counts = {}
        for e in self.entries:
            counts[e["agent"]] = counts.get(e["agent"], 0) + 1
        return counts

    def tokens_per_agent(self) -> dict:
        totals = {}
        for e in self.entries:
            totals[e["agent"]] = totals.get(e["agent"], 0) + e["total_tokens"]
        return totals

    def latency_per_agent(self) -> dict:
        totals = {}
        for e in self.entries:
            totals[e["agent"]] = totals.get(e["agent"], 0) + e["latency_s"]
        return totals

    def failure_rate(self) -> float:
        if not self.entries:
            return 0.0
        failures = sum(1 for e in self.entries if not e["success"])
        return failures / len(self.entries)

    def summary(self) -> dict:
        return {
            "total_calls":        len(self.entries),
            "total_tokens":       self.total_tokens(),
            "total_latency_s":    round(self.total_latency(), 2),
            "failure_rate_pct":   round(self.failure_rate() * 100, 1),
            "calls_per_agent":    self.calls_per_agent(),
            "tokens_per_agent":   self.tokens_per_agent(),
            "latency_per_agent":  self.latency_per_agent(),
        }
