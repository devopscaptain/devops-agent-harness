#!/usr/bin/env python3
"""
policy_check.py — S3 migration-bucket compliance guardrail.

This is deliberately a standalone, dependency-free script: it is meant to be
run the exact same way by a human, a CI pipeline, or an agent harness, so
that "pass" means the same thing to all three. It uses simple text/regex
scanning rather than a full HCL parser — good enough for this guardrail,
and easy to read for anyone auditing what the check actually verifies.

Exit code 0  -> compliant
Exit code 1  -> violations found (see stdout)

Usage:
    python3 policy_check.py path/to/main.tf
"""

import re
import sys
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    bucket_names: list = field(default_factory=list)
    violations: list = field(default_factory=list)

    def ok(self) -> bool:
        return len(self.violations) == 0


REQUIRED_TAGS = ["Environment", "Owner", "CostCenter", "DataClassification"]


def find_bucket_resources(text: str):
    """Return list of (resource_name, local_name) for aws_s3_bucket resources."""
    return re.findall(r'resource\s+"aws_s3_bucket"\s+"([^"]+)"', text)


def has_resource_targeting(text: str, resource_type: str, bucket_local_name: str) -> str | None:
    """
    Find a resource block of `resource_type` whose body references the given
    bucket (via `bucket = aws_s3_bucket.<name>.id` or `.bucket`), and return
    that block's body text, or None if not found.
    """
    pattern = re.compile(
        r'resource\s+"' + re.escape(resource_type) + r'"\s+"[^"]+"\s*\{(.*?)\n\}',
        re.DOTALL,
    )
    ref_pattern = re.compile(
        r'aws_s3_bucket\.' + re.escape(bucket_local_name) + r'\.(id|bucket)'
    )
    for match in pattern.finditer(text):
        body = match.group(1)
        if ref_pattern.search(body):
            return body
    return None


def check_encryption(text: str, bucket_local_name: str, result: CheckResult):
    body = has_resource_targeting(text, "aws_s3_bucket_server_side_encryption_configuration", bucket_local_name)
    if body is None or "apply_server_side_encryption_by_default" not in body:
        result.violations.append(
            f"S3 bucket '{bucket_local_name}' has no server-side encryption configuration"
        )


def check_versioning(text: str, bucket_local_name: str, result: CheckResult):
    body = has_resource_targeting(text, "aws_s3_bucket_versioning", bucket_local_name)
    if body is None or not re.search(r'status\s*=\s*"Enabled"', body):
        result.violations.append(
            f"S3 bucket '{bucket_local_name}' has no versioning configuration"
        )


def check_public_access_block(text: str, bucket_local_name: str, result: CheckResult):
    body = has_resource_targeting(text, "aws_s3_bucket_public_access_block", bucket_local_name)
    if body is None:
        result.violations.append(
            f"S3 bucket '{bucket_local_name}' has no public access block resource"
        )
        return
    required_flags = [
        "block_public_acls",
        "block_public_policy",
        "ignore_public_acls",
        "restrict_public_buckets",
    ]
    missing_or_false = []
    for flag in required_flags:
        m = re.search(flag + r'\s*=\s*(true|false)', body)
        if not m or m.group(1) != "true":
            missing_or_false.append(flag)
    if missing_or_false:
        result.violations.append(
            f"S3 bucket '{bucket_local_name}' public access block missing/false for: "
            + ", ".join(missing_or_false)
        )


def check_tags(text: str, bucket_local_name: str, result: CheckResult):
    # Find the aws_s3_bucket block itself and look for a tags = { ... } body inside it.
    pattern = re.compile(
        r'resource\s+"aws_s3_bucket"\s+"' + re.escape(bucket_local_name) + r'"\s*\{(.*?)\n\}',
        re.DOTALL,
    )
    m = pattern.search(text)
    bucket_body = m.group(1) if m else ""
    tags_match = re.search(r'tags\s*=\s*\{(.*?)\}', bucket_body, re.DOTALL)
    tags_body = tags_match.group(1) if tags_match else ""
    missing = [t for t in REQUIRED_TAGS if t not in tags_body]
    if missing:
        result.violations.append(
            f"Missing required tag(s) on '{bucket_local_name}': " + ", ".join(missing)
        )


def run_check(path: str) -> CheckResult:
    with open(path, "r") as f:
        text = f.read()

    result = CheckResult()
    buckets = find_bucket_resources(text)
    result.bucket_names = buckets

    if not buckets:
        result.violations.append("No aws_s3_bucket resource found in file")
        return result

    for bucket_local_name in buckets:
        check_encryption(text, bucket_local_name, result)
        check_versioning(text, bucket_local_name, result)
        check_public_access_block(text, bucket_local_name, result)
        check_tags(text, bucket_local_name, result)

    return result


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 policy_check.py path/to/main.tf")
        sys.exit(2)

    result = run_check(sys.argv[1])

    if result.ok():
        print(f"✅ PASS: compliant ({', '.join(result.bucket_names)})")
        sys.exit(0)
    else:
        print(f"❌ FAIL: {len(result.violations)} violation(s) found")
        for v in result.violations:
            print(f"  - {v}")
        sys.exit(1)


if __name__ == "__main__":
    main()
