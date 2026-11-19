#!/usr/bin/env python3
"""Fetch the last year of contributions and the public repo count into data/github.json.

Needs a token in GH_TOKEN (the workflow passes one). A personal access token
saved as the PROFILE_TOKEN secret also counts private contributions if you turn
that on in your GitHub profile settings; the default GITHUB_TOKEN sees public
activity only.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))
login = os.environ.get("GH_LOGIN") or cfg["login"]
token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not token:
    sys.exit("Set GH_TOKEN (or GITHUB_TOKEN) before running this script.")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false) { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "profile-cards",
    },
)
with urllib.request.urlopen(req, timeout=30) as resp:
    payload = json.load(resp)

if payload.get("errors") or not (payload.get("data") or {}).get("user"):
    sys.exit(f"GraphQL error: {payload.get('errors') or 'user not found'}")

user = payload["data"]["user"]
cal = user["contributionsCollection"]["contributionCalendar"]
out = {
    "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "total": cal["totalContributions"],
    "repos": user["repositories"]["totalCount"],
    "weeks": [
        [{"d": d["date"], "c": d["contributionCount"], "w": d["weekday"]} for d in wk["contributionDays"]]
        for wk in cal["weeks"]
    ],
}
(ROOT / "data" / "github.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(f"{out['total']} contributions, {out['repos']} public repos")
