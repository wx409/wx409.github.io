#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cross_song_index.py —— 曲目 × 指数 × 场次交叉分析

输入：data/setlists.json（64 场歌单）、dashboard/dashboard_data.json（song_index 逐曲指数）
输出：data/song_show_index.json + docs/交叉分析_曲目×指数×场次_2026-11-22.md
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
from song_names import canon  # noqa

SET = ROOT / "data" / "setlists.json"
DASH = ROOT / "dashboard" / "dashboard_data.json"
OUT = ROOT / "data" / "song_show_index.json"
MD = ROOT / "docs" / "交叉分析_曲目×指数×场次_2026-11-22.md"


def d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def window_avg(points, center, lo, hi):
    vals = []
    for ds, v in points:
        try:
            dd = d(ds)
        except Exception:
            continue
        if center + timedelta(days=lo) <= dd <= center + timedelta(days=hi) and v and v > 0:
            vals.append(float(v))
    return statistics.mean(vals) if vals else None


def main():
    shows = json.loads(SET.read_text(encoding="utf-8"))["setlists"]
    shows = shows.values() if isinstance(shows, dict) else shows
    import pandas as pd
    df = pd.read_csv(r"E:\wx\wx_textmine_out\music_index_long.csv")
    df = df.dropna(subset=["date", "song", "index"])
    byname = {}
    for song, g in df.groupby("song"):
        pts = [(str(d)[:10], float(v)) for d, v in zip(g["date"], g["index"])]
        byname.setdefault(canon(str(song)), []).append({"points": pts})
    rows, agg = [], defaultdict(lambda: {"n": 0, "lifts": [], "cities": set()})
    for sh in shows:
        sd = sh.get("date")
        if not sd:
            continue
        try:
            center = d(sd)
        except Exception:
            continue
        for song in sh.get("songs") or []:
            title = song.get("title") if isinstance(song, dict) else song
            if not title:
                continue
            cands = byname.get(canon(title)) or byname.get(title)
            if not cands:
                continue
            pts = cands[0].get("points") or []
            pre = window_avg(pts, center, -7, -1)
            post = window_avg(pts, center, 1, 7)
            if not pre or not post:
                continue
            lift = round((post - pre) / pre * 100, 1)
            row = {"date": sd, "city": sh.get("city"), "tour": sh.get("tour"),
                   "song": title, "pre": round(pre, 1), "post": round(post, 1), "lift_pct": lift}
            rows.append(row)
            a = agg[canon(title)]
            a["n"] += 1
            a["lifts"].append(lift)
            a["cities"].add(sh.get("city") or "")
    songs_out = []
    for name, a in agg.items():
        if not a["lifts"]:
            continue
        songs_out.append({"song": name, "shows": a["n"],
                          "avg_lift_pct": round(statistics.mean(a["lifts"]), 1),
                          "median_lift_pct": round(statistics.median(a["lifts"]), 1),
                          "cities": sorted(a["cities"])})
    songs_out.sort(key=lambda x: -x["shows"])
    doc = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "shows_with_index": len({r["date"] for r in rows}),
           "song_show_rows": len(rows), "songs": songs_out, "rows": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 曲目 × 指数 × 场次 交叉分析", "", "生成：%s" % doc["generated_at"], "",
             "覆盖：有指数窗口的场次 **%d** 场 / 曲目-场次记录 **%d** 条。" % (doc["shows_with_index"], len(rows)), "",
             "## 常唱曲目（Top 20，按场次）", "",
             "| 歌曲 | 场次 | 平均 T+1~7 变化 | 中位 | 城市 |", "|---|---:|---:|---:|---|"]
    for s in songs_out[:20]:
        lines.append("| %s | %d | %+.1f%% | %+.1f%% | %s |" % (s["song"], s["shows"], s["avg_lift_pct"], s["median_lift_pct"], "、".join(s["cities"][:5])))
    stable = [s for s in songs_out if s["shows"] >= 3 and s["avg_lift_pct"] <= 0]
    hot = [s for s in songs_out if s["shows"] >= 2 and s["avg_lift_pct"] >= 20]
    lines += ["", "## 现场常唱但指数不动（≥3 场，平均变化 ≤0）", ""]
    for s in stable[:15]:
        lines.append("- %s：%d 场，%+.1f%%" % (s["song"], s["shows"], s["avg_lift_pct"]))
    lines += ["", "## 唱后明显上涨（≥2 场，平均 ≥+20%）", ""]
    for s in hot[:15]:
        lines.append("- %s：%d 场，%+.1f%%" % (s["song"], s["shows"], s["avg_lift_pct"]))
    lines += ["", "## 口径", "",
              "- D0=演出日；前窗 T-7~T-1，后窗 T+1~T+7；只取指数 >0 的天。",
              "- 歌曲名经 `song_names.canon()` 归一；指数来自 dashboard_data.song_index。",
              "- 指数覆盖从 2024-07 起，2019-2024 早期场次大多没有窗口，故样本有限。"]
    MD.write_text("\n".join(lines), encoding="utf-8")
    print("rows", len(rows), "songs", len(songs_out), "→", OUT, "|", MD)


if __name__ == "__main__":
    raise SystemExit(main())
