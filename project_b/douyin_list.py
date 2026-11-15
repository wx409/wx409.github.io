#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音主页作品清单（Playwright + 本地 cookie 注入，只列 ID，不下载）。

用法：python -X utf8 project_b/douyin_list.py [--max 200] [--out list.json]
产出：E:\\wx\\论文素材_王晰作传\\抖音\\video_ids.json
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

COOK = Path(r"E:\wx\论文素材_王晰作传\抖音\douyin_cookies.txt")
OUT = Path(r"E:\wx\论文素材_王晰作传\抖音\video_ids.json")
URL = "https://www.douyin.com/user/MS4wLjABAAAA6ORM3-ViSSI9SXozDl3OTaLLTHf-gm0ew9PgHRHr1ZA"


def load_cookies():
    out = []
    for line in COOK.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        p = line.split("\t")
        if len(p) >= 7:
            out.append({"name": p[5], "value": p[6], "domain": p[0], "path": p[2],
                        "secure": p[3].upper() == "TRUE",
                        "expires": float(p[4]) if p[4].isdigit() else -1})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=300)
    a = ap.parse_args()

    ids, seen = [], set()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}, locale="zh-CN")
        ctx.add_cookies(load_cookies())
        pg = ctx.new_page()
        pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)
        print("标题:", pg.title()[:60])

        for i in range(40):
            links = pg.eval_on_selector_all(
                'a[href*="/video/"]', "els => els.map(e => e.href)")
            new = 0
            for u in links:
                m = re.search(r"/video/(\d{15,25})", u)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    ids.append(m.group(1))
                    new += 1
            print(f"  轮 {i+1}: 新增 {new}｜累计 {len(ids)}")
            if len(ids) >= a.max:
                break
            pg.mouse.wheel(0, 4000)
            time.sleep(1.6)

        ctx.close(); b.close()

    OUT.write_text(json.dumps({"profile": URL, "count": len(ids), "ids": ids},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"共 {len(ids)} 个作品 ID → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
