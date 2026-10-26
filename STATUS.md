# STATUS — Official Free Help Directory

Last verified: 2026-10-26 &middot; Maintained by Asdale Dynamics, LLC

## What was built

A single-file, offline, no-tracking directory (`index.html`) of services that are
officially free and sell nothing — one JSON-driven card each for:

1. SSA (claims, card replacement, benefit letters) — **no** paid "agents"
2. Medicare.gov counselors + SHIP (plan advice without commissions)
3. 211 (free local referrals: rent, food, utilities)
4. IRS Free File + VITA (free tax filing, income caps noted)
5. CFPB complaint tool (bank/credit/debt disputes on the record)
6. FTC fraud reporting + IdentityTheft.gov recovery plan
7. Your state Attorney General's consumer office (via USA.gov)

Every card states: what it **saves you**, what it **cannot do**, what to **have
ready**, **verified-free-on** and **recheck-by** dates, and **scam-lookalike URL**
warnings with the official domain. Filters (search + category chips + live count)
read the JSON embedded in the file; the cards are also pre-rendered as static HTML,
so the page works with JavaScript disabled.

**Policy enforced:** every URL is `https://` on a per-card `.gov` whitelist; any
affiliate/tracking marker (`?tag=`, `?ref=`, `utm_`, `bit.ly`, `/go/?`, …) fails the
build. No affiliate links exist anywhere, by design and by test.

## File layout

```
data/resources.json    source of truth — 7 cards + categories + page copy
templates/page.html    page shell (CSS + JS inline, zero external assets)
tools/validate.py      JSON schema + policy validator (stdlib only)
tools/build.py         validate → inject JSON + pre-rendered cards → index.html
tools/check_links.py   optional live URL probe (needs internet)
tests/test_site.py     21-test unittest suite (schema, render, offline, integrity)
index.html             the deliverable (single file, ~70 KB)
README.md              usage + maintenance manual
LICENSE                MIT, Copyright (c) 2026 Asdale Dynamics, LLC
```

## How to run

```bash
open index.html                 # macOS      (or double-click / xdg-open on Linux)
python3 tools/build.py          # rebuild after editing data or template
python3 tests/test_site.py      # or: python3 -m unittest discover -s tests
python3 tools/check_links.py    # optional; needs internet
```

Requires Python 3.10+ only (stdlib). The generated page needs nothing — no server,
no build cache, no network.

## Verification results (2026-10-26)

- `python3 tools/build.py` — clean build, no unreplaced tokens, **7 cards**, 70,195 bytes.
- `python3 tests/test_site.py` — **21/21 tests pass** (schema validation incl. negative
  controls, JSON embed == source, all 7 cards render with required sections, all anchors
  on whitelisted official domains, zero external assets, reproducible rebuild byte-identical,
  LICENSE/README checks, no-secrets scan).
- `python3 tools/check_links.py` — **11/15 URLs HTTP 200**; **0 hard failures**.
  4 URLs return **403 from this datacenter IP** (www.ssa.gov ×2, consumerfinance.gov ×2):
  server-side bot protection, not dead pages — `consumerfinance.gov/complaint/`
  fetched successfully via a normal web client and showed the expected "Submit a
  complaint" page and phone (855) 411-2372. **SSA URLs flagged for manual browser
  verification during the next recheck.**

## Known gaps

- Data verified **without live browsing of every page** — facts are phrased to defer
  to official sites (e.g. IRS limits "at irs.gov"), and every card carries an explicit
  recheck date. Quarterly recheck cadence documented in README.
- ssa.gov blocks automated probes from this environment; treat its 403s as
  unverified-until-manual, not broken.
- The state-AG card points to the official USA.gov locator rather than embedding all
  50 offices — keeps the file small and always-current, but is one click away rather
  than in-line.
- `check_links.py` is best-effort (no JS rendering, no cookie flows); it cannot
  simulate browser-only sites fully.
- Filters hide/show cards client-side; with JS fully disabled the pre-rendered page
  shows every card (no filtering) — accepted trade-off for offline reliability.
- No CMS or CI pipeline — build/tests are run locally before commit (Python stdlib
  only so nothing to install).
- Never published: repo stays local, no remote, no pushes (explicit project rule).
