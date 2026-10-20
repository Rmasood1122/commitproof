---
description: How much of this repo did Claude help write? Instant answer from git history — share of commits and lines added with a Claude trailer, by author and month. No setup, no key, writes nothing
argument-hint: "[--since 2026-01-01] [--json]"
---

Scan this repository's git history:

```
sh "${CLAUDE_PLUGIN_ROOT}/core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py" history $ARGUMENTS
```

How to present it:

- Lead with the headline numbers: commits and lines added with a Claude
  trailer, and their share. Then the busiest authors and the trend by month.
- Keep the label the tool prints: this comes from commit trailers, it is
  **unsigned**, and it is a starting estimate, not evidence. Trailers are
  plain text anyone can add, delete or rewrite, and Claude-assisted commits
  whose trailer was dropped count as not AI-assisted. Never round it up into
  "Claude wrote X% of the code" — it counts commits and the lines added in
  them, not which lines Claude typed.
- If the repo has no receipts yet, end with the one-line offer the tool
  prints: `/receipt-init` makes every commit from now on tamper-evident.
  Don't run it unasked — it creates a key and installs a git hook, which is
  the user's call.
- If receipts are already on, point to `/receipt-report` for the signed view.
