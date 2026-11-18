#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音增量同步（王晰主页）：抓作品列表 → 对比本地 → 下载新增 → 更新索引。

用法：
  python -X utf8 project_b\\douyin_sync.py            # 增量同步
  python -X utf8 project_b\\douyin_sync.py --dry-run  # 只对比，不下载
  python -X utf8 project_b\\douyin_sync.py --max-scroll 60

原理：Playwright 打开王晰抖音主页，监听 `aweme/post` 接口响应，拿到
aweme_id + play_addr + 文案 + 时间；与 `awemes.json` 对比后只下载缺的。
产出：E:\\wx\\论文素材_王晰作传\\抖音\\<日期>_<id>.mp4，并更新 awemes.json / video_ids.txt。

注意：yt-dlp 现会报 “Fresh cookies”，本脚本不走 yt-dlp，用直链 + 浏览器 cookie。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(r"E:\wx\论文素材_王晰作传\抖音")
COOK = BASE / "douyin_cookies.txt"
AW = BASE / "awemes.json"
IDS = BASE / "video_ids.txt"
PROFILE = ("https://www.douyin.com/user/"
           "MS4wLjABAAAA6ORM3-ViSSI9SXozDl3OTaLLTHf-gm0ew9PgHRHr1ZA")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def load_cookies() -> list[dict]:
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


def capture(max_scroll: int) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("缺少 playwright：", e)
        return {}
    captured: dict[str, dict] = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, locale="zh-CN")
        ctx.add_cookies(load_cookies())
        page = ctx.new_page()

        def on_resp(r):
            if "aweme/post" not in r.url:
                return
            try:
                j = r.json()
            except Exception:
                return
            for a in (j.get("aweme_list") or []):
                if a.get("aweme_id"):
                    captured[str(a["aweme_id"])] = a

        page.on("response", on_resp)
        page.goto(PROFILE, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        for _ in range(max_scroll):
            page.mouse.wheel(0, 3500)
            page.wait_for_timeout(1500)
        b.close()
    return captured


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-scroll", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not AW.exists():
        print("缺少 awemes.json：", AW)
        return 1
    old = json.loads(AW.read_text(encoding="utf-8"))
    captured = capture(a.max_scroll)
    if not captured:
        print("未抓到作品（页面可能要求验证/登录；不影响本地已有存档）")
        return 2

    miss = [k for k in captured if k not in old]
    print("抓到 %d 条｜本地 %d 条｜新增 %d 条" % (len(captured), len(old), len(miss)))
    if not miss:
        print("无新增")
        return 0
    if a.dry_run:
        for k in miss:
            v = captured[k]
            ct = v.get("create_time") or 0
            print("  +", k, datetime.fromtimestamp(ct).strftime("%Y-%m-%d") if ct else "",
                  (v.get("desc") or "")[:40])
        return 0

    import requests
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.douyin.com/"})
    for c in load_cookies():
        sess.cookies.set(c["name"], c["value"], domain=c["domain"])

    ok = fail = 0
    for k in miss:
        v = captured[k]
        urls = (((v.get("video") or {}).get("play_addr") or {}).get("url_list") or [])
        if not urls:
            print("  无 play_addr:", k); fail += 1; continue
        ct = v.get("create_time") or 0
        day = datetime.fromtimestamp(ct).strftime("%Y%m%d") if ct else "unknown"
        out = BASE / ("%s_%s.mp4" % (day, k))
        if out.exists() and out.stat().st_size > 10000:
            print("  已存在:", out.name); continue
        got = False
        for u in urls[:3]:
            try:
                r = sess.get(u, timeout=60)
                if r.status_code == 200 and len(r.content) > 10000:
                    out.write_bytes(r.content)
                    print("  下载:", out.name, len(r.content) // 1024, "KB")
                    got = True; ok += 1
                    break
            except Exception as e:
                print("  下载失败:", str(e)[:60])
        if not got:
            fail += 1

    # 合并索引（只补新条目，不覆盖已有）
    for k in miss:
        v = captured[k]
        old.setdefault(k, {
            "desc": v.get("desc", ""),
            "ct": v.get("create_time") or 0,
            "dur": ((v.get("video") or {}).get("duration") or 0) / 1000.0,
            "play_addr": (((v.get("video") or {}).get("play_addr") or {}).get("url_list") or [""])[0],
        })
    AW.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    IDS.write_text("\n".join(old.keys()) + "\n", encoding="utf-8")
    print("完成：下载 %d / 失败 %d｜awemes 总数 %d" % (ok, fail, len(old)))
    return 0 if fail == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
