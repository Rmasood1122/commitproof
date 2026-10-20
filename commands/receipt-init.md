---
description: Start here — one-time setup that turns on receipts for this repo so every commit (AI-assisted or not) gets a tamper-evident record. Creates a gitignored signing key, a vendored verifier, and a git post-commit hook
argument-hint: "[--no-git-hook] [--force]"
---

Initialize receipts in the user's current repository:

```
sh "${CLAUDE_PLUGIN_ROOT}/core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py" init $ARGUMENTS
```

After it succeeds, explain the three facts the user must not learn later:

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

If init refuses because the key is tracked by git, that is fail-closed
working as designed: help them run `git rm --cached .titan/key`, then retry.
A key that has ever been pushed is burned — rotate it (`init --force`) and
say plainly that receipts signed with the burned key prove nothing anymore.
