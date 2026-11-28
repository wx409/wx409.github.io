#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gap_reason.py —— 解释每个缺口场次「为什么还缺」：没找到 / 只有切片 / 已下整场但曲目对不上 / 下载未完成

判定逻辑（对每个缺口场次）：
  A 本地已有整场（≥20min 的音轨）但曲目仍缺 → setlist_mismatch（曲序/曲名对不上）
  B 本地只有 <20min 的切片            → clip_only
  C 本地一个文件都没有：
      C1 搜索「王晰 城市 巡演名」60min+ 无命中、普通搜索也无命中 → not_found
      C2 普通搜索有命中但都 <20min（切片）                        → found_clip_only
      C3 60min+ 有命中但没下载                                    → found_not_downloaded

输出：data/audio_gap_reason.md / .json（并更新 audio_gap_report.md 的说明段）
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
AUD = Path(r"E:\wx王晰巡演_最优音频".replace("E:\\wx王", "E:\\wx\\王"))
AUD = Path(r"E:\wx\王晰巡演_最优音频")
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")

sys.path.insert(0, str(ROOT / "project_b"))
import importlib.util


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


AB = load("ab", str(ROOT / "project_b" / "bili_best_fetch.py"))

TOURWORD = {"一巡": ("Cherish", "珍晰", "一巡"), "二巡": ("二巡",), "三巡": ("图景", "三巡"),
            "四巡": ("肆益", "四巡"), "五巡": ("吾", "五巡"), "六巡": ("沉响与长歌", "六巡")}


def dur_of(p):
    try:
        r = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_format", "-of", "json", str(p)],
                           capture_output=True, text=True, timeout=30)
        return float((json.loads(r.stdout or "{}").get("format") or {}).get("duration") or 0)
    except Exception:
        return 0.0


def search(kw, h, dur=None):
    q = urllib.parse.quote(kw)
    url = (f"https://api.bilibili.com/x/web-interface/search/type?search_type=video"
           f"&keyword={q}&order=click" + (f"&duration={dur}" if dur else ""))
    j = AB.get(url, h)
    return [re.sub(r"<[^>]+>", "", v.get("title") or "") for v in
            (((j or {}).get("data") or {}).get("result") or [])]


def main():
    cov = json.loads((DATA / "song_coverage_status.json").read_text(encoding="utf-8"))
    by = defaultdict(int)
    for m in cov.get("missing") or []:
        by[(m["tour"], m["date"], m["city"])] += 1

    h = AB.headers()
    out = []
    for (tour, dt, city), n in sorted(by.items(), key=lambda kv: -kv[1]):
        folder = AUD / tour / f"{dt}_{city}"
        files = [p for p in folder.rglob("*.flac")] if folder.exists() else []
        durs = {p.name: round(dur_of(p) / 60, 1) for p in files}
        whole = [k for k, v in durs.items() if v >= 20]
        clips = [k for k, v in durs.items() if v < 20]
        if whole:
            reason = "setlist_mismatch（已有整场，但曲目/曲序对不上）"
        elif clips:
            reason = "clip_only（本地只有单曲切片）"
        else:
            words = TOURWORD.get(tour, (tour,))
            q1 = f"王晰 {city} {words[0]}"
            long_hits = [t for t in search(q1, h, dur=4) if "王晰" in t and city in t]
            time.sleep(2)
            any_hits = [t for t in search(f"王晰 {city}", h) if "王晰" in t and city in t]
            time.sleep(2)
            if long_hits:
                reason = "found_not_downloaded（60min+ 有命中但没下）"
            elif any_hits:
                reason = "found_clip_only（只搜到切片，无整场）"
            else:
                reason = "not_found（搜索无任何命中）"
        out.append({"tour": tour, "date": dt, "city": city, "missing_songs": n,
                    "local_files": len(files), "local_whole": len(whole),
                    "local_clips": len(clips), "reason": reason,
                    "dur_sample": dict(list(durs.items())[:5])})
        print(f"{tour} {dt} {city}: 缺{n}首 | 本地{len(files)}文件(整场{len(whole)}/切片{len(clips)}) | {reason}", flush=True)

    (DATA / "audio_gap_reason.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# 缺口原因（为什么还缺）", "", "| 场次 | 缺口 | 本地整场 | 本地切片 | 原因 |", "|---|---|---|---|---|"]
    for x in out:
        md.append(f"| {x['tour']} {x['date']} {x['city']} | {x['missing_songs']} | {x['local_whole']} | {x['local_clips']} | {x['reason']} |")
    (DATA / "audio_gap_reason.md").write_text("\n".join(md), encoding="utf-8")
    print("\n写出 data/audio_gap_reason.md / .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
