#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""没有外部对照组时的替代设计：歌单内/外的「同期 DiD」+ 安慰剂检验。

思路（全部只用站内数据）
  · 处理组 = 该场歌单里的歌；对照组 = 同期有数据的其它歌（同一歌手、同一平台、同一时间窗）
  · 每个比较对象先算自身变化：Δ = log(窗口后均值) − log(基线均值)
      baseline = [D-21, D-7]，post = [D+1, D+7]（与站内 7 日口径一致）
  · 效应 = median(Δ处理) − median(Δ对照)：对照组专门吸收"这周大盘/曲库整体在动"的部分
  · 安慰剂：随机抽 400 个"假演出日"，用同一套处理组/对照组算同一个统计量 → 零分布
      p = 假日期上 |效应| ≥ 真实效应的比例。这是 N=1 场景下替代"外部对照组"的标准做法。

输出：data/event_did.json
用法：python -X utf8 project_b\\analyze_event_did.py [--placebo 400]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "event_did.json"
SETLISTS = ROOT / "data" / "setlists.json"
LONG = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")

PRE = (-21, -7)
POST = (1, 7)
MIN_PTS = 3

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load():
    per_song = defaultdict(dict)      # song -> {date: index}
    with open(LONG, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()[:10]
            try:
                v = float(str(r.get("index", "")).replace(",", ""))
            except ValueError:
                continue
            if len(d) == 10 and v > 0:
                per_song[(r.get("song") or "").strip()][d] = v
    dates = sorted({d for m in per_song.values() for d in m})
    return per_song, dates


def window_mean(series, d0, d1, dates):
    i0, i1 = bisect_left(dates, d0), bisect_left(dates, d1)
    win = dates[i0:i1]
    vals = [series[d] for d in win if d in series]
    return statistics.mean(vals) if len(vals) >= MIN_PTS else None


def effect_at(per_song, dates, event_date, treated_songs):
    """返回 (效应, n_treated, n_control) 或 None。"""
    y, m, dd = map(int, event_date.split("-"))
    D = date(y, m, dd)
    pre = ((D + timedelta(days=PRE[0])).isoformat(), (D + timedelta(days=PRE[1])).isoformat())
    post = ((D + timedelta(days=POST[0])).isoformat(), (D + timedelta(days=POST[1])).isoformat())
    if post[1] > dates[-1] or pre[0] < dates[0]:
        return None
    dt, dc = [], []
    for song, s in per_song.items():
        a = window_mean(s, *pre, dates)
        b = window_mean(s, *post, dates)
        if a is None or b is None or a <= 0 or b <= 0:
            continue
        d = (b / a) - 1.0
        (dt if song in treated_songs else dc).append(d)
    if len(dt) < 3 or len(dc) < 5:
        return None
    return (statistics.median(dt) - statistics.median(dc), len(dt), len(dc))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebo", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261106)
    args = ap.parse_args()

    per_song, dates = load()
    shows = json.loads(SETLISTS.read_text(encoding="utf-8")).get("setlists") or {}

    rows = []
    for key, s in shows.items():
        d = (s.get("date") or "")[:10]
        if not d or d < dates[0] or d > dates[-1]:
            continue
        songs = {(x.get("title") or "").strip() for x in (s.get("songs") or [])}
        songs.discard("")
        if not songs:
            continue
        res = effect_at(per_song, dates, d, songs)
        if not res:
            continue
        rows.append({"date": d, "city": s.get("city") or "", "tour": s.get("tour") or "",
                     "scene": s.get("scene") or "", "n_setlist": len(songs),
                     "effect": round(res[0] * 100, 2), "n_treated": res[1], "n_control": res[2]})
    rows.sort(key=lambda r: r["date"])
    if not rows:
        print("没有可分析的场次（集中在 2023 年后才有指数数据）")
        return 1

    effs = [r["effect"] for r in rows]
    obs_med = statistics.median(effs)

    # 安慰剂：随机假日期 + 随机取一个真实歌单作伪处理组（规模与真实处理组相近）
    rng = random.Random(args.seed)
    lo_i, hi_i = 40, len(dates) - 30
    real_sets = []
    for s0 in shows.values():
        ss = {(x.get("title") or "").strip() for x in (s0.get("songs") or [])}
        ss.discard("")
        if ss:
            real_sets.append(ss)
    null = []
    for _ in range(args.placebo):
        d = dates[rng.randrange(lo_i, hi_i)]
        songs = rng.choice(real_sets)
        res = effect_at(per_song, dates, d, songs)
        if res:
            null.append(res[0] * 100)

    p = (sum(1 for x in null if abs(x) >= abs(obs_med)) + 1) / (len(null) + 1) if null else None
    payload = {
        "schema": "event-did/v1",
        "design": "歌单内(处理) vs 同期其它歌(对照) 的 DiD；基线 [D-21,D-7]，效应窗 [D+1,D+7]",
        "why": "没有外部对照组时，用同一歌手同一平台的'未唱歌曲'吸收大盘与曲库整体变化；再用假日期做安慰剂得到零分布",
        "window": {"pre": PRE, "post": POST},
        "n_shows": len(rows),
        "median_effect_pct": round(obs_med, 2),
        "placebo": {"n": len(null), "median_pct": round(statistics.median(null), 2) if null else None,
                    "p_two_sided": round(p, 3) if p is not None else None},
        "shows": rows,
        "generated_at": date.today().isoformat(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("可分析场次 %d｜效应中位 %+.2f%%｜安慰剂 %d 次（中位 %+.2f%%）｜双侧 p=%s"
          % (len(rows), obs_med, len(null),
             statistics.median(null) if null else 0, p))
    for r in sorted(rows, key=lambda x: -abs(x["effect"]))[:6]:
        print("  %s %s %s 效应 %+.2f%%（处理 %d / 对照 %d）"
              % (r["date"], r["city"], r["tour"], r["effect"], r["n_treated"], r["n_control"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
