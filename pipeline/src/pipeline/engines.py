"""LLM "engines": one interface, several back-ends.

The pipeline only needs one operation: send a system prompt + a user prompt, get back a
JSON object matching a JSON Schema, plus token usage. Keeping this behind a small
interface lets us swap Claude Code (default: uses the user's Claude subscription, no API
key) for another provider later, and use a fake engine in tests.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class EngineResult:
    data: dict | None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    raw: dict = field(default_factory=dict)


class Engine(Protocol):
    name: str

    def run(self, system_prompt: str, user_prompt: str, schema: dict) -> EngineResult: ...


class ClaudeCodeEngine:
    """Runs `claude -p` (Claude Code, non-interactive) with structured output.

    - Our own system prompt replaces Claude Code's default one (~3k fewer tokens per call).
    - No tools, no MCP servers, no session saved.
    - Runs in an empty temporary directory so no project CLAUDE.md is loaded.
    """

    def __init__(self, model: str = "haiku", timeout: float = 600.0, executable: str = "claude"):
        self.model = model
        self.timeout = timeout
        self.executable = shutil.which(executable) or executable
        self.name = f"claude-code:{model}"

    def run(self, system_prompt: str, user_prompt: str, schema: dict) -> EngineResult:
        with tempfile.TemporaryDirectory(prefix="labby-llm-") as workdir:
            prompt_file = Path(workdir) / "system_prompt.md"
            prompt_file.write_text(system_prompt, encoding="utf-8")
            cmd = [
                self.executable,
                "-p",
                "--model", self.model,
                "--output-format", "json",
                "--tools", "",
                "--strict-mcp-config",
                "--no-session-persistence",
                "--system-prompt-file", str(prompt_file),
                "--json-schema", json.dumps(schema, separators=(",", ":")),
            ]  # fmt: skip
            try:
                proc = subprocess.run(
                    cmd,
                    env=_clean_env(),
                    input=user_prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=workdir,
                    timeout=self.timeout,
                )
            except FileNotFoundError:
                return EngineResult(
                    None, error="`claude` CLI not found (is Claude Code installed?)"
                )
            except subprocess.TimeoutExpired:
                return EngineResult(None, error=f"timeout after {self.timeout}s")
        return parse_claude_output(proc.returncode, proc.stdout, proc.stderr)


def _clean_env() -> dict[str, str]:
    """Environment for `claude`, with whitespace removed from the auth token.

    A token pasted into a CI secret often carries a trailing newline; recent Claude Code
    versions then ignore it entirely ("Not logged in").
    """
    env = dict(os.environ)
    token = env.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = "".join(token.split())
    return env


def parse_claude_output(returncode: int, stdout: str, stderr: str) -> EngineResult:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        message = (stderr or stdout or "").strip()[:300]
        return EngineResult(None, error=f"exit {returncode}, non-JSON output: {message}")

    usage = payload.get("usage") or {}
    input_tokens = (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )
    result = EngineResult(
        data=payload.get("structured_output"),
        input_tokens=input_tokens,
        output_tokens=usage.get("output_tokens", 0),
        raw={k: payload.get(k) for k in ("subtype", "is_error", "num_turns", "api_error_status")},
    )
    if payload.get("is_error") or returncode != 0:
        result.error = f"claude error: {payload.get('result') or payload.get('subtype')}"[:300]
    elif result.data is None:
        result.error = "no structured_output in response"
    return result


class FakeEngine:
    """Returns canned responses (tests); records the prompts it receives."""

    name = "fake"

    def __init__(self, responses: list[EngineResult | dict]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def run(self, system_prompt: str, user_prompt: str, schema: dict) -> EngineResult:
        self.calls.append((system_prompt, user_prompt))
        response = self.responses.pop(0)
        if isinstance(response, dict):
            return EngineResult(response, input_tokens=100, output_tokens=10)
        return response
