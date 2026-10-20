---
description: Write a signed, chained receipt for the current commit — file hashes, diff hash, author, and provenance (AI-assisted or not, session, model, tool version)
---

Create a receipt for HEAD:

```
sh "${CLAUDE_PLUGIN_ROOT}/core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py" create
```

- One receipt per commit: re-running on the same HEAD is a no-op, not a
  duplicate. Normally you never need this — the hooks receipt commits
  automatically; use it to receipt a commit both hooks missed.
- "refusing to extend a broken chain" is fail-closed working as designed —
  something in `.titan/attestations/` was altered or lost. Run
  `/verify-chain` to locate it; NEVER "fix" a broken chain by deleting or
  editing receipts to make verification pass — that is exactly the
  tampering receipts exist to expose. The honest path is: keep the broken
  chain as evidence, investigate what changed, and if the chain must
  restart, start a new tree and say so in the commit message.
- `provenance.ai_assisted` comes from the commit's Claude trailers and from
  whether the Claude Code hook recorded it; model, Claude Code version and
  transcript hash are what the hook observed locally. They are recorded
  claims by the tool, not proof of authorship — never present them as more.

If the repo isn't initialized, offer `/receipt-init` instead of improvising.
