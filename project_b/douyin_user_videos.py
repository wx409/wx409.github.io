#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""douyin_user_videos.py —— 抖音用户主页视频列表（拦截 aweme/post）"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(r"D:\wx409.github.io")
COOKIE = Path(r"E:\wx\index_records\douyin_cookie_raw.txt")
OUT = Path(r"E:\wx\私有工具\douyin_users")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
URL = sys.argv[1] if len(sys.argv) > 1 else ""
NAME = sys.argv[2] if len(sys.argv) > 2 else "user"


def main():
    raw = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    cookies = [{"name": p.split("=", 1)[0].strip(), "value": p.split("=", 1)[1].strip(),
                "domain": ".douyin.com", "path": "/"} for p in raw.split(";") if "=" in p]
    items = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, viewport={"width": 1280, "height": 900}, locale="zh-CN")
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        def on_resp(r):
            if "aweme/post" not in r.url:
                return
            try:
                j = r.json()
            except Exception:
                return
            for a in j.get("aweme_list") or []:
                aid = a.get("aweme_id")
                if not aid:
                    continue
                st = a.get("statistics") or {}
                items[aid] = {"id": aid, "desc": (a.get("desc") or "")[:120],
                              "digg": st.get("digg_count") or 0,
                              "comment": st.get("comment_count") or 0,
                              "share": st.get("share_count") or 0}

        page.on("response", on_resp)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1800)
        b.close()
    rows = sorted(items.values(), key=lambda x: (-x["comment"], -x["digg"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (NAME + ".json")).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(NAME, len(rows), "条视频")
    for r in rows[:10]:
        print(r["id"], "评论", r["comment"], "赞", r["digg"], r["desc"][:40])


if __name__ == "__main__":
    main()
