#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快手同步：王晰主页视频 → 与抖音同目录存档。

依赖登录 Cookie：E:\\wx\\index_records\\kuaishou.txt（一行，浏览器 document.cookie 原样）
用法：
  python -X utf8 project_b\\kuaishou_sync.py --dry
  python -X utf8 project_b\\kuaishou_sync.py
产出：E:\\wx\\论文素材_王晰作传\\抖音\\快手\\<日期>_<id>.mp4 + kuaishou_photos.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(r"E:\wx\论文素材_王晰作传\抖音\快手")
COOK = Path(r"E:\wx\index_records\kuaishou.txt")
PROFILE = "https://www.kuaishou.com/profile/3x66gi9wh3fz4dw?source=SEARCH"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def parse_cookie(line: str) -> list[dict]:
    out = []
    for part in (line or "").split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({"name": k.strip(), "value": v.strip(), "domain": ".kuaishou.com", "path": "/"})
    return out


def walk(obj, found: list[dict]):
    if isinstance(obj, dict):
        if obj.get("photoUrl") and (obj.get("id") or obj.get("photoId")):
            found.append(obj)
        for v in obj.values():
            walk(v, found)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, found)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if not COOK.exists() or not COOK.read_text(encoding="utf-8").strip():
        print("缺少 Cookie：把浏览器里 kuaishou.com 的 document.cookie 粘进", COOK)
        return 1
    cookies = parse_cookie(COOK.read_text(encoding="utf-8").strip())

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("缺少 playwright：", e); return 1

    found: list[dict] = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, locale="zh-CN")
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        def on_resp(r):
            if "rest/v/profile/feed" not in r.url:
                return
            try:
                j = json.loads(r.text())
            except Exception:
                return
            for f in j.get("feeds") or []:
                ph = f.get("photo") or {}
                if ph.get("id"):
                    found.append(ph)

        page.on("response", on_resp)
        page.goto(PROFILE, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(6000)
        if "登录" in page.inner_text("body")[:300]:
            print("页面显示登录入口——Cookie 可能失效，仍尝试读取已加载内容")
        for _ in range(30):
            page.mouse.wheel(0, 3200)
            page.wait_for_timeout(1500)
        b.close()

    uniq = {}
    for x in found:
        pid = str(x.get("id") or x.get("photoId"))
        uniq.setdefault(pid, x)
    print("抓到作品候选：", len(uniq))
    if not uniq:
        print("未抓到作品：Cookie 失效或被风控（页面要求登录/验证）")
        return 2
    if a.limit:
        uniq = dict(list(uniq.items())[:a.limit])

    BASE.mkdir(parents=True, exist_ok=True)
    import requests
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.kuaishou.com/"})
    for c in cookies:
        sess.cookies.set(c["name"], c["value"], domain=c["domain"])

    meta, ok = {}, 0
    for pid, x in uniq.items():
        ts = x.get("timestamp") or x.get("createTime") or 0
        try:
            ts = int(ts)
            if ts > 1e12:
                ts //= 1000
        except Exception:
            ts = 0
        day = datetime.fromtimestamp(ts).strftime("%Y%m%d") if ts else "unknown"
        urls = x.get("photoUrls") or []
        url = (urls[0].get("url") if urls and isinstance(urls[0], dict) else "") or x.get("photoUrl") or ""
        out = BASE / ("%s_%s.mp4" % (day, pid))
        meta[pid] = {"id": pid, "caption": x.get("caption") or "", "timestamp": ts,
                     "duration": x.get("duration"), "url": url, "date": day}
        if not url:
            print("跳过（无地址）", pid); continue
        if out.exists() and out.stat().st_size > 10000:
            print("已存在", out.name); continue
        if a.dry:
            print("[dry]", out.name, url[:80]); continue
        try:
            r = sess.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 10000:
                out.write_bytes(r.content)
                ok += 1
                print("下载", out.name, len(r.content) // 1024, "KB")
            else:
                print("失败", pid, r.status_code, len(r.content))
        except Exception as e:
            print("失败", pid, str(e)[:80])

    (BASE / "kuaishou_photos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("完成：下载 %d｜作品 %d｜目录 %s" % (ok, len(meta), BASE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
