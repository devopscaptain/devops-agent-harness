"""
The loop. Everything else in harness/ exists to support this.

Note what this file does NOT do: it never trusts the model's own claim that
the task is finished. Success is defined once, in one place (did
run_policy_check return passed=True?), and the harness — not the model —
is the one checking it.
"""

import anthropic

from . import config
from .tools import TOOL_SCHEMAS, dispatch


class PolicyCheckNotYetPassed(Exception):
    pass


class DevOpsAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.messages = []
        self.policy_passed = False

    def run(self, task: str) -> dict:
        self.messages.append({"role": "user", "content": task})

        for turn in range(1, config.MAX_TURNS + 1):
            print(f"\n--- Turn {turn}/{config.MAX_TURNS} ---")

            response = self.client.messages.create(
                model=config.MODEL,
                max_tokens=2000,
                system=config.SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=self.messages,
            )

            self.messages.append({"role": "assistant", "content": response.content})

            tool_calls = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            for block in text_blocks:
                print(f"[model] {block.text.strip()}")

            if not tool_calls:
                # Model stopped requesting tools. That is NOT the same as
                # "task succeeded" — the harness still checks the fact.
                return self._finish(turn, reason="model stopped without a passing check")

            tool_results = []
            for call in tool_calls:
                print(f"[tool]  {call.name}({call.input})")
                result_text = dispatch(call.name, call.input)
                print(f"[result] {result_text[:300]}")

                if call.name == "run_policy_check" and result_text.startswith("[PASS]"):
                    self.policy_passed = True

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": result_text,
                    }
                )

            self.messages.append({"role": "user", "content": tool_results})

            if self.policy_passed:
                return self._finish(turn, reason="policy_check.py passed")

        return self._finish(config.MAX_TURNS, reason="turn budget exhausted")

    def _finish(self, turns_used: int, reason: str) -> dict:
        outcome = "SUCCESS" if self.policy_passed else "FAILED"
        print(f"\n=== {outcome} after {turns_used} turn(s): {reason} ===")
        return {
            "success": self.policy_passed,
            "turns_used": turns_used,
            "reason": reason,
        }
