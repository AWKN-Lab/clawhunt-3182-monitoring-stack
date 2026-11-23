#!/usr/bin/env python3
"""Generate MANIFEST.sha256 for this repository.

Format is compatible with `sha256sum -c MANIFEST.sha256`:

    <sha256><two spaces>./relative/path

Run from the repository root, ideally on a clean copy that contains no .git
directory, so the manifest describes exactly the files that are published.

Usage: python3 tools/gen-manifest.py [--root .]
"""
import argparse
import hashlib
import os
import sys

EXCLUDE_NAMES = {"MANIFEST.sha256"}
EXCLUDE_DIRS = {".git", "__pycache__"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for name in sorted(filenames):
            if name in EXCLUDE_NAMES:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            rows.append(f"{sha256(path)}  ./{rel}")
    rows.sort(key=lambda r: r.split("  ./", 1)[1])
    out = os.path.join(root, "MANIFEST.sha256")
    with open(out, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(rows) + "\n")
    print(f"wrote {out} files={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
