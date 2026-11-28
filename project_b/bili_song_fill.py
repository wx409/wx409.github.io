#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_song_fill.py —— 一巡补齐（逐曲搜索 + 指定 UP 主空间扫描）

背景（用户判断）：一巡 2019 几乎没有整场上传，只能按「王晰 珍晰 <城市> <歌曲名>」逐曲找；
另外有几个专门传一巡片段的 UP 主，空间里直接翻更快。

两种模式：
  --by-queries   对缺口曲目逐首搜「王晰 珍晰 <城市> <曲名>」（再退回「王晰 <曲名> <城市>」）
  --from-spaces  扫描指定 mid 的空间（wbi 分页），标题含 王晰 + 城市 的逐条比对缺口曲目

命中后：探 playurl 最高音轨 → 音频-only → FLAC 落到 <巡次>/<日期_城市>/{[B站-UP]<曲名>.flac} → 登 Excel
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
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
AU = load("au", str(ROOT / "project_b" / "bili_up_audit.py"))
AB.VIDEO_POLICY = "none"

SPACES = ["438328208", "406225978", "399411353", "211704454", "417218821", "6742688"]


def norm(s):
    return re.sub(r"[\s，,。、·・\-—_（）()《》「」【】]+", "", str(s or ""))


def search(kw, h):
    q = urllib.parse.quote(kw)
    url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={q}&order=click"
    j = AB.get(url, h)
    out = []
    for v in ((j or {}).get("data") or {}).get("result") or []:
        t = re.sub(r"<[^>]+>", "", v.get("title") or "").strip()
        out.append({"bv": v.get("bvid"), "title": t, "up": v.get("author") or "B站"})
    return out


def title_date(text):
    """从标题里抽日期（支持 20190816 / 2019.8.16 / 2019-08-16 / 2019年8月16日）。"""
    import re as _re
    for pat in (r"(20\d{2})(\d{2})(\d{2})",
                r"(20\d{2})[.\-_/年](\d{1,2})[.\-_/月](\d{1,2})"):
        for m in _re.finditer(pat, str(text or "")):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y}{mo:02d}{d:02d}"
    return ""


def verify_date(bv, title, d8, h, tolerance_days=120):
    """防止张冠李戴：标题带日期就必须等于该场；否则看投稿时间是否在该场附近。"""
    from datetime import datetime
    td = title_date(title)
    if td:
        return (td == d8), f"标题日期 {td}"
    j = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
    pub = ((j or {}).get("data") or {}).get("pubdate") or 0
    if not pub or not d8:
        return False, "无日期线索"
    try:
        pdt = datetime.fromtimestamp(pub)
        sdt = datetime.strptime(d8, "%Y%m%d")
        delta = abs((pdt - sdt).days)
        return delta <= tolerance_days, f"投稿 {pdt:%Y-%m-%d}（差 {delta} 天）"
    except Exception:
        return False, "日期解析失败"


def owner_of(bv, h):
    try:
        j = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
        return ((j or {}).get("data") or {}).get("owner", {}).get("name") or "B站"
    except Exception:
        return "B站"


def fetch_song(bv, up, song, tour, d8, city, h, ws, idx, dry=False):
    q = AB.streams(bv, h)
    if not q or not q.get("a_url"):
        return False
    print(f"      {q.get('a_kbps')}kbps {q.get('dur')}s {bv} {q.get('title','')[:34]}", flush=True)
    if dry:
        return True
    AB.fetch(bv, up, h, ws, idx)
    return True


def mark_pending(pending, ws, idx):
    """在 Excel 备注列写「待核」，标明依据（仅投稿时间近似）。"""
    if "备注" not in idx:
        from openpyxl import utils
        ws.cell(row=1, column=len(ws[1]) + 1, value="备注")
        idx["备注"] = len(ws[1]) - 1
    n = 0
    for row in ws.iter_rows(min_row=2):
        raw = str(row[idx["原始路径"]].value or "")
        for bv, why in pending.items():
            if bv in raw:
                row[idx["备注"]].value = f"待核（{why}）"
                n += 1
    print(f"      标记待核 {n} 行", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by-queries", action="store_true")
    ap.add_argument("--from-spaces", action="store_true")
    ap.add_argument("--tour-filter", default="一巡")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--relaxed", action="store_true", help="放宽：城市可不在标题，但必须通过日期核对")
    ap.add_argument("--tolerance", type=int, default=120, help="投稿时间容差天数")
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(AB.XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    h = AB.headers()
    PENDING = {}          # bv -> 日期核对依据（仅投稿时间通过的标待核）

    cov = json.loads((ROOT / "data" / "song_coverage_status.json").read_text(encoding="utf-8"))
    miss = [m for m in (cov.get("missing") or []) if m["tour"] == args.tour_filter]
    by_show = defaultdict(list)
    for m in miss:
        by_show[(m["tour"], m["date"], m["city"])].append(m["song"])
    print(f"{args.tour_filter} 缺口 {len(miss)} 首 / {len(by_show)} 场", flush=True)

    if args.from_spaces:
        # 空间扫描：把标题里带城市和曲名的视频收进候选
        cands = []
        for mid in SPACES:
            vids = AU.space(AB.DL, h, mid, 2)
            print(f"  空间 {mid}: {len(vids)} 条", flush=True)
            for v in vids:
                t = (v.get("title") or "")
                if "王晰" not in t:
                    continue
                cands.append({"bv": v.get("bvid"), "title": t})
            time.sleep(4)
        print(f"  候选 {len(cands)} 条", flush=True)
        used = 0
        for (tour, d8, city), songs in sorted(by_show.items(), key=lambda kv: -len(kv[1])):
            for song in list(songs):
                hit = None
                for c in cands:
                    if city and city in c["title"] and norm(song) and norm(song) in norm(c["title"]):
                        hit = c
                        break
                if hit:
                    if fetch_song(hit["bv"], owner_of(hit["bv"], h), song, tour, d8, city, h, ws, idx, args.dry_run):
                        songs.remove(song); used += 1
                        if not args.dry_run:
                            wb.save(AB.XLSX)
                    time.sleep(2)
                    if used >= args.limit:
                        break
            if used >= args.limit:
                break
        print(f"空间命中并入库 {used} 首", flush=True)
        return 0

    if args.by_queries:
        done = 0
        for (tour, d8, city), songs in sorted(by_show.items(), key=lambda kv: -len(kv[1])):
            for song in list(songs):
                bv = None; up = None
                for kw in (f"王晰 珍晰 {city} {song}", f"王晰 {song} {city}"):
                    res = search(kw, h)
                    time.sleep(2)
                    for r in res:
                        t = r["title"]
                        if "王晰" not in t or norm(song) not in norm(t):
                            continue
                        if city not in t and not args.relaxed:
                            continue
                        ok, why = verify_date(r["bv"], t, d8, h)
                        if not ok:
                            print(f"      跳过（日期不符：{why}）：{t[:40]}", flush=True)
                            continue
                        print(f"      日期核对通过（{why}）：{t[:40]}", flush=True)
                        if why.startswith("投稿"):
                            PENDING[r["bv"]] = why
                        bv, up = r["bv"], r["up"]; break
                    if bv:
                        break
                if not bv:
                    continue
                if fetch_song(bv, up or owner_of(bv, h), song, tour, d8, city, h, ws, idx, args.dry_run):
                    done += 1
                    if not args.dry_run:
                        wb.save(AB.XLSX)
                time.sleep(2)
                if done >= args.limit:
                    print(f"达到上限 {args.limit}", flush=True)
                    return 0
        if PENDING and not args.dry_run:
            mark_pending(PENDING, ws, idx)
            wb.save(AB.XLSX)
        print(f"逐曲搜索入库 {done} 首；待核 {len(PENDING)} 条", flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
