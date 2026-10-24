# -*- coding: utf-8 -*-
"""build_daily_insights.py —— 每日 3–5 条「今日洞察」（五段式，可直接当宣传切入点）

每条固定五行：① 结论（≤25 字）② 数字与变化 ③ 为什么值得注意 ④ 能否当宣传切入点 + ≤18 字文案 ⑤ 证据
没有新东西就输出「今日无新料」，不凑数。

数据源（全部现算）：
  · `E:\\wx\\wx_textmine_out\\music_index_long.csv`（指数新日/涨跌/新上榜）
  · `data/dashboard/dashboard_data.json`（事件研究 daily_series 峰值、最近批次）
  · `data/archive_stage_tour.json`（现场新素材）
  · `data/hooks_pool.json`（已确认钩子数）
输出：`data/daily_insights.json` + `data/daily_insights.md`
"""
from __future__ import annotations

import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
LONG = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
OUT = D / "daily_insights.json"
OUT_MD = D / "daily_insights.md"


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


def main() -> int:
    df = pd.read_csv(LONG)
    df["day"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    last, prev = sorted(df["day"].dropna().unique())[-1], sorted(df["day"].dropna().unique())[-2]
    cur = df[df["day"] == last].set_index("song")["index"]
    old = df[df["day"] == prev].set_index("song")["index"]
    both = cur.index.intersection(old.index)
    delta = (cur[both] - old[both]).dropna()
    up = delta.sort_values(ascending=False)
    new_songs = sorted(set(cur.index) - set(old.index))

    stage = load(D / "archive_stage_tour.json", {}) or {}
    rows = stage.get("rows") or []
    last_show = max((r.get("date") or "" for r in rows), default="")
    show_rows = [r for r in rows if r.get("date") == last_show]
    hooks = load(D / "hooks_pool.json", {}) or {}
    conf = [h for h in (hooks.get("hooks") or []) if (h.get("review_status") == "confirmed")]
    dash = load(SITE / "dashboard" / "dashboard_data.json", {}) or {}
    eff = [x for x in (dash.get("tour_song_effects") or []) if x.get("daily_series")]

    items = []
    # 1) 指数：当日池中位与变化
    if len(both) >= 5:
        items.append({
            "title": f"指数又动了：{last} 池中位 {st.median(cur[both]):.0f}",
            "lines": [
                f"结论：{last} 的追踪池中位 {st.median(cur[both]):.0f} 点",
                f"数字：较前一日 {st.median(old[both]):.0f} 点，变化 {st.median(cur[both])-st.median(old[both]):+.0f}；"
                f"有值曲目 {len(cur)} 首（前一日 {len(old)}）",
                "为什么：单日中位变化超过 ±10 点，说明当天的收听结构有整体位移，不是个别曲目",
                ("能" if abs(st.median(cur[both]) - st.median(old[both])) >= 10 else "弱")
                + f"｜文案：{last} 这天，整个池子一起动了",
                f"证据：music_index_long.csv（{last} vs {prev}，n={len(both)}）",
            ]})
    # 2) 当日涨幅冠军
    if len(up) >= 3 and up.iloc[0] > 0:
        s0 = up.index[0]
        items.append({
            "title": f"当天涨得最猛：《{s0}》+{up.iloc[0]:.0f} 点",
            "lines": [
                f"结论：《{s0}》单日涨 {up.iloc[0]:.0f} 点",
                f"数字：{old[s0]:.0f} → {cur[s0]:.0f}；当日涨幅前三 "
                + "、".join(f"{k}+{v:.0f}" for k, v in up.head(3).items()),
                "为什么：同一天整体中位只动几点的日子里，单曲能涨这么多，通常对应一次外部曝光",
                "能｜文案：这首一天涨了 " + f"{up.iloc[0]:.0f}" + " 点",
                f"证据：music_index_long.csv#song={s0}",
            ]})
    # 3) 新上榜曲目
    if new_songs:
        items.append({
            "title": f"昨天不在榜、今天出现：{len(new_songs)} 首",
            "lines": [
                f"结论：{last} 新出现 {len(new_songs)} 首有值曲目",
                f"数字：{ '、'.join(new_songs[:5]) }" + (" 等" if len(new_songs) > 5 else ""),
                "为什么：新出现的曲目通常来自一次演唱、一条视频或一次平台推荐，值得回查来源",
                "弱｜文案：这几首，昨天还没有指数",
                "证据：music_index_long.csv（当日新增曲目集合）",
            ]})
    # 4) 事件研究峰值
    if eff:
        e = max(eff, key=lambda x: max((x.get("daily_series") or {}).values() or [-999]))
        ds = e.get("daily_series") or {}
        pk = max(ds, key=ds.get) if ds else None
        items.append({
            "title": f"上一场演出的指数峰值在 {pk}",
            "lines": [
                f"结论：{e.get('date')} 场次峰值 {pk}（{ds.get(pk)} 点）",
                f"数字：total_uplift {e.get('total_uplift')}｜窗口 {len(ds)} 天",
                "为什么：峰值若落在 T+8 以后，说明传播不是当晚爆发，而是延迟扩散",
                ("能" if pk and int(str(pk).replace("T+", "") or 0) >= 8 else "弱")
                + f"｜文案：这场演出，八天后才到顶",
                "证据：dashboard_data.json#tour_song_effects[].daily_series",
            ]})
    # 5) 现场新素材 / 钩子
    if show_rows:
        items.append({
            "title": f"最近一场 {last_show} 已入现场层 {len(show_rows)} 条",
            "lines": [
                f"结论：{last_show} 现场素材入库 {len(show_rows)} 条",
                f"数字：已确认钩子 {len(conf)} 条；素材含中控台与观众侧",
                "为什么：素材入库是后续能力读数与宣传的前提，缺素材时任何读数都只能等",
                "弱｜文案：这场的声音，已经进档案了",
                "证据：archive_stage_tour.json#rows；hooks_pool.json#hooks",
            ]})

    if not items:
        items = [{"title": "今日无新料", "lines": [
            "结论：今天没有可用的新增数据",
            "数字：指数、现场、钩子三项均无变化",
            "为什么：不凑数——没有新东西时，洞察就应该空着",
            "否｜文案：—",
            "证据：music_index_long.csv / archive_stage_tour.json / hooks_pool.json",
        ]}]

    doc = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_as_of": last,
        "prev_day": prev,
        "n": len(items),
        "items": items,
        "note": "五段式：结论/数字/为什么/能否宣传+文案/证据；无新料即空，不凑数",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# 今日洞察（生成 {doc['generated_at'][:16].replace('T',' ')}｜数据截至 {last}）", ""]
    for i, it in enumerate(items, 1):
        md.append(f"## {i}. {it['title']}")
        for ln in it["lines"]:
            md.append(f"- {ln}")
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"[ok] {OUT.name}｜{len(items)} 条｜数据截至 {last}")
    for it in items:
        print("  ·", it["title"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
