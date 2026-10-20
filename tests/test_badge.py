"""v1.3: a README badge — the growth loop, held to the report's honesty.

`report --badge F` / `history --badge F` write a self-contained SVG (no
badge service: nothing phones home) and print a README snippet linking back
to the plugin. A badge is a claim on someone's front page, so it may say
"chain verified" only when the chain is intact AND every signature checks
out, never shows a share next to a failed verification, and always says
"unsigned" when it comes from trailers."""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from _shell import shell_argv

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"
REPO_URL = "https://github.com/Rmasood1122/commitproof"
CLAUDE = "Co-Authored-By: Claude <noreply@anthropic.com>"


def sh(cmd, cwd):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def run(cwd, *args):
    return subprocess.run([sys.executable, str(RECEIPT), *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8")


def commit(repo, msgs, name, message):
    (repo / name).write_text(name + "\n")
    m = msgs / f"{name}.msg"
    m.write_text(message)
    sh(f"git add {name} && git commit -q -F '{m.as_posix()}'", repo)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    msgs = tmp_path / "msgs"
    r.mkdir(), msgs.mkdir()
    sh("git init -q -b main && git config user.email t@t && git config user.name T", r)
    (r / "seed").write_text("seed\n")
    sh("git add -A && git commit -qm seed", r)
    assert run(r, "init", "--no-git-hook").returncode == 0
    for i, msg in enumerate(["feat: human\n", f"feat: ai\n\n{CLAUDE}\n",
                             f"feat: ai2\n\n{CLAUDE}\n", "fix: human\n"]):
        commit(r, msgs, f"f{i}.py", msg)
        assert run(r, "create").returncode == 0
    return r


def svg_text(path: Path) -> str:
    root = ET.parse(path).getroot()          # must be well-formed XML
    return " ".join(t.text or "" for t in root.iter() if t.tag.endswith(("text", "title")))


def receipts(repo):
    return sorted((repo / ".titan" / "attestations").rglob("*.json"))


def test_verified_chain_badge(repo, tmp_path):
    badge = tmp_path / "badge.svg"
    r = run(repo, "report", "--out", str(tmp_path / "r.md"), "--badge", str(badge))
    assert r.returncode == 0, r.stderr
    text = svg_text(badge)
    assert "AI-assisted" in text and "50% · chain verified" in text
    assert f"]({REPO_URL}" in r.stdout          # README snippet links back


def test_no_key_badge_says_structure_only(repo, tmp_path):
    (repo / ".titan" / "key").unlink()
    badge = tmp_path / "badge.svg"
    assert run(repo, "report", "--badge", str(badge)).returncode == 0
    text = svg_text(badge)
    assert "structure only" in text and "verified" not in text


def test_bad_signature_badge_fails_without_a_share(repo, tmp_path):
    p = receipts(repo)[0]
    r = json.loads(p.read_text())
    r["signature"] = "0" * 64                    # structure intact, signature wrong
    p.write_text(json.dumps(r, indent=2) + "\n")
    badge = tmp_path / "badge.svg"
    run(repo, "report", "--badge", str(badge))
    text = svg_text(badge)
    assert "verification FAILED" in text and "%" not in text


def test_broken_chain_badge_fails_without_a_share(repo, tmp_path):
    p = receipts(repo)[-1]
    r = json.loads(p.read_text())
    r["provenance"]["ai_assisted"] = not r["provenance"]["ai_assisted"]
    p.write_text(json.dumps(r, indent=2) + "\n")
    badge = tmp_path / "badge.svg"
    run(repo, "report", "--badge", str(badge))
    text = svg_text(badge)
    assert "verification FAILED" in text and "%" not in text


def test_history_badge_is_labelled_unsigned_and_writes_only_the_badge(repo, tmp_path):
    badge = tmp_path / "hist.svg"
    r = run(repo, "history", "--badge", str(badge))
    assert r.returncode == 0, r.stderr
    text = svg_text(badge)
    assert "of commits · unsigned" in text and "verified" not in text
    assert f"]({REPO_URL}" in r.stderr           # snippet stays out of the document
    assert f"]({REPO_URL}" not in r.stdout


def test_badge_and_report_create_missing_folders(repo):
    """The README suggests docs/ai-audit-badge.svg; a repo without docs/
    crashed with FileNotFoundError."""
    r = run(repo, "report", "--out", "evidence/report.md", "--badge", "docs/badge.svg")
    assert r.returncode == 0, r.stderr
    assert (repo / "evidence" / "report.md").exists() and (repo / "docs" / "badge.svg").exists()
    r = run(repo, "history", "--badge", "img/hist.svg")
    assert r.returncode == 0, r.stderr
    assert (repo / "img" / "hist.svg").exists()
