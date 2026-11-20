"""Fill the README template: the command's sh blocks, byte for byte, and the
sample answer rendered by code from fixture c's golden values.

Usage: python render_readme.py TEMPLATE PLUGIN_DIR FIXTURES_DIR OUT
Placeholders: {{STEP1}} {{STEP2}} {{STEP2B}} {{SAMPLE}}
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from block_check import blocks, render_layout  # noqa: E402
from fixtures import isolated_env  # noqa: E402
from golden import golden  # noqa: E402


def main(template: Path, plugin: Path, fixtures: Path, out: Path) -> int:
    step1, step2, step2b = blocks(plugin)
    g = golden(fixtures / "c", env=isolated_env(fixtures / "_git"))
    sample = "\n".join(("> " + line) if line else ">" for line in render_layout(g).splitlines())
    t = template.read_text(encoding="utf-8").replace("\r\n", "\n")
    for k, v in (("{{STEP1}}", step1), ("{{STEP2}}", step2), ("{{STEP2B}}", step2b), ("{{SAMPLE}}", sample)):
        assert t.count(k) == 1, k
        t = t.replace(k, v)
    out.write_text(t, encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(t.split())} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main(*(Path(a) for a in sys.argv[1:5])))
