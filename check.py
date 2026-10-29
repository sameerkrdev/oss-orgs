"""Self-check: parsers + data/gsoc.json matches the GSoC API counts. Run: python -I check.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import classify, contributor_ref, gh_login, name_match, parse_github  # noqa: E402
from programs import PREFIX, TERM  # noqa: E402

m = PREFIX.match("CNCF - Jaeger: Jaeger v2 Helm Chart (2024 Term 3)")
assert m.group(1) == "Jaeger" and TERM.sub("", m.group(2)) == "Jaeger v2 Helm Chart"
assert TERM.sub("", "Expanding coverage (2025 Term ") == "Expanding coverage"
assert not PREFIX.match("Open Mainframe Project - Mainframe Modernization White Paper")

assert name_match("Sahil Patidar", None, "SahilPatidar")
assert name_match("Meet Soni", "Meet Soni", "inosmeet")
assert not name_match("AnshulPatil2005", "Emmett Lalish", "elalish")

assert gh_login("Ahmed Osama") is None
assert gh_login("@jane-doe") == "jane-doe"
assert gh_login("https://github.com/jane-doe/") == "jane-doe"
assert gh_login("jane_doe") is None

assert contributor_ref("https://gist.github.com/dre-droid/effd22ce0f7ed1") == ("owner", "dre-droid")
assert contributor_ref("https://gist.github.com/effd22ce0f7ed13914d446367b4bab64") is None  # anonymous gist id
assert contributor_ref("https://github.com/polypheny/Polypheny-UI/pull/100") == ("item", "polypheny", "Polypheny-UI", "100")
assert contributor_ref("https://github.com/org/repo/pulls?q=is%3Apr+author%3Ajane-doe") == ("author", "jane-doe")
assert contributor_ref("https://lunamorrow.github.io/2024/10/30/final.html") == ("owner", "lunamorrow")
assert contributor_ref("https://medium.com/@someone/post") is None
assert contributor_ref("https://github.com/elalish/manifold/blob/master/docs/x.md") == ("repo", "elalish")
assert parse_github("https://github.com/synfig/synfig.git") == ("repo", "synfig", "synfig")
assert parse_github("https://github.com/orgs/foo") is None
assert classify("chat", "https://owasp.org/slack/invite")[0] == "slack"
assert classify("chat", "https://t.me/x")[0] == "telegram"
assert classify("chat", "https://circuitverse.org/slack")[0] == "slack"
assert classify("chat", "https://circleci.com/gh/a/b")[0] != "irc"
assert classify("chat", "https://webchat.oftc.net/?channels=x")[0] == "irc"
assert classify("mailingList", "https://groups.google.com/g/x")[0] == "mailinglist"
assert classify("email", "a@b.org") == ("email", "mailto:a@b.org")

d = json.loads((Path(__file__).parent / "data" / "gsoc.json").read_text("utf-8"))
orgs_per_year = {y: sum(1 for o in d["orgs"] if y in o["years"]) for y in d["years"]}
projects_per_year = {y: sum(1 for p in d["projects"] if p["year"] == y) for y in d["years"]}
assert orgs_per_year == {2024: 194, 2025: 185, 2026: 183}, orgs_per_year
assert projects_per_year == {2024: 1127, 2025: 1191, 2026: 1101}, projects_per_year
slugs = {o["slug"] for o in d["orgs"]}
assert all(p["org"] in slugs for p in d["projects"]), "project with unknown org"
assert all(p["gh"] in d["users"] for p in d["projects"] if p.get("gh")), "project gh user missing"
print("ok", orgs_per_year, projects_per_year,
      f"github: {sum(1 for p in d['projects'] if p.get('gh'))}, prs: {sum(1 for p in d['projects'] if p.get('prs'))}")
