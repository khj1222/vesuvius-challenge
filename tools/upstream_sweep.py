#!/usr/bin/env python
"""Sweep every upstream thread this repository is involved in, and report what changed.

Reads the public GitHub API without credentials. Prints one line per thread and then the
comments and reviews newer than a cutoff, so a session can see at a glance whether anything
needs an answer.

Usage
-----
    python tools/upstream_sweep.py                 # anything newer than 24 hours
    python tools/upstream_sweep.py --since 2026-08-31T12:00:00Z
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys

REPO = "ScrollPrize/villa"
US = "khj1222"

# threads we opened, were asked into, or commented on
THREADS = [
    (1535, "our PR: flat_depth_targets"),
    (1608, "our PR: holdout config generator"),
    (1661, "our PR: patch cache fingerprint (F4)"),
    (1662, "our PR: compile fallback (F2)"),
    (1663, "our PR: staged publish (F3)"),
    (1231, "our issue: no validation mask"),
    (1611, "our issue: renderer stall"),
    (1638, "our issue: held-out audit (closed, locked)"),
    (1471, "their PR: striped TIFF streaming (we were asked in)"),
    (1580, "their PR: input scale report (we commented)"),
    (1582, "their issue: representation provenance (we commented)"),
    (192, "their issue: accurate 3d ink labels (we contributed)"),
    (1547, "their issue: duplicate surfaces (our corpus)"),
]


def curl(url: str):
    raw = subprocess.run(["curl", "-sL", url], capture_output=True).stdout.decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default=None,
                        help="ISO timestamp; default is 24 hours ago.")
    parser.add_argument("--hours", type=float, default=24.0)
    args = parser.parse_args(argv)

    cutoff = (args.since or
              (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=args.hours))
              .strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"cutoff: {cutoff}\n")

    news = []
    for number, label in THREADS:
        issue = curl(f"https://api.github.com/repos/{REPO}/issues/{number}")
        if not issue or "number" not in issue:
            print(f"  #{number}: could not read")
            continue
        is_pr = "pull_request" in issue
        extra = ""
        if is_pr:
            pull = curl(f"https://api.github.com/repos/{REPO}/pulls/{number}") or {}
            extra = (f" draft={pull.get('draft')} merged={pull.get('merged')} "
                     f"mergeable={pull.get('mergeable')} reviewers="
                     f"{[r['login'] for r in pull.get('requested_reviewers') or []]}")
        print(f"  #{number:<5} {issue['state']:<6} {issue.get('state_reason') or '':<12} "
              f"upd {issue['updated_at'][:16]} cmts {issue['comments']:<3}{extra}  {label}")

        for comment in curl(f"https://api.github.com/repos/{REPO}/issues/{number}/comments?per_page=100") or []:
            if comment["created_at"] > cutoff and comment["user"]["login"] != US:
                news.append((comment["created_at"], number, comment["user"]["login"],
                             "comment", " ".join((comment.get("body") or "").split())[:400],
                             comment["html_url"]))
        if is_pr:
            for review in curl(f"https://api.github.com/repos/{REPO}/pulls/{number}/reviews?per_page=100") or []:
                if (review.get("submitted_at") or "") > cutoff and review["user"]["login"] != US:
                    news.append((review["submitted_at"], number, review["user"]["login"],
                                 f"review {review['state']}",
                                 " ".join((review.get("body") or "").split())[:400],
                                 review["html_url"]))

    print()
    if not news:
        print(f"nothing new from anyone else since {cutoff}")
        return 0
    print(f"=== {len(news)} new item(s) from others ===")
    for when, number, who, kind, body, url in sorted(news):
        print(f"\n  [{when}] #{number} {who} ({kind})")
        print(f"  {url}")
        print(f"  {body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
