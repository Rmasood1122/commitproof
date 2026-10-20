---
description: Verify the full receipt chain offline — structure (single unbroken chain from GENESIS, content hashes) and every signature (SSH against .titan/allowed_signers, HMAC under .titan/key); --public-only checks what needs no secret, --structure-only skips signatures
argument-hint: "[--public-only] [--structure-only] [--allowed-signers FILE]"
---

Verify everything:

```
sh "${CLAUDE_PLUGIN_ROOT}/core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py" verify $ARGUMENTS
```

Report the result exactly as it is:

- **PASS** means: every receipt's content is unchanged since signing, the
  chain is a single unbroken line from GENESIS, and every signature checks
  out. Relay the tool's own caveats with it:
  - **SSH signatures** name who signed ("signed by alice@… (12)"): each was
    made by the key `.titan/allowed_signers` lists for that person. That
    identifies the key, not who controls it, and the list is only as
    trustworthy as its git history.
  - **HMAC signatures** don't identify anyone: HMAC is a shared secret.
- **PASS (public signatures only)** (`--public-only`) means SSH signatures
  were checked and HMAC ones were deliberately skipped. Say how many HMAC
  receipts went unchecked.
- **PASS (structure only)** means the chain and content hashes are
  consistent but no signature was checked. Relay that limitation verbatim;
  it is a weaker claim.
- **CHAIN FAIL / SIG FAIL** names the exact receipt. Do not delete or edit
  it to get to green; the failure IS the finding. Help the user diff the
  offending receipt against git history to see what changed and when. An
  SSH SIG FAIL can also mean the signer's key isn't in `allowed_signers` (a
  teammate who never ran `/receipt-init --ssh`); check that before calling it
  tampering, and never add a key just to make it pass without the user
  confirming it's that person's key.
- **SIGNATURES NOT CHECKED (exit 2)** means some HMAC receipts and no
  `.titan/key` here (typically a fresh clone), or SSH receipts with no
  `ssh-keygen` / `allowed_signers`. Everything else still ran and its result
  is real; say so, then say what was not checked. Never call this a PASS.
- **ANCHOR** (always printed last) says how many receipts are committed and
  pushed. Relay it every time, even on PASS: a chain that verifies but exists
  only on this machine is not yet evidence to anyone else — the key-holder
  could rewrite it. If anything is untracked/uncommitted/unpushed, give the
  exact command: `git add .titan/attestations && git commit && git push`.

`--allowed-signers FILE` trusts that list instead of the repo's own: use it
when the person verifying shouldn't take the audited repo's word for who may
sign. This runs fully offline — no network, no service, just the files,
`ssh-keygen`, the key if there is one, and local git metadata.
