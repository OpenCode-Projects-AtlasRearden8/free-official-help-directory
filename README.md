# Official Free Help Directory

A plain-English, offline-friendly directory of services that are **officially free and
sell you nothing**: SSA, Medicare.gov counselors (SHIP), 211, IRS Free File + VITA,
the CFPB complaint tool, FTC fraud reporting, and your state Attorney General's
consumer help. Every card says what the service **saves you**, what it **cannot do**,
what to **have ready**, when it was **verified free**, when to **recheck it**, and how
to spot **scam lookalike URLs**.

Built for beginners, low-energy days, and cautious screens: one self-contained HTML
file, no JavaScript frameworks, no fonts or images to download, no tracking, and
**no affiliate links, ever**.

Maintained by **Asdale Dynamics, LLC** (Dylan Asdale) as part of its
beginner-friendly plain-English tools collection. Unofficial guide — not affiliated
with any government agency or United Way.

## Quick start

```bash
# open the finished page
open index.html            # macOS    (or just double-click it)
xdg-open index.html        # Linux

# rebuild the page after editing data/resources.json or templates/page.html
python3 tools/build.py

# validate the JSON schema and check the page renders every card
python3 tests/test_site.py                 # or: python3 -m unittest discover -s tests

# (optional, needs internet) probe that every official URL still answers
python3 tools/check_links.py
```

You only need Python 3.10+ (stdlib only). The output `index.html` works with
JavaScript **off** too — filter chips and search are progressive enhancements; the
cards are pre-rendered by the build.

## How it works

```
data/resources.json     ← source of truth (schema below)
templates/page.html     ← page shell with placeholders (__CARDS__, __DATA_JSON__, …)
tools/validate.py       ← schema + policy validator (used by build and tests)
tools/build.py          ← injects parsed, escaped JSON + pre-rendered cards → index.html
tools/check_links.py    ← optional live URL probe (needs internet)
tests/test_site.py      ← unittest suite: schema, render, offline-ness, reproducible build
index.html               ← the deliverable; commit it
```

The build **validates before building** (it aborts on any schema or policy issue),
embeds the JSON in the file so the page stays JSON-driven at runtime (search,
category chips, and the "recheck overdue" badge all read it), and pre-renders every
card as static HTML for no-JS browsers.

### Card schema (`data/resources.json`)

| Field | Meaning |
| --- | --- |
| `id` | stable slug used for anchors, tests, and card ids |
| `category` | one of the ids in `categories` (drives the filter chips) |
| `title`, `tagline`, `what_it_is` | what the resource is, in plain English |
| `official_urls` | the real, free portals — must be `https://` on an `allowed_hosts` domain |
| `allowed_hosts` | domain whitelist for this card; blocks lookalike links at build time |
| `saves_you` | the money/time a paid alternative would cost (≥ 60 chars, enforced) |
| `cannot_do` | honest limits so nobody expects legal advice — or a refund |
| `have_ready` | checklist to gather before calling or filing |
| `verified_free_on`, `recheck_by` | when free status was last confirmed / must be re-confirmed (≤ 200 days apart, enforced) |
| `scam_warnings` | lookalike URLs and fake-fee traps, each with the official domain |
| `phone`, `eligibility_notes` | optional extras shown on the card |

### House rules (enforced by `tools/validate.py` and tests)

- Every URL is `https://` on that card's `allowed_hosts` whitelist.
- No affiliate, tracking, or redirector markers in any URL (`?tag=`, `?ref=`,
  `utm_`, `amzn.to`, `bit.ly`, `/go/?…` and friends fail the build).
- `verified_free_on` ≤ `recheck_by`, with a maximum 200-day window.
- The page ships no external assets, images, fonts, or inline event handlers.
- The exact MIT copyright line `Copyright (c) 2026 Asdale Dynamics, LLC` is required
  in `LICENSE`, and tests keep it that way.

## Maintenance checklist

1. **Quarterly recheck** — before any card's `recheck_by` date: click every
   `official_urls` link, confirm the service is still free and the shipping numbers
   still match `phone`, then set `verified_free_on` to today and push `recheck_by`
   forward (~3 months). The built page shows an amber **"Recheck overdue"** badge on
   any card past its date. Run `python3 tools/check_links.py` to probe them all.
2. **Seasonal facts** — income limits (IRS Free File, VITA), enrollment windows
   (Medicare Oct 15 – Dec 7), and filing-season dates change yearly. If you can't
   verify a number for this year, phrase the card to defer to the official page.
3. **Adding a card** — add it to `data/resources.json` following the schema above,
   choose a conservative `allowed_hosts` (top-level official domains only; allow
   `www.` implicitly), add at least one scam warning, then rebuild + test.
4. **Never** let an affiliate, referral, or sponsored link in — the tests fail the
   build instead of trusting anyone's memory. If you genuinely need to mention a
   paid option, write it as plain text, not a link.
5. **No secrets, no personal data** in the dataset or the page, ever.

## License & credit

MIT — see `LICENSE`. This project is created and maintained by
**Asdale Dynamics, LLC**. The listed government services belong to their own
agencies; this directory earns nothing from them and is an independent,
unofficial guide.
