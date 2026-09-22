"""
Tools available to the model, and the harness-side code that actually runs
them. This file is the entire trust boundary of the system: the model can
only ever *request* one of these; it never executes anything directly.
"""

import os
import subprocess

from . import config

# All file access is jailed to the repo root. This is a harness-level
# guardrail, not something the model is asked to respect.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _safe_path(relative_path: str) -> str:
    full = os.path.abspath(os.path.join(REPO_ROOT, relative_path))
    if not full.startswith(REPO_ROOT):
        raise PermissionError(f"Path escapes repo root: {relative_path}")
    return full


TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file, given a path relative to the repo root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to repo root, e.g. example_problem/main.tf"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite a file with new content, given a path relative to the repo root. Only example_problem/main.tf may be written.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "The full new file content."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_policy_check",
        "description": "Run the compliance guardrail scanner against example_problem/main.tf and return its output and pass/fail status. This is the ONLY way to know whether the fix is actually correct.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def read_file(path: str) -> str:
    full = _safe_path(path)
    with open(full, "r") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    if path != "example_problem/main.tf":
        raise PermissionError(
            f"Harness denied write to '{path}': only example_problem/main.tf may be modified."
        )
    full = _safe_path(path)
    with open(full, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"


def run_policy_check() -> dict:
    cmd = config.ALLOWED_COMMANDS["policy_check"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    return {
        "passed": proc.returncode == 0,
        "exit_code": proc.returncode,
        "output": proc.stdout + proc.stderr,
    }


def dispatch(tool_name: str, tool_input: dict) -> str:
    """
    Single choke point for every tool call the model makes. This is where a
    real harness would also hang permission prompts, audit logging, and
    PreToolUse hooks — every action passes through here before anything
    happens on disk or in a shell.
    """
    try:
        if tool_name == "read_file":
            return read_file(tool_input["path"])
        elif tool_name == "write_file":
            return write_file(tool_input["path"], tool_input["content"])
        elif tool_name == "run_policy_check":
            result = run_policy_check()
            status = "PASS" if result["passed"] else "FAIL"
            return f"[{status}] exit_code={result['exit_code']}\n{result['output']}"
        else:
            return f"Error: unknown tool '{tool_name}'"
    except Exception as e:
        return f"Error: {e}"
