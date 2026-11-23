#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_llms_pages.py —— 从页面标记自动派生 llms.txt 的“内容与传播层”区块"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
LLMS = ROOT / "llms.txt"
START = "<!-- LLMS-PAGES:START -->"
END = "<!-- LLMS-PAGES:END -->"


def main():
    items = []
    for p in sorted(ROOT.glob("*.html")):
        s = p.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r'<meta\s+name=["\']llms["\']\s+content=["\']1["\']', s, re.I):
            continue
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', s, re.S)
        title = html.unescape(re.sub(r"\s+", " ", t.group(1)).strip()) if t else p.stem
        desc = html.unescape(re.sub(r"\s+", " ", d.group(1)).strip()) if d else ""
        desc = re.sub(r"｜王晰数字档案.*$", "", desc)[:110]
        items.append("- [%s](https://wx409.github.io/%s): %s" % (title, p.name, desc))
    block = START + "\n## 内容与传播层（页面标记自动派生）\n\n" + "\n".join(items) + "\n" + END
    s = LLMS.read_text(encoding="utf-8")
    if START in s and END in s:
        s = re.sub(re.escape(START) + r".*?" + re.escape(END), block, s, flags=re.S)
    else:
        s = s.replace("\n## 完整档案", "\n" + block + "\n\n## 完整档案", 1)
    LLMS.write_text(s, encoding="utf-8")
    print("llms 内容层页面", len(items))


if __name__ == "__main__":
    main()
