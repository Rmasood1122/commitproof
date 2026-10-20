"""Plugin-structure self-validation — mirrors directory lints that bit us on
plugin #1: manifest schema, kebab name, frontmatter, NO broad allowed-tools
pre-approvals, icon present, no CLAUDE.md, no personal/client strings,
hook must be non-breaking (--auto + || true)."""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_schema():
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", m["name"])
    for key in ("version", "description", "license", "repository", "homepage",
                "supportUrl", "documentationUrl", "privacyPolicyUrl", "icon"):
        assert m.get(key), key
    assert m["author"]["name"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", m["version"])


def test_marketplace_has_description():
    mp = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    assert mp.get("description")  # plugin-1 lesson: warning without it
    assert mp["plugins"][0]["source"] == "./"


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), path
    return yaml.safe_load(text.split("---\n", 2)[1])


def test_commands_frontmatter_and_no_broad_grants():
    cmds = sorted((ROOT / "commands").glob("*.md"))
    assert {c.stem for c in cmds} == {"receipt-init", "receipt", "verify-chain",
                                      "receipt-report", "ai-history"}
    for c in cmds:
        data = frontmatter(c)
        assert data.get("description"), c
        # plugin-1 policy hold: never pre-approve broad tool access
        assert "allowed-tools" not in data, c


def test_skill_frontmatter():
    data = frontmatter(ROOT / "skills/receipt-integrity/SKILL.md")
    assert data.get("description")


def test_hook_is_nonbreaking_and_matcher_is_a_tool_name():
    h = json.loads((ROOT / "hooks/hooks.json").read_text())
    entry = h["hooks"]["PostToolUse"][0]
    # hook matchers match TOOL NAMES only — "Bash\(.*commit" NEVER fires
    # (that syntax belongs to permission rules). Shipped that bug once.
    assert entry["matcher"] == "Bash"
    cmd = entry["hooks"][0]["command"]
    assert " hook" in cmd and "|| true" in cmd  # filter in-script; never fail a commit
    assert "${CLAUDE_PLUGIN_ROOT}" in cmd


def test_icon_is_128():
    s = (ROOT / ".claude-plugin/icon.svg").read_text()
    assert 'width="128"' in s and 'height="128"' in s


def test_core_is_stdlib_only():
    banned = re.compile(r"^\s*(import|from)\s+(requests|yaml|numpy|cryptography|pydantic)\b", re.M)
    for p in (ROOT / "core").glob("*.py"):
        assert not banned.search(p.read_text()), p


def test_no_claude_md_at_root():
    assert not (ROOT / "CLAUDE.md").exists()


def test_no_personal_or_client_strings():
    banned = re.compile(r"appealforge|rehanrana11", re.I)
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".svg"} \
                and ".git" not in p.parts and p.name != "test_structure.py":
            assert not banned.search(p.read_text(errors="ignore")), p


def test_readme_claims_match_behavior():
    readme = (ROOT / "README.md").read_text()
    # the honest-limits sentence must exist and stay
    assert "Does not prove" in readme
    assert "shared secret" in readme
    # stdlib claim is enforced by test_core_is_stdlib_only above
    assert "stdlib only" in readme.lower() or "Stdlib only" in readme


def test_action_yml_is_composite_and_uses_pinned_verifier_by_default():
    import yaml
    a = yaml.safe_load((ROOT / "action.yml").read_text())
    assert a["runs"]["using"] == "composite"
    step = a["runs"]["steps"][0]["run"]
    assert "verify --structure-only" in step and 'python3 "$TOOL" verify' in step
    assert "rm -f .titan/key" in step and "exit $rc" in step   # key never outlives the step; report written even on failure
    assert "key" in a["inputs"] and a["inputs"]["key"]["required"] is False

    # Trust model: the action's OWN pinned verifier is the default; the audited
    # repo's vendored verifier is used only behind an explicit opt-in, never
    # silently. This is the whole point of a tamper-evidence CI gate — the
    # thing being audited must not supply the auditor.
    assert 'TOOL="${GITHUB_ACTION_PATH}/core/receipt.py"' in step
    assert "allow_repo_verifier" in a["inputs"]
    assert a["inputs"]["allow_repo_verifier"]["default"] == "false"
    # the repo's verifier is reachable ONLY when the opt-in is true
    assert '"${TITAN_ALLOW_REPO_VERIFIER}" = "true"' in step
    assert '.titan/tools/receipt.py' in step
    # and using it must emit a warning that the check is not independent
    assert "::warning" in step


def test_readme_documents_provenance_and_coverage_limits():
    readme = (ROOT / "README.md").read_text()
    assert "ai_assisted" in readme
    assert "install-hook" in readme            # hooks aren't cloned; README must say so
    assert "recorded claim" in readme.lower() or "recorded claims" in readme.lower()


def test_readme_discloses_what_the_plugin_runs():
    """The directory's security scan expects the README to describe everything
    the plugin runs, sends or fetches; the hook runs on every Bash call."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## What it runs and touches" in readme
    for must in ("every Bash tool call", "transcript", ".git/hooks/post-commit", "Network:** none"):
        assert must in readme, must
