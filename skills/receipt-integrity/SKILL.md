---
name: receipt-integrity
description: Use whenever someone needs to know or prove which commits AI wrote — "how much of this did Claude write", "which commits did Claude write", "audit trail for AI-generated code", "what share of our code is AI-assisted", "SOC 2 / HIPAA / PCI change-control evidence", "can we prove this history wasn't rewritten", AI provenance or an AI bill of materials — and whenever receipts, /receipt-init, /verify-chain or /receipt-report come up or a verification fails. Covers setup, what hash-chained HMAC receipts prove and don't, and handling a failed check without laundering it.
---

# Receipt integrity (and its honest limits)

Use this skill whenever the user works with change receipts, asks what the
receipts prove, prepares compliance claims involving them, or when a
verification fails.

## "How much of this did Claude write?"

Answer it now with `/ai-history`: it reads the Claude trailers already in git
history and needs no setup. Keep its label: unsigned, from commit trailers, a
starting estimate rather than evidence, counting commits and lines added in
them, not lines Claude typed.

## Not set up yet?

If `.titan/key` doesn't exist in the repo, nothing is being receipted. Offer
`/receipt-init` — the one-time setup — and say what it does (gitignored signing
key, vendored verifier, git post-commit hook). Don't run it unasked: creating a
key and installing a hook is the user's decision. Commits made before init stay
unreceipted; never backfill them as if they had been recorded at the time —
`/ai-history` is the honest view of the past, receipts the record from init on.

## What a receipt chain actually proves

- **Content integrity:** the recorded file hashes, diff hash, and metadata
  have not been altered since the receipt was written — any edit breaks the
  recomputed hash.
- **Ordering:** each receipt binds the previous one's hash; reordering or
  removing a middle receipt breaks the walk. Chain rules are fail-closed:
  forks, double-genesis, dangling predecessors, and hash mismatches are hard
  errors, never guesses.
- **Under a shared key (HMAC receipts):** the signature proves the signer
  held `.titan/key` — nothing more.
- **By a named key (SSH receipts, `/receipt-init --ssh`):** the signature
  proves it was made by the SSH key `.titan/allowed_signers` lists for the
  receipt's `signer.principal`, and anyone can check it with no secret.

## What it does NOT prove — never let a claim drift past these

1. **Not identity, for HMAC receipts.** HMAC is a symmetric secret: anyone
   holding the key can produce valid signatures, including re-signing altered
   history wholesale. If a compliance draft says an HMAC chain "proves who made
   the change," correct it to "proves the change is unaltered since signing,
   under a key the team controls."
1b. **SSH receipts identify a key, not a person.** They prove which key
   signed, under the principal `allowed_signers` maps it to. That's a person
   only as far as key custody goes (a shared or stolen key signs as its owner),
   and the mapping is only as trustworthy as `allowed_signers`' git history:
   someone with push access could add a key, visibly. Safe wording: "signed by
   the SSH key registered to alice@example.com". Not "alice approved it", and
   not "non-repudiable" without the user's auditor signing off. CI can pin a
   trusted list (`--allowed-signers` / the action's `allowed_signers` input)
   rather than trusting the repo under audit. The receipt's `signer` (who and
   which key) is inside the hash, so swapping it breaks the chain.
2. **Not review, not quality.** A receipt attests WHAT changed, not that
   anyone approved it or that it was good.
3. **Not truthful provenance.** `provenance.ai_assisted`, `basis`, `models`,
   `claude_code_version`, `session_id` and the transcript hash are recorded
   claims: trailers copied from the commit message, plus what the Claude Code
   hook observed locally when it wrote the receipt. The chain proves they were
   not edited afterwards — flipping `ai_assisted` breaks verification — not
   that they were accurate when written. Present them as recorded claims,
   never as verified facts.
3b. **Not complete coverage.** Only receipted commits are counted. Commits made
   before init, or in a clone without the git hook and outside Claude Code,
   have no receipt. A report's AI-assisted percentage is "of receipted
   commits"; say so when it is quoted.
4. **Only as strong as the earliest independent copy.** A chain that only
   ever lived on one machine proves ordering to its owner alone. Committing
   `.titan/attestations/` and pushing gives every clone an independent
   copy — that distribution, not the math, is what makes tampering visible
   to others.

## Operating rules

- The key is never committed; a key that has ever been pushed is burned —
  rotate, and state plainly that pre-rotation receipts now prove nothing.
- Verification failures are findings, not obstacles. Never delete, edit, or
  regenerate receipts to make `verify` pass; that is the exact attack the
  system exists to expose. Preserve the failing state, then investigate.
- Receipts are committed; the key is not. Auto-receipting via the commit
  hook must never break a commit — an uninitialized repo is a silent no-op,
  by design.

## For compliance write-ups

Safe sentence template: "Every commit made through our tooling is recorded
in a hash-chained, HMAC-signed receipt committed alongside the code, carrying
the commit's content hashes and a recorded provenance claim (AI-assisted or
not, model and tool version where observed); any post-hoc alteration of
recorded history is detectable by offline verification." For SSH-signed
chains, replace "HMAC-signed" with "signed by the committing developer's
registered SSH key" and add "verifiable by anyone with the repository, with no
shared secret." `/receipt-report`
produces the evidence document with its verification result and this
limits footer attached — do not strip the footer. Do not add "non-repudiable," "cryptographically proves
authorship," or named framework compliance (SOC2/EU AI Act) without the
user's own auditor signing off — offer the mapping as input to that
conversation, not as its conclusion.
