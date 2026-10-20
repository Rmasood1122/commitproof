---
description: Generate a markdown compliance report from the receipt chain — AI-assisted share, by author/month/recorder, models and tool versions recorded, chain verification result, honest limits
argument-hint: "[--out docs/ai-change-receipts.md] [--badge docs/ai-audit-badge.svg]"
---

Produce the report:

```
sh "${CLAUDE_PLUGIN_ROOT}/core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py" report $ARGUMENTS
```

How to present it:

- The **Verification** section is the point. If the chain is BROKEN or any
  signature is invalid, lead with that — do not summarize the counts as if
  they were trustworthy, and never offer to "clean up" receipts so the report
  looks better. The failure is the finding.
- The AI-assisted share counts only receipted commits. Commits made before
  `/receipt-init`, or outside both hooks, have no receipt. Say so if the user
  is about to quote a percentage to an auditor.
- The "What this report proves — and does not" footer stays in the document.
  If the user wants to drop it for a cleaner look, decline and explain: a
  report that overclaims is worse than no report.
- `--badge FILE` writes a README badge from the same verification: it shows
  "chain verified" only when the chain is intact and every signature
  checked out, "structure only" without the key, and "verification FAILED"
  (no share) otherwise. Give the user the README line the tool prints.
  Never hand-edit the SVG or regenerate it somewhere the key passes so it
  looks better — the badge is a claim on their front page.
- Framework mapping (SOC 2 CC8.1, HIPAA change control, PCI-DSS §6, ISO
  42001, EU AI Act record-keeping): offer it as input to THEIR auditor's
  judgement, never as a conclusion. The receipt-integrity skill has the safe
  sentence template.
