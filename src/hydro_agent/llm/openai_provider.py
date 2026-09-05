"""OpenAI Responses API implementation of the provider-neutral tool loop."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from hydro_agent.llm.base import ToolExecutor


class OpenAIResponsesProvider:
    """Use strict function tools with the OpenAI Responses API."""

    def __init__(self, api_key: str, model: str = "gpt-5.4-mini", max_steps: int = 6) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("使用 OpenAI Provider 需要安装 openai。") from exc
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.max_steps = max_steps

    def run(
        self,
        question: str,
        system_prompt: str,
        tools: Sequence[dict[str, Any]],
        execute_tool: ToolExecutor,
    ) -> tuple[str, list[tuple[str, dict[str, Any], dict[str, Any]]]]:
        response = self._client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=question,
            tools=list(tools),
        )
        executed: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        for _ in range(self.max_steps):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return response.output_text, executed
            outputs = []
            for call in calls:
                arguments = json.loads(call.arguments)
                result = execute_tool(call.name, arguments)
                executed.append((call.name, arguments, result))
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
            response = self._client.responses.create(
                model=self.model,
                instructions=system_prompt,
                previous_response_id=response.id,
                input=outputs,
                tools=list(tools),
            )
        raise RuntimeError("Agent 超过最大工具调用轮数，已停止以防止无限循环。")
