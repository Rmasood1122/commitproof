#!/usr/bin/env python3
"""commitproof — change-attestation receipts for AI-assisted commits.

Profile: schema_version "change-attestation/v1"
  - Canonicalization: TRS-1 sorted-keys (vendored canonical.py, byte-
    compatible with titan-gate's), exclusions {signature, receipt_hash, ...}.
  - Signing: hmac-sha256-v1 (shared .titan/key) or ssh-sig-v1 (the committer's
    SSH key, checked against .titan/allowed_signers), over the receipt
    hash; see signing.py. Chains may mix them; each receipt is checked by
    its own signing_version.
  - Chain: vendored chain_state rules — single GENESIS, forks/dangling
    prevs/tampered hashes are hard errors, never guesses.
  - Tree: .titan/attestations/ (its OWN tree; never mixed with a judge-
    receipt chain — mixed profiles in one tree are a hard error upstream).

WHAT A RECEIPT PROVES (and does not — say it exactly like this):
  Proves: this commit's recorded content hashes, in this order, under this
  shared key, have not been altered since the receipt was written.
  Does NOT prove: who held the key (HMAC is a shared secret — anyone with
  the key can re-sign; third-party non-repudiation needs the upstream
  titan-gate Ed25519/TSA profiles), that the change was reviewed, or that
  the attribution trailer is truthful — attribution is copied from the
  commit message, an ATTESTATION by whoever wrote the commit.

PROVENANCE (v1.1): each receipt carries a `provenance` block — whether the
commit was AI-assisted and on what basis (commit trailers, or recorded by the
Claude Code hook), which recorder wrote the receipt, and best-effort
session id / model / Claude Code version read from the hook payload and the
session transcript. These answer the auditor's questions (which model, which
tool version, reproducible from what) but they are RECORDED CLAIMS: the
transcript is a local file this tool read, not something it can prove.

Subcommands:
  init [--no-git-hook] generate .titan/key (hex), gitignore it, refuse if
                      the key would be tracked by git; vendor this tool into
                      .titan/tools/ and install a git post-commit hook so
                      EVERY commit gets a receipt (human ones flagged
                      ai_assisted=false) — not only those Claude runs
  install-hook        (re)install the git post-commit hook + vendored tools
  create [--auto] [--recorder R]
                      receipt for HEAD; --auto exits 0 silently when the
                      repo has no key (hook mode: never break a commit)
  hook                PostToolUse entry point: reads the Claude Code hook
                      JSON from stdin (hook matchers match TOOL NAMES only,
                      so hooks.json matches "Bash" and THIS filters), no-ops
                      unless the command was a git commit, then = create
                      --auto --recorder claude-code-hook. Exits 0 on any
                      unparseable input.
  verify [--structure-only]
                      walk .titan/attestations/: chain structure + every
                      signature; exit 0 only if ALL verify. --structure-only
                      checks chain + content hashes without the key (CI
                      without the secret) and SAYS signatures were not checked.
                      Without a key (a fresh clone) it behaves the same way:
                      structure is checked and reported, signatures declared
                      UNCHECKED, exit 2. Always ends with an ANCHOR line: how
                      many receipts are committed AND pushed — distribution is
                      the only defence against a key-holder rewrite, so verify
                      measures it.
  report [--out F]    markdown summary for a compliance evidence folder:
                      receipts, AI-assisted share, by recorder/author/month,
                      chain verification result, and the honest-limits footer
  history [--since D] [--json]
                      zero-setup: share of commits (and lines added) carrying
                      a Claude trailer, from git history alone. Writes
                      nothing, needs no key, and labels itself unsigned

Exit codes: 0 ok · 1 verification/chain failure · 2 usage/config error.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing                                 # noqa: E402
from canonical import canonical_bytes           # noqa: E402
from chain_state import (                       # noqa: E402
    GENESIS, ChainStateError, latest_receipt_hash,
)

SCHEMA = "change-attestation/v1"
PLUGIN_VERSION = "1.4.0"          # kept equal to .claude-plugin/plugin.json (tested)
KEY_PATH = Path(".titan/key")
ALLOWED_SIGNERS = Path(".titan/allowed_signers")   # committed: who may SSH-sign
TREE = Path(".titan/attestations")
TOOLS_DIR = Path(".titan/tools")
# per-clone (local git config, never committed): this developer's SSH key
CFG_SSH_KEY, CFG_PRINCIPAL = "commitproof.signingkey", "commitproof.principal"
HOOK_MARK = "# commitproof post-commit hook"
LEGACY_HOOK_MARKS = ("# titan-receipts post-commit hook",)   # v1.0–1.2, still ours
AI_TRAILER_RE = re.compile(r"claude|anthropic", re.I)
# Trailer keys are case-insensitive: Claude Code writes Co-Authored-By, GitHub
# squash merges write Co-authored-by. A case-sensitive match recorded the
# GitHub form as ai_assisted=false.
CO_AUTHOR_RE = re.compile(r"^Co-Authored-By:\s*(.+)$", re.M | re.I)
SESSION_RE = re.compile(r"^Claude-Session:\s*(\S+)$", re.M | re.I)
# The Linux kernel's form: `Assisted-by: AGENT:MODEL` (1,723 kernel commits in
# a year named Claude this way and were counted as human).
ASSISTED_RE = re.compile(r"^Assisted-by:\s*(.+)$", re.M | re.I)


def ai_trailers(msg: str) -> bool:
    """True when a commit message carries a Claude co-author, assisted-by or
    session trailer. The one rule receipts and `history` both count by."""
    named = CO_AUTHOR_RE.findall(msg) + ASSISTED_RE.findall(msg)
    return any(AI_TRAILER_RE.search(c) for c in named) or bool(SESSION_RE.search(msg))


def die(msg: str, code: int = 2) -> "int":
    print(f"FAIL: {msg}", file=sys.stderr)
    return code


def git(*args: str) -> str:
    # encoding is explicit: git emits paths and diffs as UTF-8 bytes, and
    # text=True alone decodes with the platform locale — cp1252 on Windows —
    # which mangled 'café.py' into 'cafÃ©.py' (no such file → content hash
    # silently dropped) and made diff_sha256 differ between a receipt written
    # on Windows and one written on Linux for the same commit.
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def git_config(key: str) -> str | None:
    try:
        return git("config", "--get", key).strip() or None
    except RuntimeError:
        return None    # unset


def local_signer() -> tuple[str, Path | None, str | None] | None:
    """How THIS clone signs: ("ssh", key, principal), ("hmac", None, None),
    or None when it can't sign. SSH wins when both are set up: a repo that
    moved to SSH keeps its HMAC key only so earlier receipts still verify."""
    key = git_config(CFG_SSH_KEY)
    if key:
        return "ssh", Path(key), git_config(CFG_PRINCIPAL) or git_config("user.email")
    if KEY_PATH.exists():
        return "hmac", None, None
    return None


def repo_root() -> Path | None:
    try:
        return Path(git("rev-parse", "--show-toplevel").strip())
    except RuntimeError:
        return None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def load_key() -> bytes | None:
    """Read and validate .titan/key. A corrupt or too-short key must never
    sign anything — an empty key would HMAC 'successfully' and produce
    receipts that prove nothing. Returns None after printing FAIL."""
    try:
        key = bytes.fromhex(KEY_PATH.read_text().strip())
    except (ValueError, OSError):
        print(f"FAIL: {KEY_PATH} is not valid hex — corrupt key; restore it "
              f"or rotate (init --force) and disclose the break", file=sys.stderr)
        return None
    if len(key) < 16:
        print(f"FAIL: {KEY_PATH} is too short ({len(key)} bytes) — refusing "
              f"to sign with a weak/empty key", file=sys.stderr)
        return None
    return key


def changed_files(sha: str) -> tuple[list[dict], str, int]:
    """(files, patch, n_parents) for a commit.

    - NUL-separated name-status (-z): git C-quotes non-ASCII/special paths
      in line mode, which turned 'café.py' into '"caf\\303\\251.py"' — a path
      that matches no file, so its content hash was silently DROPPED. An
      attestation tool must never silently skip content.
    - Merge commits diff against the FIRST parent: 'git show' prints the
      combined diff for merges, which is usually empty — a receipt with
      files=[] attests nothing without saying so.
    """
    parents = git("rev-list", "--parents", "-n", "1", sha).split()[1:]
    if len(parents) >= 2:
        raw = git("diff", "--name-status", "-z", f"{sha}^1", sha)
        patch = git("diff", f"{sha}^1", sha)
    else:
        raw = git("show", "--name-status", "-z", "--format=", sha)
        patch = git("show", "--format=", sha)
    files: list[dict] = []
    toks = raw.split("\0")
    i = 0
    while i < len(toks):
        status = toks[i].strip()
        if not status:
            i += 1
            continue
        n_paths = 2 if status[:1] in ("R", "C") else 1  # rename/copy: old, new
        paths = [t for t in toks[i + 1:i + 1 + n_paths]]
        i += 1 + n_paths
        if not paths or not paths[-1]:
            continue
        entry: dict = {"path": paths[-1], "status": status[:1]}
        fp = Path(paths[-1])
        if fp.is_file():
            entry["sha256"] = sha256_file(fp)
        files.append(entry)
    return files, patch, len(parents)


def _is_titan_path(path: str) -> bool:
    """True if a changed path is inside the .titan/ tree — the attestation
    machinery itself (receipt chain, vendored tools, key). Used to identify
    receipts-only bookkeeping commits that must not be receipted, which would
    otherwise regress forever. A .gitignore-only or any other change is the
    user's and is still receipted."""
    p = path.replace("\\", "/")
    return p == ".titan" or p.startswith(".titan/")


# ---------------------------------------------------------------- init
def cmd_init(args: argparse.Namespace) -> int:
    root = repo_root()
    if root is None:
        return die("not inside a git repository")
    os.chdir(root)
    use_ssh = getattr(args, "ssh", None) is not None or ALLOWED_SIGNERS.exists()
    if use_ssh:
        return _init_ssh(args, Path(root))
    if KEY_PATH.exists() and not args.force:
        print(f"key exists: {KEY_PATH} (use --force to rotate — old receipts "
              f"then verify only with the OLD key; keep it somewhere safe)")
        if not getattr(args, "no_git_hook", False):
            for w in vendor_tools(Path(root)):
                print(f"vendored: {w}")
            print(install_git_hook(Path(root)))
        return 0
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_text(secrets.token_hex(32) + "\n")
    try:
        KEY_PATH.chmod(0o600)
    except OSError:
        pass  # windows
    _ensure_gitignore()
    # fail-closed: a tracked key is a published key
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(KEY_PATH)],
                             capture_output=True)
    if tracked.returncode == 0:
        KEY_PATH.unlink()
        return die(".titan/key is TRACKED by git — untrack it "
                   "(git rm --cached .titan/key) before generating a key", 1)
    print(f"key written: {KEY_PATH} (never commit it; receipts are only as "
          f"private as this key)")
    if not getattr(args, "no_git_hook", False):
        for w in vendor_tools(Path(root)):
            print(f"vendored: {w}")
        print(install_git_hook(Path(root)))
    return 0


def _resolve_ssh_key(explicit: str) -> Path:
    """--ssh KEY, else git's own SSH signing key (gpg.format=ssh), else the
    usual ~/.ssh keys. Literal `key::` signing keys aren't paths: pass one."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    if git_config("gpg.format") == "ssh":
        sk = git_config("user.signingkey")
        if sk and not sk.startswith(("key::", "ssh-", "ecdsa-", "sk-")):
            return Path(sk).expanduser()
    for name in ("id_ed25519", "id_ecdsa", "id_rsa"):
        for p in (Path.home() / ".ssh" / name, Path.home() / ".ssh" / f"{name}.pub"):
            if p.is_file():
                return p
    raise signing.SigningError("no SSH key found — pass one: /receipt-init --ssh PATH")


def _init_ssh(args: argparse.Namespace, root: Path) -> int:
    """Register this developer's SSH key in .titan/allowed_signers and sign
    from now on with it. Nothing secret is created, and nothing is written
    until a probe signature succeeds without a terminal — the same way the
    hooks will sign."""
    principal = git_config("user.email")
    if not principal:
        return die("set git user.email first — it names you in .titan/allowed_signers")
    try:
        key = _resolve_ssh_key(getattr(args, "ssh", None) or "")
        pub = signing.public_key(key)
        fp = signing.fingerprint(pub)
        signing.ssh_sign(key, b"commitproof init probe")
    except signing.SigningError as exc:
        return die(f"SSH key not usable for receipts: {exc}. A key with a passphrase "
                   f"must be loaded in ssh-agent (ssh-add), because hooks can't prompt.")
    entry = f'{principal} namespaces="{signing.NAMESPACE}" {pub}'
    lines = ALLOWED_SIGNERS.read_text(encoding="utf-8").splitlines() if ALLOWED_SIGNERS.exists() else []
    if any(ln.split()[:1] == [principal] and pub in ln for ln in lines):
        print(f"allowed_signers: already lists {principal} ({fp})")
    else:
        ALLOWED_SIGNERS.parent.mkdir(parents=True, exist_ok=True)
        ALLOWED_SIGNERS.write_text("\n".join([*lines, entry]) + "\n", encoding="utf-8", newline="\n")
        print(f"allowed_signers: added {principal} ({fp})")
    git("config", "--local", CFG_SSH_KEY, str(key))
    git("config", "--local", CFG_PRINCIPAL, principal)
    print(f"signing key: {key} (this clone's git config, never committed)")
    _ensure_gitignore()
    if KEY_PATH.exists():
        print(f"{KEY_PATH} kept: earlier HMAC receipts still verify with it")
    if not getattr(args, "no_git_hook", False):
        for w in vendor_tools(root):
            print(f"vendored: {w}")
        print(install_git_hook(root))
    print(f"Commit {ALLOWED_SIGNERS.as_posix()} with the receipts. There is no secret to share: "
          f"anyone can verify, and each teammate runs /receipt-init --ssh in their own clone.")
    return 0


def _ensure_gitignore() -> None:
    gi = Path(".gitignore")
    text = gi.read_text() if gi.exists() else ""
    for line in (".titan/key", ".titan/tools/__pycache__/"):
        if line not in text.splitlines():
            text = (text.rstrip("\n") + "\n" if text else "") + line + "\n"
            gi.write_text(text)
            print(f"gitignore: added {line}")


# ---------------------------------------------------------- git hook
POST_COMMIT = f"""#!/bin/sh
{HOOK_MARK} — receipt EVERY commit, human or AI. Inside a Claude Code
# session the plugin's PostToolUse hook writes a richer receipt (session,
# model, transcript hash), so defer to it there. Never fails the commit.
if [ -n "$CLAUDECODE" ]; then exit 0; fi
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
if [ -f "$root/.titan/tools/receipt.py" ]; then
  # First Python 3.10+ on PATH: Windows can have python/py but no python3,
  # and its WindowsApps python3 alias only prints a Store message.
  for py in python3 python py; do
    if "$py" -c 'import sys; sys.exit(sys.version_info < (3, 10))' </dev/null >/dev/null 2>&1; then
      "$py" "$root/.titan/tools/receipt.py" create --auto --recorder git-post-commit || true
      break
    fi
  done
fi
exit 0
"""


def vendor_tools(root: Path) -> list[str]:
    """Copy this tool next to the receipts so the git hook (and CI) need no
    plugin installed. Commit .titan/tools/ like code."""
    src_dir = Path(__file__).resolve().parent
    (root / TOOLS_DIR).mkdir(parents=True, exist_ok=True)
    written = []
    for name in ("receipt.py", "canonical.py", "chain_state.py", "signing.py"):
        src = src_dir / name
        if not src.exists():
            continue
        dst = root / TOOLS_DIR / name
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            dst.write_bytes(src.read_bytes())
            written.append(str(TOOLS_DIR / name))
    return written


def install_git_hook(root: Path) -> str:
    """Install (or append to) .git/hooks/post-commit. Returns what happened."""
    try:
        hooks_dir = Path(git("rev-parse", "--git-path", "hooks").strip())
    except RuntimeError:
        hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.is_absolute():
        hooks_dir = root / hooks_dir
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "post-commit"
    if hook.exists():
        existing = hook.read_text()
        marks = (HOOK_MARK, *LEGACY_HOOK_MARKS)
        if any(existing.startswith(f"#!/bin/sh\n{m}") for m in marks) and existing != POST_COMMIT:
            # the whole file is ours, from an older version (python3-only)
            hook.write_text(POST_COMMIT, newline="\n")
            return "git hook: updated .git/hooks/post-commit"
        if any(m in existing for m in marks):
            return "git hook: already installed"
        first = existing.splitlines()[0] if existing.splitlines() else ""
        if first.startswith("#!") and not re.search(r"/(sh|bash|dash|zsh)\b", first):
            return (f"git hook: NOT installed — {hook} is not a shell script ({first}); "
                    f"appending sh would break it. Call "
                    f"`python3 .titan/tools/receipt.py create --auto --recorder git-post-commit` "
                    f"from that hook yourself.")
        tail = [ln.strip() for ln in existing.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if tail and re.match(r"(exit|exec)\b", tail[-1]):
            return (f"git hook: NOT installed — {hook} ends with `{tail[-1]}`, so anything "
                    f"appended after it would never run (common with husky / pre-commit "
                    f"managers). Add this line before it: "
                    f"`python3 \"$(git rev-parse --show-toplevel)/.titan/tools/receipt.py\" "
                    f"create --auto --recorder git-post-commit || true`")
        if "husky" in str(hooks_dir) or "/.husky/" in existing:
            return (f"git hook: NOT installed — {hooks_dir} is husky-managed and regenerated "
                    f"on install; add the receipt line to your husky post-commit hook instead.")
        # append, never clobber someone else's hook
        body = existing.rstrip("\n") + "\n\n" + "\n".join(
            ln for ln in POST_COMMIT.splitlines() if not ln.startswith("#!")) + "\n"
        hook.write_text(body, newline="\n")   # sh scripts: LF on every platform
        action = "git hook: appended to existing post-commit"
    else:
        hook.write_text(POST_COMMIT, newline="\n")
        action = "git hook: installed .git/hooks/post-commit"
    try:
        hook.chmod(hook.stat().st_mode | 0o111)
    except OSError:
        pass
    return action


def cmd_install_hook(args: argparse.Namespace) -> int:
    root = repo_root()
    if root is None:
        return die("not inside a git repository")
    os.chdir(root)
    for w in vendor_tools(root):
        print(f"vendored: {w}")
    msg = install_git_hook(root)
    print(msg)
    if "NOT installed" in msg:
        return 1
    print("Every commit now gets a receipt (ai_assisted true/false). Commit "
          ".titan/tools/ so clones can run `receipt.py install-hook` too — "
          "git hooks themselves are not cloned.")
    return 0


# ---------------------------------------------------------------- create
def _attribution(subject_body: str) -> dict:
    """Copy attribution trailers from the commit message — an ATTESTATION
    by the commit author, recorded verbatim, never invented here."""
    co = CO_AUTHOR_RE.findall(subject_body)
    asst = ASSISTED_RE.findall(subject_body)
    ses = SESSION_RE.findall(subject_body)
    out: dict = {"source": "commit-trailers"}
    if co:
        out["co_authored_by"] = co
    if asst:
        out["assisted_by"] = asst
    if ses:
        out["session"] = ses[0]
    for env in ("CLAUDE_SESSION_ID",):
        if os.environ.get(env):
            out.setdefault("session", os.environ[env])
            out["source"] = "commit-trailers+env"
    return out


def _transcript_facts(path: str | None) -> dict | None:
    """Best-effort facts from a Claude Code session transcript (JSONL):
    model(s) that produced assistant turns, the Claude Code version, line
    count, and a sha256 of the file AS IT WAS when the receipt was written.
    All of this is a recorded claim about a local file — never present it as
    proof of what the model did."""
    if not path:
        return None
    tp = Path(path)
    if not tp.is_file():
        return None
    models: list[str] = []
    version = None
    lines = 0
    h = hashlib.sha256()
    try:
        with open(tp, "rb") as f:
            for raw in f:
                h.update(raw)
                lines += 1
                try:
                    m = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if not isinstance(m, dict):
                    continue
                if isinstance(m.get("version"), str):
                    version = m["version"]
                msg = m.get("message")
                if isinstance(msg, dict):
                    mdl = msg.get("model")
                    if isinstance(mdl, str) and mdl and not mdl.startswith("<") \
                            and mdl not in models:
                        models.append(mdl)
    except OSError:
        return None
    out: dict = {"lines": lines, "content_sha256": h.hexdigest(),
                 "path_sha256": hashlib.sha256(str(tp).encode()).hexdigest()}
    if models:
        out["models"] = models
    if version:
        out["claude_code_version"] = version
    return out


def _provenance(msg: str, recorder: str, hook: dict | None) -> dict:
    """Why we believe this commit was (or wasn't) AI-assisted, and what we
    could record about the tool that assisted. Every field is a recorded
    claim; `basis` says where each came from."""
    ses_trailer = SESSION_RE.findall(msg)
    basis: list[str] = []
    if ai_trailers(msg):
        basis.append("commit-trailers")
    if recorder == "claude-code-hook":
        basis.append("claude-code-hook")
    prov: dict = {
        "ai_assisted": bool(basis),
        "basis": basis,
        "recorder": recorder,
        "recorder_version": PLUGIN_VERSION,
    }
    hook = hook or {}
    # Environment is trusted only when we are demonstrably inside a Claude
    # Code session; a git post-commit hook from a human terminal must never
    # inherit a stale session id from the environment.
    in_claude = bool(os.environ.get("CLAUDECODE"))
    session = hook.get("session_id") or (
        in_claude and (os.environ.get("CLAUDE_CODE_SESSION_ID")
                       or os.environ.get("CLAUDE_SESSION_ID")))
    if session:
        prov["session_id"] = str(session)
    elif ses_trailer:
        prov["session_id"] = ses_trailer[0]
    if hook.get("tool_use_id"):
        prov["tool_use_id"] = str(hook["tool_use_id"])
    if hook.get("permission_mode"):
        prov["permission_mode"] = str(hook["permission_mode"])
    tf = _transcript_facts(hook.get("transcript_path"))
    if tf:
        prov["transcript"] = {k: tf[k] for k in ("lines", "content_sha256", "path_sha256")}
        if "models" in tf:
            prov["models"] = tf["models"]
        if "claude_code_version" in tf:
            prov["claude_code_version"] = tf["claude_code_version"]
    if "claude_code_version" not in prov and in_claude and os.environ.get("CLAUDE_CODE_VERSION"):
        prov["claude_code_version"] = os.environ["CLAUDE_CODE_VERSION"]
    return prov


def cmd_create(args: argparse.Namespace) -> int:
    root = repo_root()
    if root is None:
        return 0 if args.auto else die("not inside a git repository")
    os.chdir(root)
    signer = local_signer()
    if signer is None:
        if args.auto:
            return 0  # hook mode: repo not initialized — silently do nothing
        return die("no signing set up in this clone — run receipt.py init first (or init --ssh)")
    key = None
    if signer[0] == "hmac" and ALLOWED_SIGNERS.exists():
        # verify treats HMAC after the move to SSH as a downgrade; don't write one
        try:
            head = git("rev-parse", "HEAD").strip()
        except RuntimeError:
            head = "(none yet)"
        return _signing_failed(args, head,
                               f"this repo signs receipts with SSH ({ALLOWED_SIGNERS.as_posix()}) "
                               f"and this clone has only the old HMAC key; run "
                               f"/receipt-init --ssh here")
    if signer[0] == "hmac":
        key = load_key()
        if key is None:
            return 1  # a corrupt key is a loud failure even in --auto (|| true
                      # protects the commit; silence would hide a broken setup)

    try:
        sha = git("rev-parse", "HEAD").strip()
        branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
        msg = git("log", "-1", "--format=%B", "HEAD")
        author = git("log", "-1", "--format=%an <%ae>", "HEAD").strip()
        committed_at = git("log", "-1", "--format=%cI", "HEAD").strip()
        subject = msg.splitlines()[0] if msg.splitlines() else ""
        files, patch, n_parents = changed_files(sha)
    except RuntimeError as exc:
        return 0 if args.auto else die(str(exc))

    # Receipts-only commits: a commit whose every changed path is under
    # .titan/ (the attestation chain and vendored tools) is bookkeeping, not
    # a code change to attest. Receipting it in
    # hook mode causes an unbounded regress — committing the receipts fires the
    # hook, which writes a new receipt, which dirties the tree again, so the
    # "all receipts committed and pushed" clean anchor can never be reached.
    # The auto hook therefore skips such commits; a manual `/receipt` still
    # records one if the user explicitly asks.
    if args.auto and files and all(_is_titan_path(f["path"]) for f in files):
        return 0

    # skip duplicates (hook may fire twice; amend re-fires): one receipt per sha
    if TREE.exists():
        for p in TREE.rglob("*.json"):
            try:
                if json.loads(p.read_text()).get("commit", {}).get("sha") == sha:
                    if not args.auto:
                        print(f"receipt already exists for {sha[:12]} ({p})")
                    return 0
            except (json.JSONDecodeError, OSError):
                return die(f"unreadable receipt in tree: {p}", 1)

    try:
        prev = latest_receipt_hash(TREE)
    except ChainStateError as exc:
        return die(f"refusing to extend a broken chain: {exc}", 1)

    now = datetime.now(timezone.utc)
    receipt: dict = {
        "schema_version": SCHEMA,
        "signing_version": signing.SSH_V1 if signer[0] == "ssh" else signing.HMAC_V1,
        "receipt_id": str(uuid.uuid4()),
        "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root_date": now.strftime("%Y-%m-%d"),
        "repo": Path(root).name,
        "commit": {"sha": sha, "branch": branch, "subject": subject[:200],
                   "parents": n_parents, "author": author,
                   "committed_at": committed_at},
        "files": files,
        "diff_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "attribution": _attribution(msg),
        "provenance": _provenance(msg, getattr(args, "recorder", "manual") or "manual",
                                  getattr(args, "hook_payload", None)),
        "prev_receipt_hash": prev,
    }
    try:
        if signer[0] == "ssh":
            # who signed is part of the hashed content: swapping it breaks the chain
            receipt["signer"] = {"principal": signer[2] or "",
                                 "key": signing.fingerprint(signing.public_key(signer[1]))}
        receipt["receipt_hash"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
        message = receipt["receipt_hash"].encode()
        receipt["signature"] = (signing.ssh_sign(signer[1], message) if signer[0] == "ssh"
                                else signing.hmac_sign(key, message))
    except signing.SigningError as exc:
        return _signing_failed(args, sha, str(exc))

    out = TREE / receipt["root_date"] / f"{receipt['receipt_id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    ai = "ai-assisted" if receipt["provenance"]["ai_assisted"] else "human"
    print(f"receipt: {out}  commit {sha[:12]}  {ai}  prev "
          f"{prev[:12] if prev != GENESIS else GENESIS}")
    return 0


def _signing_failed(args: argparse.Namespace, sha: str, why: str) -> int:
    """No receipt is better than an unsigned one, but a missing receipt must
    never be silent. In the Claude Code hook, stderr on exit 0 reaches nobody,
    so tell the user with a systemMessage; elsewhere, fail loudly."""
    text = (f"CommitProof: couldn't sign the receipt for commit {sha[:12]}, so it has "
            f"no receipt. {why}. If your SSH key has a passphrase, load it with "
            f"`ssh-add`; /receipt-init --ssh re-checks the setup.")
    if getattr(args, "hook_payload", None) is not None:
        print(json.dumps({"systemMessage": text, "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text + " Tell the user once; don't retry or work "
                                        "around it — signing is their key's decision."}}))
        return 0
    return die(text, 1)


# ---------------------------------------------------------------- hook
# A `git commit` invocation inside ONE shell segment (split on ; && || |):
# `git log | grep commit` and `git status; echo commit` must not match.
GIT_COMMIT_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:\w+=\S*\s+)*git(?:\s+-[-\w=./:]+(?:\s+[^\s-][\w=./:@]*)?)*\s+commit\b")


def cmd_hook(args: argparse.Namespace) -> int:
    """Claude Code PostToolUse entry point. Hook matchers match TOOL NAMES
    only (docs: hooks reference) — a matcher like 'Bash\\(.*commit' NEVER
    fires because the tool name is just 'Bash'. So hooks.json matches every
    Bash call and this reads the hook JSON from stdin to act only on git
    commits. False positives are harmless (create --auto dedupes per sha);
    false negatives lose receipts — so the filter is deliberately loose."""
    try:
        payload = json.load(sys.stdin)
        cmd = (payload.get("tool_input") or {}).get("command") or ""
    except (json.JSONDecodeError, AttributeError, ValueError):
        return 0  # unparseable hook input: never break anything
    if not isinstance(cmd, str) or not GIT_COMMIT_RE.search(cmd):
        return 0
    # A receipt written here CLAIMS the commit was made in this session
    # (basis: claude-code-hook). So the commit must actually have happened:
    # the command must have succeeded, and HEAD must be newer than the hook
    # invocation window — a failed `git commit` ("nothing to commit", hook
    # rejected) must not receipt the human's existing HEAD as AI-assisted.
    if not _commit_succeeded(payload):
        return 0
    root = repo_root()
    if root is not None and not (root / KEY_PATH).exists() and not git_config(CFG_SSH_KEY):
        _first_run_notice(root)   # uninitialized: tell the user once, then stay silent
        return 0
    args.auto = True
    args.recorder = "claude-code-hook"
    args.hook_payload = payload if isinstance(payload, dict) else None
    return cmd_create(args)


NOTICE_USER = (
    "CommitProof: this commit was NOT receipted — receipts aren't set up in "
    "this repo yet. /ai-history shows how much of this repo Claude already "
    "co-wrote (no setup). Run /receipt-init once to start a tamper-evident audit "
    "trail of every commit (AI-assisted or not). Shown once per repo; silence "
    "with COMMITPROOF_QUIET=1.")
NOTICE_CLAUDE = (
    "CommitProof is installed but not initialized in this repository, so the "
    "commit that just succeeded has no receipt. The user has already been shown a "
    "one-time notice naming /receipt-init. Do not run /receipt-init or "
    "`receipt.py init` yourself: it creates a signing key and installs a git hook, "
    "which is the user's decision. Do not repeat the notice unless the user asks "
    "about receipts, audit trails, or AI provenance; if they do, /receipt-init is "
    "the one-time setup.")


def _state_dir() -> Path:
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data:
        return Path(data)
    return Path.home() / ".titan-receipts"


def _first_run_notice(root: Path) -> None:
    """Emit the setup notice at most once per repository. The record lives in
    the plugin's own data dir — never inside the user's repo. If the record
    can't be written, say nothing: an unrecordable notice would repeat on every
    commit, and nagging is worse than silence. Never raises."""
    if os.environ.get("COMMITPROOF_QUIET") or os.environ.get("TITAN_RECEIPTS_QUIET"):
        return
    try:
        key = hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:32]
        marker = _state_dir() / "notified" / key
        marker.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(str(Path(root).resolve()) + "\n")
    except OSError:
        return  # already notified (FileExistsError) or nowhere to record it
    print(json.dumps({
        "systemMessage": NOTICE_USER,
        "hookSpecificOutput": {"hookEventName": "PostToolUse",
                               "additionalContext": NOTICE_CLAUDE},
    }))


def _commit_succeeded(payload: dict) -> bool:
    resp = payload.get("tool_response")
    text = ""
    if isinstance(resp, dict):
        for k in ("exit_code", "exitCode", "returncode", "code"):
            if k in resp and resp[k] not in (None, 0, "0"):
                return False
        if resp.get("interrupted") is True:
            return False
        text = " ".join(str(resp.get(k, "")) for k in ("stdout", "stderr", "output", "content"))
    elif isinstance(resp, str):
        text = resp
    if re.search(r"nothing to commit|no changes added to commit|Aborting commit|"
                 r"nothing added to commit|did not match any|fatal:|error:", text):
        return False
    # HEAD must be recent: committed within the last 10 minutes.
    try:
        ts = int(git("log", "-1", "--format=%ct", "HEAD").strip())
    except (RuntimeError, ValueError):
        return False
    import time
    return (time.time() - ts) < 600


# ---------------------------------------------------------------- verify
def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    if root is not None:
        os.chdir(root)
    if not TREE.exists() or not any(TREE.rglob("*.json")):
        return die("no attestations at .titan/attestations/ — nothing to verify")
    structure_only = getattr(args, "structure_only", False)

    # Structure first: it needs no key, so a clone that has the attestations
    # but not the (correctly gitignored) key still gets a real answer.
    try:
        head = latest_receipt_hash(TREE)  # full structural walk, fail-closed
    except ChainStateError as exc:
        print(f"CHAIN FAIL: {exc}", file=sys.stderr)
        return 1
    n = sum(1 for _ in TREE.rglob("*.json"))

    if structure_only:
        # Explicitly asked to skip signatures — an intended check, not a failure.
        print(f"chain OK (structure only): {n} receipt(s), head {head[:12]}…")
        print("NOT CHECKED: signatures — no key was used. This proves the "
              "receipts are internally consistent and unaltered relative to "
              "their own hashes, not that they were signed by the key holder.")
        _report_anchor()
        return 0

    public_only = getattr(args, "public_only", False)
    if KEY_PATH.exists() and not public_only and load_key() is None:
        return 2   # corrupt key: load_key printed why
    rows = check_signatures([(p, json.loads(p.read_text())) for p in sorted(TREE.rglob("*.json"))],
                            _allowed_signers(args), use_hmac=not public_only)
    bad = [row for row in rows if row[2] == "invalid"]
    for p, _r, _s, detail in bad:
        print(f"SIG FAIL: {p} ({detail})", file=sys.stderr)
    if bad:
        print(f"VERDICT: FAIL — {len(bad)}/{n} bad signatures", file=sys.stderr)
        return 1
    s = summarize(rows)
    if s["ssh_ok"]:
        print(f"SSH signatures: {sum(s['ssh_ok'].values())} valid against "
              f"{_allowed_signers(args).as_posix()} — signed by "
              + ", ".join(f"{who} ({c})" for who, c in sorted(s["ssh_ok"].items())))
    if s["hmac_ok"]:
        print(f"HMAC signatures: {s['hmac_ok']} valid under {KEY_PATH.as_posix()} "
              f"(a shared secret: these don't identify who signed)")
    if s["ssh_unchecked"]:
        print(f"SSH SIGNATURES NOT CHECKED: {len(s['ssh_unchecked'])} receipt(s) — "
              f"{s['ssh_unchecked'][0][3]}", file=sys.stderr)
    pinned = bool(getattr(args, "allowed_signers", None))
    if s["hmac_unchecked"] and public_only and pinned:
        # a pinned signer list is a policy: every receipt must be checkable
        print(f"NOT CHECKED: {len(s['hmac_unchecked'])} HMAC signature(s), and with a pinned "
              f"--allowed-signers a receipt that can't be checked fails. Provide the HMAC "
              f"key, or verify without pinning.", file=sys.stderr)
        _report_anchor()
        return 2
    if s["hmac_unchecked"] and public_only:
        print(f"NOT CHECKED: {len(s['hmac_unchecked'])} HMAC signature(s) — they need the "
              f"shared {KEY_PATH.as_posix()}, which --public-only doesn't use")
    elif s["hmac_unchecked"]:
        # F-T3: no key, and structure-only was not requested (e.g. a fresh
        # clone) — say exactly what was and wasn't checked, then fail closed.
        # Structure alone is useful information, not a PASS.
        print(f"chain structure OK: {n} receipt(s), one unbroken line from "
              f"GENESIS, every stored receipt_hash matches its content, head {head[:12]}…")
        print(f"SIGNATURES NOT CHECKED: {len(s['hmac_unchecked'])} HMAC receipt(s) and no "
              f".titan/key in this checkout (it is gitignored by design). Structure alone "
              f"proves the files are internally consistent, not that they were signed under "
              f"the team's key. Obtain the key out-of-band to verify signatures.",
              file=sys.stderr)
    if s["ssh_unchecked"] or (s["hmac_unchecked"] and not public_only):
        _report_anchor()
        return 2
    print(f"chain OK{' (public signatures only)' if s['hmac_unchecked'] else ''}: "
          f"{n} receipt(s), head {head[:12]}…")
    if s["ssh_ok"]:
        print(f"PASS means: contents unchanged since signing, and each SSH signature "
              f"was made by the key {ALLOWED_SIGNERS.as_posix()} lists for its signer.")
    if s["hmac_ok"]:
        print("PASS means: contents unchanged since signing, under this shared "
              "key. It does not identify the signer.")
    _report_anchor()
    return 0


def _allowed_signers(args: argparse.Namespace) -> Path:
    """--allowed-signers lets a verifier (CI) pin who may sign instead of
    trusting the file in the repo under audit."""
    given = getattr(args, "allowed_signers", None)
    return Path(given) if given else ALLOWED_SIGNERS


def check_signatures(rows: list[tuple[Path, dict]], allowed: Path,
                     use_hmac: bool = True) -> list[tuple[Path, dict, str, str]]:
    """One verdict per receipt: (path, receipt, valid|invalid|unchecked, detail)."""
    hmac_key = load_key() if use_hmac and KEY_PATH.exists() else None
    needs_ssh = any(r.get("signing_version") == signing.SSH_V1 for _, r in rows)
    with signing.SshVerifier(allowed if needs_ssh else None) as ssh:
        out = [(p, r, *signing.check(r, hmac_key, ssh)) for p, r in rows]
    # No downgrade: once the chain moved to SSH, a later HMAC receipt is how
    # someone without a registered key would slip past --public-only (HMAC is
    # skipped there). Order comes from the chain's own prev links, which a
    # forger can't reorder without breaking later SSH signatures.
    seen_ssh = False
    rank = {id(r): i for i, r in enumerate(chain_order([r for _, r in rows]))}
    for i in sorted(range(len(out)), key=lambda i: rank.get(id(out[i][1]), len(out))):
        p, r, st, detail = out[i]
        if r.get("signing_version") == signing.SSH_V1:
            seen_ssh = True
        elif seen_ssh:
            out[i] = (p, r, "invalid", "HMAC receipt after the chain moved to SSH: "
                                       "signature downgrade")
    return out


def chain_order(rs: list[dict]) -> list[dict]:
    """Receipts from GENESIS forward by their prev links. A broken chain (it
    already fails structure) yields what is reachable, then the rest."""
    by_prev = {r.get("prev_receipt_hash"): r for r in rs}
    ordered, cur, seen = [], GENESIS, set()
    while cur in by_prev and cur not in seen:
        seen.add(cur)
        nxt = by_prev[cur]
        ordered.append(nxt)
        cur = nxt.get("receipt_hash")
    return ordered + [r for r in rs if all(r is not o for o in ordered)]


def summarize(rows: list[tuple[Path, dict, str, str]]) -> dict:
    def is_ssh(r: dict) -> bool:
        return r.get("signing_version") == signing.SSH_V1
    ssh_ok: dict[str, int] = {}
    for _, r, st, who in rows:
        if st == "valid" and is_ssh(r):
            ssh_ok[who] = ssh_ok.get(who, 0) + 1
    return {"ssh_ok": ssh_ok,
            "hmac_ok": sum(1 for _, r, st, _ in rows if st == "valid" and not is_ssh(r)),
            "ssh_unchecked": [x for x in rows if x[2] == "unchecked" and is_ssh(x[1])],
            "hmac_unchecked": [x for x in rows if x[2] == "unchecked" and not is_ssh(x[1])],
            "invalid": [x for x in rows if x[2] == "invalid"]}


# ---------------------------------------------------------------- report
def _load_tree() -> list[dict]:
    out = []
    for p in sorted(TREE.rglob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            raise RuntimeError(f"unreadable receipt: {p}")
    return out


def cmd_report(args: argparse.Namespace) -> int:
    root = repo_root()
    if root is not None:
        os.chdir(root)
    if not TREE.exists() or not any(TREE.rglob("*.json")):
        return die("no attestations at .titan/attestations/ — nothing to report")
    try:
        rs = _load_tree()
    except RuntimeError as exc:
        return die(str(exc), 1)

    # verification result is part of the report — a report on an unverified
    # chain would be exactly the kind of document this tool exists to prevent
    try:
        latest_receipt_hash(TREE)
        chain = "intact"
    except ChainStateError as exc:
        chain = f"BROKEN — {exc}"
    allowed = _allowed_signers(args)
    rows = check_signatures([(Path(str(r.get("receipt_id", "?"))), r) for r in rs], allowed)
    sigs = summarize(rows)
    bad_sig = len(sigs["invalid"])
    ssh_rs = [r for r in rs if r.get("signing_version") == signing.SSH_V1]
    n_ssh, n_hmac = len(ssh_rs), len(rs) - len(ssh_rs)
    all_checked = not sigs["ssh_unchecked"] and not sigs["hmac_unchecked"]

    def prov(r: dict) -> dict:
        return r.get("provenance") or {}

    total = len(rs)

    def legacy_ai(r: dict) -> bool:   # v1.0 receipt: only the trailers can tell
        co = (r.get("attribution") or {}).get("co_authored_by") or []
        return any(AI_TRAILER_RE.search(c) for c in co) or bool((r.get("attribution") or {}).get("session"))

    ai = [r for r in rs if prov(r).get("ai_assisted") or (not prov(r) and legacy_ai(r))]
    unknown = [r for r in rs if not prov(r) and not legacy_ai(r)]   # v1.0, no AI trailer: can't say
    by_recorder: dict[str, int] = {}
    by_author: dict[str, list[int]] = {}
    by_month: dict[str, list[int]] = {}
    models: dict[str, int] = {}
    versions: dict[str, int] = {}
    for r in rs:
        rec = prov(r).get("recorder", "unknown (v1.0 receipt)")
        by_recorder[rec] = by_recorder.get(rec, 0) + 1
        a = (r.get("commit") or {}).get("author", "unknown (v1.0 receipt)")
        is_ai = r in ai
        by_author.setdefault(a, [0, 0])
        by_author[a][0] += 1
        by_author[a][1] += int(is_ai)
        month = (r.get("root_date") or "????-??")[:7]
        by_month.setdefault(month, [0, 0])
        by_month[month][0] += 1
        by_month[month][1] += int(is_ai)
        for m in prov(r).get("models", []):
            models[m] = models.get(m, 0) + 1
        v = prov(r).get("claude_code_version")
        if v:
            versions[v] = versions.get(v, 0) + 1

    def pct(n: int, d: int) -> str:
        return f"{100.0 * n / d:.0f}%" if d else "–"

    L: list[str] = []
    L.append(f"# AI-assisted change receipts — {Path.cwd().name}")
    L.append("")
    L.append(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
             f"by commitproof {PLUGIN_VERSION} from `.titan/attestations/`.")
    L.append("")
    L.append("## Verification")
    L.append("")
    L.append(f"- Chain structure (single unbroken line from GENESIS, content hashes recomputed): **{chain}**")
    def sig_state(want_ssh: bool, unchecked: list, n_kind: int) -> str:
        bad = sum(1 for _, r, st, _ in rows
                  if st == "invalid" and (r.get("signing_version") == signing.SSH_V1) == want_ssh)
        if bad:
            return f"**{bad}/{n_kind} INVALID**"
        if unchecked:
            return f"**not checked** ({unchecked[0][3]})"
        return "**all valid**"

    if n_ssh:
        L.append(f"- Signatures (SSH, each against its signer's key in `{allowed.as_posix()}`): "
                 + sig_state(True, sigs["ssh_unchecked"], n_ssh))
    if n_hmac:
        if sigs["hmac_unchecked"]:
            L.append("- Signatures (HMAC-SHA256 under the repo key): **not checked** "
                     "(no key available where this report was generated)")
        else:
            L.append("- Signatures (HMAC-SHA256 under the repo key): "
                     + sig_state(False, [], n_hmac))
    if n_ssh:
        signed: dict[tuple[str, str], int] = {}
        for r in ssh_rs:
            who = r.get("signer") or {}
            k = (str(who.get("principal", "?")), str(who.get("key", "?")))
            signed[k] = signed.get(k, 0) + 1
        L += ["", "## Signed by", "", "| signer | SSH key | receipts |", "|---|---|---|"]
        for (who, fp), c in sorted(signed.items(), key=lambda kv: -kv[1]):
            L.append(f"| {who} | `{fp}` | {c} |")
        if n_hmac:
            L.append(f"| shared repo key (HMAC: doesn't identify a signer) | – | {n_hmac} |")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append(f"| | count | share |\n|---|---|---|")
    L.append(f"| Receipted commits | {total} | |")
    L.append(f"| AI-assisted (per recorded basis) | {len(ai)} | {pct(len(ai), total)} |")
    L.append(f"| Not AI-assisted | {total - len(ai) - len(unknown)} | {pct(total - len(ai) - len(unknown), total)} |")
    if unknown:
        L.append(f"| Unknown (v1.0 receipts without provenance) | {len(unknown)} | {pct(len(unknown), total)} |")
    L.append("")
    L.append("## By recorder")
    L.append("")
    L.append("| recorder | receipts |\n|---|---|")
    for k, v in sorted(by_recorder.items()):
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## By author")
    L.append("")
    L.append("| author | commits | AI-assisted |\n|---|---|---|")
    for k, (n, a) in sorted(by_author.items(), key=lambda kv: -kv[1][0]):
        L.append(f"| {k} | {n} | {a} ({pct(a, n)}) |")
    L.append("")
    L.append("## By month")
    L.append("")
    L.append("| month | commits | AI-assisted |\n|---|---|---|")
    for k, (n, a) in sorted(by_month.items()):
        L.append(f"| {k} | {n} | {a} ({pct(a, n)}) |")
    if models or versions:
        L.append("")
        L.append("## Tooling recorded")
        L.append("")
        for m, n in sorted(models.items(), key=lambda kv: -kv[1]):
            L.append(f"- model `{m}`: {n} receipt(s)")
        for v, n in sorted(versions.items(), key=lambda kv: -kv[1]):
            L.append(f"- Claude Code `{v}`: {n} receipt(s)")
    L.append("")
    L.append("## What this report proves — and does not")
    L.append("")
    who_signed = []
    if n_ssh:
        who_signed.append(
            f"SSH-signed receipts were each signed by the key `{ALLOWED_SIGNERS.as_posix()}` "
            "lists for the named signer: that identifies the key, not who controls it, and "
            "the key-to-person mapping is only as trustworthy as that file's history.")
    if n_hmac:
        who_signed.append("For HMAC-signed receipts it does **not** prove who held "
                          "the key (HMAC is a shared secret).")
    L.append("Each receipt records a commit's changed-file hashes, diff hash, author, "
             "and provenance claims, hash-chained to the previous receipt and signed. "
             "An intact chain with valid signatures means the recorded history has not been "
             "altered since signing. " + " ".join(who_signed) + " It does **not** prove that "
             "any change was reviewed, or that the AI-assistance claims are true — "
             "`ai_assisted` comes from commit trailers and from "
             "the Claude Code hook that wrote the receipt, and model/version/transcript fields "
             "are what that tool observed locally. Commits made outside both the Claude Code "
             "hook and the git post-commit hook have no receipt and are not counted.")
    text = "\n".join(L) + "\n"
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"report: {args.out}")
    else:
        sys.stdout.write(text)
    if getattr(args, "badge", None):
        # a share is shown only beside a verification that passed
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if chain != "intact" or bad_sig:
            value, color = "verification FAILED", BADGE_RED
        elif all_checked:
            value, color = f"{pct(len(ai), total)} · chain verified", BADGE_BLUE
        elif sigs["ssh_ok"] or sigs["hmac_ok"]:
            value, color = f"{pct(len(ai), total)} · partly verified", BADGE_GREY
        else:
            value, color = f"{pct(len(ai), total)} · structure only", BADGE_GREY
        snippet = write_badge(args.badge, value, color,
                              f"{len(ai)} of {total} receipted commits, as of {today}")
        print(snippet, file=sys.stdout if getattr(args, "out", None) else sys.stderr)
    return 0


# ----------------------------------------------------------------- badge
HOMEPAGE = "https://github.com/Rmasood1122/commitproof"   # = plugin.json homepage (tested)
BADGE_BLUE, BADGE_GREY, BADGE_RED = "#007ec6", "#6c757d", "#e05d44"


def write_badge(path: str, value: str, color: str, title: str) -> str:
    """Write a self-contained shields-style SVG — no badge service, so
    nothing phones home — and return the README snippet that shows it,
    linking back to this plugin."""
    label = "AI-assisted"

    def width(s: str) -> int:   # Verdana 11px measures ~5.6–6.3px a glyph here
        return int(len(s) * 6.5) + 10

    lw, vw = width(label), width(value)
    e = html.escape
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{lw + vw}" height="20" '
        f'role="img" aria-label="{e(label)}: {e(value)}">'
        f'<title>{e(title)}</title>'
        f'<clipPath id="r"><rect width="{lw + vw}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#555"/>'
        f'<rect x="{lw}" width="{vw}" height="20" fill="{color}"/></g>'
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
        f'font-size="11"><text x="{lw / 2:.1f}" y="14">{e(label)}</text>'
        f'<text x="{lw + vw / 2:.1f}" y="14">{e(value)}</text></g></svg>\n')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(svg, encoding="utf-8", newline="\n")
    return (f"badge: {path}\nREADME: [![{label}: {value}]({Path(path).as_posix()})]"
            f"({HOMEPAGE} \"{title}\")")


# --------------------------------------------------------------- history
def _scan_history(since: str | None) -> list[tuple[str, str, bool, int]]:
    """(author, month, has_claude_trailer, lines_added) per non-merge commit.
    Lines under .titan/ are receipt bookkeeping, not work, and are skipped."""
    cmd = ["log", "--no-merges", "--numstat",
           "--format=%x1e%H%x1f%an <%ae>%x1f%cI%x1f%B%x1d"]
    if since:
        cmd.append(f"--since={since}")
    out = []
    for rec in git(*cmd).split("\x1e")[1:]:
        head, _, stat = rec.partition("\x1d")
        parts = head.split("\x1f", 3)
        if len(parts) < 4:
            continue
        _sha, author, when, body = parts
        added = 0
        for line in stat.splitlines():
            cols = line.split("\t", 2)
            if len(cols) == 3 and cols[0].isdigit() and not _is_titan_path(cols[2]):
                added += int(cols[0])
        out.append((author, when[:7], ai_trailers(body), added))
    return out


def cmd_history(args: argparse.Namespace) -> int:
    """How much of this repo did Claude help write — answered from the commit
    trailers already in git history. Zero setup: reads git, writes nothing,
    needs no key. Unsigned by nature, and says so; receipts are the signed
    record from /receipt-init onward."""
    root = repo_root()
    if root is None:
        return die("not inside a git repository")
    os.chdir(root)
    try:
        git("rev-parse", "--verify", "-q", "HEAD")
    except RuntimeError:
        print("No commits yet — nothing to scan.")
        return 0
    try:
        rows = _scan_history(getattr(args, "since", None))
    except RuntimeError as exc:
        return die(str(exc))
    if not rows:
        print("No non-merge commits in range — nothing to scan.")
        return 0

    n = len(rows)
    n_ai = sum(1 for r in rows if r[2])
    lines = sum(r[3] for r in rows)
    lines_ai = sum(r[3] for r in rows if r[2])
    initialized = KEY_PATH.exists() or ALLOWED_SIGNERS.exists() or bool(git_config(CFG_SSH_KEY))
    if getattr(args, "json", False):
        print(json.dumps({"repo": Path(root).name, "commits": n, "ai_commits": n_ai,
                          "lines_added": lines, "ai_lines_added": lines_ai,
                          "since": getattr(args, "since", None),
                          "basis": "commit-trailers", "signed": False}, indent=2))
        return 0

    def pct(a: int, d: int) -> str:
        return f"{100.0 * a / d:.0f}%" if d else "–"

    def tally(key) -> dict[str, list[int]]:
        t: dict[str, list[int]] = {}
        for r in rows:
            t.setdefault(key(r), [0, 0])
            t[key(r)][0] += 1
            t[key(r)][1] += int(r[2])
        return t

    L = [f"# How much of {Path(root).name} did Claude help write?", "",
         "Read from the commit trailers already in this repo's git history "
         "(`Co-Authored-By: Claude …`, `Assisted-by: Claude…`, `Claude-Session:`). No setup, no key, "
         "nothing written — and **unsigned**: a starting estimate, not evidence.", "",
         "| | commits | lines added |", "|---|---|---|",
         f"| Scanned (non-merge) | {n} | {lines} |",
         f"| With a Claude trailer | {n_ai} ({pct(n_ai, n)}) | {lines_ai} ({pct(lines_ai, lines)}) |",
         "", "## By author", "",
         "| author | commits | with a Claude trailer |", "|---|---|---|"]
    authors = sorted(tally(lambda r: r[0]).items(), key=lambda kv: -kv[1][0])
    for k, (c, a) in authors[:15]:
        L.append(f"| {k} | {c} | {a} ({pct(a, c)}) |")
    if len(authors) > 15:
        c = sum(v[0] for _, v in authors[15:])
        a = sum(v[1] for _, v in authors[15:])
        L.append(f"| {len(authors) - 15} other authors | {c} | {a} ({pct(a, c)}) |")
    L += ["", "## By month", "",
          "| month | commits | with a Claude trailer |", "|---|---|---|"]
    months = sorted(tally(lambda r: r[1]).items())
    if len(months) > 12:
        c = sum(v[0] for _, v in months[:-12])
        a = sum(v[1] for _, v in months[:-12])
        L.append(f"| before {months[-12][0]} | {c} | {a} ({pct(a, c)}) |")
    for k, (c, a) in months[-12:]:
        L.append(f"| {k} | {c} | {a} ({pct(a, c)}) |")
    L += ["", "## What this does and doesn't tell you", "",
          "It counts commits whose message carries a Claude trailer, and the lines "
          "added in those commits — not which lines Claude typed. Trailers are plain "
          "text: anyone can add or delete them, and history can be rewritten. Claude-"
          "assisted commits whose trailer was dropped (or squash-merged without it) "
          "count as not AI-assisted. A starting estimate, not evidence.", ""]
    if initialized:
        L.append("**Signed view:** receipts are on in this repo — `/receipt-report` "
                 "covers every commit since `/receipt-init` with chain and signature "
                 "verification.")
    else:
        L.append("**Make it evidence from here on:** `/receipt-init` gives every new "
                 "commit a hash-chained, signed receipt, so a later rewrite of this "
                 "record shows up in `/verify-chain`.")
    sys.stdout.write("\n".join(L) + "\n")
    if getattr(args, "badge", None):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(write_badge(args.badge, f"{pct(n_ai, n)} of commits · unsigned", BADGE_GREY,
                          f"{n_ai} of {n} commits carry a Claude trailer, as of {today} "
                          f"(unsigned, from git history)"), file=sys.stderr)
    return 0


# ---------------------------------------------------------------- anchor
def anchor_status() -> dict:
    """How much of .titan/attestations/ exists outside this working tree.

    HMAC is a shared secret, so the key-holder can rewrite and re-sign the
    whole chain locally and `verify` cannot tell. The defence the README
    promises is DISTRIBUTION: once receipts are committed and pushed, every
    clone holds an independent copy a rewrite would have to chase down.
    This measures whether that defence is actually in place.

    Returns counts: total, untracked, modified (tracked but dirty), unpushed
    (committed locally, not on the upstream), plus `upstream` (name or None).
    Never raises — a repo with no remote just reports unpushed=unknown.
    """
    files = sorted(str(p) for p in TREE.rglob("*.json"))
    out = {"total": len(files), "untracked": 0, "modified": 0,
           "unpushed": None, "upstream": None}
    if not files:
        return out
    st = subprocess.run(["git", "status", "--porcelain", "--", str(TREE)],
                        capture_output=True, text=True, encoding="utf-8")
    for line in st.stdout.splitlines():
        code = line[:2]
        if code == "??":
            out["untracked"] += 1
        elif code.strip():
            out["modified"] += 1
    up = subprocess.run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                        capture_output=True, text=True, encoding="utf-8")
    if up.returncode != 0:
        return out  # no upstream configured: cannot know what is pushed
    out["upstream"] = up.stdout.strip()
    # receipt files touched by commits that are ahead of upstream
    ahead = subprocess.run(["git", "diff", "--name-only", f"{out['upstream']}...HEAD",
                            "--", str(TREE)], capture_output=True, text=True, encoding="utf-8")
    out["unpushed"] = len([l for l in ahead.stdout.splitlines() if l.strip()])
    return out


def _report_anchor() -> None:
    a = anchor_status()
    if a["total"] == 0:
        return
    loose = a["untracked"] + a["modified"] + (a["unpushed"] or 0)
    if a["upstream"] is None:
        print(f"ANCHOR: no upstream remote — {a['total']} receipt(s) exist only in "
              f"this working tree. Against the key-holder, a local-only chain is a "
              f"claim, not evidence: commit and push .titan/attestations/.",
              file=sys.stderr)
    elif loose == 0:
        print(f"ANCHOR: all {a['total']} receipt(s) committed and pushed to "
              f"{a['upstream']} — every clone holds an independent copy.")
    else:
        parts = []
        if a["untracked"]:
            parts.append(f"{a['untracked']} untracked")
        if a["modified"]:
            parts.append(f"{a['modified']} modified-uncommitted")
        if a["unpushed"]:
            parts.append(f"{a['unpushed']} committed-not-pushed")
        print(f"ANCHOR: {', '.join(parts)} of {a['total']} receipt(s) are not on "
              f"{a['upstream']}. Until pushed they are only as trustworthy as this "
              f"machine: `git add .titan/attestations && git commit && git push`.",
              file=sys.stderr)


def main() -> int:
    # A piped stdout on Windows defaults to the locale codepage (cp1252): '—'
    # reached Claude Code as invalid UTF-8 and a non-Latin author name raised
    # UnicodeEncodeError mid-report. Callers (Claude Code, git, CI) read UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--force", action="store_true")
    p.add_argument("--ssh", nargs="?", const="", default=None, metavar="KEY",
                   help="sign with your SSH key (default: git's SSH signing key, "
                        "else ~/.ssh/id_ed25519) and register it in .titan/allowed_signers")
    p.add_argument("--no-git-hook", action="store_true",
                   help="do not vendor tools / install the git post-commit hook")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("install-hook"); p.set_defaults(fn=cmd_install_hook)
    p = sub.add_parser("create"); p.add_argument("--auto", action="store_true")
    p.add_argument("--recorder", default="manual",
                   choices=["manual", "claude-code-hook", "git-post-commit"])
    p.set_defaults(fn=cmd_create, hook_payload=None)
    p = sub.add_parser("hook"); p.set_defaults(fn=cmd_hook, auto=True, recorder="claude-code-hook",
                                               hook_payload=None)
    p = sub.add_parser("verify"); p.add_argument("--structure-only", action="store_true")
    p.add_argument("--public-only", action="store_true",
                   help="check SSH signatures, skip HMAC ones (verification with no secret)")
    p.add_argument("--allowed-signers", metavar="FILE",
                   help="trust this allowed_signers file instead of the repo's")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("report"); p.add_argument("--out")
    p.add_argument("--badge", help="also write a README badge SVG here")
    p.add_argument("--allowed-signers", metavar="FILE",
                   help="trust this allowed_signers file instead of the repo's")
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("history"); p.add_argument("--since", help="e.g. 2026-01-01 or '6 months ago'")
    p.add_argument("--json", action="store_true", help="machine-readable summary")
    p.add_argument("--badge", help="also write a README badge SVG here")
    p.set_defaults(fn=cmd_history)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
