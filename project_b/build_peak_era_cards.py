# -*- coding: utf-8 -*-
"""高光期效果卡：雾里 / 黎明前的黑暗 / 神魂颠倒 —— 用四源还原"很有效果"。

为什么单独做：用户明确指出这三首"有效果"，但它们的指数记录都很短（30 天量级），
且指数与高光期错开 → 单看指数会误判。本卡把**舞台素材 / 文本 / 声音 / 指数**并列，
并给出指数逐月分布，让"效果"有据可依。
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import load as load_idx  # noqa: E402

OUT = Path(r"E:\wx\论文素材_王晰作传\高光期效果卡.md")
TARGETS = ["雾里", "黎明前的黑暗", "神魂颠倒", "一生中最爱", "贝加尔湖畔"]


def main() -> int:
    master = json.loads((SITE / "data" / "song_evidence_master.json").read_text(encoding="utf-8"))
    rows = {r["song"]: r for r in master["rows"]}
    df = load_idx()
    g = df.dropna(subset=["current_index"])
    g = g[g["current_index"] > 0]

    L = ["# 高光期效果卡（四源并列）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}", "",
         "> 用途：对「用户直觉认为很有效果」的曲目，用**舞台素材 / 文本 / 声音 / 指数**四源并列核验；",
         "> 指数只占一列——因为他的指数数据与高光期错开。", ""]
    for t in TARGETS:
        # 模糊匹配（源里曲名可能带合作者/演出后缀）
        cands = [k for k in rows if k.startswith(t)]
        if not cands:
            L += [f"## {t}", "", "（总表中无记录）", ""]
            continue
        key = max(cands, key=lambda k: rows[k]["sources_with_data"])
        r = rows[key]
        subs = g[g["canon"].astype(str).str.startswith(t)]
        monthly = defaultdict(list)
        for d, v in zip(subs["day"], subs["current_index"]):
            monthly[d[:7]].append(float(v))
        L += [f"## {t}", "", f"- 总表键：`{key}`（源内写法可能含合作者）",
              f"- 声学：最低音 {r.get('low_note') or '—'}｜低音占比 {r.get('bass_share') if r.get('bass_share') is not None else '—'}",
              f"- 演出场次 **{r['show_count']}**｜舞台素材 **{r['stage_materials']}**｜文本提及 **{r['text_mentions']}**｜声音素材 **{r['voice_mentions']}**",
              f"- 指数：记录 **{r['idx_days']}** 天｜中位 {r['idx_median']}｜峰值 {r['idx_peak']}｜首日 {r['idx_first']}",
              f"- **有据来源数：{r['sources_with_data']} / 6**", ""]
        if monthly:
            L += ["| 月份 | 天数 | 中位指数 | 峰值 |", "|---|---|---|---|"]
            for m in sorted(monthly)[:14]:
                vs = monthly[m]
                L.append(f"| {m} | {len(vs)} | {round(statistics.median(vs),1)} | {max(vs):.0f} |")
        else:
            L.append("（指数源内无 >0 记录）")
        L.append("")
    L += ["## 口径", "",
          "- 声学仅录音室曲目；舞台素材来自现场层；文本/声音为整名出现计数（通用词只算书名号内）",
          "- 指数为权威全量源 `current_index > 0`（0 值=占位行已剔除）；短记录不等于「没效果」，只等于「未被平台长期跟踪」", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"→ {OUT}")
    for t in TARGETS:
        cands = [k for k in rows if k.startswith(t)]
        if cands:
            r = rows[max(cands, key=lambda k: rows[k]["sources_with_data"])]
            print(f"  {t:<10} 演出 {r['show_count']:>2}｜舞台 {r['stage_materials']:>2}｜文本 {r['text_mentions']:>3}"
                  f"｜声音 {r['voice_mentions']:>3}｜指数 {r['idx_days']:>4} 天｜源数 {r['sources_with_data']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
