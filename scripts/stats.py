"""Generate profile/stats.svg and profile/langs.svg, private repos included.

Needs GH_TOKEN with `repo` + `read:user` scope (GITHUB_TOKEN can't see your private repos).
"""
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from html import escape

USER = "zcy22606"
TOKEN = os.environ["GH_TOKEN"]
OUT = os.path.join(os.path.dirname(__file__), "..", "profile")


def api(path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def search_count(kind, q):
    return api(f"/search/{kind}?per_page=1&q=" + urllib.parse.quote(q))["total_count"]


def fmt(n):
    return f"{n:,}"


year_ago = (dt.date.today() - dt.timedelta(days=365)).isoformat()
gql = api("/graphql", {"query": """{user(login:"%s"){
  contributionsCollection{contributionCalendar{totalContributions}}
  repositories(ownerAffiliations:OWNER,isFork:false,first:100){nodes{
    languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}""" % USER})["data"]["user"]

stats = [
    ("Contributions (last year)", gql["contributionsCollection"]["contributionCalendar"]["totalContributions"]),
    ("Commits (last year)", search_count("commits", f"author:{USER} committer-date:>{year_ago}")),
    ("Commits (all time)", search_count("commits", f"author:{USER}")),
    ("Pull requests", search_count("issues", f"author:{USER} type:pr")),
]

langs = {}
for repo in gql["repositories"]["nodes"]:
    for e in repo["languages"]["edges"]:
        name, color = e["node"]["name"], e["node"]["color"] or "#8b949e"
        langs.setdefault(name, [0, color])[0] += e["size"]
top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
total = sum(v[0] for _, v in top)

FONT = "font-family='-apple-system,Segoe UI,Helvetica,Arial,sans-serif'"
GRAY = "#8b949e"  # readable on both light and dark GitHub themes

rows = "".join(
    f"<text x='0' y='{24 + i * 30}' fill='{GRAY}' font-size='14'>{escape(label)}</text>"
    f"<text x='300' y='{24 + i * 30}' fill='{GRAY}' font-size='14' font-weight='600' text-anchor='end'>{fmt(n)}</text>"
    for i, (label, n) in enumerate(stats)
)
stats_svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='300' height='130' {FONT}>{rows}</svg>"

x, bar = 0.0, ""
for _, (size, color) in top:
    w = 300 * size / total
    bar += f"<rect x='{x:.2f}' y='8' width='{w:.2f}' height='8' fill='{color}'/>"
    x += w
legend = "".join(
    f"<circle cx='{(i % 2) * 150 + 5}' cy='{44 + (i // 2) * 26}' r='5' fill='{color}'/>"
    f"<text x='{(i % 2) * 150 + 16}' y='{49 + (i // 2) * 26}' fill='{GRAY}' font-size='13'>"
    f"{escape(name)} {size / total * 100:.1f}%</text>"
    for i, (name, (size, color)) in enumerate(top)
)
langs_svg = (
    f"<svg xmlns='http://www.w3.org/2000/svg' width='300' height='130' {FONT}>"
    f"<clipPath id='r'><rect y='8' width='300' height='8' rx='4'/></clipPath>"
    f"<g clip-path='url(#r)'>{bar}</g>{legend}</svg>"
)

os.makedirs(OUT, exist_ok=True)
for name, svg in (("stats.svg", stats_svg), ("langs.svg", langs_svg)):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(svg)
print(stats, [(n, round(v[0] / total * 100, 1)) for n, v in top])
