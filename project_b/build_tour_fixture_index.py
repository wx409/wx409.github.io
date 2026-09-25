# -*- coding: utf-8 -*-
"""巡演常驻曲目 × 指数：Besame Mucho 案例 + 六巡曲目的指数表现 + 常驻/偶发对照。

正向视角（用户要求）：看微观起伏，不做悲情叙事。
要点：
  · 曲名先过 song_names.canon() 归并（否则 (Live) 等写法会漏算）
  · 常驻度用 songs_meta.show_count（该曲有记录的演出场次）
  · 六巡《回》= 2026-06-13（重庆）起，用其曲目单逐首看指数近期表现

用法：python -X utf8 project_b\\build_tour_fixture_index.py
产出：data/tour_fixture_index.json ＋ 追加到 声学×指数交叉_正向分析.md
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from song_names import canon  # noqa: E402

CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
OUT_JSON = SITE / "data" / "tour_fixture_index.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\声学×指数交叉_正向分析.md")
TOUR6_FROM = "2026-06-13"


def slope(pts):
    if len(pts) < 5:
        return None
    x0 = datetime.fromisoformat(pts[0][0])
    xs = [(datetime.fromisoformat(d) - x0).days for d, _ in pts]
    ys = [v for _, v in pts]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den else None


def main() -> int:
    # ── 指数：按规范名合并 ────────────────────────────────
    raw = defaultdict(list)
    with CSV.open(encoding="utf-8-sig", errors="ignore") as f:
        f.readline()
        for line in f:
            p = line.rstrip("\n").split(",")
            if len(p) >= 3:
                try:
                    raw[canon(p[1])].append((p[0], float(p[2])))
                except ValueError:
                    pass
    for k in raw:
        raw[k].sort()
    last = max(d for v in raw.values() for d, _ in v)
    print(f"指数（按规范名合并）：{len(raw)} 首｜最新 {last}")

    meta = json.loads((SITE / "data" / "songs_meta.json").read_text(encoding="utf-8"))
    songs = meta["songs"]
    by_canon = {}
    for k, v in songs.items():
        nm = (v or {}).get("name") or k
        by_canon[canon(nm)] = {"key": k, **v}

    sets_raw = json.loads((SITE / "data" / "setlists.json").read_text(encoding="utf-8"))["setlists"]
    sets = list(sets_raw.values()) if isinstance(sets_raw, dict) else sets_raw
    t6 = [s for s in sets if str(s.get("tour", "")).startswith("六巡")]
    t6_songs = []
    for s in t6:
        for x in s.get("songs") or []:
            t6_songs.append(canon(x.get("title")))
    t6_counter = defaultdict(int)
    for x in t6_songs:
        t6_counter[x] += 1
    print(f"六巡场次 {len(t6)}｜曲目 {len(t6_counter)} 个｜出现≥2 次 {sum(1 for v in t6_counter.values() if v>=2)} 个")

    def idx_of(name):
        return raw.get(canon(name)) or []

    # ── 案例卡：Besame Mucho ───────────────────────────────
    bs = [k for k in raw if "besame" in k.lower()]
    bs_pts = sorted([x for k in bs for x in raw[k]])
    case = {"canonical": bs, "points": len(bs_pts),
            "first": bs_pts[0][0] if bs_pts else None,
            "last": bs_pts[-1][0] if bs_pts else None}
    if bs_pts:
        case["median_all"] = round(statistics.median([v for _, v in bs_pts]), 1)
        case["slope_all"] = round(slope(bs_pts) or 0, 3)
        byy = defaultdict(list)
        for d, v in bs_pts:
            byy[d[:4]].append((d, v))
        case["by_year"] = {y: {"n": len(p), "median": round(statistics.median([v for _, v in p]), 1),
                               "slope": (round(slope(p), 3) if slope(p) is not None else None)}
                           for y, p in sorted(byy.items())}
        after = [x for x in bs_pts if x[0] >= TOUR6_FROM]
        case["since_tour6"] = {"n": len(after),
                               "median": round(statistics.median([v for _, v in after]), 1) if after else None,
                               "dates": [d for d, _ in after]}
        case["show_count"] = (by_canon.get(canon("Besame Mucho")) or {}).get("show_count")
        case["tour6_appearances"] = t6_counter.get(canon("Besame Mucho"), 0)
    print(f"\n[案例] Bésame Mucho：{case['points']} 天｜{case.get('first')} → {case.get('last')}"
          f"｜中位 {case.get('median_all')}｜六巡以来 {case.get('since_tour6')}")

    # ── 六巡曲目的指数近期表现（合并写法后） ─────────────────
    rows = []
    for name, cnt in t6_counter.items():
        pts = idx_of(name)
        recent = [x for x in pts if x[0] >= TOUR6_FROM]
        pre = [x for x in pts if x[0] < TOUR6_FROM]
        if not pts:
            rows.append({"song": name, "tour6_plays": cnt, "index_days": 0, "note": "指数池无记录"})
            continue
        rows.append({
            "song": name, "tour6_plays": cnt, "index_days": len(pts),
            "median_all": round(statistics.median([v for _, v in pts]), 1),
            "slope_all": (round(slope(pts), 3) if slope(pts) is not None else None),
            "recent_n": len(recent),
            "recent_median": (round(statistics.median([v for _, v in recent]), 1) if recent else None),
            "recent_slope": (round(slope(recent), 3) if slope(recent) is not None else None),
            "pre_median": (round(statistics.median([v for _, v in pre]), 1) if pre else None),
        })
    rows.sort(key=lambda r: (-(r.get("recent_slope") or -99), -(r.get("tour6_plays") or 0)))

    # ── 常驻 vs 偶发（按 show_count 分组看指数趋势） ──────────
    grp = {"常驻(≥10场)": [], "半常驻(4-9场)": [], "偶发(1-3场)": []}
    for name, info in by_canon.items():
        sc = info.get("show_count") or 0
        pts = idx_of(name)
        if len(pts) < 30:
            continue
        sl = slope(pts)
        if sl is None:
            continue
        k = "常驻(≥10场)" if sc >= 10 else ("半常驻(4-9场)" if sc >= 4 else "偶发(1-3场)")
        grp[k].append({"song": name, "show_count": sc, "slope": sl,
                       "median": statistics.median([v for _, v in pts])})
    summary = {}
    for k, v in grp.items():
        if v:
            summary[k] = {"n": len(v),
                          "median_slope": round(statistics.median([x["slope"] for x in v]), 3),
                          "median_index": round(statistics.median([x["median"] for x in v]), 1),
                          "positive_share": round(100 * sum(1 for x in v if x["slope"] > 0) / len(v), 1)}
    print("\n[常驻 vs 偶发]")
    for k, v in summary.items():
        print(f"  {k}: n={v['n']}｜斜率中位 {v['median_slope']:+.3f}｜指数中位 {v['median_index']}｜上升占比 {v['positive_share']}%")

    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "tour6_from": TOUR6_FROM, "index_last": last,
               "case_besame_mucho": case, "tour6_songs": rows,
               "fixture_vs_occasional": summary}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 追加报告章节 ──────────────────────────────────────
    L = ["", "---", "", "# 附：巡演常驻曲目 × 指数（含 Bésame Mucho 案例）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜六巡《回》起点 **{TOUR6_FROM}**｜指数最新 **{last}**", "",
         "## A. 案例：Bésame Mucho", "",
         f"- 规范名合并后（原 `Bésame Mucho` + `Bésame Mucho (Live)` 两条）：**{case['points']} 天**，{case['first']} → {case['last']}",
         f"- 全期中位 **{case.get('median_all')}**｜全期斜率 **{case.get('slope_all')}**/天",
         f"- 演出记录 **{case.get('show_count')}** 场（含六巡 **{case.get('tour6_appearances')}** 次）", "",
         "| 年份 | 有记录天数 | 指数中位 | 年内斜率/天 |", "|---|---|---|---|"]
    for y, v in (case.get("by_year") or {}).items():
        L.append(f"| {y} | {v['n']} | {v['median']} | {v['slope'] if v['slope'] is not None else '—'} |")
    s6 = case.get("since_tour6") or {}
    L += ["", f"**六巡以来**：仅 **{s6.get('n')} 天**有指数记录（{', '.join(s6.get('dates') or []) or '—'}）"
              f"，中位 {s6.get('median')}。",
          "> 结论：**现场常驻 ≠ 指数池持续追踪**。他连续在六巡演这首歌，但平台的追踪池 2026 年几乎不再收录它",
          "> —— 这是「作品热度」与「平台跟踪口径」的差异，不是唱得不好；也说明**看微观起伏必须同时看是否还在被追踪**。", "",
          "## B. 六巡曲目的指数表现（按规范名合并后）", "",
          "| 曲目 | 六巡演出次数 | 指数天数 | 全期中位 | 近期记录数 | 近期中位 |", "|---|---|---|---|---|---|"]
    for r in rows[:20]:
        if r.get("index_days"):
            L.append(f"| {r['song']} | {r['tour6_plays']} | {r['index_days']} | {r.get('median_all','—')} "
                     f"| {r.get('recent_n',0)} | {r.get('recent_median','—')} |")
        else:
            L.append(f"| {r['song']} | {r['tour6_plays']} | 0 | — | — | （指数池无记录） |")
    L += ["", "## C. 常驻 vs 偶发（指数趋势对照）", "",
          "| 分组 | n | 斜率中位/天 | 指数中位 | 上升占比 |", "|---|---|---|---|---|"]
    for k, v in summary.items():
        L.append(f"| {k} | {v['n']} | {v['median_slope']:+.3f} | {v['median_index']} | {v['positive_share']}% |")
    L += ["", "> 读法：分组只是**描述性对照**，不构成因果。常驻曲目通常也是代表作，因此指数本就更高。", ""]
    if OUT_MD.exists():
        base = OUT_MD.read_text(encoding="utf-8")
        marker = "# 附：巡演常驻曲目 × 指数"
        if marker in base:                      # 幂等：去掉旧附节再写
            base = base.split("\n---\n\n" + marker)[0]
        OUT_MD.write_text(base.rstrip() + "\n" + "\n".join(L), encoding="utf-8")
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}（已追加 A/B/C 三节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
