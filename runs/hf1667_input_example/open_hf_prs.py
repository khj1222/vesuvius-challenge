"""Open one pull request per PHerc.1667-iteration-N model repo on the Hugging Face Hub.

Each PR replaces README.md and modeling_inkdetection.py with the patched copies in
patched/iteration-N/ (the same two-hunk patch applied to each repo's own files).

Run with your own Hugging Face login (`hf auth login` first). Dry run by default:
    python open_hf_prs.py               # shows what would be sent, sends nothing
    python open_hf_prs.py --send        # opens the six PRs
    python open_hf_prs.py --send --only 5
"""
import argparse, sys
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd

HERE = Path(__file__).resolve().parent
DESCRIPTION = HERE / "hf_pr_description.md"
TITLE = "Model card / docstring: state the input scaling that actually works (clip [0,200] / 255)"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="actually open the PRs")
    ap.add_argument("--only", type=int, nargs="*", help="iteration numbers, default all six")
    args = ap.parse_args()
    iterations = args.only if args.only else [0, 1, 2, 3, 4, 5]
    description = DESCRIPTION.read_text(encoding="utf-8")
    api = HfApi()
    if args.send:
        me = api.whoami()["name"]
        print(f"logged in as {me}")
    for it in iterations:
        repo = f"scrollprize/PHerc.1667-iteration-{it}"
        src = HERE / "patched" / f"iteration-{it}"
        ops = [
            CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=str(src / "README.md")),
            CommitOperationAdd(path_in_repo="modeling_inkdetection.py", path_or_fileobj=str(src / "modeling_inkdetection.py")),
        ]
        print(f"{repo}: {len(ops)} files from {src}")
        if not args.send:
            continue
        info = api.create_commit(
            repo_id=repo, repo_type="model", operations=ops,
            commit_message=TITLE, commit_description=description, create_pr=True,
        )
        print("  ->", info.pr_url)
    if not args.send:
        print("dry run only; pass --send to open the pull requests")

if __name__ == "__main__":
    sys.exit(main())
