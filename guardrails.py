"""
guardrails.py
-------------
Everything that keeps an autonomous agent from doing something expensive,
unbounded, or irreversible without a human in the loop.

Three independent controls:
  1. BudgetTracker  - stops the run if it would exceed a dollar spend cap
  2. StepLimiter    - stops the run after N reasoning/tool cycles
  3. ApprovalPolicy - pauses before executing any tool marked 'sensitive'
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


# Example per-million-token rates (USD). Prices change — verify current
# numbers at https://docs.claude.com before relying on this for real budgeting.
PRICE_PER_MILLION_TOKENS = {
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
}


class BudgetExceeded(Exception):
    pass


class StepLimitExceeded(Exception):
    pass


class ApprovalDenied(Exception):
    pass


@dataclass
class BudgetTracker:
    max_usd: float
    model: str
    spent_usd: float = 0.0

    def record(self, input_tokens: int, output_tokens: int) -> float:
        rates = PRICE_PER_MILLION_TOKENS.get(self.model, {"input": 3.0, "output": 15.0})
        cost = (input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"]
        self.spent_usd += cost
        if self.spent_usd > self.max_usd:
            raise BudgetExceeded(
                f"Run stopped: spent ${self.spent_usd:.4f}, exceeding the ${self.max_usd:.2f} cap."
            )
        return cost


@dataclass
class StepLimiter:
    max_steps: int
    steps_used: int = 0

    def tick(self):
        self.steps_used += 1
        if self.steps_used > self.max_steps:
            raise StepLimitExceeded(f"Run stopped: exceeded {self.max_steps} steps.")


@dataclass
class ApprovalPolicy:
    """
    Any tool name in `sensitive_tools` requires approval before it runs.
    `approver` defaults to a console prompt but can be swapped for a Slack
    webhook, a web UI callback, or an auto-deny/auto-approve function in
    automated test runs.
    """
    sensitive_tools: set = field(default_factory=set)
    approver: Optional[Callable[[str, dict], bool]] = None

    def _default_approver(self, tool_name: str, tool_input: dict) -> bool:
        print(f"\n[APPROVAL REQUIRED] The agent wants to run '{tool_name}' with input:")
        print(f"  {tool_input}")
        answer = input("Allow this action? [y/N]: ").strip().lower()
        return answer == "y"

    def check(self, tool_name: str, tool_input: dict):
        if tool_name not in self.sensitive_tools:
            return
        approver = self.approver or self._default_approver
        if not approver(tool_name, tool_input):
            raise ApprovalDenied(f"Human reviewer declined to run '{tool_name}'.")
