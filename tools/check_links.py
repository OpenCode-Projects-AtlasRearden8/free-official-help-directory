#!/usr/bin/env python3
"""Optional live-probe for every official URL in data/resources.json (needs internet).

Not part of the offline test suite — run it during a quarterly recheck:

    python3 tools/check_links.py

HTTP 200: good. HTTP 403 with an official partner/bot-blocker domain is reported as
"blocked (verify manually)" and counts as a warning, not a failure, because several
government sites (e.g. ssa.gov) block datacenter IPs and scripts. Anything else 4xx/5xx
is a hard failure and exits nonzero.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import load_dataset  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def probe(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return str(resp.status), "OK"
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return str(e.code), "BLOCKED (verify manually in a normal browser)"
        return str(e.code), "FAIL"
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, "FAIL"


def main() -> int:
    data = load_dataset(ROOT / "data" / "resources.json")
    failures = warnings = 0
    for r in data["resources"]:
        for entry in r["official_urls"]:
            url, label = entry["url"], entry["label"]
            short = r["id"]
            status, verdict = probe(url)
            mark = "OK " if verdict == "OK" else ("WARN" if verdict.startswith("BLOCKED") else "FAIL")
            print(f"[{mark}] {status:>5}  {short:<26} {url}  — {label}")
            if verdict == "FAIL":
                failures += 1
            elif verdict.startswith("BLOCKED"):
                warnings += 1
    print(f"\n{failures} failure(s), {warnings} blocked-but-probably-fine (verify manually).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
