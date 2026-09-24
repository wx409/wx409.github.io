# -*- coding: utf-8 -*-
"""从文本挖掘的 3447 条事件里，筛出**可人工策展的生涯节点候选**（不直接上站）。

为什么这么做（第一性原理）
--------------------------
站内口径 `textmine_events` 明确写着「**不得直接当站内事实引用**」——因为 LLM 抽取有噪声：
空泛条目（"1990 经典歌曲"）、同日重复（2007 / 2007-01-01）、事实存疑（出生地）等。
所以正确用法是**把机器抽取当作"候选"，交给人工策展**，而不是灌进站内时间轴（现有 41 条精选节点）。

做法：高置信（≥0.9）→ 去掉与精选时间轴重复的 → 按"标题归一"去重 → 按年归类 → 输出**本地**清单。

产出（本地，不进公开仓库）：
  · E:\\wx\\论文素材_王晰作传\\生涯节点候选_来自文本挖掘.md
  · temp/timeline_candidates.json

用法：python -X utf8 project_b\\build_timeline_candidates.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
TM = Path(r"E:\wx\wx_textmine_out")
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\生涯节点候选_来自文本挖掘.md")
OUT_JSON = SITE / "temp" / "timeline_candidates.json"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def norm(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", str(s or "")).lower()


def main() -> int:
    mt = load(TM / "master_timeline.json") or []
    mt = mt if isinstance(mt, list) else (mt.get("events") or [])
    curated = load(SITE / "data/timeline.json") or []
    curated = curated if isinstance(curated, list) else (curated.get("items") or [])
    cur_dates = {str(c.get("date") or "")[:10] for c in curated}
    cur_norm = {norm(c.get("title")) for c in curated}

    seen, cand = set(), []
    for e in mt:
        if (e.get("confidence") or 0) < 0.9:
            continue
        title = str(e.get("title") or "").strip()
        if len(title) < 4 or title in ("经典歌曲", "其他"):
            continue
        d = str(e.get("date") or "")[:10]
        key = norm(title)[:24]
        if key in seen or key in cur_norm:
            continue
        if d in cur_dates and key in cur_norm:
            continue
        seen.add(key)
        cand.append({"date": d, "type": e.get("type"), "title": title,
                     "entities": e.get("entities") or [], "confidence": e.get("confidence"),
                     "evidence": str(e.get("evidence") or "")[:120],
                     "n_sources": len(e.get("sources") or [])})

    by_year = defaultdict(list)
    for c in cand:
        by_year[c["date"][:4] or "无日期"].append(c)
    for y in by_year:
        by_year[y].sort(key=lambda x: x["date"])

    OUT_JSON.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"),
                                    "total_mined": len(mt), "curated": len(curated),
                                    "candidates": len(cand), "by_year": {k: len(v) for k, v in sorted(by_year.items())},
                                    "items": cand}, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [f"# 生涯节点候选（来自文本挖掘，{datetime.now():%Y-%m-%d}）", "",
          f"- 机器抽取事件 **{len(mt)}** 条 → 高置信（≥0.9）且去重、排除已入选后剩余 **{len(cand)}** 条候选",
          f"- 站内精选时间轴现有 **{len(curated)}** 条（`data/timeline.json`）",
          "",
          "> ⚠️ 这些是**候选**，不是事实。口径规定 `textmine_events` **不得直接当站内事实引用**。",
          "> 人工核对后再决定是否写入 `data/timeline.json`；无独立来源的一律标「待核」。", ""]
    for y in sorted(by_year):
        md += [f"## {y}（{len(by_year[y])} 条）", ""]
        for c in by_year[y][:40]:
            md.append(f"- `{c['date']}` **{c['title']}**｜{c['type']}｜置信 {c['confidence']}"
                      + (f"｜实体 {'/'.join(map(str, c['entities'][:3]))}" if c["entities"] else ""))
        if len(by_year[y]) > 40:
            md.append(f"- …另有 {len(by_year[y]) - 40} 条（见 JSON）")
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"挖掘事件 {len(mt)} 条｜精选 {len(curated)} 条 → 候选 {len(cand)} 条")
    print("按年:", dict(sorted(by_year.items(), key=lambda x: x[0]))if False else
          {k: len(v) for k, v in sorted(by_year.items())})
    print(f"→ {OUT_MD}\n→ {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
