#!/usr/bin/env python3
"""Schema and policy validator for data/resources.json.

Pure stdlib, no dependencies. Returns a list of human-readable issues;
an empty list means the dataset passes every rule.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = 1

REQUIRED_PAGE_KEYS = ("title", "updated", "intro", "disclaimer")
REQUIRED_CARD_KEYS = (
    "id",
    "category",
    "title",
    "tagline",
    "what_it_is",
    "official_urls",
    "allowed_hosts",
    "saves_you",
    "cannot_do",
    "have_ready",
    "verified_free_on",
    "recheck_by",
    "scam_warnings",
)
STR_LIST_KEYS = ("cannot_do", "have_ready")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Direct affiliate / tracking markers that must never appear in a data URL.
AFFILIATE_RE = re.compile(
    r"[?&](utm_|ref=|ref_|tag=|aff)|affiliate|\b/click\b|"
    r"amzn\.to|bit\.ly|(?<!\w)t\.co\b|shareasale|linkshare|\bout\.php\b|/go/\?",
    re.IGNORECASE,
)

MAX_RECHECK_WINDOW_DAYS = 200


def _fail(issues: list[str], where: str, msg: str) -> None:
    issues.append(f"{where}: {msg}")


def _str_list_ok(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(x, str) and x.strip() for x in value
    )


def _host_matches(url: str, allowed: list[str]) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    host = host.lower().removeprefix("www.")
    for allow in allowed:
        a = allow.lower().removeprefix("www.")
        if host == a or host.endswith("." + a):
            return True
    return False


def _check_url(url: str, where: str, allowed: list[str] | None, issues: list[str]) -> None:
    if AFFILIATE_RE.search(url):
        _fail(issues, where, f"URL looks affiliate-ish, forbidden: {url}")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        _fail(issues, where, f"URL must be https: {url}")
    if allowed is not None and not _host_matches(url, allowed):
        _fail(issues, where, f"URL host {parsed.hostname!r} not in allowed_hosts {allowed}")


def validate(data: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["dataset: top level must be an object"]

    if data.get("schema_version") != SCHEMA_VERSION:
        _fail(issues, "schema_version", f"must be {SCHEMA_VERSION}")

    page = data.get("page")
    if not isinstance(page, dict):
        _fail(issues, "page", "must be an object")
        page = {}
    for key in REQUIRED_PAGE_KEYS:
        v = page.get(key)
        if not (isinstance(v, str) and v.strip()):
            _fail(issues, f"page.{key}", "required non-empty string")
    updated = page.get("updated", "")
    if not (isinstance(updated, str) and DATE_RE.match(updated)):
        _fail(issues, "page.updated", f"must be YYYY-MM-DD: {updated!r}")

    categories = data.get("categories")
    if not (isinstance(categories, list) and categories):
        _fail(issues, "categories", "must be a non-empty list")
        categories = []
    cat_ids: set[str] = set()
    for i, cat in enumerate(categories):
        where = f"categories[{i}]"
        if not isinstance(cat, dict) or not ID_RE.match(str(cat.get("id", ""))):
            _fail(issues, where, "needs id matching [a-z0-9-]+")
            continue
        if cat["id"] in cat_ids:
            _fail(issues, where, f"duplicate category id {cat['id']!r}")
        cat_ids.add(cat["id"])
        if not (isinstance(cat.get("label"), str) and cat["label"].strip()):
            _fail(issues, where, "needs a non-empty label")

    resources = data.get("resources")
    if not (isinstance(resources, list) and resources):
        _fail(issues, "resources", "must be a non-empty list")
        resources = []
    seen_ids: set[str] = set()

    today = dt.date.today()
    for i, r in enumerate(resources):
        where = f"resources[{i}] {r.get('id', '<missing-id>') if isinstance(r, dict) else ''}"
        if not isinstance(r, dict):
            _fail(issues, where, "each resource must be an object")
            continue
        rid = r.get("id")
        if not (isinstance(rid, str) and ID_RE.match(rid)):
            _fail(issues, where, "id must match [a-z0-9-]+")
        elif rid in seen_ids:
            _fail(issues, where, f"duplicate resource id {rid!r}")
        else:
            seen_ids.add(rid)

        if r.get("category") not in cat_ids:
            _fail(issues, where, f"category {r.get('category')!r} not defined in categories")

        for key in ("title", "tagline", "what_it_is"):
            if not (isinstance(r.get(key), str) and r[key].strip()):
                _fail(issues, where, f"{key} required non-empty string")
        saves = r.get("saves_you")
        if not (isinstance(saves, str) and len(saves) >= 60):
            _fail(issues, where, "saves_you must be a substantive string (>=60 chars)")

        for key in STR_LIST_KEYS:
            if not _str_list_ok(r.get(key)):
                _fail(issues, where, f"{key} must be a non-empty list of strings")

        allowed = r.get("allowed_hosts")
        if not (_str_list_ok(allowed)):
            _fail(issues, where, "allowed_hosts must be a non-empty list of strings")
            allowed = None

        urls = r.get("official_urls")
        if not (isinstance(urls, list) and urls):
            _fail(issues, where, "official_urls must be a non-empty list")
        else:
            for j, entry in enumerate(urls):
                u_where = f"{where}.official_urls[{j}]"
                if not isinstance(entry, dict):
                    _fail(issues, u_where, "must be an object with label + url")
                    continue
                if not (isinstance(entry.get("label"), str) and entry["label"].strip()):
                    _fail(issues, u_where, "label required")
                url = entry.get("url")
                if not isinstance(url, str):
                    _fail(issues, u_where, "url required string")
                else:
                    _check_url(url, u_where, allowed, issues)

        phone = r.get("phone")
        if phone is not None and not (isinstance(phone, str) and phone.strip()):
            _fail(issues, where, "phone must be a non-empty string when present")
        eligibility = r.get("eligibility_notes")
        if eligibility is not None and not (isinstance(eligibility, str) and eligibility.strip()):
            _fail(issues, where, "eligibility_notes must be a non-empty string when present")

        verified = r.get("verified_free_on")
        recheck = r.get("recheck_by")
        for name, val in (("verified_free_on", verified), ("recheck_by", recheck)):
            if not (isinstance(val, str) and DATE_RE.match(val)):
                _fail(issues, where, f"{name} must be YYYY-MM-DD: {val!r}")
        if isinstance(verified, str) and isinstance(recheck, str) and DATE_RE.match(verified) and DATE_RE.match(recheck):
            try:
                v_date = dt.date.fromisoformat(verified)
                r_date = dt.date.fromisoformat(recheck)
            except ValueError:
                _fail(issues, where, "dates are not calendar-valid")
            else:
                if r_date < v_date:
                    _fail(issues, where, "recheck_by must be on/after verified_free_on")
                elif (r_date - v_date).days > MAX_RECHECK_WINDOW_DAYS:
                    _fail(
                        issues,
                        where,
                        f"recheck_by is more than {MAX_RECHECK_WINDOW_DAYS} days after verification",
                    )
                if v_date > today:
                    _fail(issues, where, "verified_free_on is in the future")

        scams = r.get("scam_warnings")
        if not (isinstance(scams, list) and scams):
            _fail(issues, where, "scam_warnings must be a non-empty list")
        else:
            for j, s in enumerate(scams):
                s_where = f"{where}.scam_warnings[{j}]"
                if not isinstance(s, dict):
                    _fail(issues, s_where, "must be object with watch_out + safe_domain")
                    continue
                for key in ("watch_out", "safe_domain"):
                    if not (isinstance(s.get(key), str) and s[key].strip()):
                        _fail(issues, s_where, f"{key} required non-empty string")

    return issues


def load_dataset(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve()
    default = here.parent.parent / "data" / "resources.json"
    path = Path(argv[1]) if len(argv) > 1 else default
    data = load_dataset(path)
    issues = validate(data)
    if issues:
        print(f"FAILED: {len(issues)} issue(s) in {path}")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"OK: {path} is valid ({len(data.get('resources', []))} resources).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main([]))
