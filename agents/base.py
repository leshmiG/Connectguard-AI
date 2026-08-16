"""
agents/base.py
----------------
The same ReAct loop pattern used throughout — one agent, tools, guardrails,
tracing. Kept synchronous here since APScheduler (the scheduler used for
this project) runs jobs on worker threads, not an event loop.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import anthropic

from guardrails import ApprovalDenied, ApprovalPolicy, BudgetTracker, StepLimiter
from tracing import Tracer

logger = logging.getLogger("pyxis_agent")


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., str]
    sensitive: bool = False


class ToolAgent:
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        tools: list[Tool],
        budget: BudgetTracker,
        tracer: Tracer,
        approval_policy: Optional[ApprovalPolicy] = None,
        max_steps: int = 6,
        api_key: Optional[str] = None,
    ):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.client = anthropic.Anthropic(api_key=api_key)
        self.budget = budget
        self.tracer = tracer
        self.approval_policy = approval_policy or ApprovalPolicy(
            sensitive_tools={t.name for t in tools if t.sensitive}
        )
        self.steps = StepLimiter(max_steps=max_steps)
        self.messages: list[dict] = []

    def _log(self, event_type: str, **fields):
        self.tracer.event(event_type, agent=self.name, **fields)

    def _tool_specs(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in self.tools.values()]

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        tool = self.tools.get(name)
        if tool is None:
            return f"Error: no such tool '{name}'"
        try:
            self.approval_policy.check(name, tool_input)
        except ApprovalDenied as e:
            self._log("approval_denied", tool=name)
            return f"Blocked: {e}"
        try:
            result = tool.handler(**tool_input)
            self._log("tool_success", tool=name)
            return str(result)
        except Exception as e:
            logger.exception(f"Tool '{name}' failed")
            self._log("tool_error", tool=name, error=str(e))
            return f"Error running '{name}': {e}"

    def run(self, task: str) -> str:
        self.messages.append({"role": "user", "content": task})
        self._log("task_start", task=task)

        while True:
            self.steps.tick()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                tools=self._tool_specs(),
                messages=self.messages,
            )
            cost = self.budget.record(response.usage.input_tokens, response.usage.output_tokens)
            self._log("model_call", cost_usd=round(cost, 6), cumulative_usd=round(self.budget.spent_usd, 6))
            self.messages.append({"role": "assistant", "content": response.content})

            tool_calls = [b for b in response.content if b.type == "tool_use"]
            if not tool_calls:
                answer = "".join(b.text for b in response.content if b.type == "text")
                self._log("task_end", answer=answer)
                return answer

            results = []
            for call in tool_calls:
                self._log("tool_call", tool=call.name, input=call.input)
                result = self._execute_tool(call.name, call.input)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})
            self.messages.append({"role": "user", "content": results})
