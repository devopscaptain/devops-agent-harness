# Agent harness vs. other ways of using AI for this same problem

Same problem — a non-compliant Terraform bucket — solved four different
ways. What changes is not the model's intelligence; it's how much of the
work the harness does versus how much is left to trust.

## Method 1: Ask a chatbot in a browser tab

> "Here's my main.tf, make it pass our S3 compliance policy."

You paste the file, get back a "fixed" version, paste it into your editor.

- The model never saw `policy_check.py`, so its idea of "compliant" is
  whatever it remembers about S3 best practices — it can miss your org's
  specific tag names or your exact public-access-block requirement.
- Nothing runs. You find out if it actually passes when CI runs later,
  or a reviewer catches it.
- No iteration: if the first answer is wrong, you're back in the chat
  manually pasting the CI error and hoping the second answer is right.
- No audit trail beyond your chat history.

## Method 2: IDE autocomplete (Copilot-style)

You start typing `resource "aws_s3_bucket_server_side_encryption_configuration"`
and the model completes the block.

- Faster than method 1, but it's suggestion-at-a-time — the model has no
  view of whether the *whole file* is now compliant, only whether this one
  block looks locally plausible.
- Still no verification loop. You still run the checker yourself, read the
  failure, and go fix the next thing by hand.
- Good for typing speed; does nothing for "is this actually done."

## Method 3: One-shot agent ("write me a compliant bucket from scratch")

You ask an agent-flavored tool to generate the whole file in one pass,
grounded in a description of your policy.

- Better than 1 and 2 because it can *read* your policy doc as input.
- Still typically single-shot: it generates once, and if it misreads one
  requirement (e.g. forgets one required tag), nothing catches that before
  you do.
- No guarantee the generated file is even tested against the real scanner
  the CI pipeline uses — "looks right" and "passes `policy_check.py`" are
  different claims.

## Method 4: This repo — an agent harness with a verification loop

- **Tool-grounded, not memory-grounded.** The agent reads `policy.md` and
  the actual current `main.tf` through tools — it's working from your real
  files, not its training data's idea of S3 best practices.
- **Verified, not asserted.** After every edit, the harness runs the real
  `policy_check.py` — the same script your CI pipeline runs — and the
  loop's success condition is that script's exit code, not the model
  saying "this should be compliant now."
- **Iterative.** If the first edit only fixes 3 of 4 violations, the
  scanner says so, and the harness feeds that straight back to the model
  for another pass — up to a hard turn budget the harness enforces, not the
  model.
- **Bounded.** `write_file` in `harness/tools.py` refuses to touch anything
  except `example_problem/main.tf`. The model can *ask* to edit
  `policy_check.py` to make the check pass trivially — the harness's
  permission logic won't let it, regardless of how it's asked.
- **Auditable.** Every tool call, every check result, and every edit is
  printed turn-by-turn (`run_agent.py`'s stdout) — you get a record of what
  was tried and what the scanner actually said at each step, not just a
  final diff.

## The one-line version

Methods 1–3 all put a human in the loop as the verifier, at some point,
whether that's now or later in CI. Method 4 puts the *real verifier* — the
same script CI trusts — inside the loop itself, and lets the harness, not
the model's confidence, decide when the job is actually finished.
