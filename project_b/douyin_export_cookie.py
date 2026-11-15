#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从调试浏览器导出 cookie（含 msToken 等 JS 设置项）→ yt-dlp 用的 Netscape 文件。"""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"E:\wx\论文素材_王晰作传\抖音\douyin_cookies.txt")


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = b.contexts[0]
        ck = ctx.cookies()
        exp = int(time.time()) + 30 * 86400
        lines = ["# Netscape HTTP Cookie File", "# 由调试浏览器导出", ""]
        n = 0
        for c in ck:
            if "douyin" not in c.get("domain", ""):
                continue
            dom = c["domain"]
            lines.append("\t".join([
                dom,
                "TRUE" if dom.startswith(".") else "FALSE",
                c.get("path") or "/",
                "TRUE" if c.get("secure") else "FALSE",
                str(int(c.get("expires") or exp)),
                c["name"], c["value"],
            ]))
            n += 1
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        names = [c["name"] for c in ck if "douyin" in c.get("domain", "")]
        print(f"导出 {n} 条 → {OUT}")
        for k in ("ttwid", "msToken", "s_v_web_id", "sessionid", "odin_tt"):
            print("  ", k, "✓" if k in names else "✗")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
