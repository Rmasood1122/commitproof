"""Directory-listing readiness: the manifest checks the plugin directory applies.

Mirrors the manifest part of eval-conductor's readiness battery, so a listing edit
(description, keywords, names) can't silently break what the directory accepts.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
MARKET = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


def test_name_is_kebab_case():
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", PLUGIN["name"]), PLUGIN["name"]


def test_description_length_fits_the_directory():
    assert 30 <= len(PLUGIN["description"]) <= 2000, len(PLUGIN["description"])
    for entry in MARKET["plugins"]:
        assert 30 <= len(entry.get("description", "")) <= 2000, entry["name"]


def test_keywords_are_a_nonempty_list_of_strings():
    kw = PLUGIN.get("keywords")
    assert isinstance(kw, list) and kw and all(isinstance(k, str) and k for k in kw), kw


def test_marketplace_lists_exactly_this_plugin():
    assert [p["name"] for p in MARKET["plugins"]] == [PLUGIN["name"]]
