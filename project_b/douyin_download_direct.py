#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接下载抖音 mp4（用采集到的 play_addr + 浏览器导出的 cookie）。

用法：python -X utf8 project_b/douyin_download_direct.py [--limit N]
产出：E:\wx\论文素材_王晰作传\抖音\<日期>_<id>.mp4 + _download_log.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(r"E:\wx\论文素材_王晰作传\抖音")
AW = BASE / "awemes.json"
COOK = BASE / "douyin_cookies.txt"
LOG = BASE / "_download_log.json"


def load_cookie() -> str:
    pairs = []
    for line in COOK.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        p = line.split("\t")
        if len(p) >= 7:
            pairs.append(f"{p[5]}={p[6]}")
    return "; ".join(pairs)


def main() -> int:
    limit = 0
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    aw = json.loads(AW.read_text(encoding="utf-8"))
    items = sorted(aw.items(), key=lambda kv: -(kv[1].get("ct") or 0))
    if limit:
        items = items[:limit]
    cookie = load_cookie()
    print(f"待下载 {len(items)} 条")

    ok, fail = [], []
    for i, (vid, v) in enumerate(items, 1):
        url = v.get("url") or ""
        if not url:
            fail.append(vid); continue
        day = datetime.fromtimestamp(v["ct"]).strftime("%Y%m%d") if v.get("ct") else "unknown"
        dest = BASE / f"{day}_{vid}.mp4"
        if dest.exists() and dest.stat().st_size > 200_000:
            ok.append(vid); continue
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Referer": "https://www.douyin.com/",
            "Cookie": cookie,
            "Range": "bytes=0-",
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) < 100_000:
                fail.append(vid)
                print(f"[{i}/{len(items)}] 太小 {vid} {len(data)}")
                continue
            dest.write_bytes(data)
            ok.append(vid)
            print(f"[{i}/{len(items)}] OK {dest.name} {len(data)/1e6:.1f}MB")
        except Exception as e:
            fail.append(vid)
            print(f"[{i}/{len(items)}] FAIL {vid} {type(e).__name__} {str(e)[:50]}")
        time.sleep(0.3)

    LOG.write_text(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M"),
                               "ok": len(ok), "fail": len(fail),
                               "ok_ids": ok, "fail_ids": fail},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n成功 {len(ok)}｜失败 {len(fail)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
