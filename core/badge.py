"""Self-contained README badge (no badge service, nothing phones home).

Kept in its own module on purpose: this file holds the plugin's homepage
URL and reads NOTHING from the environment; receipt.py holds no URLs and,
since 1.3.2, reads no session-id variable at all (session ids come from the
hook payload or a Claude-Session trailer). The split keeps the separation
visible in the layout rather than only in the code."""
from __future__ import annotations

import html
from pathlib import Path

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
