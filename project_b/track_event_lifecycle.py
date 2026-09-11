# -*- coding: utf-8 -*-
"""活动生命周期追踪 —— 官宣 / 开票 / 开演，逐里程碑自动统计「指数前后变化」。

用途：任何一次活动（单场演唱会、专辑发行、综艺播出）从官宣到开演会产生多次数据波动，
本脚本把「里程碑日期」和「该日期前后的追踪曲目池日均指数」绑在一起，每次跑自动回填，
后续开票、开演只要在 event_lifecycle.json 里补一行日期即可，无需改代码。

数据源（本地单一事实源，不进公开仓库）：
  E:\\wx\\wx_textmine_out\\music_index_long.csv（date, song, index）
  口径与 data/archive_baseline.json 一致：追踪曲目池日均（非全站；每日最终指数）

输出：
  data/event_lifecycle.json   里程碑 + 每个里程碑的窗口统计（站点可引用）
  data/event_lifecycle.md     人读报告（含口径与边界）

用法：
  python -X utf8 project_b/track_event_lifecycle.py            # 刷新全部窗口
  python -X utf8 project_b/track_event_lifecycle.py --md-only  # 只重渲 md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STORE = DATA / "event_lifecycle.json"
REPORT = DATA / "event_lifecycle.md"
INDEX_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")

CALIBER = "追踪曲目池日均（每日最终指数；口径同 data/archive_baseline.json）"
WINDOWS = [("pre7", -7, -1), ("pre3", -3, -1), ("d0", 0, 0), ("post3", 1, 3), ("post7", 1, 7)]


def daily_series() -> dict[str, float]:
    out: dict[str, float] = {}
    if not INDEX_CSV.exists():
        return out
    try:
        import pandas as pd
        df = pd.read_csv(INDEX_CSV)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["idx"] = pd.to_numeric(df["index"], errors="coerce")
        df = df[df["idx"] > 0]
        g = df.groupby(df["date"].dt.strftime("%Y-%m-%d"))["idx"].agg(["mean", "count"])
        for d, r in g.iterrows():
            out[d] = {"mean": round(float(r["mean"]), 1), "n": int(r["count"])}
    except Exception as e:
        print(f"[WARN] 指数长表读取失败：{type(e).__name__} {e}")
    return out


def window_stats(series: dict, d0: datetime) -> dict:
    res = {"date": d0.strftime("%Y-%m-%d"), "windows": {}, "n_days": len(series)}
    for name, a, b in WINDOWS:
        vals, ns = [], []
        for off in range(a, b + 1):
            k = (d0 + timedelta(days=off)).strftime("%Y-%m-%d")
            if k in series:
                vals.append(series[k]["mean"])
                ns.append(series[k]["n"])
        res["windows"][name] = {
            "n_days": len(vals),
            "mean_index": round(statistics.mean(vals), 1) if vals else None,
            "median_index": round(statistics.median(vals), 1) if vals else None,
            "avg_tracked_songs": round(statistics.mean(ns), 1) if ns else None,
            "complete": len(vals) == (b - a + 1),
        }
    pre = res["windows"]["pre7"]["mean_index"]
    post = res["windows"]["post7"]["mean_index"]
    if pre and post:
        res["delta_pct_post7_vs_pre7"] = round((post / pre - 1) * 100, 1)
    else:
        res["delta_pct_post7_vs_pre7"] = None
    p3, o3 = res["windows"]["pre3"]["mean_index"], res["windows"]["post3"]["mean_index"]
    res["delta_pct_post3_vs_pre3"] = round((o3 / p3 - 1) * 100, 1) if p3 and o3 else None
    return res


def render_md(doc: dict) -> str:
    L = ["# 活动生命周期追踪", "",
         f"> 刷新：{doc.get('generated_at')} ｜ 口径：{CALIBER}",
         "> 追踪曲目池每日覆盖数十首作品，窗口均值用于看**方向与量级**，不做单曲级因果；样本不足的窗口标「数据不足」。", ""]
    for ev in doc.get("events") or []:
        L.append(f"## {ev.get('title')}")
        if ev.get("organizer"):
            L.append(f"- 主办：{ev['organizer']}｜地点：{ev.get('venue') or '待定'}"
                     + (f"｜演出日期：{ev['show_date']}" if ev.get("show_date") else ""))
        if ev.get("note"):
            L.append(f"- 说明：{ev['note']}")
        L.append("")
        L.append("| 里程碑 | 日期 | 前7日均 | 前3日均 | 当日 | 后3日均 | 后7日均 | 后7日vs前7日 | 来源 |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for ms in ev.get("milestones") or []:
            w = (ms.get("stats") or {}).get("windows") or {}
            f = lambda k: ("—" if not w.get(k, {}).get("mean_index") else f"{w[k]['mean_index']:.0f}"
                           + ("" if w[k].get("complete") else "（部分）"))
            d = ms.get("delta_pct_post7_vs_pre7")
            L.append(f"| {ms.get('kind')} | {ms.get('date')} | {f('pre7')} | {f('pre3')} | {f('d0')} | "
                     f"{f('post3')} | {f('post7')} | " + (f"{d:+.1f}%" if d is not None else "—") +
                     f" | {ms.get('source_label') or ms.get('source') or ''} |")
        L.append("")
        if ev.get("future"):
            L.append("**待发生**：" + "；".join(f"{x['kind']} {x['date']}" for x in ev["future"]) + "")
            L.append("")
    L += ["---", "",
          "## 维护方式（省 token）", "",
          "1. 新活动：在 `data/event_lifecycle.json` 的 `events` 里加一条（title/venue/organizer/show_date/milestones）。",
          "2. 新里程碑（开票/开演/收官）：只在该活动的 `milestones` 里补 `{kind, date, source, source_label}`。",
          "3. 跑 `python -X utf8 project_b/track_event_lifecycle.py`（已接入每日 deploy_all），窗口统计自动回填。", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md-only", action="store_true")
    args = ap.parse_args()

    doc = json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else {"schema": 1, "events": []}
    series = {} if args.md_only else daily_series()
    if not args.md_only:
        for ev in doc.get("events") or []:
            for ms in ev.get("milestones") or []:
                if not ms.get("date"):
                    continue
                try:
                    d0 = datetime.strptime(ms["date"][:10], "%Y-%m-%d")
                except ValueError:
                    continue
                ms["stats"] = window_stats(series, d0)
        doc["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        doc["caliber"] = CALIBER
        doc["index_days_local"] = len(series)
        STORE.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    REPORT.write_text(render_md(doc), encoding="utf-8")

    for ev in doc.get("events") or []:
        for ms in ev.get("milestones") or []:
            st = ms.get("stats") or {}
            w = st.get("windows") or {}
            print(f"  {ev.get('title','')[:22]}｜{ms.get('kind')} {ms.get('date')}｜"
                  f"pre7={w.get('pre7',{}).get('mean_index')} post7={w.get('post7',{}).get('mean_index')} "
                  f"Δ={st.get('delta_pct_post7_vs_pre7')}%"
                  + ("" if w.get("post7", {}).get("complete") else "（后窗未满，自动续算）"))
    print(f"[OK] {STORE}")
    print(f"[OK] {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
