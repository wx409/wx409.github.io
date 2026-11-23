#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archive_link.py —— 把指定链接存成本地快照（微博 API / 普通网页 Playwright）

用法：
  python -X utf8 project_b/archive_link.py "https://m.weibo.cn/status/5368380228895334" --name tass-shaman
  python -X utf8 project_b/archive_link.py "https://example.com/article" --name xinhua-xxx

输出：E:\\wx\\私有工具\\link_archive\\YYYY-MM-DD\\<name>\\
  meta.json / text.md / page.html / page.png / assets/
仅本地存档，不自动发布；引用前请核对原文与版权。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(r"D:\wx\私有工具\link_archive")
COOKIE = Path(r"E:\wx\index_records\wb.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def get(url, cookie=""):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://m.weibo.cn/", "Cookie": cookie})
    return urllib.request.urlopen(req, timeout=25).read()


def archive_weibo(url, out):
    m = re.search(r"(?:status|detail)/(\d+)", url)
    if not m:
        raise ValueError("无法从链接识别微博 status id")
    sid = m.group(1)
    ck = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    raw = get("https://m.weibo.cn/statuses/show?id=" + sid, ck)
    j = json.loads(raw.decode("utf-8", "replace"))
    d = j.get("data") or {}
    if not d:
        raise RuntimeError("微博接口无 data（可能需登录/失效）")
    text = re.sub(r"<[^>]+>", "", d.get("text") or "")
    user = (d.get("user") or {}).get("screen_name") or ""
    title = "%s：%s" % (user, text[:60].replace("\n", " "))
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (out / "weibo.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "text.md").write_text("# %s\n\n%s\n\n原文：%s\n" % (title, text, url), encoding="utf-8")
    for i, p in enumerate(d.get("pics") or [], 1):
        u = p.get("url") or p.get("large", {}).get("url")
        if not u:
            continue
        try:
            (assets / ("img%02d.jpg" % i)).write_bytes(get(u, ck))
        except Exception as e:
            print("图片失败", u, e)
    return {"platform": "weibo", "id": sid, "title": title, "text": text,
            "created_at": d.get("created_at"), "url": url,
            "assets": [str(p.relative_to(out)) for p in assets.glob("*")]}


def archive_web(url, out):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 900}, user_agent=UA)
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(2500)
        title = pg.title()
        text = pg.inner_text("body")
        html = pg.content()
        (out / "page.html").write_text(html, encoding="utf-8")
        (out / "text.md").write_text("# %s\n\n%s\n\n原文：%s\n" % (title, text, url), encoding="utf-8")
        try:
            pg.screenshot(path=str(out / "page.png"), full_page=True)
        except Exception as e:
            print("截图失败", e)
        b.close()
    return {"platform": "web", "title": title, "text": text, "url": url,
            "html": "page.html", "screenshot": "page.png"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    out = ROOT / date.today().isoformat() / (a.name or hashlib.sha1(a.url.encode()).hexdigest()[:10])
    out.mkdir(parents=True, exist_ok=True)
    info = archive_weibo(a.url, out) if "weibo.cn" in a.url or "weibo.com" in a.url else archive_web(a.url, out)
    meta = {"archived_at": datetime.now().isoformat(timespec="seconds"), "url": a.url, **info}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("已存档：", out)
    print("标题：", info.get("title"))


if __name__ == "__main__":
    main()
