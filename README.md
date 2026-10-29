# oss-orgs

Static explorer for open-source mentorship programs and company-backed OSS projects.

- **GSoC** (Google Summer of Code) 2024–2026: 253 orgs, 3,419 contributor projects
- **LFX Mentorship** 2024–2026: 83 orgs, 484 mentee projects
- **Summer of Bitcoin** 2026: 25 orgs, mentors, 75 alumni
- **Hiring OSS**: 280 company-backed projects (Go, JS/TS, Python, Rust, Java/Kotlin, C/C++) with PR activity, starter issues and careers links

Plain HTML/CSS/JS, no build step, no dependencies.

Live: https://oss-orgs.vercel.app

## Using the site

- Header switch **GSoC / LFX / SoB** picks the program (or `index.html?p=gsoc|lfx|sob`).
- **Organizations**: search, filter by year, category, tech and community platform; sort by name, projects, stars or years. Click a card for the org page: description, repo stats, languages, community channels, founders/funding (with sources) and every project per year with its contributor and PRs.
- **Contributors**: table of every contributor project with GitHub/LinkedIn/X (as they published them), PRs merged and final work. SoB shows its alumni list instead.
- **Insights**: top tech, categories and orgs.
- **Hiring OSS** (`oss.html`): company-backed projects by language with stars, merged PRs (30 days), good first issues, community channels and careers page.

## Step-by-step guide

### 1. Run it locally

1. Clone the repo:
   ```sh
   git clone https://github.com/sameerkrdev/oss-orgs.git
   cd oss-orgs
   ```
2. Open `index.html` in your browser (double-click it). That's it: the data is already in `data/`, and the pages work straight from disk with no server.
3. Optional, if your browser blocks local files: serve the folder and open http://localhost:8000
   ```sh
   python -m http.server 8000
   ```

### 2. Refresh the data

1. Install [Python 3.12+](https://www.python.org/downloads/) (no packages needed) and the [GitHub CLI](https://cli.github.com/).
2. Log in to GitHub so the scripts get a token (higher API limits):
   ```sh
   gh auth login
   ```
3. Run the script for what you want to update:
   ```sh
   python -I fetch.py              # GSoC        -> data/gsoc.json + data/gsoc.js  (add --limit 5 for a quick test)
   python -I programs.py lfx       # LFX         -> data/lfx.*
   python -I programs.py sob       # SoB         -> data/sob.*
   python -I oss_fetch.py          # Hiring OSS  -> data/oss.*
   ```
   Every HTTP response is cached in `cache/` (gitignored), so a stopped run resumes where it left off and reruns are fast. To pull fresh data, delete `cache/` first. A cold `fetch.py` run takes about an hour (GitHub search allows 30 requests/min).
4. Check the result:
   ```sh
   python -I check.py              # prints "ok ..." or fails with the broken assert
   ```
5. Reload `index.html` to see the new data.

### 3. Deploy to Vercel

The site is plain static files: no build command, no framework.

1. Push the repo to GitHub (with `data/` committed).
2. Go to https://vercel.com/new, sign in with GitHub and **Import** the repo.
3. Settings on the import screen:
   - Framework Preset: **Other**
   - Build Command: leave empty
   - Output Directory: leave empty (root `.`)
4. Click **Deploy**. You get a URL like `https://<project>.vercel.app`.
5. From now on every push to `main` redeploys automatically.

`.vercelignore` keeps `cache/`, the Python scripts and logs out of the upload.

Deploy without GitHub instead (uploads your local folder):
```sh
npx vercel login
npx vercel deploy --prod
```

### 4. Update the live site

```sh
python -I programs.py lfx          # 1. refresh whichever data you need
python -I check.py                 # 2. self-check
git add data
git commit -m "Refresh data"       # 3. commit
git push                           # 4. Vercel redeploys in ~30 s
```

### 5. Optional: limit who can see it

The site shows contributor names and profile links. To make it private: Vercel → Project → Settings → **Deployment Protection** → enable Vercel Authentication (free) or Password Protection (Pro).

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
