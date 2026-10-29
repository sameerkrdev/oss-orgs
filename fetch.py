"""Fetch GSoC 2024-2026 orgs + projects and enrich them from GitHub, Wikidata, Open Collective.

Every HTTP response is cached under cache/, so reruns are resumable and free.
Usage: python -I fetch.py [--limit N]
"""
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT / "data"
YEARS = (2024, 2025, 2026)
GSOC = "https://summerofcode.withgoogle.com/api"
GH = "https://api.github.com"
UA = "gsoc-explorer/0.1 (personal research script)"
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None

_token = None
_search_lock = threading.Lock()
_last_search = [0.0]


def log(*a):
    print(*a, flush=True)


def gh_token():
    global _token
    if _token is None:
        _token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    return _token


def get(url, body=None, search=False):
    """GET (or POST json `body`) with disk cache. Returns (status, data)."""
    key = hashlib.sha1((url + (json.dumps(body, sort_keys=True) if body else "")).encode()).hexdigest()
    path = CACHE / key[:2] / f"{key}.json"
    if path.exists():
        c = json.loads(path.read_text("utf-8"))
        return c["s"], c["d"]
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if url.startswith(GH):
        headers["Authorization"] = f"Bearer {gh_token()}"
        headers["Accept"] = "application/vnd.github+json"
    if isinstance(body, str):  # SPARQL query
        headers["Content-Type"] = "application/sparql-query"
        headers["Accept"] = "application/sparql-results+json"
    elif body is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(6):
        if search:  # GitHub search API: 30 req/min
            with _search_lock:
                wait = _last_search[0] + 2.1 - time.time()
                if wait > 0:
                    time.sleep(wait)
                _last_search[0] = time.time()
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                s, raw = r.status, r.read()
        except urllib.error.HTTPError as e:
            s, raw = e.code, e.read()
            if s in (403, 429) and (e.headers.get("X-RateLimit-Remaining") == "0" or e.headers.get("Retry-After") or b"rate limit" in raw.lower()):
                reset = float(e.headers.get("X-RateLimit-Reset") or 0)
                pause = int(max(float(e.headers.get("Retry-After") or 0), reset - time.time() + 2, 30))
                log(f"  rate limited, sleeping {pause}s ({url[:80]})")
                time.sleep(min(pause, 3700))
                continue
            if s >= 500:
                time.sleep(2 ** attempt)
                continue
        except (http.client.HTTPException, OSError) as e:  # timeouts, resets, truncated bodies
            log(f"  net error {e} ({url[:80]}), retry")
            time.sleep(2 ** attempt)
            continue
        try:
            d = json.loads(raw or b"null")
        except ValueError:
            d = None
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"s": s, "d": d}), "utf-8")
        os.replace(tmp, path)
        return s, d
    return 0, None


def pmap(fn, items, workers=8):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fn, items))


def host(url):
    try:
        h = urllib.parse.urlparse(url if "://" in url else "https://" + url).netloc.lower()
    except ValueError:  # malformed, e.g. stray "[" read as an IPv6 host
        return ""
    return h[4:] if h.startswith("www.") else h


def same_site(a, b):
    a, b = host(a), host(b)
    return bool(a and b) and (a == b or a.endswith("." + b) or b.endswith("." + a))


# ---------- community links ----------

CHAT = [
    ("slack", ("slack.com", "slack.")), ("discord", ("discord.gg", "discord.com", "discordapp")),
    ("zulip", ("zulip",)), ("matrix", ("matrix.to", "matrix.", "element.io", "app.element")),
    ("gitter", ("gitter.im",)), ("irc", ("libera.chat", "irc.", "oftc.net", "kiwiirc", "freenode")),
    ("telegram", ("t.me", "telegram")), ("whatsapp", ("whatsapp", "wa.me")),
    ("mattermost", ("mattermost",)), ("rocketchat", ("rocket.chat", "rocketchat")),
    ("github", ("github.com",)), ("gitlab", ("gitlab",)),
]


def classify(name, value):
    v = value.strip()
    if name == "email" or (v and "@" in v and "://" not in v):
        return "email", v if v.startswith("mailto:") else "mailto:" + v
    url = v if "://" in v else "https://" + v
    h = host(url)
    if name == "twitter" or h in ("twitter.com", "x.com"):
        return "x", url
    if name == "facebook":
        return "facebook", url
    if name == "blog":
        return "blog", url
    for kind, needles in CHAT:
        if any(n in h for n in needles):
            return kind, url
    for kind in ("slack", "discord", "zulip", "matrix", "gitter", "telegram", "whatsapp", "mattermost", "rocketchat"):
        if kind in url.lower():  # e.g. owasp.org/slack/invite
            return kind, url
    if "discourse" in h or "forum" in h or "discuss" in h or "/forum" in url:
        return "forum", url
    if name == "mailingList" or "groups.google" in h or "lists." in h or "mail" in h:
        return "mailinglist", url
    return "chat" if name == "chat" else "other", url


# ---------- GitHub url parsing ----------

RESERVED = {"orgs", "apps", "features", "sponsors", "settings", "topics", "marketplace", "search", "collections", "about", "login"}


def parse_github(url):
    """Return ('owner', o) | ('repo', o, r) | None for a github.com source URL."""
    m = re.match(r"https?://(?:www\.)?github\.com/([\w.-]+)(?:/([\w.-]+))?", url or "")
    if not m or m.group(1).lower() in RESERVED:
        return None
    o, r = m.group(1), m.group(2)
    if r and r.endswith(".git"):
        r = r[:-4]
    return ("repo", o, r) if r else ("owner", o)


def contributor_ref(url):
    """Where to look for the contributor's GitHub login in a final-work URL."""
    if not url:
        return None
    u = url.strip()
    m = re.search(r"author(?:%3A|:|=)([A-Za-z0-9-]+)", u)
    if m and "github.com" in u:
        return ("author", m.group(1))
    m = re.match(r"https?://gist\.github\.com/([\w-]+)(?:/|$|\?|#)", u)
    if m and not re.fullmatch(r"[0-9a-f]{20,}", m.group(1)):
        return ("owner", m.group(1))
    m = re.match(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(pull|issues)/(\d+)", u)
    if m:
        return ("item", m.group(1), m.group(2), m.group(4))
    m = re.match(r"https?://([\w-]+)\.github\.io", u)
    if m:
        return ("owner", m.group(1))
    p = parse_github(u)
    if p:
        return ("repo", p[1])  # weakest signal: anyone's repo can host the report
    return None


def gh_login(v):
    """GSoC's github_username is free text: accept a login, @login or profile URL; reject names."""
    v = (v or "").strip().rstrip("/")
    m = re.search(r"github\.com/([^/?#\s]+)", v)
    v = (m.group(1) if m else v).lstrip("@")
    return v if re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", v) else None


def name_tokens(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 1}


def name_match(name, gh_name, login):
    """Does the GSoC contributor name plausibly belong to this GitHub account?"""
    a = name_tokens(name)
    sq = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())  # noqa: E731
    n, lg = sq(name), login.lower()
    return bool(a & (name_tokens(gh_name) | name_tokens(login))) or bool(n and (n in sq(lg) or sq(lg) in n)) \
        or any(len(t) >= 4 and t in lg for t in a)


# ---------- steps ----------

def step_gsoc():
    orgs, projects = {}, []
    for y in YEARS:
        s, data = get(f"{GSOC}/program/{y}/organizations/")
        assert s == 200, f"orgs {y}: {s}"
        for o in data:
            cur = orgs.setdefault(o["slug"], {"years": [], "links": {}})
            cur["years"].append(y)
            for k in ("name", "slug", "logo_url", "website_url", "tagline", "description", "license", "categories",
                      "tech_tags", "topic_tags", "source_code", "ideas_link", "contributor_guidance_url"):
                cur[k] = o.get(k)  # later years overwrite -> latest profile
            for l in o.get("contact_links") or []:
                kind, url = classify(l["name"], l["value"])
                cur["links"][url] = kind
        s, data = get(f"{GSOC}/projects/?program_slug={y}")
        assert s == 200, f"projects {y}: {s}"
        for p in data["entities"]["projects"]:
            projects.append({
                "id": p["uid"], "year": y, "org": p["organization_slug"], "title": p["title"],
                "body": p.get("body") or "", "size": p.get("size"), "tech": p.get("tech_tags") or [],
                "topics": p.get("topic_tags") or [], "status": p.get("status"),
                "mentors": p.get("assigned_mentors") or [],
                "name": (p.get("contributor_name") or "").strip().strip("<>").strip(),
                "code": p.get("project_code_url"), "gsoc_gh": p.get("github_username"),
                "url": f"https://summerofcode.withgoogle.com/programs/{y}/projects/{p['uid']}",
            })
        log(f"{y}: {len(data['entities']['projects'])} projects")
    for o in orgs.values():
        o["links"] = [{"type": k, "url": u} for u, k in o["links"].items()]
        o["page"] = f"https://summerofcode.withgoogle.com/programs/{o['years'][-1]}/organizations/{o['slug']}"
    return orgs, projects


def step_github_orgs(orgs):
    def one(o):
        ref = parse_github(o.get("source_code"))
        if not ref:
            return None
        owner = ref[1]
        g = {"owner": owner}
        s, u = get(f"{GH}/users/{owner}")
        if s == 200:
            g.update(type=u.get("type"), blog=u.get("blog"), twitter=u.get("twitter_username"),
                     email=u.get("email"), followers=u.get("followers"), public_repos=u.get("public_repos"),
                     owner_created=u.get("created_at"), owner_name=u.get("name"), location=u.get("location"))
        repo = ref[2] if ref[0] == "repo" else None
        if not repo:  # org URL -> most-starred repo
            s, rs = get(f"{GH}/users/{owner}/repos?per_page=100&sort=pushed")
            if s == 200 and rs:
                repo = max(rs, key=lambda r: r.get("stargazers_count", 0))["name"]
        if repo:
            s, r = get(f"{GH}/repos/{owner}/{repo}")
            if s == 200:
                g.update(repo=r["full_name"], stars=r["stargazers_count"], forks=r["forks_count"],
                         issues=r["open_issues_count"], lang=r.get("language"), topics=r.get("topics") or [],
                         created=r.get("created_at"), pushed=r.get("pushed_at"), homepage=r.get("homepage"), desc=r.get("description"))
                s, langs = get(f"{GH}/repos/{r['full_name']}/languages")
                if s == 200 and langs:
                    tot = sum(langs.values()) or 1
                    g["langs"] = {k: round(v * 100 / tot, 1) for k, v in sorted(langs.items(), key=lambda kv: -kv[1])[:8]}
        return g

    for o, g in zip(orgs.values(), pmap(one, list(orgs.values()))):
        o["gh"] = g
    log(f"github orgs: {sum(1 for o in orgs.values() if o.get('gh'))}/{len(orgs)}")


WD = "https://www.wikidata.org/w/api.php"
WD_PROPS = {"P112": "founded_by", "P571": "inception", "P749": "parent", "P127": "owned_by", "P859": "sponsor",
            "P8324": "funder", "P452": "industry", "P169": "ceo", "P488": "chair", "P159": "hq", "P17": "country"}


def site_variants(url):
    u = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    h, path = host(url), u.path.rstrip("/")
    return {f"{sc}://{w}{h}{pth}" for sc in ("http", "https") for w in ("", "www.") for pth in {path, path + "/", "", "/"}}


def step_wikidata(orgs):
    """Batched SPARQL: items whose official website (P856) or GitHub username (P2037) is the org's."""
    by_site, by_gh = {}, {}
    for slug, o in orgs.items():
        if o.get("website_url"):
            for v in site_variants(o["website_url"]):
                by_site[v] = slug
        if (o.get("gh") or {}).get("owner"):
            by_gh[o["gh"]["owner"]] = slug
    cands = {}  # slug -> [(qid, via_site)]
    sites, ghs = sorted(by_site), sorted(by_gh)
    for i in range(0, max(len(sites), len(ghs)), 400):
        vs = " ".join(f"<{x}>" for x in sites[i:i + 400] if ">" not in x and " " not in x)
        vg = " ".join(json.dumps(x) for x in ghs[i:i + 400])
        q = (f"SELECT ?item ?site ?gh WHERE {{ {{ VALUES ?site {{ {vs} }} ?item wdt:P856 ?site }} "
             f"UNION {{ VALUES ?gh {{ {vg} }} ?item wdt:P2037 ?gh }} }}")
        s, r = get("https://query.wikidata.org/sparql", body=q)
        assert s == 200, f"sparql {s}"
        for b in r["results"]["bindings"]:
            qid = b["item"]["value"].rsplit("/", 1)[1]
            slug = by_site.get(b["site"]["value"]) if "site" in b else by_gh.get(b["gh"]["value"])
            if slug:
                cands.setdefault(slug, []).append((qid, "site" in b))
    qids = sorted({q for l in cands.values() for q, _ in l})
    ents = {}
    for i in range(0, len(qids), 50):
        s, r = get(f"{WD}?action=wbgetentities&format=json&props=claims|sitelinks&ids={'|'.join(qids[i:i + 50])}")
        ents.update((r or {}).get("entities") or {})

    def pick(slug):
        best = max(cands.get(slug, []), default=None,
                   key=lambda c: (c[1], sum(1 for p in WD_PROPS if p in (ents.get(c[0]) or {}).get("claims", {}))))
        if not best:
            return None
        e = ents.get(best[0]) or {}
        return best[0], e.get("claims") or {}, (e.get("sitelinks") or {}).get("enwiki", {}).get("title")

    found = [pick(slug) for slug in orgs]
    need = set()
    for f in found:
        if f:
            for p in WD_PROPS:
                for c in f[1].get(p, []):
                    v = c["mainsnak"].get("datavalue", {}).get("value")
                    if isinstance(v, dict) and v.get("id"):
                        need.add(v["id"])
    labels = {}
    need = sorted(need)
    for i in range(0, len(need), 50):
        s, ents = get(f"{WD}?action=wbgetentities&format=json&props=labels&languages=en&ids={'|'.join(need[i:i + 50])}")
        for qid, e in ((ents or {}).get("entities") or {}).items():
            labels[qid] = ((e.get("labels") or {}).get("en") or {}).get("value", qid)
    for o, f in zip(orgs.values(), found):
        if not f:
            continue
        qid, claims, wiki = f
        facts = {"wikidata": f"https://www.wikidata.org/wiki/{qid}"}
        if wiki:
            facts["wikipedia"] = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(wiki.replace(" ", "_"))
        for p, k in WD_PROPS.items():
            vals = []
            for c in claims.get(p, []):
                v = c["mainsnak"].get("datavalue", {}).get("value")
                if isinstance(v, dict) and v.get("id"):
                    vals.append(labels.get(v["id"], v["id"]))
                elif isinstance(v, dict) and v.get("time"):
                    vals.append(v["time"].lstrip("+")[:4])
            if vals:
                facts[k] = list(dict.fromkeys(vals))
        o["facts"] = facts
    log(f"wikidata matched: {sum(1 for f in found if f)}/{len(orgs)}")


OC = "https://api.opencollective.com/graphql/v2"
OC_Q = """query($slug:String){account(slug:$slug,throwIfMissing:false){slug name website githubHandle repositoryUrl
 stats{totalAmountReceived{valueInCents currency} yearlyBudget{valueInCents currency}}
 ... on AccountWithHost{host{name slug}}}}"""


def step_opencollective(orgs, out):
    """Fills out[slug] (runs in its own thread; OC throttles to a few req/min)."""
    for slug, o in orgs.items():
        owner = (o.get("gh") or {}).get("owner", "")
        cands = dict.fromkeys(c for c in (o["slug"], owner.lower(), re.sub(r"[^a-z0-9]+", "-", o["name"].lower()).strip("-")) if c)
        for c in cands:
            s, r = get(OC, body={"query": OC_Q, "variables": {"slug": c}})
            a = ((r or {}).get("data") or {}).get("account")
            if not a:
                continue
            gh = (a.get("githubHandle") or "").lower()
            ok = same_site(a.get("website") or "", o.get("website_url") or "") or (
                owner and (gh.split("/")[0] == owner.lower() or f"github.com/{owner.lower()}/" in (a.get("repositoryUrl") or "").lower() + "/"))
            if not ok:
                continue
            st = a.get("stats") or {}
            raised, budget = st.get("totalAmountReceived") or {}, st.get("yearlyBudget") or {}
            out[slug] = {
                "url": f"https://opencollective.com/{a['slug']}", "host": (a.get("host") or {}).get("name"),
                "raised": round((raised.get("valueInCents") or 0) / 100), "budget": round((budget.get("valueInCents") or 0) / 100),
                "currency": raised.get("currency") or budget.get("currency") or "USD"}
            break
    log(f"open collective matched: {len(out)}/{len(orgs)}")


def step_contributors(orgs, projects):
    org_owner = {slug: ((o.get("gh") or {}).get("owner") or "").lower() for slug, o in orgs.items()}
    users = {}

    def user(login):
        s, u = get(f"{GH}/users/{login}")
        return u if s == 200 else None

    def resolve(p):
        """-> (login, how, extra_owner) ; never guesses from the contributor's name alone."""
        if gh_login(p["gsoc_gh"]):
            return gh_login(p["gsoc_gh"]), "gsoc", None
        ref = contributor_ref(p["code"])
        if not ref:
            return None, None, None
        if ref[0] == "author":
            gp = parse_github(p["code"])
            return ref[1], "author", gp[1] if gp else None
        if ref[0] == "item":
            s, it = get(f"{GH}/repos/{ref[1]}/{ref[2]}/issues/{ref[3]}")
            login = ((it or {}).get("user") or {}).get("login") if s == 200 else None
            return login, "author", ref[1]
        login = ref[1]
        if login.lower() == org_owner.get(p["org"]):
            return None, None, login
        u = user(login)
        if not u:
            return None, None, None
        if u.get("type") != "User":
            return None, None, u["login"]
        return login, "repo" if ref[0] == "repo" else "owner", None

    resolved = pmap(resolve, projects)
    # an account "owning" final-work links of 2+ different contributors in one org is the org's/lead's
    # account (e.g. a lead's personal repo hosting the project): unlink it from contributors it doesn't name-match
    names_per_owner = {}
    for p, (login, how, _) in zip(projects, resolved):
        if how in ("owner", "repo"):
            names_per_owner.setdefault((p["org"], login.lower()), set()).add(p["name"].lower())
    for i, (p, (login, how, extra)) in enumerate(zip(projects, resolved)):
        if how in ("owner", "repo") and (how == "repo" or len(names_per_owner[(p["org"], login.lower())]) > 1) \
                and not name_match(p["name"], (user(login) or {}).get("name"), login):
            resolved[i] = (None, None, login)
        elif how == "repo":
            resolved[i] = (login, "owner", extra)
    seen = {}  # org slug -> {github owner: hits}, from final-work links
    for p, (login, how, extra) in zip(projects, resolved):
        if extra:
            c = seen.setdefault(p["org"], {})
            c[extra] = c.get(extra, 0) + 1
    contrib = {l.lower() for l, _, _ in resolved if l}
    for slug, o in orgs.items():
        main_owner = (o.get("gh") or {}).get("owner")
        extra = [k for k, _ in sorted(seen.get(slug, {}).items(), key=lambda kv: -kv[1])
                 if k.lower() != (main_owner or "").lower() and k.lower() not in contrib]
        o["gh_owners"] = ([main_owner] if main_owner else []) + extra
    for p, (login, how, extra) in zip(projects, resolved):
        if not login:
            continue
        u = user(login)
        if not u:
            continue
        # owner-of-link matches are dropped when the account is one of the project's mentors
        mentors = {m.lower() for m in p["mentors"]}
        if how == "owner" and ((u.get("name") or "").lower() in mentors or login.lower() in mentors):
            continue
        p["gh"], p["how"] = u["login"], how
        p["name_ok"] = name_match(p["name"], u.get("name"), login)
        users[u["login"]] = u
    log(f"contributors with github: {sum(1 for p in projects if p.get('gh'))}/{len(projects)}")

    logins = sorted(users)
    socials = dict(zip(logins, pmap(lambda l: get(f"{GH}/users/{l}/social_accounts")[1] or [], logins)))
    out = {}
    for l, u in users.items():
        out[l] = {k: u.get(k) for k in ("name", "bio", "company", "location", "blog", "twitter_username", "followers", "public_repos", "avatar_url", "created_at")}
        out[l]["socials"] = [{"provider": s["provider"], "url": s["url"]} for s in socials.get(l) or [] if isinstance(s, dict)]
    return out


def step_prs(orgs, projects):
    todo = [p for p in projects if p.get("gh")]
    for i, p in enumerate(todo):
        # ponytail: owners only from source_code + final-work links; orgs spread over unseen GitHub orgs are undercounted
        owners = [o for o in (orgs.get(p["org"]) or {}).get("gh_owners", [])[:6] if o.lower() != p["gh"].lower()]
        if not owners:
            continue
        y = p["year"]
        q = f"is:pr author:{p['gh']} " + " ".join(f"user:{o}" for o in sorted(owners)) + f" created:{y}-01-01..{y}-12-31"
        s, r = get(f"{GH}/search/issues?per_page=100&sort=created&order=asc&q={urllib.parse.quote(q)}", search=True)
        if s != 200 or not r:
            continue
        items = r.get("items") or []
        merged = [it for it in items if (it.get("pull_request") or {}).get("merged_at")]
        p["prs"] = {
            "total": r.get("total_count", 0), "merged": len(merged),
            "open": sum(1 for it in items if it.get("state") == "open"),
            "search": "https://github.com/search?type=pullrequests&q=" + urllib.parse.quote(q),
            "items": [{"t": it["title"], "u": it["html_url"],
                       "s": "merged" if (it.get("pull_request") or {}).get("merged_at") else it.get("state")}
                      for it in (merged + [x for x in items if x not in merged])[:12]],
        }
        if i % 100 == 0:
            log(f"  prs {i}/{len(todo)}")
    log(f"projects with PR data: {sum(1 for p in projects if p.get('prs'))}")


def main():
    orgs, projects = step_gsoc()
    if LIMIT:
        keep = set(list(orgs)[:LIMIT])
        orgs = {k: v for k, v in orgs.items() if k in keep}
        projects = [p for p in projects if p["org"] in keep]
    step_github_orgs(orgs)
    step_wikidata(orgs)
    oc = {}
    oc_thread = threading.Thread(target=step_opencollective, args=(orgs, oc))
    oc_thread.start()
    write(orgs, projects, {})  # page usable early; rewritten below
    users = step_contributors(orgs, projects)
    write(orgs, projects, users)
    step_prs(orgs, projects)
    oc_thread.join()
    for slug, v in oc.items():
        orgs[slug].setdefault("facts", {})["oc"] = v
    write(orgs, projects, users)


GSOC_META = {"key": "gsoc", "name": "GSoC", "title": "Google Summer of Code", "sources": "the GSoC API, GitHub, Wikidata and Open Collective"}


def write(orgs, projects, users, meta=GSOC_META, years=YEARS, **extra):
    data = {"generated": time.strftime("%Y-%m-%d"), "program": meta, "years": list(years),
            "orgs": sorted(orgs.values(), key=lambda o: o["name"].lower()), "projects": projects, "users": users, **extra}
    OUT.mkdir(exist_ok=True)
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (OUT / f"{meta['key']}.json").write_text(txt, "utf-8")
    (OUT / f"{meta['key']}.js").write_text("window.DATA=" + txt + ";\n", "utf-8")
    log(f"wrote data/{meta['key']}.json: {len(orgs)} orgs, {len(projects)} projects, {len(users)} users, {len(txt) // 1024} KB")


if __name__ == "__main__":
    main()
