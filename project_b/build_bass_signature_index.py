# -*- coding: utf-8 -*-
"""A 个案核验 + B 六巡相关曲目 + C 低音特色曲的市场表现（跳出现有框架）。

专业视角
--------
此前分析用「平均声学指标」（稳定性/颤音/跨度）去相关指数 —— 那是**歌手通用指标**，
无法体现他的**声部稀缺性**。本脚本改看**低音特征本身**：
  · 最低音深度 low_hz（B1–D2 主区 = 低于男低音下限 E2 82.4Hz）
  · 低音区占比 register_share.low_lt_C3（< C3 的音符时长占比）—— 真正"低音区漂亮"的度量
并检验：**这些歌的市场表现（指数水平/趋势/演出频次）是否不同**。

用法：python -X utf8 project_b\\build_bass_signature_index.py
产出：data/bass_signature_index.json ＋ E:\\wx\\论文素材_王晰作传\\低音特色曲_市场表现.md
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import load, canon  # noqa: E402

OUT_JSON = SITE / "data" / "bass_signature_index.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\低音特色曲_市场表现.md")
E2 = 82.41          # 男低音常规下限
D2 = 73.42
TOUR6 = ("2026-06-13", "2026-08-23")
PRE6 = ("2026-01-01", "2026-06-12")


def med(xs):
    return round(statistics.median(xs), 1) if xs else None


def main() -> int:
    df = load()
    good = df.dropna(subset=["current_index"])
    good = good[good["current_index"] > 0]      # 0 值 = 占位行（无指数），必须剔除
    series = {k: dict(g.groupby("day")["current_index"].max()) for k, g in good.groupby("canon")}
    last = max(d for v in series.values() for d in v)

    alb = json.loads((SITE / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
    songs = {canon(x["title"]): x for x in alb["songs"] if x.get("title")}
    meta = json.loads((SITE / "data" / "songs_meta.json").read_text(encoding="utf-8"))["songs"]
    shows = {}
    for k, v in meta.items():
        shows[canon((v or {}).get("name") or k)] = (v or {}).get("show_count") or 0

    # ══ A. 个案核验 ═══════════════════════════════════════
    print("=== A. 个案核验 ===")
    cases = []
    for label, d0 in (("2024-06-07 音乐剧《光影少年》", "2024-06-07"),
                      ("2026-08-23 六巡「回」广州站", "2026-08-23")):
        from datetime import date, timedelta
        dd = date.fromisoformat(d0)
        win = lambda lo, hi: [(dd + timedelta(days=k)).isoformat() for k in range(lo, hi + 1)]
        pre_d, post_d = win(-14, -1), win(1, 14)
        pre = [v for s, vals in series.items() for d, v in vals.items() if d in pre_d]
        post = [v for s, vals in series.items() for d, v in vals.items() if d in post_d]
        # 该事件当天/前后有无"新进池"的歌（解释异常幅度）
        new_in = [s for s, vals in series.items()
                  if any(d in post_d for d in vals) and not any(d in pre_d for d in vals)]
        cases.append({"event": label, "date": d0, "pre_n": len(pre), "post_n": len(post),
                      "pre_median": med(pre), "post_median": med(post),
                      "delta": round((med(post) or 0) - (med(pre) or 0), 1),
                      "new_songs_in_pool": len(new_in), "new_songs": new_in[:8]})
        c = cases[-1]
        print(f"  {label}: 前中位 {c['pre_median']} → 后中位 {c['post_median']}（Δ{c['delta']:+}）"
              f"｜窗口内新进池 {c['new_songs_in_pool']} 首 {c['new_songs'][:4]}")

    # ══ B. 六巡相关曲目 ═══════════════════════════════════
    print("\n=== B. 六巡期间指数提升榜（2026-06-13~08-23 vs 2026 前半年）===")
    lift = []
    for s, vals in series.items():
        a = [v for d, v in vals.items() if TOUR6[0] <= d <= TOUR6[1]]
        b = [v for d, v in vals.items() if PRE6[0] <= d <= PRE6[1]]
        if len(a) >= 2 and len(b) >= 2:
            ma, mb = statistics.median(a), statistics.median(b)
            lift.append({"song": s, "tour6_n": len(a), "pre_n": len(b),
                         "tour6_median": round(ma, 1), "pre_median": round(mb, 1),
                         "delta": round(ma - mb, 1),
                         "pct": round(100 * (ma - mb) / mb, 1) if mb else None,
                         "show_count": shows.get(s, 0)})
    lift.sort(key=lambda x: -x["delta"])
    for r in lift[:10]:
        print(f"  ↑ {r['song']:<20} {r['pre_median']:>7} → {r['tour6_median']:>7}（{r['delta']:+7.1f}）"
              f"｜演出 {r['show_count']} 场")
    bm = next((r for r in lift if "esame" in r["song"].lower() or "ésame" in r["song"]), None)
    print(f"  Bésame Mucho: {bm}")

    # ══ C. 低音特色 × 市场表现 ════════════════════════════
    print("\n=== C. 低音特色曲 vs 其他（声部特征口径）===")
    rows = []
    for s, a in songs.items():
        vals = series.get(s)
        if not vals or len(vals) < 20:
            continue
        rs = a.get("register_share") or {}
        rows.append({"song": s, "album": a.get("album"), "low_hz": a.get("low_hz"),
                     "low_note": a.get("low"), "low_share": rs.get("low_lt_C3"),
                     "vibrato_hz": a.get("vibrato_hz"), "median_index": med(list(vals.values())) or 0,
                     "days": len(vals), "show_count": shows.get(s, 0)})
    deep = [r for r in rows if (r["low_hz"] or 999) <= D2]
    b1 = [r for r in rows if (r["low_hz"] or 999) <= E2]
    rest = [r for r in rows if (r["low_hz"] or 999) > E2]
    def grp(name, arr):
        if not arr:
            return {"name": name, "n": 0}
        return {"name": name, "n": len(arr),
                "median_index": med([x["median_index"] for x in arr]),
                "median_show": med([x["show_count"] for x in arr]),
                "median_days": med([x["days"] for x in arr])}
    groups = [grp("极低音（≤D2 73.4Hz）", deep), grp("低音区（≤E2 82.4Hz）", b1),
              grp("其他", rest)]
    for g in groups:
        if g["n"]:
            print(f"  {g['name']:<22} n={g['n']:<3} 指数中位 {g['median_index']:>7}"
                  f"｜演出中位 {g['median_show']:>5} 场｜有记录 {g['median_days']} 天")
    # 低音占比三分位
    shares = sorted([r for r in rows if r["low_share"] is not None], key=lambda x: x["low_share"])
    if len(shares) >= 9:
        k = len(shares) // 3
        lo, mid, hi = shares[:k], shares[k:2 * k], shares[2 * k:]
        for nm, arr in (("低音占比 低 1/3", lo), ("中 1/3", mid), ("高 1/3", hi)):
            print(f"  {nm:<22} n={len(arr):<3} 指数中位 {med([x['median_index'] for x in arr])}"
                  f"｜演出中位 {med([x['show_count'] for x in arr])} 场"
                  f"｜低音占比中位 {med([x['low_share'] for x in arr])}")

    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "source_last_day": last, "cases": cases,
               "tour6_lift": lift, "tour6_lift_top": lift[:25],
               "bass_groups": groups,
               "low_share_tertiles": ([{"name": "低", "n": len(lo), "median_index": med([x['median_index'] for x in lo])},
                                       {"name": "中", "n": len(mid), "median_index": med([x['median_index'] for x in mid])},
                                       {"name": "高", "n": len(hi), "median_index": med([x['median_index'] for x in hi])}]
                                      if len(shares) >= 9 else []),
               "rows": rows}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 低音特色曲 × 市场表现（跳出生学均值框架）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜指数源最新 {last}", "",
         "## 一、为什么换口径", "",
         "此前的「稳定性/颤音/跨度」是**歌手通用指标**，任何歌手都可比；",
         "他的**稀缺性在声部本身**——所以本表改看：最低音深度、**低音区占比**（<C3 音符时长占比）。", "",
         "## 二、个案核验（事件窗口幅度是否真实）", "",
         "| 事件 | 前中位 | 后中位 | Δ | 窗口内新进池歌曲数 |", "|---|---|---|---|---|"]
    for c in cases:
        L.append(f"| {c['event']} | {c['pre_median']} | {c['post_median']} | {c['delta']:+} | {c['new_songs_in_pool']} |")
    L += ["", "## 三、六巡期间指数提升榜（Top 15）", "",
          "| 曲目 | 巡演前中位 | 六巡期中位 | Δ | 演出场次 |", "|---|---|---|---|---|"]
    for r in lift[:15]:
        L.append(f"| {r['song']} | {r['pre_median']} | {r['tour6_median']} | {r['delta']:+.1f} | {r['show_count']} |")
    L += ["", f"**Bésame Mucho**：{bm if bm else '六巡期与前期样本不足'}（六巡期为其常驻曲目）", "",
          "## 四、低音特色曲 vs 其他", "",
          "| 分组 | n | 指数中位 | 演出场次中位 | 指数记录天数中位 |", "|---|---|---|---|---|"]
    for g in groups:
        if g["n"]:
            L.append(f"| {g['name']} | {g['n']} | {g['median_index']} | {g['median_show']} | {g['median_days']} |")
    if payload["low_share_tertiles"]:
        L += ["", "低音区占比三分位：", ""]
        for t in payload["low_share_tertiles"]:
            L.append(f"- {t['name']} 1/3：n={t['n']}｜指数中位 {t['median_index']}")
    L += ["", "## 五、边界", "",
          "- 指数源：权威全量源；口径 `current_index`；同日取 max",
          "- 声学：录音室 72 曲稳定音口径；`low_lt_C3` = 低于 C3 的音符时长占比",
          "- 分组对照为**描述性**，存在代表作/宣发混杂，不作因果断言", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
