#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_city_search.py —— 对「按 UP 空间扫不到」的缺口场次，改用关键词搜索兜底

场景：某些站（一巡大连、五巡长沙元旦、五巡北京生日…）九个 UP 的投稿里没有，
但 B站 搜索里可能有其他账号传的整场/半场。

做法：
  1 读 data/song_coverage_status.json 的缺口场次（tour/date/city）
  2 对每场用关键词搜：`王晰 <城市>`、`王晰 <城市> 全场`、`王晰 <城市> <年份>`
  3 过滤：标题含「王晰」+ 城市；优先含 全场/整场/上半场/下半场/完整
  4 输出 temp/bv_city_fill.txt（BV + 来源标签），供 bili_best_fetch.py --bvs-file 使用

用法：python -X utf8 project_b/bili_city_search.py [--only-missing]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
import importlib.util


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


DL = load("dl", str(ROOT / "project_b" / "download_bilibili.py"))
WHOLE = ("全场", "整场", "上半场", "下半场", "完整", "全程")


def headers():
    ck = (DL.get_session_cookie() or "")
    extra = DL.load_bili_cookie() or ""
    if extra:
        ck = ck + "; " + extra
    return {"User-Agent": DL.UA, "Cookie": ck, "Referer": "https://search.bilibili.com/"}


def search(keyword, h):
    kw = urllib.parse.quote(keyword)
    url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate&page=1"
    for _ in range(3):
        try:
            j = DL.http_get_json(url, headers=h)
        except Exception:
            time.sleep(10); continue
        if j.get("code") == 0:
            res = (j.get("data") or {}).get("result") or []
            out = []
            for v in res:
                t = re.sub(r"<[^>]+>", "", v.get("title") or "")
                out.append({"bv": v.get("bvid"), "title": t.strip(),
                            "up": v.get("author"), "play": v.get("play"),
                            "pubdate": v.get("pubdate")})
            return out
        time.sleep(15)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-queries", type=int, default=40)
    args = ap.parse_args()

    cov = json.loads((ROOT / "data" / "song_coverage_status.json").read_text(encoding="utf-8"))
    by_show = defaultdict(int)
    for m in cov.get("missing") or []:
        by_show[(m["tour"], m["date"], m["city"])] += 1

    h = headers()
    picked, queried = [], 0
    for (tour, dt, city), n in sorted(by_show.items(), key=lambda kv: -kv[1]):
        year = dt[:4]
        for q in (f"王晰 {city}", f"王晰 {city} 全场", f"王晰 {city} {year}"):
            if queried >= args.max_queries:
                break
            res = search(q, h)
            queried += 1
            cands = [x for x in res if x["bv"] and "王晰" in x["title"] and city in x["title"]]
            if cands:
                cands.sort(key=lambda x: (any(w in x["title"] for w in WHOLE), x.get("play") or 0), reverse=True)
                best = cands[0]
                print(f"{tour} {dt} {city} ← {best['bv']} {best['title'][:44]} (查询「{q}」)", flush=True)
                picked.append(best)
                break
            time.sleep(3)
        time.sleep(2)

    lines = [f"{x['bv']} citysearch" for x in picked]
    (ROOT / "temp" / "bv_city_fill.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n关键词兜底命中 {len(picked)} 场；写入 temp/bv_city_fill.txt", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
