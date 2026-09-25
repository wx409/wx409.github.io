# -*- coding: utf-8 -*-
"""个案雕刻（数据量小 → 逐曲当案例，不做统计推断）

A. 核验「一生中最爱 +427」是否为"新进池"假象
B. 低音深度 → 演出场次 → 指数 三联表（他的招牌能力是否换来保留曲目）
C. 用户点名的三首「有效」曲：雾里 / 黎明前的黑暗 / 神魂颠倒
   —— 验证共同点：**跨声部对唱 × 大型晚会曝光**，且它们恰是**指数寿命最长**的一批
用法：python -X utf8 project_b\\build_case_sculpt.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import load, canon  # noqa: E402

FOCUS = ["雾里", "黎明前的黑暗", "神魂颠倒", "一生中最爱", "贝加尔湖畔", "山楂树",
         "谁", "晚风暖暖", "多听有益", "Bésame Mucho", "在路上", "重庆野玫瑰"]
PEAK_ERA = ["雾里", "黎明前的黑暗", "神魂颠倒", "一生中最爱", "贝加尔湖畔", "山楂树",
            "她真漂亮", "Sound of Silence", "Over the Rainbow", "亲密爱人", "月弯弯"]


def med(xs):
    return round(statistics.median(xs), 1) if xs else None


def main() -> int:
    df = load()
    g = df.dropna(subset=["current_index"])
    g = g[g["current_index"] > 0]
    series = {k: dict(x.groupby("day")["current_index"].max()) for k, x in g.groupby("canon")}
    meta = json.loads((SITE / "data" / "songs_meta.json").read_text(encoding="utf-8"))["songs"]
    info = {}
    for k, v in meta.items():
        nm = (v or {}).get("name") or k
        info[canon(re.sub(r"\s+", " ", str(nm)).split("\n")[0])] = v
    alb = json.loads((SITE / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
    ac = {canon(x["title"]): x for x in alb["songs"] if x.get("title")}

    # ── A. 一生中最爱 核验 ───────────────────────────────
    print("=== A. 核验「一生中最爱 +427」 ===")
    s = "\u4e00\u751f\u4e2d\u6700\u7231"
    vals = series.get(s, {})
    d0 = date(2026, 6, 13)
    for label, lo, hi in (("六巡前 90 天", -90, -1), ("六巡期", 0, 71), ("六巡后 30 天", 72, 102)):
        ds = (d0 + timedelta(days=lo)).isoformat(), (d0 + timedelta(days=hi)).isoformat()
        sub = {d: v for d, v in vals.items() if ds[0] <= d <= ds[1]}
        print(f"  {label:<12} 记录 {len(sub):>3} 天｜中位 {med(list(sub.values()))}｜"
              f"峰值 {max(sub.values()) if sub else '—'}")
    newpt = sorted(d for d in vals if d >= "2026-06-01")
    print(f"  六巡前后逐日: {[(d, vals[d]) for d in newpt][:14]}")

    # ── B. 三联表 ────────────────────────────────────────
    print("\n=== B. 低音深度 → 演出场次 → 指数（三联表，按最低音升序）===")
    rows = []
    for name, a in ac.items():
        vals2 = series.get(name)
        sc = (info.get(name) or {}).get("show_count") or 0
        rows.append({"song": name, "low": a.get("low"), "low_hz": a.get("low_hz"),
                     "low_share": (a.get("register_share") or {}).get("low_lt_C3"),
                     "show_count": sc, "idx_days": len(vals2) if vals2 else 0,
                     "idx_median": med(list(vals2.values())) if vals2 else None,
                     "idx_peak": max(vals2.values()) if vals2 else None})
    rows = [r for r in rows if r["low_hz"]]
    rows.sort(key=lambda r: r["low_hz"])
    print(f"  {'曲目':<18}{'最低音':<8}{'Hz':>7}{'低音占比':>9}{'演出':>5}{'指数天':>6}{'指数中位':>9}")
    for r in rows[:18]:
        print(f"  {r['song'][:17]:<18}{str(r['low']):<8}{r['low_hz']:>7}"
              f"{(r['low_share'] if r['low_share'] is not None else '—'):>9}"
              f"{r['show_count']:>5}{r['idx_days']:>6}{str(r['idx_median']):>9}")

    # ── C. 点名三首 + 高光期曲目 ──────────────────────────
    print("\n=== C. 点名三首 / 高光期曲目：共同点检验 ===")
    out = []
    for nm in FOCUS + [x for x in PEAK_ERA if x not in FOCUS]:
        cn = canon(nm)
        vals3 = series.get(cn)
        m = info.get(cn) or {}
        a = ac.get(cn) or {}
        out.append({"song": nm, "idx_days": len(vals3) if vals3 else 0,
                    "first": (min(vals3) if vals3 else None), "last": (max(vals3) if vals3 else None),
                    "median": med(list(vals3.values())) if vals3 else None,
                    "peak": (max(vals3.values()) if vals3 else None),
                    "show_count": m.get("show_count") or 0,
                    "duet": "是" if re.search(r"[王晰].*(张韶涵|么红|黄霄云|尹姝贻)|/|&", str(m.get("name") or nm)) else "—",
                    "low_hz": a.get("low_hz"), "low_note": a.get("low")})
    out.sort(key=lambda x: -x["idx_days"])
    print(f"  {'曲目':<16}{'指数天':>7}{'首日':>12}{'中位':>7}{'峰值':>7}{'演出':>5}{'对唱':>5}")
    for r in out[:20]:
        print(f"  {r['song'][:15]:<16}{r['idx_days']:>7}{str(r['first']):>12}"
              f"{str(r['median']):>7}{str(r['peak']):>7}{r['show_count']:>5}{r['duet']:>5}")
    # 指数寿命 vs 对唱/晚会 的关系
    long_track = [r for r in out if r["idx_days"] >= 500]
    print(f"\n  指数寿命 ≥500 天：{len(long_track)} 首 → {[r['song'] for r in long_track]}")
    duets = [r for r in out if r["duet"] == "是"]
    print(f"  其中含对唱/合作标记：{len(duets)} 首 → {[r['song'] for r in duets]}")

    (SITE / "data" / "case_sculpt.json").write_text(json.dumps(
        {"generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
         "triple_table": rows, "focus": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→ data/case_sculpt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
