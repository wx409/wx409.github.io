#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月度事件研究 v3：先给每首歌做「自身基线归一」，再看月度热度与异常。

为什么要有这一步（v1/v2 的教训）
  v1 用「当月有数据的歌的均值」→ 被在池曲目数支配（2023-10 约 20 首、2024-10 约 46 首、2026-10 约 11 首），
     跨月不可比；2026-10 的 −40% 里有很大一块是池子缩小，不能直接做事件归因。
  v2 固定 15 首面板 → 消掉池子效应，但小篮子被个别大歌带动，序列更抖。

v3 做法
  1) 逐首歌：ratio_t = index_t / median(index_{t-90 .. t-1})（只用过去，不看未来）
     至少 30 个历史观测才算得出；不足则跳过该点。
  2) 月度热度 heat = 当月全部 [曲×日] ratio 的**中位**：1.00 = 与该曲自身近 90 天持平。
  3) 广度 breadth = ratio>1 的 [曲×日] 占比（多少歌同时在升）。
  4) 异常判定跑在 heat 上：稳健 z（相对过去 12 个月中位）≥2.5，或 环比 ≥20%。
  5) 事件仍是候选解释，非因果。

同时保留 v1 的池均值 index 与 n_songs 作对照。

输出：data/monthly_events.json（schema v3）
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "monthly_events.json"
DASH = ROOT / "dashboard" / "dashboard_data.json"
LONG_CANDIDATES = [
    Path(r"E:\wx\wx_textmine_out\music_index_long.csv"),
    Path(r"E:\wx\index_records\music_index_long.csv"),
]

BASE_WIN = 90
MIN_HIST = 30
MIN_DAYS = 15
Z_FLAG = 2.5
MOM_FLAG = 0.20

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load_daily():
    path = next((p for p in LONG_CANDIDATES if p.exists()), None)
    if path is None:
        return {}, None
    series = defaultdict(list)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = (row.get("date") or "").strip()[:10]
            try:
                v = float(str(row.get("index", "")).replace(",", ""))
            except ValueError:
                continue
            if len(d) < 10 or v <= 0:
                continue
            series[(row.get("song") or "").strip()].append((d, v))
    for s in series:
        series[s].sort()
    return dict(series), path


def ratios(series):
    out = {}
    for song, pts in series.items():
        for i, (d, v) in enumerate(pts):
            hist = [x[1] for x in pts[max(0, i - BASE_WIN):i]]
            if len(hist) < MIN_HIST:
                continue
            base = statistics.median(hist)
            if base <= 0:
                continue
            out[(d, song)] = v / base
    return out


def load_events():
    d = json.loads(DASH.read_text(encoding="utf-8"))
    buckets = defaultdict(list)
    for key, kind in (("tour_events", "巡演"), ("release_events", "发行"), ("performance_events", "演出/晚会")):
        for item in d.get(key) or []:
            if not item:
                continue
            buckets[str(item[0])[:7]].append({
                "kind": kind,
                "title": str(item[1]) if len(item) > 1 else "",
                "sub": str(item[2]) if len(item) > 2 else "",
            })
    return dict(buckets)


def trend_dev(vals, win=12):
    out = []
    for i, v in enumerate(vals):
        hist = [x for x in vals[max(0, i - win):i] if x]
        if len(hist) < 6 or not v:
            out.append(None)
            continue
        base = statistics.median(hist)
        out.append(round((v / base - 1) * 100, 1) if base else None)
    return out


def robust_z(vals):
    clean = [v for v in vals if v is not None]
    if len(clean) < 6:
        return [None] * len(vals)
    med = statistics.median(clean)
    mad = statistics.median([abs(x - med) for x in clean]) or 1e-9
    return [None if v is None else round((v - med) / (1.4826 * mad), 2) for v in vals]


def main() -> int:
    series, src = load_daily()
    events = load_events()

    if series:
        rat = ratios(series)
        by_month = defaultdict(list)
        days_by_month = defaultdict(set)
        for (d, s), r in rat.items():
            by_month[d[:7]].append(r)
            days_by_month[d[:7]].add(d)
        per_day = defaultdict(list)
        for s, pts in series.items():
            for d, v in pts:
                per_day[d].append(v)
        pool_by_month = defaultdict(list)
        for d, vals in per_day.items():
            pool_by_month[d[:7]].append((statistics.mean(vals), len(vals)))

        rows = []
        for m in sorted(by_month):
            rs = by_month[m]
            pool = pool_by_month.get(m) or [(None, None)]
            rows.append({
                "month": m,
                "heat": round(statistics.median(rs), 3),
                "breadth": round(sum(1 for x in rs if x > 1) / len(rs), 3),
                "n_ratios": len(rs),
                "n_days": len(days_by_month[m]),
                "index": round(statistics.mean(x[0] for x in pool), 1) if pool[0][0] else None,
                "n_songs": round(statistics.mean(x[1] for x in pool)) if pool[0][1] else None,
            })
        caliber = ("逐曲自身基线归一：ratio = 当日指数 / 该曲前 %d 天中位（需 ≥%d 个历史观测）；"
                   "月度热度 = 当月全部 [曲×日] ratio 的中位；1.00 = 与自身基线持平"
                   % (BASE_WIN, MIN_HIST))
        method = ("异常判定跑在热度上：稳健 z（相对过去 12 个月中位偏离）≥2.5 或 环比 ≥20%；"
                  "广度 = ratio>1 的 [曲×日] 占比。池均值 index 仅作对照")
    else:
        d = json.loads(DASH.read_text(encoding="utf-8"))
        rows = [{"month": m, "heat": None, "breadth": None, "n_ratios": 0, "n_days": 1,
                 "index": v, "n_songs": None}
                for m, v in zip(d.get("time_labels") or [], d.get("trend_raw") or [])]
        caliber = "回退：dashboard_data.json 的 trend_raw（无日级长表，无法做自身基线归一）"
        method = "常态口径（回退）"

    heats = [r["heat"] for r in rows]
    devs = trend_dev(heats)
    zs = robust_z(devs)
    for i, r in enumerate(rows):
        h = r["heat"]
        p = rows[i - 1]["heat"] if i and rows[i - 1]["heat"] else None
        r["mom_pct"] = round((h / p - 1) * 100, 1) if (h and p) else None
        r["dev_pct"] = devs[i]
        r["z"] = zs[i]
        ev = events.get(r["month"], [])
        r["events"] = ev
        r["n_events"] = len(ev)
        low_cov = r["n_days"] < MIN_DAYS
        r["coverage_ok"] = not low_cov
        trig = []
        if r["z"] is not None and abs(r["z"]) >= Z_FLAG:
            trig.append("z")
        if r["mom_pct"] is not None and abs(r["mom_pct"]) >= MOM_FLAG * 100:
            trig.append("mom")
        r["trigger"] = trig
        r["anomaly"] = bool(not low_cov and trig)
        if low_cov:
            r["note"] = "覆盖不足（%d 天 < %d），不参与异常判定" % (r["n_days"], MIN_DAYS)
        if r["anomaly"]:
            r["attribution"] = {
                "same_month": ev,
                "prev_month": events.get(rows[i - 1]["month"], []) if i else [],
                "note": "候选解释，非因果；月度粒度不能拆分同月多事件",
            }

    payload = {
        "schema": "monthly-events/v3",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": str(src) if src else "dashboard_data.json",
        "caliber": caliber,
        "method": method,
        "min_days": MIN_DAYS,
        "months": rows,
        "summary": {
            "n_months": len(rows),
            "n_anomaly": sum(1 for r in rows if r["anomaly"]),
            "n_low_coverage": sum(1 for r in rows if not r["coverage_ok"]),
            "n_events": sum(r["n_events"] for r in rows),
            "n_songs_total": len(series) if series else None,
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    s = payload["summary"]
    print(caliber)
    print("月份 %d｜异常 %d｜覆盖不足 %d｜事件 %d｜全期曲目 %s"
          % (s["n_months"], s["n_anomaly"], s["n_low_coverage"], s["n_events"], s["n_songs_total"]))
    for r in rows:
        if r["anomaly"]:
            print("  %s 热度=%.2f 广度=%s 环比=%s z=%s 事件%d"
                  % (r["month"], r["heat"] or 0,
                     ("%.0f%%" % (r["breadth"] * 100)) if r["breadth"] is not None else "—",
                     ("%+.1f%%" % r["mom_pct"]) if r["mom_pct"] is not None else "—",
                     r["z"], r["n_events"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
