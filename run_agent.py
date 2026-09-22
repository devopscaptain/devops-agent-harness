#!/usr/bin/env python3
"""
Entrypoint. Run with:

    export ANTHROPIC_API_KEY=sk-ant-...
    pip install -r requirements.txt
    python3 run_agent.py

Requires network access to api.anthropic.com.
"""

import sys

from harness.agent import DevOpsAgent
from harness.tools import read_file

TASK = """Fix example_problem/main.tf so that it passes example_problem's
compliance guardrail, per example_problem/policy.md. Use run_policy_check
to verify your work before declaring the task complete."""


def main():
    print("=" * 70)
    print("DevOps Agent Harness — S3 Compliance Guardrail Fix")
    print("=" * 70)
    print("\nCurrent policy.md:\n")
    print(read_file("example_problem/policy.md"))

    agent = DevOpsAgent()
    result = agent.run(TASK)

    print("\nFinal example_problem/main.tf:\n")
    print(read_file("example_problem/main.tf"))

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
