# Guardrail: S3 Buckets Used for Migration Artifacts

All `aws_s3_bucket` resources under `example_problem/` (staging buckets for
MGN/DMS migration artifacts) MUST satisfy the following before merge:

1. **Encryption at rest** — an `aws_s3_bucket_server_side_encryption_configuration`
   resource must exist, targeting the bucket, with an `apply_server_side_encryption_by_default`
   block.
2. **Versioning** — an `aws_s3_bucket_versioning` resource must exist,
   targeting the bucket, with `versioning_configuration { status = "Enabled" }`.
3. **No public access** — an `aws_s3_bucket_public_access_block` resource must
   exist, targeting the bucket, with all four settings (`block_public_acls`,
   `block_public_policy`, `ignore_public_acls`, `restrict_public_buckets`)
   set to `true`.
4. **Required tags** — the bucket resource's `tags` block must include:
   `Environment`, `Owner`, `CostCenter`, `DataClassification`.

Non-negotiable: do not satisfy this policy by removing the bucket resource,
renaming it out of scope, or disabling the check. The fix must be a real,
compliant bucket configuration.
