#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_supplement.py —— 补全阶段的「质量补充」：把高码率但没被选中的音轨也收进来

背景（用户策略）：
  补全阶段优先「整场/半场」（覆盖多首），代价是码率常常只有 86–200 kbps；
  等覆盖率够了，就切到**质量优先**：把码率更高（≥200 kbps）但当时没选中的音轨
  作为**补充**放进同一场次目录，并补登 Excel。

与 bili_best_fetch 的区别：
  - 不替换已有文件；同场可以有多条（整场 + 高质量单曲/另一版整场）
  - 只收 ≥ --min-kbps 的；按 BV 去重（Excel 里有 BV 列）
  - 每条写明「补充」，Excel 里级别标 A(补充 …)

用法：
  python -X utf8 project_b/bili_supplement.py --limit 8 --min-kbps 200
  python -X utf8 project_b/bili_supplement.py --city 杭州 --tour 五巡
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


def clean_city(c):
    return re.sub(r"[（(].*?[)）]", "", str(c or "")).strip()


def search(kw, h, dur=None, page=1):
    q = urllib.parse.quote(kw)
    url = (f"https://api.bilibili.com/x/web-interface/search/type?search_type=video"
           f"&keyword={q}&order=click&page={page}" + (f"&duration={dur}" if dur else ""))
    j = AB.get(url, h)
    out = []
    for v in ((j or {}).get("data") or {}).get("result") or []:
        t = re.sub(r"<[^>]+>", "", v.get("title") or "").strip()
        out.append({"bv": v.get("bvid"), "title": t, "up": v.get("author") or "B站",
                    "play": v.get("play") or 0})
    return out


def existing_bvs(ws, idx):
    s = set()
    if "BV" not in idx:
        return s
    for r in ws.iter_rows(min_row=2, values_only=True):
        v = str(r[idx["BV"]] or "").strip()
        if v.startswith("BV"):
            s.add(v)
    return s


def owner_of(bv, h):
    try:
        j = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
        return ((j or {}).get("data") or {}).get("owner", {}).get("name") or "B站"
    except Exception:
        return "B站"


def multip_needed(bv, h):
    """该 BV 是否是多 P（分曲目）投稿；是则返回 P 数。"""
    j = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
    pages = ((j or {}).get("data") or {}).get("pages") or []
    return len(pages)


def run_multip(bv, tour, date8, city):
    """多 P 投稿交给 bili_multip_fetch.py 逐 P 抓。"""
    import subprocess
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "project_b" / "bili_multip_fetch.py"),
           "--bv", bv, "--tour", tour, "--date", date8, "--city", city]
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def supplement(city, tour, h, ws, idx, have, min_kbps=200, per_show=2, dry=False):
    city = clean_city(city)
    words = TOURWORD.get(tour, (tour,))
    cands, seen = [], set()
    for w in (words[0], tour):
        for dur in (None, 4):          # 先找普通结果（多为单曲/高码率），再找整场
            for x in search(f"王晰 {city} {w}", h, dur=dur):
                bv = x["bv"]
                if not bv or bv in seen or bv in have:
                    continue
                t = x["title"]
                if "王晰" not in t or city not in t or not any(a in t for a in words):
                    continue
                seen.add(bv); cands.append(x)
            time.sleep(2)
        if len(cands) >= 10:
            break
    if not cands:
        return []
    rows = []
    for x in cands[:12]:
        q = AB.streams(x["bv"], h)
        ak = q.get("a_kbps") or 0
        dur_min = round(int(q.get("dur") or 0) / 60, 1)
        rows.append({"bv": x["bv"], "title": x["title"], "a_kbps": ak,
                     "v_kbps": q.get("v_kbps") or 0, "dur_min": dur_min,
                     "res": f"{q.get('v_w')}x{q.get('v_h')}"})
        time.sleep(2)
    rows = [r for r in rows if r["a_kbps"] >= min_kbps]
    rows.sort(key=lambda r: r["a_kbps"], reverse=True)
    picked = rows[:per_show]
    out = []
    for r in picked:
        print(f"    + {r['a_kbps']}kbps {r['dur_min']}min {r['res']} {r['bv']} {r['title'][:38]}", flush=True)
        if dry:
            out.append(r); continue
        AB.fetch(r["bv"], owner_of(r["bv"], h), h, ws, idx)
        have.add(r["bv"])
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="")
    ap.add_argument("--tour", default="")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--min-kbps", type=int, default=200)
    ap.add_argument("--per-show", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(AB.XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    have = existing_bvs(ws, idx)
    h = AB.headers()
    print(f"已有 B站 BV {len(have)} 条；门槛 {args.min_kbps}kbps", flush=True)

    if args.city and args.tour:
        acts = supplement(args.city, args.tour, h, ws, idx, have, args.min_kbps, args.per_show, args.dry_run)
        if not args.dry_run:
            wb.save(AB.XLSX)
        print(f"补充 {len(acts)} 条")
        return 0

    cov = json.loads((ROOT / "data" / "song_coverage_status.json").read_text(encoding="utf-8"))
    shows = []
    for m in cov.get("missing") or []:
        shows.append((m["tour"], m["city"]))
    seen_show, uniq = set(), []
    for t, c in shows:
        if (t, c) in seen_show:
            continue
        seen_show.add((t, c)); uniq.append((t, c))
    print(f"从缺口场次里选 {min(args.limit, len(uniq))} 个做质量补充", flush=True)
    total = 0
    for tour, city in uniq[: args.limit]:
        print(f"\n{tour} {city}", flush=True)
        total += len(supplement(city, tour, h, ws, idx, have, args.min_kbps, args.per_show, args.dry_run))
        if not args.dry_run:
            wb.save(AB.XLSX)
        time.sleep(2)
    print(f"\n合计补充 {total} 条", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
