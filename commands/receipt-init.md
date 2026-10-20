---
description: Start here — one-time setup that turns on receipts for this repo so every commit (AI-assisted or not) gets a tamper-evident record. --ssh signs with your own SSH key (no shared secret, anyone can verify); default is a gitignored shared HMAC key. Also vendors the verifier and installs a git post-commit hook
argument-hint: "[--ssh [KEY]] [--hmac] [--no-git-hook] [--force]"
---

Initialize receipts in the user's current repository:

```
sh "${CLAUDE_PLUGIN_ROOT}/core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py" init $ARGUMENTS
```

**Before running without `--ssh`,** check whether the user has an SSH key
(`git config gpg.format` is `ssh`, or `~/.ssh/id_ed25519.pub` exists). If they
do, recommend `--ssh`: each receipt is then signed by their own key, there's
no secret to share, and fresh clones and CI can verify signatures. Ask; don't
choose for them. In a repo that already has `.titan/allowed_signers`, plain
init uses SSH automatically.

After it succeeds, explain the three facts the user must not learn later.

**With `--ssh`:**

1. Their SSH public key and git email were added to `.titan/allowed_signers`.
   Commit that file with the receipts: it says who may sign, and a change to
   it shows in git history. The private key never leaves their machine; the
   key path is in this clone's local git config only.
2. Receipts land in `.titan/attestations/` and the verifier is vendored into
   `.titan/tools/`. Both SHOULD be committed.
3. Each teammate runs `/receipt-init --ssh` in their own clone; it adds their
   key beside the others. A key with a passphrase must be loaded in
   ssh-agent (`ssh-add`), because hooks can't prompt.

**Without `--ssh` (HMAC):**

1. `.titan/key` is the shared signing key. It is gitignored and must NEVER
   be committed — receipts are only as trustworthy as this key is private.
   If they want it backed up, that backup lives outside the repo.
2. Receipts land in `.titan/attestations/` and the verifier is vendored into
   `.titan/tools/`. Both SHOULD be committed — they are the audit trail and
   the means to check it, and they travel with the repo.
3. Coverage: the git `post-commit` hook receipts every commit made in this
   clone (human commits get `ai_assisted: false`); the plugin's own hook
   receipts commits made in Claude Code sessions with session/model/version
   detail. Git hooks are not cloned — teammates run
   `python3 .titan/tools/receipt.py install-hook` once per clone. Commits
   made without either hook have no receipt.

If `--ssh` refuses with "SSH key not usable", nothing was written. Relay the
reason (no key found, or it needs a passphrase): `ssh-add` the key, or pass
another with `--ssh PATH`. Don't fall back to HMAC unless the user asks.

If init refuses because the key is tracked by git, that is fail-closed
working as designed: help them run `git rm --cached .titan/key`, then retry.
A key that has ever been pushed is burned — rotate it (`init --force`) and
say plainly that receipts signed with the burned key prove nothing anymore.
