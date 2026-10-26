#!/usr/bin/env python3
"""Test suite for the Official Free Help Directory.

Validates (offline, stdlib only):
  1. the JSON dataset against data/resources.json's schema rules,
  2. that the built index.html actually renders every card,
  3. the no-affiliate-links / official-domain-only policy,
  4. that the page is a fully offline single file,
  5. that the build is reproducible from source files,
  6. basic integrity of README/LICENSE/STATUS and no secrets.

Run one of:
    python3 tests/test_site.py
    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import copy
import html as html_module
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build  # noqa: E402
import validate as schema  # noqa: E402

COPYRIGHT_LINE = "Copyright (c) 2026 Asdale Dynamics, LLC"
DO_REQUIRED_SECTIONS = (
    "Saves you",
    "What it cannot do",
    "Have ready",
    "Spot the fakes",
    "Verified free on",
    "recheck by",
)


class PageParser(HTMLParser):
    """Collects anchors, cards, the embedded JSON blob, and any external asset refs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.cards: list[dict[str, str]] = []
        self.hrefs: list[str] = []
        self.external_refs: list[str] = []
        self.in_data_json = False
        self.json_chunks: list[str] = []
        self.inputs: list[dict[str, str]] = []
        self.buttons: list[str] = []
        self.count_targets: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        d = {k: (v or "") for k, v in attrs}
        classes = d.get("class", "")
        if tag == "article" and "card" in classes.split():
            self.cards.append(d)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
        if tag == "script":
            if "src" in d:
                self.external_refs.append(f"script src={d['src']}")
            if d.get("id") == "resources-data":
                self.in_data_json = True
        if tag in ("link", "img", "iframe", "embed", "object", "video", "audio", "source"):
            ref = d.get("src") or d.get("href") or d.get("data")
            if ref:
                self.external_refs.append(f"{tag}={ref}")
        if tag == "input" and d.get("id") == "search":
            self.inputs.append(d)
        if tag == "button" and "chip" in classes.split():
            self.buttons.append(d.get("data-category", ""))
        if tag == "p" and d.get("id") == "count":
            self.count_targets.append(tag)

    def handle_startendtag(self, tag: str, attrs) -> None:  # type: ignore[override]
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self.in_data_json:
            self.json_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag == "script" and self.in_data_json:
            self.in_data_json = False


class SiteTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = schema.load_dataset(ROOT / "data" / "resources.json")
        cls.html_text = (ROOT / "index.html").read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(cls.html_text)
        parser.close()
        cls.page = parser

    # ---------- dataset / schema ----------

    def test_dataset_loads_and_validates(self):
        issues = schema.validate(self.data)
        self.assertEqual(issues, [], "schema issues:\n" + "\n".join(issues))

    def test_minimum_cards(self):
        self.assertGreaterEqual(len(self.data["resources"]), 7)

    def test_all_resources_cover_expected_officials(self):
        ids = {r["id"] for r in self.data["resources"]}
        for needle in (
            "ssa-", "medicare-ship-", "united-way-211", "irs-free-file-",
            "cfpb-", "ftc-", "state-ag-",
        ):
            self.assertTrue(any(i.startswith(needle) for i in ids), f"missing card {needle}*")

    def test_dates_ordered(self):
        for r in self.data["resources"]:
            self.assertGreaterEqual(r["recheck_by"], r["verified_free_on"], r["id"])

    def test_no_affiliate_markers_in_any_data_url(self):
        for r in self.data["resources"]:
            combined = [u["url"] for u in r["official_urls"]]
            for url in combined:
                self.assertIsNone(schema.AFFILIATE_RE.search(url), f"affiliate marker in {url}")

    def test_validator_negative_controls(self):
        bad = copy.deepcopy(self.data)
        bad["resources"][0]["official_urls"][0]["url"] = (
            "https://tracker.example.com/?tag=dylan-20&id=ssa"
        )
        self.assertTrue(schema.validate(bad))

        bad2 = copy.deepcopy(self.data)
        bad2["resources"][0]["verified_free_on"] = "2027-01-01"  # future
        bad2["resources"][1]["recheck_by"] = "2000-01-01"  # before verify
        self.assertTrue(schema.validate(bad2))

        bad3 = copy.deepcopy(self.data)
        bad3["resources"][2]["official_urls"][0]["url"] = "https://impostor.io/pretend"
        bad3["resources"][2]["scam_warnings"] = [{"watch_out": "x", "safe_domain": "x.example"}]
        self.assertTrue(schema.validate(bad3))

        bad4 = copy.deepcopy(self.data)
        del bad4["resources"][3]["have_ready"]
        self.assertTrue(schema.validate(bad4))

    # ---------- rendered page ----------

    def test_page_is_parseable_with_doctype(self):
        self.assertTrue(self.html_text.lstrip().lower().startswith("<!doctype html>"))
        self.page.feed(self.html_text)  # no raise

    def test_every_resource_renders_as_a_card(self):
        rendered_ids = {c["data-id"] for c in self.page.cards if c.get("data-id")}
        expected_ids = {r["id"] for r in self.data["resources"]}
        self.assertEqual(rendered_ids, expected_ids)
        self.assertEqual(len(self.page.cards), len(self.data["resources"]))

    def test_cards_contain_required_sections(self):
        for r in self.data["resources"]:
            i = self.html_text.index(f'id="card-{r["id"]}"')
            j = self.html_text.index("</article>", i)
            block = self.html_text[i:j]
            for section in DO_REQUIRED_SECTIONS:
                self.assertIn(section, block, f"card {r['id']} missing “{section}”")

    def test_every_official_url_is_linked(self):
        for r in self.data["resources"]:
            for u in r["official_urls"]:
                self.assertIn(u["url"], self.page.hrefs, f"missing link {u['url']}")

    def test_all_anchors_are_official_whitelisted_https(self):
        allowed: set[str] = set()
        for r in self.data["resources"]:
            for host in r["allowed_hosts"]:
                allowed.add(host.removeprefix("www."))
        for href in self.page.hrefs:
            parsed = urlparse(href)
            self.assertEqual(parsed.scheme, "https", href)
            host = (parsed.hostname or "").removeprefix("www.")
            self.assertTrue(
                any(host == a or host.endswith("." + a) for a in allowed),
                f"anchor not on an official domain: {href}",
            )

    def test_filters_ui_present(self):
        self.assertEqual(len(self.page.inputs), 1, "search input missing")
        pressed = [b for b in self.page.buttons if b]
        self.assertGreaterEqual(len(pressed), 5, "category chips missing")
        self.assertIn('id="count"', self.html_text)

    def test_filters_have_searchable_card_text(self):
        for r in self.data["resources"]:
            needle = r["title"].split(" ")[0].lower()
            i = self.html_text.index(f'id="card-{r["id"]}"')
            match = re.compile(r'data-search="([^"]*)"', re.S).search(self.html_text, i)
            self.assertIsNotNone(match, f"card {r['id']} lacks data-search")
            self.assertLess(match.start() - i, 400, f"card {r['id']} data-search not in tag")
            hay = html_module.unescape(match.group(1)).lower()
            self.assertIn(needle, hay, f"card {r['id']} data-search missing title text")

    def test_embedded_json_matches_source(self):
        raw = "".join(self.page.json_chunks)
        embedded = json.loads(raw)
        self.assertEqual(embedded, self.data)

    # ---------- single offline file ----------

    def test_no_external_assets(self):
        self.assertEqual(self.page.external_refs, [], "page must be 100% offline")
        self.assertNotIn("@import", self.html_text)
        self.assertNotRegex(self.html_text, r'url\(\s*["\']?https?://')
        self.assertNotIn("<img", self.html_text.lower())

    def test_no_inline_event_handlers(self):
        self.assertNotRegex(self.html_text, r"\son[a-z]+\s*=", "no inline JS handlers")

    # ---------- reproducible build ----------

    def test_rebuild_is_deterministic_and_up_to_date(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "index.html"
            build.build(out)
            self.assertEqual(out.read_bytes(), (ROOT / "index.html").read_bytes())

    # ---------- repo integrity ----------

    def test_license_exact_copyright_line(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn(COPYRIGHT_LINE, text)
        self.assertIn("MIT License", text)

    def test_readme_credits_and_policy(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", text)
        self.assertTrue(
            re.search(r"no affiliate links", text, re.IGNORECASE),
            "README must state the no-affiliate policy",
        )

    def test_status_md_exists(self):
        self.assertTrue((ROOT / "STATUS.md").is_file())

    def test_no_secrets(self):
        secret_paths = [
            p
            for p in ROOT.rglob("*")
            if p.is_file()
            and ".git" not in p.parts
            and p.suffix in {".py", ".json", ".html", ".md", ".txt"}
        ]
        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"sk-(live|test)-[A-Za-z0-9]{10,}"),
            re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
            re.compile(r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9\-_]{16,}['\"]"),
            re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        ]
        for path in secret_paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pat in patterns:
                self.assertIsNone(pat.search(text), f"possible secret in {path}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
