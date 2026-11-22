#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""douyin_comments.py —— 抖音指定视频评论抓取（有头浏览器拦截 comment/list）

用法：python -X utf8 project_b\\douyin_comments.py 7304607274968911104 7437115159329377572
输出：E:\\wx\\私有工具\\douyin_comments\\<id>.json + data/douyin_comments.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(r"D:\wx409.github.io")
COOKIE = Path(r"E:\wx\index_records\douyin_cookie_raw.txt")
OUTDIR = Path(r"E:\wx\私有工具\douyin_comments")
PUB = ROOT / "data" / "douyin_comments.json"
IDS = sys.argv[1:] or ["7304607274968911104", "7437115159329377572", "7618564386047211747"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def main():
    raw = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    cookies = [{"name": p.split("=", 1)[0].strip(), "value": p.split("=", 1)[1].strip(),
                "domain": ".douyin.com", "path": "/"} for p in raw.split(";") if "=" in p]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, viewport={"width": 1280, "height": 900}, locale="zh-CN")
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        for vid in IDS:
            comments, meta = [], {}
            def on_resp(r):
                u = r.url
                if "comment/list" not in u and "comment/list/reply" not in u:
                    return
                try:
                    j = r.json()
                except Exception:
                    return
                for c in j.get("comments") or []:
                    t = (c.get("text") or "").strip()
                    if t:
                        comments.append({"text": t, "likes": c.get("digg_count") or 0})
            page.on("response", on_resp)
            try:
                page.goto("https://www.douyin.com/video/" + vid, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(8000)
                for _ in range(3):
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(1500)
                meta = {"title": page.title(), "url": page.url}
            except Exception as e:
                meta = {"error": str(e)[:120]}
            page.remove_listener("response", on_resp)
            doc = {"id": vid, "meta": meta, "count": len(comments), "comments": comments}
            (OUTDIR / (vid + ".json")).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
            out.append({"id": vid, "title": meta.get("title", "")[:80], "count": len(comments),
                        "top": [c["text"][:60] for c in sorted(comments, key=lambda x: -x["likes"])[:5]]})
            print(vid, "comments", len(comments))
        b.close()
    PUB.write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%d %H:%M"), "videos": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", PUB)


if __name__ == "__main__":
    main()
