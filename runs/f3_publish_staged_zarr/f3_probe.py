"""What actually blocks a directory rename on Windows?

The prepare script fails at `partial.replace(output)` with WinError 5 after writing every
tile. This asks which condition reproduces that, so the fix addresses the real cause
rather than the first plausible one.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path


def attempt(name: str, setup) -> dict[str, object]:
    root = Path(tempfile.mkdtemp(prefix="f3probe."))
    staged = root / "out.zarr.partial"
    target = root / "out.zarr"
    staged.mkdir()
    (staged / "chunk.0.0").write_bytes(b"payload")
    (staged / ".zarray").write_text("{}", encoding="utf-8")
    holder = None
    try:
        holder = setup(staged)
        try:
            staged.replace(target)
            outcome = "renamed"
        except Exception as exc:  # noqa: BLE001 - the failure is the datum
            outcome = f"{type(exc).__name__}: {getattr(exc, 'winerror', None)} {exc}"
    finally:
        try:
            if holder is not None:
                close = getattr(holder, "close", None)
                if callable(close):
                    close()
        except Exception:  # noqa: BLE001
            pass
        try:
            shutil.rmtree(root, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
    return {"case": name, "result": str(outcome)[:150]}


def open_file_inside(staged: Path):
    return open(staged / "chunk.0.0", "rb")


def open_file_for_write_inside(staged: Path):
    return open(staged / "chunk.0.1", "wb")


def unfinished_scandir(staged: Path):
    iterator = os.scandir(staged)
    next(iterator)  # leave the directory handle open
    return iterator


def cwd_inside(staged: Path):
    class _Cwd:
        def __init__(self, previous: str) -> None:
            self.previous = previous

        def close(self) -> None:
            os.chdir(self.previous)

    previous = os.getcwd()
    os.chdir(staged)
    return _Cwd(previous)


def nothing(staged: Path):
    return None


CASES = [
    ("nothing held", nothing),
    ("a file inside open for read", open_file_inside),
    ("a file inside open for write", open_file_for_write_inside),
    ("an unfinished os.scandir on the directory", unfinished_scandir),
    ("the process cwd inside the directory", cwd_inside),
]

print(json.dumps([attempt(name, setup) for name, setup in CASES], indent=1))
