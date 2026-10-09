#!/usr/bin/env python
"""Sweep every upstream thread this repository is involved in, and report what changed.

Prints one line per thread and then the comments and reviews newer than a cutoff, so a session
can see at a glance whether anything needs an answer.

Uses the `gh` CLI when it is installed and logged in, which raises the rate limit from 60
requests an hour to 5,000 and makes sweeping cheap. Without it, falls back to the
unauthenticated API over curl, where one sweep costs 30-40 of the hour's 60 calls.

Edited comments are reported too. Filtering on creation time alone misses a comment that was
revised in place, which happened on #1547: the thread's `updated_at` moved and the sweep found
nothing, because the author had edited an older comment rather than adding one.

Usage
-----
    python tools/upstream_sweep.py                 # anything newer than 24 hours
    python tools/upstream_sweep.py --since 2026-08-31T12:00:00Z
    python tools/upstream_sweep.py --no-gh         # force the unauthenticated path
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "ScrollPrize/villa"
US = "khj1222"

# threads we opened, were asked into, or commented on
THREADS = [
    (2012, "our PR: ink threshold calibrate/apply (docs/27 tool, on main)"),
    (1703, "our PR: eager fallback (F2, on main)"),
    (1705, "our PR: staged publish (F3, on main)"),
    (1796, "our PR: Copy TTA direction priors (on main)"),
    # merged, superseded or closed, still worth watching for a late maintainer word
    (1701, "our PR: patch cache fingerprint (F4, merged)"),
    (1803, "our PR: render_ink scale pass-through (closed, superseded by #1886)"),
    (1608, "our PR: holdout config generator (auto-closed)"),
    (1535, "our PR: flat_depth_targets (auto-closed)"),
    (1661, "our PR: F4 (superseded by 1701)"),
    (1662, "our PR: F2 (superseded by 1703)"),
    (1663, "our PR: F3 (superseded by 1705)"),
    (1231, "our issue: no validation mask"),
    (1611, "our issue: renderer stall"),
    (1638, "our issue: held-out audit (closed, locked)"),
    (1471, "their PR: striped TIFF streaming (we were asked in)"),
    (1580, "their PR: input scale report (we commented)"),
    (1819, "their PR: Hecate train/distill (we asked for the split manifest)"),
    (1893, "their issue: render voxel unit (we reproduced it)"),
    (1659, "their issue: PHerc.1667 input conventions (we commented)"),
    (1898, "their issue: native depth blur (we gave our blur-arm data)"),
    (1582, "their issue: representation provenance (we commented)"),
    (192, "their issue: accurate 3d ink labels (we contributed)"),
    (1547, "their issue: duplicate surfaces (our corpus)"),
]


# Hugging Face discussions we opened (not on GitHub, so the GitHub API above never sees them)
HF_THREADS = [
    *[(f"scrollprize/PHerc.1667-iteration-{i}", 1, "our HF PR: card /255 input convention")
      for i in range(6)],
    ("Qualzz20/afv_fiber_9um", 1, "our HF discussion: docs/28 numbers for the card"),
]
HF_US = "khj1222"

_GH: str | None = None       # resolved gh binary, or None for the curl fallback


def find_gh() -> str | None:
    """Locate an authenticated gh, or return None. Windows installs it off PATH."""

    override = os.environ.get("GH_BIN")
    candidates = [override] if override else []
    candidates.append(shutil.which("gh"))
    candidates += [r"C:\Program Files\GitHub CLI\gh.exe",
                   r"C:\Program Files (x86)\GitHub CLI\gh.exe"]
    for candidate in candidates:
        if not candidate or not Path(candidate).exists():
            continue
        status = subprocess.run([candidate, "auth", "status"],
                                capture_output=True, text=True, errors="replace")
        if status.returncode == 0:
            return candidate
    return None


def api(path: str):
    """GET one API path. `path` is repo-relative, e.g. issues/1608/comments?per_page=100."""

    url = f"https://api.github.com/repos/{REPO}/{path}"
    if _GH:
        done = subprocess.run([_GH, "api", f"repos/{REPO}/{path}"],
                              capture_output=True, text=True, errors="replace")
        raw = done.stdout
    else:
        raw = subprocess.run(["curl", "-sL", url],
                             capture_output=True).stdout.decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def rate_limit() -> str:
    body = None
    if _GH:
        done = subprocess.run([_GH, "api", "rate_limit"],
                              capture_output=True, text=True, errors="replace")
        try:
            body = json.loads(done.stdout)
        except json.JSONDecodeError:
            body = None
    else:
        raw = subprocess.run(["curl", "-sL", "https://api.github.com/rate_limit"],
                             capture_output=True).stdout.decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = None
    core = ((body or {}).get("resources") or {}).get("core") or {}
    if not core:
        return "rate limit unknown"
    return f"{core.get('remaining')}/{core.get('limit')} calls left this hour"


def hf_discussion(repo: str, num: int):
    """One Hugging Face discussion with its events, or None. Public API, no token needed."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}/discussions/{num}",
                                    timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:   # one unreachable discussion must not stop the sweep
        print(f"  HF {repo}#{num}: could not read ({exc.__class__.__name__})")
        return None


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default=None,
                        help="ISO timestamp; default is 24 hours ago.")
    parser.add_argument("--hours", type=float, default=24.0)
    parser.add_argument("--no-gh", action="store_true",
                        help="ignore gh and use the unauthenticated API.")
    args = parser.parse_args(argv)

    global _GH
    _GH = None if args.no_gh else find_gh()

    cutoff = (args.since or
              (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=args.hours))
              .strftime("%Y-%m-%dT%H:%M:%SZ"))
    backend = "gh (authenticated)" if _GH else "curl (unauthenticated, 60/hour)"
    print(f"cutoff: {cutoff}")
    print(f"api:    {backend} — {rate_limit()}\n")

    news = []
    for number, label in THREADS:
        issue = api(f"issues/{number}")
        if not issue or "number" not in issue:
            print(f"  #{number}: could not read")
            continue
        is_pr = "pull_request" in issue
        extra = ""
        if is_pr:
            pull = api(f"pulls/{number}") or {}
            extra = (f" draft={pull.get('draft')} merged={pull.get('merged')} "
                     f"mergeable={pull.get('mergeable')} reviewers="
                     f"{[r['login'] for r in pull.get('requested_reviewers') or []]}")
        print(f"  #{number:<5} {issue['state']:<6} {issue.get('state_reason') or '':<12} "
              f"upd {issue['updated_at'][:16]} cmts {issue['comments']:<3}{extra}  {label}")

        for comment in api(f"issues/{number}/comments?per_page=100") or []:
            if comment["user"]["login"] == US:
                continue
            created, edited = comment["created_at"], comment.get("updated_at") or ""
            if created > cutoff:
                kind, when = "comment", created
            elif edited > cutoff:
                # revised in place: invisible to a created_at filter, and the reason a thread's
                # updated_at can move while the sweep reports nothing new
                kind, when = f"comment EDITED (posted {created[:10]})", edited
            else:
                continue
            news.append((when, number, comment["user"]["login"], kind,
                         " ".join((comment.get("body") or "").split())[:400],
                         comment["html_url"]))
        if is_pr:
            for review in api(f"pulls/{number}/reviews?per_page=100") or []:
                if (review.get("submitted_at") or "") > cutoff and review["user"]["login"] != US:
                    news.append((review["submitted_at"], number, review["user"]["login"],
                                 f"review {review['state']}",
                                 " ".join((review.get("body") or "").split())[:400],
                                 review["html_url"]))

    for repo, num, label in HF_THREADS:
        discussion = hf_discussion(repo, num)
        if not discussion:
            continue
        events = discussion.get("events") or []
        last = max((e.get("createdAt") or "" for e in events), default="")
        print(f"  HF {repo}#{num} {discussion.get('status', ''):<6} last {last[:16]} "
              f"events {len(events):<3} {label}")
        for event in events:
            author = (event.get("author") or {}).get("name", "")
            when = (event.get("createdAt") or "").replace(".000Z", "Z")
            if author == HF_US or when <= cutoff:
                continue
            data = event.get("data") or {}
            body = (data.get("latest") or {}).get("raw") or data.get("status") or event.get("type", "")
            news.append((when, f"HF {repo}#{num}", author, event.get("type", "event"),
                         " ".join(str(body).split())[:400],
                         f"https://huggingface.co/{repo}/discussions/{num}"))

    print()
    if not news:
        print(f"nothing new from anyone else since {cutoff}")
        return 0
    print(f"=== {len(news)} new item(s) from others ===")
    for when, number, who, kind, body, url in sorted(news, key=lambda item: item[0]):
        ref = number if isinstance(number, str) else f"#{number}"
        print(f"\n  [{when}] {ref} {who} ({kind})")
        print(f"  {url}")
        print(f"  {body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
