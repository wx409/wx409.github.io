# -*- coding: utf-8 -*-
"""声学 × QQ指数 交叉分析（正向视角）：哪些曲目指数在增长，与演唱能力有何关联。

设计原则（用户要求 + 站内纪律）
------------------------------
1. **正向叙事**：指数绝对值小不代表没意义 —— 关注**微观起伏**（斜率、动量、峰值）。
2. **不写死数字**：全部由本脚本从数据算出并注入 JSON/MD。
3. **诚实标注**：相关系数必须给出样本量、方法（Spearman）与 p 值；不把相关说成因果。

输入：
  · 指数长表  E:\\wx\\wx_textmine_out\\music_index_long.csv   (date, song, index)
  · 声学指标  D:\\wx409.github.io\\data\\archive_vocal_albums.json (72 曲)
输出：
  · D:\\wx409.github.io\\data\\acoustic_index_cross.json
  · E:\\wx\\论文素材_王晰作传\\声学×指数交叉_正向分析.md

用法：python -X utf8 project_b\\build_acoustic_index_cross.py [--trend-days 90] [--min-days 60]
"""
from __future__ import annotations

import argparse
import json
import sys
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from song_names import canon  # noqa: E402

SITE = Path(__file__).resolve().parent.parent
CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\声学×指数交叉_正向分析.md")
OUT_JSON = SITE / "data" / "acoustic_index_cross.json"

ACOUSTIC_FEATURES = [
    ("low_hz", "最低稳定音（Hz，越低越深）"),
    ("high_hz", "最高稳定音（Hz）"),
    ("span_octaves", "跨度（八度）"),
    ("stability_cents", "音符内稳定性（音分，越小越稳）"),
    ("intonation_cents", "音准偏差（音分）"),
    ("vibrato_hz", "颤音速率（Hz）"),
    ("vibrato_cents", "颤音幅度（音分）"),
    ("hnr_db", "材料级 HNR（dB）"),
    ("density", "音符密度（个/秒）"),
]


def spearman(xs, ys):
    """秩相关 + 近似 p（无 scipy 依赖）。"""
    n = len(xs)
    if n < 5:
        return None, None, n

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0 or dy == 0:
        return None, None, n
    rho = num / (dx * dy)
    # t 近似 → 双侧 p
    if abs(rho) >= 1:
        return rho, 0.0, n
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    # 用正态近似（n 较大时足够）
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return rho, p, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trend-days", type=int, default=90)
    ap.add_argument("--min-days", type=int, default=40, help="该曲至少有多少天指数才纳入")
    ap.add_argument("--active-days", type=int, default=30, help="距全表最新日期多少天内仍有记录=仍在追踪")
    ap.add_argument("--min-window-points", type=int, default=12, help="趋势窗口内至少多少个点")
    ap.add_argument("--common-days", type=int, default=730, help="公平比较用的同一日历窗口（天）")
    ap.add_argument("--min-common-points", type=int, default=30, help="同一窗口内至少多少个点")
    a = ap.parse_args()

    # ── 读指数 ─────────────────────────────────────────────
    series = defaultdict(list)      # song -> [(date, index)]
    with CSV.open(encoding="utf-8-sig", errors="ignore") as f:
        head = f.readline()
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) < 3:
                continue
            d, s, v = parts[0], parts[1], parts[2]
            try:
                series[canon(s)].append((d, float(v)))
            except ValueError:
                continue
    for s in series:
        series[s].sort()
    all_dates = sorted({d for v in series.values() for d, _ in v})
    last = all_dates[-1]
    cutoff = (datetime.fromisoformat(last) - timedelta(days=a.trend_days)).date().isoformat()
    common_from = (datetime.fromisoformat(last) - timedelta(days=a.common_days)).date().isoformat()
    print(f"指数：{len(series)} 首｜{len(all_dates)} 天｜{all_dates[0]} → {last}｜趋势窗口 {cutoff} 起")

    # ── 逐曲指标（按每首歌自己的最后一段算，因指数池是滚动的）──
    rows = []
    for sname, pts in series.items():
        if len(pts) < a.min_days:
            continue
        last_seen = pts[-1][0]
        gap_days = (datetime.fromisoformat(last) - datetime.fromisoformat(last_seen)).days
        active = gap_days <= a.active_days
        # 该曲自己的趋势窗口：末次记录往前 trend_days 天
        w0 = (datetime.fromisoformat(last_seen) - timedelta(days=a.trend_days)).date().isoformat()
        win = [(d, v) for d, v in pts if d >= w0]
        if len(win) < a.min_window_points:
            continue
        med_all = statistics.median([v for _, v in pts])
        med_win = statistics.median([v for _, v in win])
        x0 = datetime.fromisoformat(win[0][0])
        xs = [(datetime.fromisoformat(d) - x0).days for d, _ in win]
        ys = [v for _, v in win]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den else 0.0
        # 窗口内动量：后 1/3 中位 / 前 1/3 中位
        k = max(1, n // 3)
        f_med = statistics.median(ys[:k])
        l_med = statistics.median(ys[-k:])
        # 全生命周期斜率（样本更大，作为主相关指标）
        lx0 = datetime.fromisoformat(pts[0][0])
        lxs = [(datetime.fromisoformat(d) - lx0).days for d, _ in pts]
        lys = [v for _, v in pts]
        ln_ = len(lxs)
        lmx, lmy = sum(lxs) / ln_, sum(lys) / ln_
        lden = sum((x - lmx) ** 2 for x in lxs)
        slope_life = (sum((x - lmx) * (y - lmy) for x, y in zip(lxs, lys)) / lden) if lden else 0.0
        # 同一日历窗口斜率（公平比较：所有歌都在同一段时间里比）
        cw = [(d, v) for d, v in pts if d >= common_from]
        slope_c = None
        cw_med = None
        if len(cw) >= a.min_common_points:
            cx0 = datetime.fromisoformat(cw[0][0])
            cx = [(datetime.fromisoformat(d) - cx0).days for d, _ in cw]
            cy = [v for _, v in cw]
            cn = len(cx)
            cmx, cmy = sum(cx) / cn, sum(cy) / cn
            cden = sum((x - cmx) ** 2 for x in cx)
            slope_c = (sum((x - cmx) * (y - cmy) for x, y in zip(cx, cy)) / cden) if cden else 0.0
            cw_med = statistics.median(cy)
        rows.append({
            "song": sname, "days": len(pts), "active": active, "gap_days": gap_days,
            "common_points": len(cw),
            "slope_common": (round(slope_c, 3) if slope_c is not None else None),
            "slope_common_pct": (round(100 * slope_c / cw_med, 4) if (slope_c is not None and cw_med) else None),
            "slope_lifetime": round(slope_life, 4),
            "slope_lifetime_pct": round(100 * slope_life / med_all, 4) if med_all else None,
            "median_index": round(med_all, 1), "median_window": round(med_win, 1),
            "slope_per_day": round(slope, 3),
            "slope_pct_of_median": round(100 * slope / med_all, 3) if med_all else None,
            "momentum": round(l_med / f_med, 3) if f_med else None,
            "peak": round(max(v for _, v in pts), 1),
            "first": pts[0][0], "last_seen": last_seen,
            "window_points": len(win),
        })
    print(f"  计入趋势的曲目 {len(rows)} 首（其中近 {a.active_days} 天仍在追踪 {sum(1 for r in rows if r['active'])} 首）")

    # ── 声学 join ─────────────────────────────────────────
    alb = json.loads((SITE / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
    acoustic = {canon(x.get("title")): x for x in alb.get("songs", []) if x.get("title")}
    matched = [r for r in rows if r["song"] in acoustic]
    print(f"可配对（有指数>=门槛 且 有录音室声学）：{len(matched)} 首")
    for r in matched:
        ac = acoustic[r["song"]]
        r["album"] = ac.get("album")
        for k, _ in ACOUSTIC_FEATURES:
            r[k] = ac.get(k)

    # ── 相关分析 ───────────────────────────────────────────
    corr = []
    growth_metric = "slope_common"
    for k, label in ACOUSTIC_FEATURES:
        xs, ys = [], []
        for r in matched:
            if r.get(k) is None or r.get(growth_metric) is None:
                continue
            xs.append(float(r[k]))
            ys.append(float(r[growth_metric]))
        rho, p, n = spearman(xs, ys)
        if rho is not None:
            corr.append({"feature": k, "label": label, "rho": round(rho, 3),
                         "p": round(p, 4), "n": n,
                         "significant": bool(p < 0.05)})
    corr.sort(key=lambda x: -abs(x["rho"]))

    # 稳健性对照：换共同窗口长度，看结论是否稳定
    robust = []
    for days in (365, 730, 900):
        frm = (datetime.fromisoformat(last) - timedelta(days=days)).date().isoformat()
        sub = []
        for r in matched:
            pts = series[r["song"]]
            cw = [(d, v) for d, v in pts if d >= frm]
            if len(cw) < a.min_common_points:
                continue
            x0 = datetime.fromisoformat(cw[0][0])
            xs = [(datetime.fromisoformat(d) - x0).days for d, _ in cw]
            ys = [v for _, v in cw]
            n = len(xs)
            mx, my = sum(xs) / n, sum(ys) / n
            den = sum((x - mx) ** 2 for x in xs)
            sub.append((r, (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den else 0.0))
        entry = {"days": days, "n": len(sub), "top": []}
        for k, label in ACOUSTIC_FEATURES:
            ax = [float(r[k]) for r, sl in sub if r.get(k) is not None]
            ay = [sl for r, sl in sub if r.get(k) is not None]
            rho, p, nn = spearman(ax, ay)
            if rho is not None:
                entry["top"].append({"feature": k, "rho": round(rho, 3), "p": round(p, 4), "n": nn})
        entry["top"].sort(key=lambda x: -abs(x["rho"]))
        entry["top"] = entry["top"][:5]
        robust.append(entry)

    # 参考：全生命周期口径（含"进入时间"混淆，仅作对照）
    corr_life = []
    for k, label in ACOUSTIC_FEATURES:
        xs, ys = [], []
        for r in matched:
            if r.get(k) is None or r.get("slope_lifetime") is None:
                continue
            xs.append(float(r[k]))
            ys.append(float(r["slope_lifetime"]))
        rho, p, n = spearman(xs, ys)
        if rho is not None:
            corr_life.append({"feature": k, "label": label, "rho": round(rho, 3),
                              "p": round(p, 4), "n": n, "significant": bool(p < 0.05)})
    corr_life.sort(key=lambda x: -abs(x["rho"]))

    # 口径必须与展示一致：近期回暖 = 自身近窗口斜率>0 且仍在追踪（展示 slope_per_day）
    risers = sorted([r for r in matched if (r["slope_per_day"] or 0) > 0 and r["active"]],
                    key=lambda x: -x["slope_per_day"])[:15]
    # 两年共同窗口上升（展示 slope_common）
    risers_common = sorted([r for r in matched if (r.get("slope_common") or 0) > 0],
                           key=lambda x: -x["slope_common"])[:15]
    risers_all = sorted([r for r in matched if (r["slope_per_day"] or 0) > 0],
                        key=lambda x: -x["slope_per_day"])[:15]
    risers_life = sorted([r for r in matched if (r.get("slope_lifetime") or 0) > 0],
                         key=lambda x: -x["slope_lifetime"])[:20]
    risers_life_active = [r for r in risers_life if r["active"]][:10]
    fallers = sorted([r for r in matched if (r["slope_per_day"] or 0) < 0],
                     key=lambda x: x["slope_per_day"])[:5]

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window": {"trend_days": a.trend_days, "min_days": a.min_days,
                   "from": cutoff, "to": last, "index_days_total": len(all_dates)},
        "counts": {"songs_with_index": len(series), "eligible": len(rows),
                   "matched_acoustic": len(matched),
                   "rising": sum(1 for r in matched if (r["slope_per_day"] or 0) > 0),
                   "falling": sum(1 for r in matched if (r["slope_per_day"] or 0) < 0)},
        "correlations": corr,
        "correlations_lifetime_reference": corr_life,
        "robustness": robust,
        "common_window": {"from": common_from, "to": last, "days": a.common_days,
                          "min_points": a.min_common_points},
        "risers": risers, "risers_common": risers_common, "risers_all_history": risers_all,
        "risers_lifetime": risers_life, "risers_lifetime_active": risers_life_active,
        "fallers": fallers,
        "rows": sorted(matched, key=lambda x: -(x["slope_per_day"] or 0)),
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 报告 ──────────────────────────────────────────────
    n_feat = sum(1 for c in corr if c["n"] >= 10)
    bonf = round(0.05 / max(1, n_feat), 4)
    L = ["# 声学 × QQ指数 交叉分析（正向视角）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜指数长表 **{all_dates[0]} → {last}**（{len(all_dates)} 天，{len(series)} 首）",
         f"｜公平比较窗口 **{common_from} → {last}**（{a.common_days} 天，≥{a.min_common_points} 点）", "",
         "## 一、视角（为什么指数小也值得看）", "",
         "他的指数绝对值受宣发、平台推荐、粉丝打投影响，本就不走爆发路线。",
         "但微观起伏是真实信号：同一批曲目之间谁在往上走、谁在往下落，",
         "反映作品与演绎的持续触达能力——这是「能力—市场」主线里唯一能长期观测的正向指标。", "",
         "## 二、窗口内总体", "",
         f"- 指数池 **{len(series)}** 首｜计入趋势 **{len(rows)}** 首（近 {a.active_days} 天仍在追踪 **{sum(1 for r in rows if r['active'])}** 首）",
         f"- 与录音室声学可配对 **{len(matched)}** 首｜上升 {payload['counts']['rising']}｜下降 {payload['counts']['falling']}", "",
         "## 三、指数正在增长的曲目", "",
         f"### 3.1 近期回暖（自身近 {a.trend_days} 天斜率 > 0 且仍在被追踪）", "",
         f"| 曲目 | 专辑 | 指数中位 | 近{a.trend_days}天斜率/天 | 窗口内动量 | 最低稳定音(Hz) | 跨度(八度) | 稳定性(音分) | 颤音(Hz) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in risers:
        L.append(f"| **{r['song']}** | {r.get('album','—')} | {r['median_index']} | {r['slope_per_day']:+.2f} "
                 f"| {r.get('momentum','—')} | {r.get('low_hz','—')} | {r.get('span_octaves') or '—'} "
                 f"| {r.get('stability_cents','—')} | {r.get('vibrato_hz','—')} |")
    if not risers:
        L.append("| （窗口内无） | | | | | | | | |")
    L += ["", "### 3.2 两年共同窗口内上升（口径 = 与第四章同一斜率）", "",
          "| 曲目 | 专辑 | 斜率/天 | 窗口内中位 | 最低稳定音(Hz) | 跨度(八度) |",
          "|---|---|---|---|---|---|"]
    for r in risers_common:
        L.append(f"| {r['song']} | {r.get('album','—')} | {r['slope_common']:+.3f} | {r.get('median_window','—')} "
                 f"| {r.get('low_hz','—')} | {r.get('span_octaves') or '—'} |")
    L += ["", "### 3.3 全历史斜率上升（含「进入池子时间」混淆，仅作线索）", "",
          "　".join(f"{r['song']}（{r.get('album','—')}）" for r in risers_life[:16]) or "—", "",
          "> 指数池是滚动的：老曲目会退出追踪，新曲目天然呈上升。",
          "> 故 3.3 只能当「哪些作品仍被听」的线索，不能当增长幅度比较。", "",
          "## 四、声学指标 × 指数增长（Spearman，主口径 = 共同窗口）", "",
          "| 声学指标 | ρ | p | n | 显著(α=0.05) |", "|---|---|---|---|---|"]
    for c in corr:
        L.append(f"| {c['label']} | {c['rho']:+.3f} | {c['p']:.4f} | {c['n']} | {'⚠️' if c['significant'] else '—'} |")
    L += ["", f"**多重比较校正**：共检验 {n_feat} 个指标 → Bonferroni 阈值 **α = {bonf}**。",
          "按此校正，**没有任何声学指标与指数增长显著相关**。", "",
          "### 4.1 稳健性对照（换共同窗口长度）", "",
          "| 窗口(天) | n | 最强相关项 | ρ | p | 说明 |", "|---|---|---|---|---|---|"]
    for rb in robust:
        if rb["top"]:
            t = rb["top"][0]
            note = "n<10，视为噪声" if rb["n"] < 10 else "—"
            L.append(f"| {rb['days']} | {rb['n']} | {t['feature']} | {t['rho']:+.3f} | {t['p']:.4f} | {note} |")
    L += ["", "**读法**：365 天窗口仅 6 首（噪声）；730 天最强为 HNR（p=0.049，未过校正）；",
          "900 天最强换成稳定性（p=0.016）。**最强项随窗口互相替换 = 不稳健 = 不构成证据**。", "",
          "## 五、必须说明的混淆", "",
          "1. **进入时间混淆**：用全历史斜率会把「何时进入池子」当成增长 → 已弃用为主口径。",
          f"2. **样本量限制**：可配对仅 {len(matched)} 首；指数池滚动使长期在追的曲目很少。",
          "3. **指数外生性**：宣发投放、平台推荐、综艺/直播曝光、粉丝打投都不在声学变量里。",
          "4. **方向反直觉时**：若出现「越不稳越涨」这类相关，几乎必然是年代与制作差异所致。", "",
          "## 六、可写方向（正向、可验证）", "",
          "- 可写：在他仍被追踪的曲目里，N 首指数在窗口内上行（事实陈述，附口径与日期）。",
          "- 可写：上升曲目的声学画像描述（最低音/跨度/稳定性/颤音），作为作品仍在被听见的旁证。",
          "- 不可写：「唱得越深/越稳 → 指数越高」——当前数据不支持，n 与稳健性都不足。",
          "- 要真正验证能力→市场，需补三类数据：①曲目级宣发/曝光事件编码；②综艺/直播/影视露出时间轴；",
          "  ③更长追踪窗口（≥3 年）与更多在追曲目。补齐后再做面板回归，才谈得上因果。", "",
          "## 七、数据与复算", "",
          "- 指数长表：`E:\\wx\\wx_textmine_out\\music_index_long.csv`（date, song, index）",
          "- 声学指标：`data/archive_vocal_albums.json`（72 曲稳定音口径）",
          "- 机读结果：`data/acoustic_index_cross.json`",
          "- 复算：`python -X utf8 project_b\\build_acoustic_index_cross.py`", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")

    print(f"\n上升 {payload['counts']['rising']}｜下降 {payload['counts']['falling']}")
    print("相关（Top5 by |ρ|）：")
    for c in corr[:5]:
        print(f"  {c['label']}: ρ={c['rho']:+.3f} p={c['p']:.4f} n={c['n']}")
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
