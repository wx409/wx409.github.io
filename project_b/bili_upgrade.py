#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_upgrade.py —— 「最优」名副其实：发现更高音质的版本时替换现有文件

判定单位：**(巡次, 日期, 城市, 曲目)**。现有音频的音质取自 Excel 的「码率kbps」列
（FLAC 实际码率，无损时很高；B站源就是 AAC 原始码率）。

升级规则：
  1 新候选音轨码率 > 现有 × (1 + --margin)（默认 15%）才算"更高"
  2 无损优先：新候选是 flac/dolby 音轨时，直接算升级
  3 替换时**不删旧文件**：旧文件移到 E:\\wx\\王晰巡演_最优音频\\_superseded\\<巡次>\\<日期_城市>\\
  4 Excel 对应行更新（目标路径/码率/BV/来源），并在「备注」写 superseded 路径

用法：
  python -X utf8 project_b/bili_upgrade.py --limit 20 --margin 0.15
  python -X utf8 project_b/bili_upgrade.py --tour 一巡 --city 北京 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime
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
AUD = AB.AUD_ROOT
SUP = AUD / "_superseded"
TOURWORD = {"一巡": ("Cherish", "珍晰", "一巡"), "二巡": ("二巡",), "三巡": ("图景", "三巡"),
            "四巡": ("肆益", "四巡"), "五巡": ("吾", "五巡"), "六巡": ("沉响与长歌", "六巡")}


def search(kw, h, dur=None):
    q = urllib.parse.quote(kw)
    url = (f"https://api.bilibili.com/x/web-interface/search/type?search_type=video"
           f"&keyword={q}&order=click" + (f"&duration={dur}" if dur else ""))
    j = AB.get(url, h)
    return [{"bv": v.get("bvid"), "title": re.sub(r"<[^>]+>", "", v.get("title") or "").strip(),
             "up": v.get("author") or "B站"}
            for v in (((j or {}).get("data") or {}).get("result") or [])]


def song_of(name):
    n = re.sub(r"^\[[^\]]+\]", "", Path(name).stem)
    return n.strip()


def owner_of(bv, h):
    try:
        j = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
        return ((j or {}).get("data") or {}).get("owner", {}).get("name") or "B站"
    except Exception:
        return "B站"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20, help="本次最多升级几首")
    ap.add_argument("--margin", type=float, default=0.15)
    ap.add_argument("--tour", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(AB.XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}
    if "备注" not in idx:
        ws.cell(row=1, column=len(cols) + 1, value="备注")
        cols.append("备注")
        idx["备注"] = len(cols) - 1

    # 现有条目：按 (巡次,日期,城市,曲目) 取最高码率
    existing = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        src = str(r[idx["来源"]] or "")
        if not src.startswith("B站-"):
            continue
        note = str(r[idx["备注"]] or "") if "备注" in idx else ""
        if "已归档" in note or "_superseded" in str(r[idx["目标路径"]] or ""):
            continue                      # 已替换的旧版不参与比较，避免反复升级同一首
        tour = str(r[idx["巡次"]] or "")
        d8 = re.sub(r"\D", "", str(r[idx["日期"]] or ""))[:8]
        city = str(r[idx["城市"]] or "")
        kbps = 0.0
        m = re.search(r"(\d+)\s*kbps", str(r[idx["级别"]] or ""))
        if m:
            kbps = float(m.group(1))
        else:
            try:
                kbps = float(r[idx["码率kbps"]] or 0)
            except Exception:
                kbps = 0.0
        if not tour or not d8 or not city:
            continue
        fname = str(r[idx["文件名"]] or "")
        raw = str(r[idx["原始路径"]] or "")
        song = song_of(fname)
        is_single = ("?p=" in raw) or (len(song) <= 25 and not any(k in song for k in ("全场", "上半场", "下半场", "全程")))
        if not is_single:
            continue
        key = (tour, d8, city, song)
        cur = existing.get(key)
        if not cur or kbps > cur["kbps"]:
            existing[key] = {"kbps": kbps, "path": str(r[idx["目标路径"]] or ""),
                             "bv": str(r[idx["BV"]] or ""), "row_src": src}

    print(f"可比较条目 {len(existing)} 个（B站来源）", flush=True)
    h = AB.headers()
    upgrades = 0
    for (tour, d8, city, song), cur in sorted(existing.items(), key=lambda kv: kv[1]["kbps"]):
        if args.tour and tour != args.tour:
            continue
        if args.city and city != args.city:
            continue
        words = TOURWORD.get(tour, (tour,))
        best = None
        for kw in (f"王晰 {city} {song}", f"王晰 {song} {city}"):
            for x in search(kw, h):
                if "王晰" not in x["title"] or song not in x["title"]:
                    continue
                if cur.get("bv") and x["bv"] == cur["bv"]:
                    continue
                q = AB.streams(x["bv"], h)
                ak = q.get("a_kbps") or 0
                kind = q.get("a_kind") or "aac"
                better = (kind in ("flac", "dolby") and ak >= cur["kbps"] * 0.6) or ak > cur["kbps"] * (1 + args.margin)
                if better and (not best or ak > best["ak"]):
                    best = {"bv": x["bv"], "ak": ak, "kind": kind, "title": x["title"], "up": x["up"]}
                time.sleep(1.5)
            if best:
                break
            time.sleep(2)
        if not best:
            continue
        print(f"[UPGRADE] {tour} {d8} {city}《{song}》 {cur['kbps']:.0f} -> {best['ak']}kbps ({best['kind']}) {best['bv']}", flush=True)
        if args.dry_run:
            upgrades += 1
            if upgrades >= args.limit:
                break
            continue
        # 下载新版
        AB.fetch(best["bv"], owner_of(best["bv"], h), h, ws, idx)
        # 旧文件移到 _superseded
        old = Path(cur["path"]) if cur["path"] else None
        if old and old.exists():
            dst_dir = SUP / tour / f"{d8}_{city}"
            dst_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(old), str(dst_dir / old.name))
                for r in ws.iter_rows(min_row=2):
                    if str(r[idx["目标路径"]].value or "") == str(old):
                        r[idx["备注"]].value = f"已归档：被 {best['bv']} 替换"
                        r[idx["码率kbps"]].value = None
                        break
                print(f"     旧文件已归档: {old.name[:50]}", flush=True)
            except Exception as e:
                print(f"     旧文件归档失败: {e}", flush=True)
        wb.save(AB.XLSX)
        upgrades += 1
        if upgrades >= args.limit:
            break

    (ROOT / "data" / "quality_upgrades.json").write_text(
        json.dumps({"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "count": upgrades},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n升级 {upgrades} 首", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
