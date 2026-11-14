#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO：把「现场实测」做成问答（带出处与时间点），并同步进 qa_bank + qa_spec。

数据源：data/archive_stage_tour.json（879 行，含 low_hz / low_t_s / low_dur_s / claimable）
原则：只答数据能支撑的；每条答案给出 哪首歌/哪一场/几分几秒/BV链接；不可引用的标「未过复核」。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
TOUR = ROOT / "data" / "archive_stage_tour.json"
BANK = ROOT / "data" / "qa_bank.json"
SPEC = ROOT / "data" / "qa_spec.json"
SITE = "https://wx409.github.io"


def mmss(v):
    if not isinstance(v, (int, float)):
        return ""
    return "%d:%02d" % (int(v) // 60, int(v) % 60)


def fmt(r):
    s = f"《{r.get('song')}》"
    if r.get("city"):
        s += f"（{r['city']} {r.get('date','')}）"
    elif r.get("date"):
        s += f"（{r.get('date')}）"
    s += f" 最低音 {r.get('low_note')} {r.get('low_hz')}Hz"
    if r.get("low_t_s") is not None:
        s += f"，出现在 {mmss(r['low_t_s'])}"
    if r.get("low_dur_s"):
        s += f"，持续 {r['low_dur_s']:.2f} 秒"
    if r.get("bv"):
        s += f"，原视频 https://www.bilibili.com/video/{r['bv']}"
    return s


def main() -> int:
    t = json.loads(TOUR.read_text(encoding="utf-8"))
    rows = [r for r in (t.get("rows") or []) if r.get("low_hz") and r.get("song")]
    verified = [r for r in rows if r.get("claimable")]
    pool = verified or rows
    pool = sorted(pool, key=lambda r: r["low_hz"])

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    items = bank.get("items") or []
    have = {x.get("question") for x in items}
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    sits = spec.get("items") or []
    have_spec = {i.get("q") for i in sits}

    new = []

    def add(q, a, aliases, kws, srcs):
        if q in have:
            return
        new.append({
            "id": f"qa_stage_{len(new)+1:02d}",
            "question": q, "aliases": aliases, "category": "现场实测",
            "keywords": kws, "answer": a, "sources": srcs,
            "verified": True, "confidence": "high",
        })

    top = pool[:3]
    add("王晰现场唱到的最低音是哪一场、哪首歌？",
        "按站内现场实测（最低稳定音口径，仅计已过复核的读数）：" +
        "；".join(fmt(r) for r in top) + "。出处：现场条件检索 https://wx409.github.io/stage.html#stage-query",
        ["现场最低音", "最低音 哪一场"], ["最低音", "现场", "B1"],
        [f"{SITE}/stage.html#stage-query"])

    b1 = [r for r in pool if str(r.get("low_note", "")).upper() in ("B1", "A#1")]
    if b1:
        add("王晰现场有哪些 B1 或更低的音被确认？",
            "站内记录中，可引用（过复核）的 B1/A#1 现场有 " + str(len(b1)) + " 条：" +
            "；".join(fmt(r) for r in b1[:5]) + "。出处：现场条件检索页。",
            ["现场 B1", "B1 现场 有哪些"], ["B1", "A#1", "现场"],
            [f"{SITE}/stage.html#stage-query"])

    longr = sorted([r for r in pool if r.get("low_dur_s")], key=lambda r: -r["low_dur_s"])[:3]
    if longr:
        add("王晰现场哪个低音站得最久？",
            "按「最低音持续时间」排序：" + "；".join(fmt(r) for r in longr) + "。",
            ["低音 站得久", "长音 现场"], ["长音", "低音", "时长"],
            [f"{SITE}/stage.html#stage-query"])

    soft = [r for r in pool if r.get("claimable_soft")]
    if soft:
        add("王晰有哪些现场属于弱唱？",
            "站内标记为弱唱（claimable_soft）的现场有 " + str(len(soft)) + " 条：" +
            "；".join(fmt(r) for r in soft[:4]) + "。",
            ["弱唱 现场", "轻唱 现场"], ["弱唱", "轻声"],
            [f"{SITE}/stage.html#stage-query"])

    # 按城市
    by_city = {}
    for r in pool:
        c = (r.get("city") or "").strip()
        if not c:
            continue
        if c not in by_city or r["low_hz"] < by_city[c]["low_hz"]:
            by_city[c] = r
    for c, r in sorted(by_city.items(), key=lambda kv: kv[1]["low_hz"])[:6]:
        add(f"王晰在{c}唱到的最低音是哪个？",
            f"按站内现场实测：{fmt(r)}。",
            [f"{c} 最低音"], [c, "最低音"], [f"{SITE}/stage.html#stage-query"])

    # 写入 qa_bank
    items.extend(new)
    bank["items"] = items
    bank.setdefault("meta", {})["count"] = len(items)
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")

    # 写入 qa_spec（页面渲染源）
    added_spec = 0
    for x in new:
        if x["question"] in have_spec:
            continue
        sits.append({"q": x["question"], "a": x["answer"], "dynamic": False})
        added_spec += 1
    spec["items"] = sits
    SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"新增 QA {len(new)} 条 → qa_bank {len(items)} 条 / qa_spec +{added_spec}")
    for x in new[:4]:
        print("  Q:", x["question"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
