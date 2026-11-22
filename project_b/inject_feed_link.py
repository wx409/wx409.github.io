#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_feed_link.py —— 给全站 HTML 的 <head> 加 Atom feed 发现链接（幂等）"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
LINK = '<link rel="alternate" type="application/atom+xml" title="王晰数字档案 Atom Feed" href="https://wx409.github.io/feed.xml">'
SKIP = {".git", "temp", "temp_dl", "tmp", "logs", "node_modules", "__pycache__", "analysis", ".venv"}


def main():
    changed = 0
    for p in ROOT.rglob("*.html"):
        if any(part in SKIP for part in p.parts):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "application/atom+xml" in s or "</head>" not in s:
            continue
        s = s.replace("</head>", LINK + "\n</head>", 1)
        p.write_text(s, encoding="utf-8")
        changed += 1
    print("注入 feed 链接", changed, "页")


if __name__ == "__main__":
    main()
