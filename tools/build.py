#!/usr/bin/env python3
"""Build the offline, single-file index.html from data/resources.json + templates/page.html.

Usage:
    python3 tools/build.py              # write index.html in the repo root
    python3 tools/build.py /tmp/out.html  # write somewhere else (used by tests)

No third-party dependencies; the output has zero external assets and works offline.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import load_dataset, validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "resources.json"
TEMPLATE_PATH = ROOT / "templates" / "page.html"
DEFAULT_OUT = ROOT / "index.html"

WS_RE = re.compile(r"\s+")


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def json_for_script(data: dict) -> str:
    """Serialize JSON for safe embedding inside a <script type="application/json"> tag."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")




def search_text(r: dict, cat_label: str) -> str:
    parts = [cat_label, r["title"], r["tagline"], r["what_it_is"], r["saves_you"]]
    parts += r["cannot_do"] + r["have_ready"] + [s["watch_out"] for s in r["scam_warnings"]]
    if r.get("phone"):
        parts.append(r["phone"])
    if r.get("eligibility_notes"):
        parts.append(r["eligibility_notes"])
    return WS_RE.sub(" ", " ".join(parts)).strip().lower()


def render_card(r: dict, categories: dict[str, str]) -> str:
    rid = r["id"]
    needle = search_text(r, categories[r["category"]])
    lines: list[str] = []
    a = lines.append
    a(
        '<article class="card" id="card-{id}" data-id="{id}" data-category="{cat}" '
        'data-search="{needle}">'.format(id=esc(rid), cat=esc(r["category"]), needle=esc(needle))
    )
    a(f'  <h2>{esc(r["title"])}</h2>')
    a(f'  <p class="tagline">{esc(r["tagline"])}</p>')
    a('  <div class="badges">')
    a(f'    <span class="badge cat">{esc(categories[r["category"]])}</span>')
    a('    <span class="badge free">Always free</span>')
    if r.get("phone"):
        a(f'    <span class="badge phone-badge">{esc(r["phone"].split("(")[0].split(",")[0].strip())}</span>')
    a("  </div>")
    a(f'  <p class="what">{esc(r["what_it_is"])}</p>')
    a('  <section><h3>Saves you</h3>')
    a(f'    <p>{esc(r["saves_you"])}</p>')
    a("  </section>")
    a("  <section><h3>What it cannot do</h3><ul>")
    for item in r["cannot_do"]:
        a(f"    <li>{esc(item)}</li>")
    a("  </ul></section>")
    a("  <section><h3>Have ready</h3><ul>")
    for item in r["have_ready"]:
        a(f"    <li>{esc(item)}</li>")
    a("  </ul></section>")
    a('  <section><h3>Official, free portals</h3><ul class="links">')
    for entry in r["official_urls"]:
        host = urlparse(entry["url"]).hostname or ""
        a(
            f'    <li><a href="{esc(entry["url"])}" rel="noopener" data-host="'
            f'{esc(host)}">{esc(entry["label"])}</a> '
            f'<small class="host-tag">({esc(host)})</small></li>'
        )
    a("  </ul></section>")
    if r.get("phone"):
        a(f'  <p class="phone">By phone: {esc(r["phone"])}</p>')
    a('  <section class="scams"><h3>Spot the fakes</h3><ul>')
    for s in r["scam_warnings"]:
        a(
            f'    <li>{esc(s["watch_out"])} <em>Official:</em> '
            f'<strong>{esc(s["safe_domain"])}</strong></li>'
        )
    a("  </ul></section>")
    if r.get("eligibility_notes"):
        a(f'  <p class="notes">Good to know: {esc(r["eligibility_notes"])}</p>')
    a(
        f'  <p class="recheck">Verified free on {esc(r["verified_free_on"])} '
        f"&middot; recheck by {esc(r['recheck_by'])}.</p>"
    )
    a("</article>")
    return "\n".join(lines)


def render_chips(data: dict) -> str:
    chips = ['    <button type="button" class="chip" data-category="all" aria-pressed="true">All</button>']
    for cat in data["categories"]:
        chips.append(
            f'    <button type="button" class="chip" data-category="{esc(cat["id"])}" '
            f'aria-pressed="false">{esc(cat["label"])}</button>'
        )
    return "\n".join(chips)


def build(out_path: Path = DEFAULT_OUT) -> Path:
    data = load_dataset(DATA_PATH)
    issues = validate(data)
    if issues:
        print("Build aborted — fix data/resources.json first:")
        for issue in issues:
            print(f"  - {issue}")
        raise SystemExit(1)

    categories = {c["id"]: c["label"] for c in data["categories"]}
    cards = "\n".join(render_card(r, categories) for r in data["resources"])

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    page = data["page"]
    short_disclaimer = (
        "An unofficial, independent directory — not affiliated with any government "
        "agency or United Way. Every listing is vetted to be officially free before "
        "it earns a card here."
    )
    replacements = {
        "__CARDS__": cards,
        "__CHIPS__": render_chips(data),
        "__DATA_JSON__": json_for_script(data),
        "__CARD_COUNT__": str(len(data["resources"])),
        "__PAGE_INTRO__": esc(page["intro"]),
        "__UPDATED__": esc(page["updated"]),
        "__BUILT_AT__": esc(dt.date.today().isoformat()),
        "__DISCLAIMER__": esc(page["disclaimer"]),
        "__DISCLAIMER_SHORT__": esc(short_disclaimer),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)

    leftover = re.findall(r"__[A-Z_]+__", template)
    if leftover:
        raise SystemExit(f"Unreplaced tokens in template: {sorted(set(leftover))}")

    out_path.write_text(template, encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUT
    path = build(out)
    data = load_dataset(DATA_PATH)
    print(f"Built {path} ({path.stat().st_size:,} bytes, {len(data['resources'])} cards).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main([]))
