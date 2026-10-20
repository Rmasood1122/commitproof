"""The README and the directory listing send installers to Claude Code.

This plugin runs in Claude Code, so the first thing a reader sees says
"Works in Claude Code" and gives the two commands that install it there, and every
install command in the README must point at this repo's own marketplace by the
names the manifests declare, so a copied command installs this plugin.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_SLUG = "Rmasood1122/commitproof"  # the public repo users install from
PREFIX = "Works in Claude Code"

PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
MARKET = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
INSTALL = [f"/plugin marketplace add {REPO_SLUG}",
           f"/plugin install {PLUGIN['name']}@{MARKET['name']}"]


def _block_after_first_line(lines):
    """Lines of the fenced code block that directly follows line 1 (blank lines allowed between)."""
    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    assert i < len(lines) and lines[i].startswith("```"), "line 1 must be followed by the install code block"
    end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("```")), None)
    assert end is not None, "the install block after line 1 is never closed"
    return [l.strip() for l in lines[i + 1:end] if l.strip()]


def test_readme_opens_with_claude_code_and_its_install_commands():
    lines = README.splitlines()
    assert lines[0].startswith(PREFIX), lines[0]
    assert _block_after_first_line(lines) == INSTALL


def test_listing_descriptions_lead_with_claude_code():
    assert PLUGIN["description"].startswith(PREFIX)
    for entry in MARKET["plugins"]:
        assert entry["description"].startswith(PREFIX), entry["name"]


def test_every_readme_install_command_points_at_this_repo():
    # whole tokens, so a URL source or an install without @marketplace can't slip past
    adds = re.findall(r"marketplace add ([^\s`]+)", README)
    installs = re.findall(r"plugin install ([^\s`]+)", README)
    assert adds and installs
    assert set(adds) == {REPO_SLUG}, adds
    assert set(installs) == {f"{PLUGIN['name']}@{MARKET['name']}"}, installs
