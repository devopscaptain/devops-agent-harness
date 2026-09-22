"""
Harness-owned configuration. Nothing in this file is negotiable by the model
mid-run — that's the point. A harness enforces limits *outside* the model's
control, not by asking it nicely to behave.
"""

MODEL = "claude-sonnet-5"

# Hard turn budget. If the agent hasn't produced a passing policy_check.py
# run within this many loop iterations, the harness stops it — regardless
# of what the model wants to try next.
MAX_TURNS = 8

# The only shell commands the harness will actually execute on the model's
# behalf. Anything else the model asks for is refused before it ever reaches
# a shell. This is the harness's permission boundary, not a suggestion in
# the prompt.
ALLOWED_COMMANDS = {
    "policy_check": ["python3", "policy_check.py", "example_problem/main.tf"],
}

SYSTEM_PROMPT = """You are a DevSecOps agent operating inside a harness with a narrow, well-defined job:

Fix example_problem/main.tf so that it passes the compliance guardrail
enforced by policy_check.py, using the requirements in
example_problem/policy.md as your specification.

Rules:
- You may only touch example_problem/main.tf. Do not create new files or
  modify policy_check.py.
- Do not satisfy the check by deleting the bucket resource, renaming it out
  of the check's scope, or otherwise gaming the scanner. The fix must be a
  real, compliant configuration a human reviewer would approve.
- After every edit, run the policy check tool to verify your change before
  claiming the task is done. Do not assert success without a passing check
  result in front of you.
- Work iteratively: read what exists, make one focused change at a time,
  verify, and adjust based on what the checker actually reports.
"""
