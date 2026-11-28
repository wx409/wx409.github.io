#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_pick_best.py —— 同一场次的多个候选里挑「音质最高」的一条抓取

两种用法：
  ① 指定场次与候选 BV（用户手工搜到的结果）
      python -X utf8 project_b/bili_pick_best.py --show "四巡 20240916 武汉" --bvs BV1PFtYecEZ6,BV11ZtaehEus,...
  ② 自动：对剩余缺口场次，用「王晰 <城市> <巡演名>」关键词搜索（巡演名=珍晰/二巡/图景/肆益/吾/沉响与长歌），
     取搜索结果里标题含城市的前 N 条，逐个探音轨码率，挑最高的一条抓取（音频-only）
      python -X utf8 project_b/bili_pick_best.py --auto --city-limit 20

判据：音轨码率（kbps）最高者胜；同码率看视频分辨率（作为原始画质线索）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
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

TOURWORD = {"一巡": "Cherish珍晰", "二巡": "二巡", "三巡": "图景", "四巡": "肆益",
            "五巡": "吾", "六巡": "沉响与长歌"}
BAD = ("混剪", "剪辑", "合集", "群像", "reaction", "盘点", "专访", "访谈", "花絮", "预告")


def search(keyword, h, pages=2):
    out = []
    for pn in range(1, pages + 1):
        kw = urllib.parse.quote(keyword)
        url = (f"https://api.bilibili.com/x/web-interface/search/type?search_type=video"
               f"&keyword={kw}&order=pubdate&page={pn}")
        j = AB.get(url, h)
        if not j:
            break
        res = (j.get("data") or {}).get("result") or []
        if not res:
            break
        for v in res:
            t = re.sub(r"<[^>]+>", "", v.get("title") or "").strip()
            out.append({"bv": v.get("bvid"), "title": t, "up": v.get("author") or "B站",
                        "play": v.get("play") or 0})
        time.sleep(3)
    return out


def best_of(bvs, h, prefer_whole=True):
    """探测候选音轨。排序原则（覆盖优先于单曲音质）：
       1) 先看是不是整场/半场（时长 ≥20 分钟）——一条能覆盖 20 首
       2) 再比音轨码率；最后看视频码率
    因为实测：330kbps 的往往是 4 分钟单曲切片，而 120kbps 的可能是 2 小时全场。"""
    rows = []
    for bv in bvs:
        q = AB.streams(bv, h)
        dur = int(q.get("dur") or 0)
        rows.append({"bv": bv, "a_kbps": q.get("a_kbps") or 0, "kind": q.get("a_kind"),
                     "v_kbps": q.get("v_kbps") or 0, "res": f"{q.get('v_w')}x{q.get('v_h')}",
                     "dur_min": round(dur / 60, 1), "whole": dur >= 1200,
                     "title": q.get("title") or ""})
        time.sleep(2)
    if prefer_whole:
        rows.sort(key=lambda x: (x["whole"], x["a_kbps"], x["v_kbps"]), reverse=True)
    else:
        rows.sort(key=lambda x: (x["a_kbps"], x["v_kbps"]), reverse=True)
    return rows


def owner_of(bv, h):
    """取投稿人昵称，写进 Excel 的来源列。"""
    try:
        j = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
        return ((j or {}).get("data") or {}).get("owner", {}).get("name") or "B站"
    except Exception:
        return "B站"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", default="")
    ap.add_argument("--city", default="", help="只在该城市/关键词命中的候选里挑（避免串场）")
    ap.add_argument("--bvs", default="")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--city-limit", type=int, default=20)
    ap.add_argument("--per-show", type=int, default=20)
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(AB.XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    h = AB.headers()

    def do_fetch(bv, up):
        ok = AB.fetch(bv, up, h, ws, idx)
        wb.save(AB.XLSX)
        return ok

    if args.show and args.bvs:
        bvs = [x.strip() for x in re.split(r"[,\s]+", args.bvs) if x.strip().startswith("BV")]
        print(f"[{args.show}] 候选 {len(bvs)} 条，逐个探音轨码率…", flush=True)
        rows = best_of(bvs, h)
        if args.city:
            keep = [r for r in rows if args.city in (r.get("title") or "")]
            if keep:
                rows = keep
            else:
                print(f"  !! 没有标题含「{args.city}」的候选，退化为全部候选", flush=True)
        for r in rows:
            print(f"  {r['a_kbps']:4}kbps {r['kind'] or '?':5} 视频{r['v_kbps']:6}kbps {r['res']:10} {r['bv']} {r['title'][:40]}", flush=True)
        win = rows[0]
        print(f"  → 选 {win['bv']}（{win['a_kbps']}kbps）", flush=True)
        do_fetch(win["bv"], owner_of(win["bv"], h))
        return 0

    if args.auto:
        cov = json.loads((ROOT / "data" / "song_coverage_status.json").read_text(encoding="utf-8"))
        from collections import defaultdict
        by = defaultdict(int)
        for m in cov.get("missing") or []:
            by[(m["tour"], m["date"], m["city"])] += 1
        shows = sorted(by.items(), key=lambda kv: -kv[1])[: args.city_limit]
        print(f"缺口场次 {len(by)}，本轮处理 {len(shows)}", flush=True)
        for (tour, dt, city), n in shows:
            word = TOURWORD.get(tour, "")
            queries = [f"王晰 {city} {word}".strip(), f"王晰 {city} 全场", f"王晰 {city}"]
            cands, seen = [], set()
            for q in queries:
                for x in search(q, h, pages=2):
                    if x["bv"] in seen or not x["bv"]:
                        continue
                    if "王晰" not in x["title"] or city not in x["title"]:
                        continue
                    if any(w in x["title"] for w in BAD):
                        continue
                    seen.add(x["bv"]); cands.append(x)
                if len(cands) >= 8:
                    break
                time.sleep(2)
            if not cands:
                print(f"  {tour} {dt} {city}: 搜索无命中", flush=True)
                continue
            cands.sort(key=lambda x: x["play"], reverse=True)
            rows = best_of([x["bv"] for x in cands[: args.per_show]], h)
            win = rows[0]
            print(f"  {tour} {dt} {city}: 候选{len(rows)} 选 {win['bv']} {win['a_kbps']}kbps {win['res']}", flush=True)
            do_fetch(win["bv"], owner_of(win["bv"], h))
            time.sleep(3)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
