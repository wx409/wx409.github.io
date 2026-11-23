#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_analytics.py —— 按 data/analytics.json 给全站注入 GoatCounter（未配置则不注入）"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
CFG = ROOT / "data" / "analytics.json"
SKIP = {".git", "temp", "tmp", "logs", "node_modules", "__pycache__", "assets"}


def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    site = (cfg.get("site") or "").strip()
    if not site:
        print("analytics.site 为空：跳过注入（不加载、不采集）")
        return
    snippet = ('<script>window.__ANALYTICS__={site:"%s"};</script>\n'
               '<script src="/assets/analytics.js" defer></script>\n' % site)
    n = 0
    for p in ROOT.rglob("*.html"):
        if any(part in SKIP for part in p.parts):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "assets/analytics.js" in s or "</body>" not in s:
            continue
        s = s.replace("</body>", snippet + "</body>", 1)
        p.write_text(s, encoding="utf-8")
        n += 1
    print("注入 analytics", n, "页｜site", site)


if __name__ == "__main__":
    main()
