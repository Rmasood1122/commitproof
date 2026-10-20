"""The one place tests build a child-process environment. Copies the runner's
environment minus anything Claude Code or this plugin sets, so a test never
inherits a real session. No URLs live here, by design (see core/badge.py)."""
import os

_PREFIXES = ("CLAUDE_", "TITAN_RECEIPTS_", "COMMITPROOF_")


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith(_PREFIXES)}
    env.update(extra)
    return env
