"""LFX Mentorship and Summer of Bitcoin in the same shape as the GSoC data, enriched by the same steps.

LFX: public mentorship API -> one project per accepted/graduated mentee (2024-2026), grouped by the
     sub-project named in the title ("CNCF - Jaeger: ...") or else the LF foundation.
SoB: the site's Softr/Airtable feeds -> 2026 orgs, mentors and alumni. SoB publishes no per-student
     project list, so the contributors tab shows alumni instead.
Usage: python -I programs.py [lfx|sob]
"""
import collections
import datetime
import html
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # -I drops the script dir
from fetch import (YEARS, get, log, parse_github, step_contributors, step_github_orgs,  # noqa: E402
                   step_opencollective, step_prs, step_wikidata, write)

slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")  # noqa: E731
text = lambda h: html.unescape(re.sub(r"<[^>]+>", "\n", h or "")).replace("\xa0", " ").strip()  # noqa: E731

# ---------- LFX ----------
LFX = "https://api.mentorship.lfx.linuxfoundation.org/projects/cache/paginate?from={}&size=200&sortby=updatedStamp&order=desc"
LFX_META = {"key": "lfx", "name": "LFX", "title": "LFX Mentorship",
            "sources": "the LFX Mentorship API, GitHub, Wikidata and Open Collective"}
PREFIX = re.compile(r"^\s*[A-Z][A-Za-z]{1,8}\s*[-–]\s*([^:]{2,40}?)\s*:\s*(.+)$")  # "CNCF - Jaeger: title"
TERM = re.compile(r"\s*\((?:19|20)\d\d[^)]*\)?\s*$")  # trailing "(2024 Term 2)", sometimes cut off


def lfx():
    raw, i = [], 0
    while True:
        s, r = get(LFX.format(i))
        assert s == 200, f"lfx {s}"
        hits = r["hits"]["hits"]
        raw += [h["_source"] for h in hits]
        i += len(hits)
        if not hits or i >= r["hits"]["total"]["value"]:
            break
    groups = collections.defaultdict(list)
    for m in raw:
        starts = [t["startDateTime"] for t in m.get("programTerms") or [] if t.get("startDateTime")]
        year = datetime.datetime.fromtimestamp(min(starts), datetime.UTC).year if starts else None
        if year not in YEARS:
            continue
        name = m["name"].strip()
        hit = PREFIX.match(name)
        org, title = (hit.group(1), hit.group(2)) if hit else (m.get("lfProjectName") or "Linux Foundation", name)
        groups[org].append((year, TERM.sub("", title), m))
    orgs, projects = {}, []
    for org, items in groups.items():
        slug = slugify(org)
        ms = [m for _, _, m in items]
        top = lambda xs: [x for x, _ in collections.Counter(x for x in xs if x).most_common()]  # noqa: E731
        owners = top((parse_github(m.get("repoLink")) or (None, None))[1] for m in ms)
        skills = top(s.strip().lower() for m in ms for s in (m.get("apprenticeNeeds") or {}).get("skills") or [] if len(s.strip()) <= 25)
        foundation = top(m.get("lfProjectName") for m in ms)
        latest = max(ms, key=lambda m: m.get("updatedStamp") or 0)
        orgs[slug] = {
            "name": org, "slug": slug, "years": sorted({y for y, _, _ in items}), "links": [],
            "logo_url": latest.get("logoUrl") if org not in foundation else latest.get("lfProjectLogo") or latest.get("logoUrl"),
            "website_url": (top(m.get("websiteUrl") for m in ms) or [None])[0],
            "tagline": f"{foundation[0]} project" if foundation and foundation[0] != org else "Linux Foundation",
            "description": "", "license": None, "categories": foundation[:1], "tech_tags": skills[:10],
            "topic_tags": top(t.strip() for m in ms for t in (m.get("industry") or "").split(","))[:8],
            "source_code": f"https://github.com/{owners[0]}" if owners else None,
            "ideas_link": None, "contributor_guidance_url": None,
            "page": "https://mentorship.lfx.linuxfoundation.org/#projects_all",
        }
        for year, title, m in items:
            need = m.get("apprenticeNeeds") or {}
            mentees = {x["userId"]: (x, st) for st, key in (("accepted", "acceptedMentees"), ("graduated", "graduatedMentees"))
                       for x in need.get(key) or []}
            for uid, (x, status) in mentees.items():
                links = x.get("profileLinks") or {}
                projects.append({
                    "id": f"{m['projectId']}:{uid}", "year": year, "org": slug, "title": title, "body": text(m.get("description")),
                    "size": next((t.get("name") for t in m.get("programTerms") or []), None),
                    "tech": [s.strip() for s in need.get("skills") or [] if len(s.strip()) <= 25],
                    "topics": [], "status": status, "mentors": [mt.get("name") for mt in need.get("mentors") or [] if mt.get("name")],
                    "name": f"{x.get('firstName') or ''} {x.get('lastName') or ''}".strip(), "code": None,
                    "gsoc_gh": links.get("githubProfileLink"), "linkedin": links.get("linkedinProfileLink"),
                    "repo": m.get("repoLink"), "url": f"https://mentorship.lfx.linuxfoundation.org/project/{m['projectId']}",
                })
    used = {p["org"] for p in projects}
    orgs = {k: v for k, v in orgs.items() if k in used}  # like GSoC: only orgs with accepted mentees
    log(f"lfx: {len(raw)} mentorships, {len(orgs)} orgs, {len(projects)} mentee projects in {YEARS}")
    return orgs, projects


# ---------- Summer of Bitcoin ----------
SOB = "https://www.summerofbitcoin.org/v1/datasource/airtable/5abf9a13-d06f-44d6-b50c-187328a34a81/"
SOB_ORGS = SOB + "e1fe7459-43b9-446e-b78f-6bac70aa6d0c/27095893-142f-450d-ba8e-b244e02722f4/7f16bea1-c0aa-46b3-af3a-82fcec855166/data"
SOB_MENTORS = SOB + "9b402bb7-abde-4f7f-94af-8986c1d84bc0/5b8f92e8-a15f-4f75-825d-cf24b190a255/6c1f0738-89b4-42d5-9077-5e811941c5e5/data"
SOB_ALUMNI = SOB + "dc1ee5c6-2d2c-421e-b282-30b90841274b/9c409cea-b34e-4e32-933f-5e868f9e7caf/419514a1-aa23-462c-a164-606afa8cda8d/data"
SOB_META = {"key": "sob", "name": "SoB", "title": "Summer of Bitcoin", "sources": "summerofbitcoin.org, GitHub, Wikidata and Open Collective"}
# the org feed has no links; repos checked by hand against GitHub (VLS lives on GitLab)
SOB_REPOS = {
    "asmap": "https://github.com/bitcoin-core/asmap-data", "bdk": "https://github.com/bitcoindevkit/bdk",
    "bitcoin core": "https://github.com/bitcoin/bitcoin", "bitcoin design": "https://github.com/BitcoinDesign/Guide",
    "bitcoin-fuzz": "https://github.com/bitcoinfuzz/bitcoinfuzz", "braidpool": "https://github.com/braidpool/braidpool",
    "coinswap": "https://github.com/citadel-tech/coinswap", "contextvm": "https://github.com/ContextVM/sdk",
    "cove": "https://github.com/bitcoinppl/cove", "demand": "https://github.com/dmnd-pool/dmnd-client",
    "fedimint": "https://github.com/fedimint/fedimint", "floresta": "https://github.com/getfloresta/Floresta",
    "flotilla": "https://github.com/coracle-social/flotilla", "formstr": "https://github.com/formstr-hq/nostr-forms",
    "jam": "https://github.com/joinmarket-webui/jam", "kern": "https://github.com/odudex/Kern",
    "krux": "https://github.com/selfcustody/krux", "nostr components": "https://github.com/saiy2k/nostr-components",
    "nostream": "https://github.com/cameri/nostream", "seedsigner": "https://github.com/SeedSigner/seedsigner",
    "shopstr": "https://github.com/shopstr-eng/shopstr", "smite": "https://github.com/lnfuzz/smite",
    "stable channels": "https://github.com/toneloc/stable-channels", "strfry": "https://github.com/hoytech/strfry",
    "vls": "https://gitlab.com/lightning-signer/validating-lightning-signer",
}


def sob_rows(url):
    s, r = get(url, body={})
    assert s == 200, f"sob {s}"
    return [x["fields"] for x in r["records"]]


def sob():
    mentors = collections.defaultdict(list)
    for m in sob_rows(SOB_MENTORS):
        if m.get("Name"):
            mentors[(m.get("Project") or "").strip().lower()].append({"name": m["Name"].strip(), "url": m.get("Twitter")})
    orgs = {}
    for f in sob_rows(SOB_ORGS):
        name = f["Name"].strip()
        src = SOB_REPOS.get(name.lower())
        gh = parse_github(src)
        tech = f.get("Technologies") or []
        orgs[slugify(name)] = {
            "name": name, "slug": slugify(name), "years": [2026], "links": [], "website_url": None,
            "logo_url": f"https://github.com/{gh[1]}.png?size=96" if gh else None,
            "tagline": (f.get("Description") or "").strip().split(". ")[0], "description": (f.get("Description") or "").strip(),
            "license": None, "categories": ["Nostr" if "Nostr" in tech else "Bitcoin"], "tech_tags": tech, "topic_tags": [],
            "source_code": src, "ideas_link": None, "contributor_guidance_url": None,
            "page": "https://www.summerofbitcoin.org/organizations", "mentors": mentors.get(name.lower(), []),
        }
    alumni = [{"name": a["Name"].strip(), "year": a.get("Year"), "role": a.get("Role"), "company": a.get("Company")}
              for a in sob_rows(SOB_ALUMNI) if a.get("Name")]
    log(f"sob: {len(orgs)} orgs, {sum(len(o['mentors']) for o in orgs.values())} mentors matched, {len(alumni)} alumni")
    return orgs, [], alumni


def run(meta, orgs, projects, **extra):
    step_github_orgs(orgs)
    for o in orgs.values():
        g = o.get("gh") or {}
        o["description"] = o["description"] or g.get("desc") or ""
        o["website_url"] = o["website_url"] or g.get("homepage") or None
    step_wikidata(orgs)
    oc = {}
    t = threading.Thread(target=step_opencollective, args=(orgs, oc))
    t.start()
    users = step_contributors(orgs, projects)
    write(orgs, projects, users, meta, **extra)
    step_prs(orgs, projects)
    t.join()
    for slug, v in oc.items():
        orgs[slug].setdefault("facts", {})["oc"] = v
    write(orgs, projects, users, meta, **extra)


if __name__ == "__main__":
    which = sys.argv[1:] or ["sob", "lfx"]
    if "sob" in which:
        o, p, alumni = sob()
        run(SOB_META, o, p, years=[2026], alumni=alumni)
    if "lfx" in which:
        run(LFX_META, *lfx())
