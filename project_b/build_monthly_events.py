#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月度事件研究：把「事件后逐日 CAR」改成「按月看变化 + 异常月归因」。

为什么要改
  · 现阶段演出密度低，逐日 CAR 窗口内经常只有一个观测，噪声大于信号；
  · 月度粒度天然把「巡演/晚会/发行」等多种事件放进同一个桶，适合先看趋势再解释。

口径（与全站一致）
  · 指数 = 追踪曲目池**日均**（每日先对当日有数据的曲目取均值，再按月取日级值的中位/均值）
  · 只统计当月有数据的天数（n_days），n_days 过少的月份标「覆盖不足」，不参与异常判定
  · 归因是**候选解释**，不是因果结论：月度粒度无法把同月多事件分开

方法选择（对照成熟实现）
  · 变化点/异常：稳健 z（中位 + MAD），做法同 ruptures 的「均值漂移」思路但不用其算法
    （本机 numba/llvmlite 被策略拦，stumpy 用不了；ruptures 纯 numpy 可跑，但 47 个点没必要）
  · 事件窗口：±1 月（前置 1 月用于捕捉「宣发提前」）
  · 归因：只给「同月事件 / 前 1 月事件」清单 + 事件密度，不给因果权重

输出：data/monthly_events.json
用法：python -X utf8 project_b\\build_monthly_events.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "monthly_events.json"
DASH = ROOT / "dashboard" / "dashboard_data.json"
LONG_CANDIDATES = [
    Path(r"E:\wx\wx_textmine_out\music_index_long.csv"),
    Path(r"E:\wx\index_records\music_index_long.csv"),
]

MIN_DAYS = 15          # 当月有效天数下限
Z_FLAG = 2.5           # 稳健 z 阈值
MOM_FLAG = 0.20        # 环比幅度阈值

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load_daily() -> dict[str, list[float]]:
    """{YYYY-MM: [日级均值, ...]}（已去重同日）。"""
    path = next((p for p in LONG_CANDIDATES if p.exists()), None)
    if path is None:
        return {}
    per_day: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = (row.get("date") or "").strip()[:10]
            if len(d) < 7:
                continue
            try:
                v = float(str(row.get("index", "")).replace(",", "").strip())
            except ValueError:
                continue
            if v <= 0:
                continue
            per_day.setdefault(d, {})[(row.get("song") or "").strip()] = v
    monthly: dict[str, list[float]] = {}
    for d, songs in per_day.items():
        vals = list(songs.values())
        if not vals:
            continue
        monthly.setdefault(d[:7], []).append(statistics.mean(vals))
    for k in monthly:
        monthly[k].sort()
    return monthly


def load_events() -> dict[str, list[dict]]:
    d = json.loads(DASH.read_text(encoding="utf-8"))
    buckets: dict[str, list[dict]] = {}
    kind_map = (("tour_events", "巡演"), ("release_events", "发行"), ("performance_events", "演出/晚会"))
    for key, kind in kind_map:
        for item in d.get(key) or []:
            if not item:
                continue
            month = str(item[0])[:7]
            title = str(item[1]) if len(item) > 1 else ""
            sub = str(item[2]) if len(item) > 2 else ""
            buckets.setdefault(month, []).append({"kind": kind, "title": title, "sub": sub})
    return buckets


def trend_dev(vals: list[float], win: int = 12) -> list[float | None]:
    """相对趋势的偏离（%）：与「过去 win 个月中位」比，避免把长期下行当异常。"""
    out: list[float | None] = []
    for i, v in enumerate(vals):
        hist = vals[max(0, i - win):i]
        if len(hist) < 6:
            out.append(None)
            continue
        base = statistics.median(hist)
        out.append(round((v / base - 1) * 100, 1) if base else None)
    return out


def robust_z(vals: list[float | None]) -> list[float | None]:
    """对已去趋势的偏离序列做稳健 z（中位 + MAD）。"""
    clean = [v for v in vals if v is not None]
    if len(clean) < 6:
        return [None] * len(vals)
    med = statistics.median(clean)
    mad = statistics.median([abs(x - med) for x in clean]) or 1e-9
    return [None if v is None else round((v - med) / (1.4826 * mad), 2) for v in vals]


def main() -> int:
    monthly = load_daily()
    events = load_events()
    if not monthly:
        print("找不到日级长表，退回 dashboard_data.json 的 trend_raw")
        d = json.loads(DASH.read_text(encoding="utf-8"))
        monthly = {m: [v] for m, v in zip(d.get("time_labels") or [], d.get("trend_raw") or [])}

    months = sorted(monthly)
    rows = []
    for m in months:
        days = monthly[m]
        rows.append({
            "month": m,
            "index": round(statistics.mean(days), 1),
            "median": round(statistics.median(days), 1),
            "n_days": len(days),
        })

    idx = [r["index"] for r in rows]
    devs = trend_dev(idx)
    zs = robust_z(devs)
    for i, r in enumerate(rows):
        r["mom_pct"] = (round((idx[i] / idx[i - 1] - 1) * 100, 1) if i and idx[i - 1] else None)
        r["dev_pct"] = devs[i]
        r["z"] = zs[i]
        ev = events.get(r["month"], [])
        r["events"] = ev
        r["n_events"] = len(ev)
        r["kinds"] = sorted({e["kind"] for e in ev})
        low_cov = r["n_days"] < MIN_DAYS
        r["coverage_ok"] = not low_cov
        # 两个信号取「或」：稳健 z 会被整年高波动撑大，单看 z 会漏掉 -40% 这种大偏离
        # 触发信号二选一：本月环比突变（≥20%）或 相对趋势的稳健 z 异常（≥2.5）。
        # 两者都不看"长期下行"本身——持续下滑只会在第一次突变时被标记。
        trig = []
        if r["z"] is not None and abs(r["z"]) >= Z_FLAG:
            trig.append("z")
        if r["mom_pct"] is not None and abs(r["mom_pct"]) >= MOM_FLAG * 100:
            trig.append("mom")
        flag = bool(not low_cov and trig)
        r["trigger"] = trig
        r["anomaly"] = bool(flag)
        if flag:
            prev = rows[i - 1]["month"] if i else None
            r["attribution"] = {
                "same_month": [e for e in ev],
                "prev_month": events.get(prev, []) if prev else [],
                "note": "候选解释，非因果；月度粒度无法拆分同月多事件",
            }
        if low_cov:
            r["note"] = f"覆盖不足（{r['n_days']} 天 < {MIN_DAYS}），不参与异常判定"

    payload = {
        "schema": "monthly-events/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "caliber": "追踪曲目池日均（每日对当日有数据曲目取均值，再按月平均）",
        "window": "先算相对过去 12 个月中位的偏离(%)，再对偏离做稳健 z(中位+MAD)；|z|≥2.5 且 |偏离|≥20%",
        "min_days": MIN_DAYS,
        "z_flag": Z_FLAG,
        "months": rows,
        "summary": {
            "n_months": len(rows),
            "n_anomaly": sum(1 for r in rows if r["anomaly"]),
            "n_low_coverage": sum(1 for r in rows if not r["coverage_ok"]),
            "n_events": sum(r["n_events"] for r in rows),
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    s = payload["summary"]
    print(f"月份 {s['n_months']}｜异常 {s['n_anomaly']}｜覆盖不足 {s['n_low_coverage']}｜事件 {s['n_events']}")
    for r in rows:
        if r["anomaly"]:
            ev = "、".join(e["title"][:22] for e in r["events"][:2]) or "（同月无登记事件）"
            mom = r['mom_pct'] if r['mom_pct'] is not None else float('nan')
            z = r['z'] if r['z'] is not None else float('nan')
            print("  %s idx=%6.1f mom=%6.1f%% z=%5.2f 事件%d: %s"
                  % (r['month'], r['index'], mom, z, len(r['events']), ev))
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
