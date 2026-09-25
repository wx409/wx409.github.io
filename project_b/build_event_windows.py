# -*- coding: utf-8 -*-
"""事件窗口分析：演出/综艺/晚会 等事件前后，曲目指数的变化。

设计（用户要求：注重关键时间范围）
----------------------------------
对每个**事件**（巡演场次 / 综艺 / 晚会 / 发歌…）取其**前后各 N 天**为窗口：
  · pre  = [日-14, 日-1] 的指数中位
  · post = [日+1, 日+14] 的指数中位
  · lift = post - pre（同时给相对变化 %）
分两组看：
  A) **该场演出的曲目**（setlist 内的歌）→ "唱了它，它涨了吗"
  B) **全池对照**（所有有数据的歌）→ 排除整体漂移（同期大盘）
显著性：符号检验（二项）——不做因果断言，只报方向与强度。

用法：python -X utf8 project_b\\build_event_windows.py [--days 14]
产出：data/event_window_index.json ＋ E:\\wx\\论文素材_王晰作传\\事件窗口_指数响应.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import load, canon, coverage  # noqa: E402

OUT_JSON = SITE / "data" / "event_window_index.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\事件窗口_指数响应.md")


def binom_two_sided(k, n, p=0.5):
    """符号检验（正态近似）"""
    if n == 0:
        return 1.0
    import math
    z = (k - n * p) / math.sqrt(n * p * (1 - p))
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def load_events():
    """事件清单：巡演场次（setlists）+ 生涯事件（timeline）"""
    ev = []
    sl = json.loads((SITE / "data" / "setlists.json").read_text(encoding="utf-8"))["setlists"]
    sl = list(sl.values()) if isinstance(sl, dict) else sl
    for s in sl:
        d = str(s.get("date") or "")[:10]
        if not d:
            continue
        ev.append({"date": d, "kind": "巡演", "label": f"{s.get('tour','')}{s.get('city','')}",
                   "songs": [canon((x or {}).get("title")) for x in (s.get("songs") or [])]})
    tl = json.loads((SITE / "data" / "timeline.json").read_text(encoding="utf-8"))
    tl = tl if isinstance(tl, list) else (tl.get("items") or [])
    for t in tl:
        d = str(t.get("date") or "")[:10]
        if not d:
            continue
        ev.append({"date": d, "kind": t.get("type") or "生涯", "label": t.get("title") or "",
                   "songs": []})
    ev.sort(key=lambda x: x["date"])
    return ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="前后窗口天数")
    a = ap.parse_args()
    N = a.days

    cov = coverage()
    df = load()
    good = df.dropna(subset=["current_index"])
    # 每首歌的日序列（同日取 max）
    series = {k: dict(g.groupby("day")["current_index"].max())
              for k, g in good.groupby("canon")}

    events = load_events()
    print(f"事件 {len(events)} 个（{events[0]['date']} → {events[-1]['date']}）")

    def window(vals, d0, lo, hi):
        return [v for d, v in vals.items()
                if (datetime.fromisoformat(d0) + timedelta(days=lo)).date().isoformat()
                <= d <= (datetime.fromisoformat(d0) + timedelta(days=hi)).date().isoformat()]

    rows, pool_rows, pool_by_event = [], [], []
    for e in events:
        d0 = e["date"]
        try:
            datetime.fromisoformat(d0)
        except Exception:
            continue
        pre_from = (datetime.fromisoformat(d0) - timedelta(days=N)).date().isoformat()
        post_to = (datetime.fromisoformat(d0) + timedelta(days=N)).date().isoformat()
        if post_to > df["day"].max():
            continue                                   # 窗口未走完
        # A) 该场演出的曲目
        for s in set(e["songs"]):
            vals = series.get(s)
            if not vals:
                continue
            pre = [v for d, v in vals.items() if pre_from <= d < d0]
            post = [v for d, v in vals.items() if d0 < d <= post_to]
            if len(pre) < 3 or len(post) < 3:
                continue
            mpre, mpost = statistics.median(pre), statistics.median(post)
            rows.append({"date": d0, "kind": e["kind"], "event": e["label"], "song": s,
                         "n_pre": len(pre), "n_post": len(post),
                         "pre": round(mpre, 1), "post": round(mpost, 1),
                         "delta": round(mpost - mpre, 1),
                         "pct": round(100 * (mpost - mpre) / mpre, 1) if mpre else None})
        # B) 全池对照（同日所有歌）
        ev_pool = []
        for s, vals in series.items():
            pre = [v for d, v in vals.items() if pre_from <= d < d0]
            post = [v for d, v in vals.items() if d0 < d <= post_to]
            if len(pre) < 3 or len(post) < 3:
                continue
            mpre, mpost = statistics.median(pre), statistics.median(post)
            pool_rows.append({"date": d0, "song": s, "delta": mpost - mpre})
            ev_pool.append(mpost - mpre)
        if ev_pool:
            pool_by_event.append({"date": d0, "kind": e["kind"], "event": e["label"],
                                  "n": len(ev_pool), "median": round(statistics.median(ev_pool), 1)})

    if not rows:
        print("无足够数据")
        return 0

    def summarize(rs, key="delta"):
        ds = [r[key] for r in rs if r.get(key) is not None]
        pos = sum(1 for x in ds if x > 0)
        return {"n": len(ds), "median": round(statistics.median(ds), 1) if ds else None,
                "mean": round(sum(ds) / len(ds), 1) if ds else None,
                "pos": pos, "pos_share": round(100 * pos / len(ds), 1) if ds else None,
                "p_sign": round(binom_two_sided(pos, len(ds)), 4)}

    by_kind = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r)
    overall = summarize(rows)
    pool = summarize(pool_rows)
    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "window_days": N, "source": cov,
               "overall_performed_songs": overall,
               "pool_control": pool,
               "by_kind": {k: summarize(v) for k, v in by_kind.items()},
               "rows": sorted(rows, key=lambda x: -(x["delta"] or 0)),
               "pool_rows_n": len(pool_rows), "pool_by_event": pool_by_event}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # 报告
    L = [f"# 事件窗口 × 指数响应（窗口 ±{N} 天）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜事件 {len(events)} 个｜"
         f"可比对 (事件,曲目) 样本 **{overall['n']}** 条", "",
         "## 一、结论速览", "",
         f"- **演出的曲目**：窗口后中位变化 **{overall['median']:+.1f}**（上升占比 {overall['pos_share']}%，"
         f"符号检验 p={overall['p_sign']}，n={overall['n']}）" if overall["median"] is not None else "",
         f"- **同期全池对照**：中位变化 **{pool['median']:+.1f}**（上升占比 {pool['pos_share']}%，"
         f"符号检验 p={pool['p_sign']}，n={pool['n']}）" if pool["median"] is not None else "",
         "", "> 读法：把「演出曲目」的变化**减去**全池变化，才是这场演出可能带来的净效应；",
         "> 本表只做**方向与稳健性**呈现，不作因果断言（宣发、平台推荐、季节都在同时动）。", "",
         "## 二、按事件类型", "", "| 类型 | 样本 | 中位变化 | 上升占比 | p(符号检验) |",
         "|---|---|---|---|---|"]
    for k, v in sorted(payload["by_kind"].items(), key=lambda kv: -kv[1]["n"]):
        L.append(f"| {k} | {v['n']} | {v['median']:+.1f} | {v['pos_share']}% | {v['p_sign']} |")
    L += ["", "## 三、响应最强的 (事件, 曲目) Top 20", "",
          "| 日期 | 类型 | 事件 | 曲目 | 前中位 | 后中位 | 变化 | 相对 |", "|---|---|---|---|---|---|---|---|"]
    for r in payload["rows"][:20]:
        L.append(f"| {r['date']} | {r['kind']} | {r['event'][:18]} | {r['song']} | {r['pre']} | {r['post']} "
                 f"| {r['delta']:+.1f} | {r['pct']}% |")
    L += ["", "## 四、边界", "",
          "- 只纳入窗口完整（事件后 N 天已过）且前后各有 ≥3 个指数点的样本",
          "- 指数源：权威全量源（`raw_archive\\raw_latest.xlsx`）；口径 `current_index`",
          "- 事件清单：`setlists.json`（巡演/签唱）+ `timeline.json`（生涯事件）；综艺/晚会有日期者自动纳入", ""]
    OUT_MD.write_text("\n".join(x for x in L if x != ""), encoding="utf-8")

    print(f"\n演出曲目：n={overall['n']}｜中位变化 {overall['median']:+.1f}｜上升占比 {overall['pos_share']}%｜p={overall['p_sign']}")
    print(f"全池对照：n={pool['n']}｜中位变化 {pool['median']:+.1f}｜上升占比 {pool['pos_share']}%｜p={pool['p_sign']}")
    print("\n按类型：")
    for k, v in sorted(payload["by_kind"].items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {k:<10} n={v['n']:<5} 中位 {v['median']:+.1f}｜上升 {v['pos_share']}%｜p={v['p_sign']}")
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
