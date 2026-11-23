#!/usr/bin/env python3
"""Secret and PII scanner for this repository.

Scans every tracked text file for credential shapes, public/private IPv4
addresses, local machine paths, agent/bid identifiers and e-mail addresses.
Exit code 0 means zero findings.

Loopback (127.0.0.0/8) and the wildcard 0.0.0.0 are intentionally allowed:
the acceptance evidence must show loopback-bound listeners.

Usage: python3 tools/scan-secrets.py [--root .]
"""
import argparse
import os
import re
import sys

RULES = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("platform_api_key", re.compile(r"cph_[A-Za-z0-9]{20,}")),
    ("openai_like_key", re.compile(r"\bsk-[A-Za-z0-9]{32,}")),
    ("inline_secret", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{16,}")),
    ("public_ipv4", re.compile(
        r"\b(?!(?:10|127|0)\.)(?!(?:192\.168)\.)(?!(?:172\.(?:1[6-9]|2\d|3[01]))\.)"
        r"(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("private_ipv4", re.compile(
        r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}"
        r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")),
    ("windows_local_path", re.compile(r"[A-Za-z]:[\\/](?:Users|awkn-lab|projects)[\\/]")),
    ("unix_home_path", re.compile(r"/home/[A-Za-z0-9._-]+/")),
    ("agent_id", re.compile(r"\b1642\b")),
    ("bid_id", re.compile(r"\b36430\b")),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".gz", ".pdf"}
SELF = os.path.basename(__file__)


def is_text(path):
    if os.path.splitext(path)[1].lower() in SKIP_EXT:
        return False
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
        return b"\x00" not in chunk
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    findings = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if name == SELF or not is_text(path):
                continue
            scanned += 1
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for no, line in enumerate(lines, 1):
                for rule, rx in RULES:
                    if rx.search(line):
                        findings.append((rule, rel, no, line.strip()[:160]))

    print(f"scanned_files={scanned}")
    if findings:
        print(f"FINDINGS={len(findings)}")
        for rule, rel, no, snippet in findings:
            print(f"  [{rule}] {rel}:{no}: {snippet}")
        return 1
    print("FINDINGS=0")
    print("VERDICT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
