#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_show_fill.py —— 按「城市 + 巡演名」在 B站 搜索（时长 ≥60 分钟过滤），挑整场最优音质

用户经验：搜「王晰 <城市> <巡演名>」并加 **时长 60 分钟以上** 过滤，整场很容易找到。
B站 search API 的参数是 `duration=4`（=60 分钟以上）。

流程：
  1 关键词：王晰 <城市> <巡演别名>（一巡 Cherish珍晰 / 三巡 图景 / 四巡 肆益 / 五巡 吾 / 六巡 沉响与长歌）
  2 搜索 duration=4，过滤：标题含城市 + 巡演别名 + 王晰
  3 逐个探 playurl：时长 ≥60min 视为整场，比音轨码率
  4 音频-only 抓取（bili_best_fetch 的 fetch），入最优音频 + Excel

用法：
  python -X utf8 project_b/bili_show_fill.py --city 杭州 --tour 四巡
  python -X utf8 project_b/bili_show_fill.py --city 北京 --tour 五巡 --top 5
  python -X utf8 project_b/bili_show_fill.py --from-gaps --limit 10
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


AB = load("ab", str(ROOT / "project_b" / "bili_best_fetch.py"))
AB.VIDEO_POLICY = "none"

TOURWORD = {"一巡": ("Cherish", "珍晰", "一巡"), "二巡": ("二巡",), "三巡": ("图景", "三巡"),
            "四巡": ("肆益", "四巡"), "五巡": ("吾", "五巡"), "六巡": ("沉响与长歌", "六巡", "「回」")}
BAD = ("混剪", "剪辑", "合集", "群像", "reaction", "盘点", "专访", "访谈", "花絮", "预告")


def search(kw, h, dur_filter=4, page=1):
    q = urllib.parse.quote(kw)
    url = (f"https://api.bilibili.com/x/web-interface/search/type?search_type=video"
           f"&keyword={q}&order=click&duration={dur_filter}&page={page}")
    j = AB.get(url, h)
    out = []
    for v in ((j or {}).get("data") or {}).get("result") or []:
        t = re.sub(r"<[^>]+>", "", v.get("title") or "").strip()
        out.append({"bv": v.get("bvid"), "title": t, "up": v.get("author") or "B站",
                    "play": v.get("play") or 0, "len": v.get("duration")})
    return out


def owner_of(bv, h):
    try:
        j = AB.get(f"https://api.bilibili.com/x/video/view?bvid={bv}", h)
        j = j or AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
        return ((j or {}).get("data") or {}).get("owner", {}).get("name") or "B站"
    except Exception:
        return "B站"


def fill_one(city, tour, h, ws, idx, top=6, dry=False):
    words = TOURWORD.get(tour, (tour,))
    cands, seen = [], set()
    for w in (words[0], tour):
        kw = f"王晰 {city} {w}"
        for x in search(kw, h, dur_filter=4):
            if not x["bv"] or x["bv"] in seen:
                continue
            t = x["title"]
            if "王晰" not in t or city not in t:
                continue
            if not any(a in t for a in words):
                continue
            if any(b in t for b in BAD):
                continue
            seen.add(x["bv"]); cands.append(x)
        time.sleep(3)
        if len(cands) >= top:
            break
    if not cands:
        print(f"  {tour} {city}: duration=4 无命中", flush=True)
        return None
    cands.sort(key=lambda x: x["play"], reverse=True)
    rows = []
    for x in cands[:top]:
        q = AB.streams(x["bv"], h)
        dur = int(q.get("dur") or 0)
        rows.append({"bv": x["bv"], "title": x["title"], "a_kbps": q.get("a_kbps") or 0,
                     "v_kbps": q.get("v_kbps") or 0, "res": f"{q.get('v_w')}x{q.get('v_h')}",
                     "dur_min": round(dur / 60, 1), "whole": dur >= 3600})
        time.sleep(2)
    rows.sort(key=lambda r: (r["whole"], r["a_kbps"], r["v_kbps"]), reverse=True)
    for r in rows:
        print(f"    {r['a_kbps']:4}kbps {r['dur_min']:6}min {'整场' if r['whole'] else '非整场'} "
              f"{r['res']:10} {r['bv']} {r['title'][:38]}", flush=True)
    win = rows[0]
    print(f"  → 选 {win['bv']}（{win['a_kbps']}kbps / {win['dur_min']}min）", flush=True)
    if dry:
        return win
    AB.fetch(win["bv"], owner_of(win["bv"], h), h, ws, idx)
    return win


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="")
    ap.add_argument("--tour", default="")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--from-gaps", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(AB.XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    h = AB.headers()

    if args.city and args.tour:
        fill_one(args.city, args.tour, h, ws, idx, args.top, args.dry_run)
        if not args.dry_run:
            wb.save(AB.XLSX)
        return 0

    if args.from_gaps:
        cov = json.loads((ROOT / "data" / "song_coverage_status.json").read_text(encoding="utf-8"))
        by = defaultdict(int)
        for m in cov.get("missing") or []:
            by[(m["tour"], m["date"], m["city"])] += 1
        shows = sorted(by.items(), key=lambda kv: -kv[1])[: args.limit]
        for (tour, dt, city), n in shows:
            print(f"\n{tour} {dt} {city}（缺 {n} 首）", flush=True)
            fill_one(city, tour, h, ws, idx, args.top, args.dry_run)
            if not args.dry_run:
                wb.save(AB.XLSX)
            time.sleep(3)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
