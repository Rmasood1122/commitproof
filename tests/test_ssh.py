"""v1.4: SSH signing — receipts that say WHO signed, verifiable with no secret.

HMAC receipts carry the caveat that anyone holding the shared .titan/key can
forge any receipt, and a fresh clone can't check signatures at all. With
`init --ssh`, each receipt is signed by the committer's own SSH key
(`ssh-keygen -Y sign`, namespace commitproof-receipt) and verified against
the public keys in the committed .titan/allowed_signers. Every "must" below
is a test: a signature only verifies for the key listed for its signer, the
signer is bound by the receipt hash, a failure to sign is never silent, and
HMAC chains keep working unchanged."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from _shell import shell_argv, posix

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"
KEYGEN = shutil.which("ssh-keygen")

pytestmark = pytest.mark.skipif(KEYGEN is None, reason="needs ssh-keygen (OpenSSH 8.2+)")


def env(**extra):
    e = {k: v for k, v in os.environ.items()
         if k != "CLAUDECODE" and not k.startswith(("CLAUDE_", "TITAN_RECEIPTS_", "COMMITPROOF_"))}
    e.update(extra)
    return e


def sh(cmd, cwd):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True, env=env())
    assert r.returncode == 0, r.stderr
    return r.stdout


def run(cwd, *args, e=None, stdin=None):
    return subprocess.run([sys.executable, str(RECEIPT), *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", env=e or env(), input=stdin)


def keypair(d: Path, name: str) -> Path:
    key = d / name
    subprocess.run([KEYGEN, "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(key)],
                   check=True, capture_output=True)
    return key


def make_repo(path: Path, email: str) -> Path:
    path.mkdir(parents=True)
    sh(f"git init -q -b main && git config user.email {email} && git config user.name Dev", path)
    (path / "seed.txt").write_text("seed\n")
    sh("git add -A && git commit -qm seed", path)
    return path


def commit(repo: Path, name: str, msg: str = "feat: change"):
    (repo / name).write_text(name + "\n")
    sh(f"git add {name} && git commit -qm '{msg}'", repo)


def receipts(repo: Path) -> list[Path]:
    return sorted((repo / ".titan" / "attestations").rglob("*.json"), key=lambda p: p.stat().st_mtime)


@pytest.fixture()
def keys(tmp_path):
    d = tmp_path / "keys"
    d.mkdir()
    return {"alice": keypair(d, "alice"), "bob": keypair(d, "bob")}


@pytest.fixture()
def alice_repo(tmp_path, keys):
    repo = make_repo(tmp_path / "repo", "alice@example.com")
    r = run(repo, "init", "--ssh", str(keys["alice"]), "--no-git-hook")
    assert r.returncode == 0, r.stdout + r.stderr
    commit(repo, "a.py")
    assert run(repo, "create").returncode == 0
    return repo


def test_init_ssh_registers_signer_without_a_shared_secret(alice_repo, keys):
    allowed = (alice_repo / ".titan" / "allowed_signers").read_text()
    pub = Path(str(keys["alice"]) + ".pub").read_text().split()[1]
    assert allowed.startswith("alice@example.com ") and pub in allowed
    assert 'namespaces="commitproof-receipt"' in allowed
    assert not (alice_repo / ".titan" / "key").exists()          # nothing to hand around
    r = json.loads(receipts(alice_repo)[0].read_text())
    assert r["signing_version"] == "ssh-sig-v1"
    assert r["signer"]["principal"] == "alice@example.com"
    assert r["signer"]["key"].startswith("SHA256:")
    assert r["signature"].startswith("-----BEGIN SSH SIGNATURE-----")


def test_ssh_receipts_verify_in_a_fresh_clone_with_no_secret(alice_repo, tmp_path):
    sh("git add .titan && git commit -qm 'chore: receipts'", alice_repo)
    clone = tmp_path / "clone"
    sh(f"git clone -q {posix(alice_repo)} {posix(clone)}", tmp_path)
    v = run(clone, "verify")
    assert v.returncode == 0, v.stdout + v.stderr
    assert "chain OK: 1" in v.stdout and "alice@example.com" in v.stdout


def test_receipt_signed_by_an_unlisted_key_fails(alice_repo, keys):
    """Bob's key claiming to be alice: the signature is real, but not by the
    key allowed_signers lists for alice."""
    sh(f"git config commitproof.signingkey {posix(keys['bob'])}", alice_repo)
    commit(alice_repo, "b.py")
    assert run(alice_repo, "create").returncode == 0
    v = run(alice_repo, "verify")
    assert v.returncode == 1 and "SIG FAIL" in v.stderr


def test_signer_is_bound_by_the_receipt_hash(alice_repo):
    p = receipts(alice_repo)[0]
    r = json.loads(p.read_text())
    r["signer"]["principal"] = "bob@example.com"
    p.write_text(json.dumps(r, indent=2) + "\n")
    v = run(alice_repo, "verify")
    assert v.returncode == 1 and "CHAIN FAIL" in v.stderr


def test_second_developer_joins_from_their_own_clone(alice_repo, keys, tmp_path):
    sh("git add .titan && git commit -qm 'chore: receipts'", alice_repo)
    clone = tmp_path / "bob-clone"
    sh(f"git clone -q {posix(alice_repo)} {posix(clone)}", tmp_path)
    sh("git config user.email bob@example.com && git config user.name Bob", clone)
    r = run(clone, "init", "--ssh", str(keys["bob"]), "--no-git-hook")
    assert r.returncode == 0, r.stdout + r.stderr
    allowed = (clone / ".titan" / "allowed_signers").read_text()
    assert "alice@example.com " in allowed and "bob@example.com " in allowed
    commit(clone, "bob.py")
    assert run(clone, "create").returncode == 0
    v = run(clone, "verify")
    assert v.returncode == 0, v.stdout + v.stderr
    assert "alice@example.com" in v.stdout and "bob@example.com" in v.stdout


def test_hmac_chain_switching_to_ssh_verifies_receipt_by_receipt(tmp_path, keys):
    repo = make_repo(tmp_path / "mixed", "alice@example.com")
    assert run(repo, "init", "--no-git-hook").returncode == 0           # HMAC first
    commit(repo, "h.py")
    assert run(repo, "create").returncode == 0
    assert run(repo, "init", "--ssh", str(keys["alice"]), "--no-git-hook").returncode == 0
    commit(repo, "s.py")
    assert run(repo, "create").returncode == 0
    kinds = [json.loads(p.read_text())["signing_version"] for p in receipts(repo)]
    assert kinds == ["hmac-sha256-v1", "ssh-sig-v1"]
    v = run(repo, "verify")
    assert v.returncode == 0, v.stdout + v.stderr
    (repo / ".titan" / "key").unlink()
    v = run(repo, "verify")
    assert v.returncode == 2                                  # HMAC receipt unchecked
    assert "SIGNATURES NOT CHECKED" in v.stderr and "alice@example.com" in v.stdout
    v = run(repo, "verify", "--public-only")
    assert v.returncode == 0, v.stdout + v.stderr             # what CI can check without a secret
    assert "1 HMAC" in v.stdout and "not checked" in v.stdout.lower()


def test_report_names_signers_and_badge_verifies_with_no_secret(alice_repo, tmp_path):
    badge = tmp_path / "b.svg"
    r = run(alice_repo, "report", "--badge", str(badge))
    assert r.returncode == 0, r.stderr
    assert "## Signed by" in r.stdout and "alice@example.com" in r.stdout
    assert "SSH" in r.stdout and "all valid" in r.stdout
    assert "chain verified" in badge.read_text(encoding="utf-8")


def test_unusable_key_is_refused_at_init_and_nothing_is_written(tmp_path):
    repo = make_repo(tmp_path / "r", "alice@example.com")
    r = run(repo, "init", "--ssh", str(tmp_path / "no-such-key"), "--no-git-hook")
    assert r.returncode == 2 and "ssh key not usable" in r.stderr.lower()
    assert not (repo / ".titan").exists()
    assert subprocess.run(["git", "config", "--get", "commitproof.signingkey"], cwd=repo,
                          capture_output=True).returncode != 0


def test_signing_failure_in_the_claude_hook_tells_the_user(alice_repo, keys):
    keys["alice"].unlink()                       # the key is gone: signing must fail
    Path(str(keys["alice"]) + ".pub").unlink()
    commit(alice_repo, "c.py")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"},
               "tool_response": {"stdout": "[main 1a2b3c4] x"}}
    r = run(alice_repo, "hook", e=env(CLAUDECODE="1"), stdin=json.dumps(payload))
    assert r.returncode == 0, r.stderr
    msg = json.loads(r.stdout)["systemMessage"]
    assert "couldn't sign" in msg.lower() and "c.py" not in msg
    assert len(receipts(alice_repo)) == 1          # no unsigned receipt was written


def test_allowed_signers_override_is_what_gets_trusted(alice_repo, keys, tmp_path):
    """CI can pin who may sign instead of trusting the audited repo's file."""
    other = tmp_path / "trusted_signers"
    other.write_text("bob@example.com " + Path(str(keys["bob"]) + ".pub").read_text())
    v = run(alice_repo, "verify", "--allowed-signers", str(other))
    assert v.returncode == 1 and "SIG FAIL" in v.stderr


def test_crlf_allowed_signers_from_an_autocrlf_checkout_still_verifies(alice_repo):
    p = alice_repo / ".titan" / "allowed_signers"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    v = run(alice_repo, "verify")
    assert v.returncode == 0, v.stdout + v.stderr


def test_init_in_an_ssh_repo_uses_git_signing_key_by_default(alice_repo, keys, tmp_path):
    """A teammate who already signs commits with SSH (gpg.format=ssh) runs
    plain /receipt-init and gets SSH receipts, not a stray HMAC key."""
    sh("git add .titan && git commit -qm 'chore: receipts'", alice_repo)
    clone = tmp_path / "carol"
    sh(f"git clone -q {posix(alice_repo)} {posix(clone)}", tmp_path)
    sh("git config user.email carol@example.com && git config gpg.format ssh && "
       f"git config user.signingkey {posix(Path(str(keys['bob']) + '.pub'))}", clone)
    r = run(clone, "init", "--no-git-hook")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (clone / ".titan" / "key").exists()
    assert "carol@example.com " in (clone / ".titan" / "allowed_signers").read_text()


def _action_step() -> str:
    import yaml
    a = yaml.safe_load((PLUGIN / "action.yml").read_text(encoding="utf-8"))
    return a["runs"]["steps"][0]["run"]


def run_action(repo: Path, **inputs):
    from _shell import POSIX_SHELL
    if POSIX_SHELL is None:
        pytest.skip("needs a POSIX shell")
    e = env(GITHUB_ACTION_PATH=PLUGIN.as_posix(), TITAN_KEY=inputs.get("key", ""),
            TITAN_REPORT=inputs.get("report", ""), TITAN_ALLOW_REPO_VERIFIER="false",
            TITAN_ALLOWED_SIGNERS=inputs.get("allowed_signers", ""),
            RUNNER_TEMP=str(repo.parent))
    return subprocess.run([POSIX_SHELL, "-c", _action_step()], cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", env=e)


def test_ci_action_checks_ssh_signatures_with_no_secret(alice_repo):
    r = run_action(alice_repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SSH signatures: 1 valid" in r.stdout and "alice@example.com" in r.stdout


def test_ci_action_pinned_signers_override_the_repo(alice_repo, keys):
    bob_only = "bob@example.com " + Path(str(keys["bob"]) + ".pub").read_text().strip()
    r = run_action(alice_repo, allowed_signers=bob_only)
    assert r.returncode == 1 and "SIG FAIL" in r.stderr
