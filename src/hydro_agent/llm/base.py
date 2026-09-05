"""Provider-neutral LLM interfaces."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, TypeAlias

ToolExecutor: TypeAlias = Callable[[str, dict[str, Any]], dict[str, Any]]


class AgentLLMProvider(Protocol):
    def run(
        self,
        question: str,
        system_prompt: str,
        tools: Sequence[dict[str, Any]],
        execute_tool: ToolExecutor,
    ) -> tuple[str, list[tuple[str, dict[str, Any], dict[str, Any]]]]:
        """Run a tool-calling loop and return text plus executed calls."""

