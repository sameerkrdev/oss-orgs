# oss-orgs

Static explorer for open-source mentorship programs and company-backed OSS projects.

- **GSoC** (Google Summer of Code) 2024–2026: 253 orgs, 3,419 contributor projects
- **LFX Mentorship** 2024–2026: 83 orgs, 484 mentee projects
- **Summer of Bitcoin** 2026: 25 orgs, mentors, 75 alumni
- **Hiring OSS**: 280 company-backed projects (Go, JS/TS, Python, Rust, Java/Kotlin, C/C++) with PR activity, starter issues and careers links

Plain HTML/CSS/JS, no build step, no dependencies.

## View

Open `index.html` in a browser (works from `file://`).

- `index.html?p=gsoc` / `?p=lfx` / `?p=sob` switches program (also the header switch)
- Tabs: Organizations, Contributors, Insights, Hiring OSS (`oss.html`)
- Org detail: description, repo stats, languages, community channels, founders/funding (Wikidata, Open Collective, with sources), projects per year with contributors and PRs

## Refresh data

Python 3.12+ stdlib only. GitHub calls use `gh auth token`, so log in with `gh auth login` first.
Every HTTP response is cached in `cache/` (gitignored), so reruns are fast and resumable.

```sh
python -I fetch.py              # GSoC  -> data/gsoc.json + data/gsoc.js   (--limit N for a smoke run)
python -I programs.py lfx       # LFX   -> data/lfx.*
python -I programs.py sob       # SoB   -> data/sob.*
python -I oss_fetch.py          # Hiring OSS -> data/oss.*
python -I check.py              # self-check: parsers + GSoC counts match the API
```

A cold run of `fetch.py` takes about an hour (GitHub search API allows 30 requests/min).

## Files

| File | What |
| --- | --- |
| `fetch.py` | GSoC API, GitHub orgs/repos, Wikidata, Open Collective, contributors, PRs; shared HTTP cache and helpers |
| `programs.py` | LFX (public mentorship API) and Summer of Bitcoin (site's Airtable feeds), same shape as GSoC |
| `oss_fetch.py` | Hand-picked company-backed repos per language; keeps those whose GitHub language matches, checks careers URLs load |
| `check.py` | Assert-based self-check |
| `index.html`, `app.js` | Program explorer |
| `oss.html`, `oss-app.js` | Hiring OSS page |
| `styles.css` | Shared styles, light/dark |
| `data/*.json` | Generated data; `data/*.js` is the same as `window.DATA=…` so pages load from disk |

## Data shape

`data/{gsoc,lfx,sob}.json`:

- `program` — `{key, name, title, sources}`
- `years` — program years covered
- `orgs[]` — `name, slug, years, logo_url, website_url, tagline, description, license, categories, tech_tags, topic_tags, source_code, ideas_link, contributor_guidance_url, page, links` (community channels), `gh` (GitHub stats), `facts` (founders/funding with sources), `mentors` (SoB)
- `projects[]` — `id, year, org, title, body, size, status, tech, mentors, name, url, code` (final work), `gh` (GitHub login), `prs`, `repo` / `linkedin` (LFX)
- `users{}` — GitHub profile per login: `name, bio, company, location, blog, twitter_username, socials, followers`
- `alumni[]` — SoB only: `name, year, role, company`

`data/oss.json`: `generated, since, groups[]` → projects with repo stats, backer, careers URL, merged PRs (30 days), good first issues, community channels.

## Privacy

Contributor contact data is limited to what people published themselves: the program's own listing, their GitHub profile, and the social accounts they linked there (LFX: GitHub/LinkedIn from their LFX profile). No guessing accounts from names. Mentor emails and résumé links from the LFX API are deliberately left out.
