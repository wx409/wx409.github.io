#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO P1：把小酒馆金句（带时间码）扩成问答条目，写进 data/qa_bank.json。

规则（可核对）：
  · 只按「情绪标签」聚合，且要求该情绪下 ≥2 条带时间码的金句；
  · 答案 = 原话摘引 + 期次 + 时间码；不写任何推断；
  · sources 指向具体 ep 页；verified=True 仅当引用全部带时间码。
用法：python project_b/build_qa_from_tavern.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
CITABLE = ROOT / "data" / "tavern_citable.json"
BANK = ROOT / "data" / "qa_bank.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cit = json.loads(CITABLE.read_text(encoding="utf-8")).get("items") or []
    by_mood = defaultdict(list)
    for it in cit:
        if not it.get("time"):
            continue
        for m in (it.get("moods") or []):
            by_mood[m].append(it)

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    items = bank.get("items") or []
    have_ids = {x.get("id") for x in items}
    existing_q = {x.get("question") for x in items}

    new = []
    n = 1
    for mood, arr in sorted(by_mood.items(), key=lambda kv: -len(kv[1])):
        if len(arr) < 2:
            continue
        arr = arr[:3]
        q = f"王晰在《深夜小酒馆》里怎么谈「{mood}」？"
        if q in existing_q:
            continue
        parts = []
        srcs = []
        for it in arr:
            parts.append(f"“{it['quote']}”（{it['episode']} · {it['time']}）")
            srcs.append(it["url"])
        answer = ("他在节目里至少提过 %d 次，原话包括：%s。"
                  "以上均为节目原话摘引，时间码由逐字稿定位；完整上下文见对应期次页面。"
                  % (len(arr), "；".join(parts)))
        new.append({
            "id": f"qa_tavern_{n:02d}",
            "question": q,
            "aliases": [f"{mood} 王晰", f"王晰 {mood}", f"{mood} 小酒馆"],
            "category": "小酒馆金句",
            "keywords": [mood, "深夜小酒馆", "金句"],
            "answer": answer,
            "sources": srcs,
            "verified": all(it.get("time") for it in arr),
            "confidence": "high" if all(it.get("time") for it in arr) else "medium",
        })
        n += 1

    # 关键词聚合：关键词出现在金句文本中，且 ≥2 条带时间码
    kw_pool = defaultdict(list)
    for it in cit:
        if not it.get("time"):
            continue
        for kw in (it.get("moods") or []):
            kw_pool[kw].append(it)
    try:
        _sum = json.loads((ROOT / "tavern" / "tavern_summaries.json").read_text(encoding="utf-8")).get("episodes", {})
    except Exception:
        _sum = {}
    for _k, _v in _sum.items():
        for kw in (_v.get("keywords") or []):
            if len(str(kw)) < 2:
                continue
            for it in cit:
                if it.get("time") and kw and kw in (it.get("quote") or ""):
                    kw_pool[kw].append(it)

    for kw, arr in sorted(kw_pool.items(), key=lambda kv: -len(set(i["quote"] for i in kv[1]))):
        uniq = []
        seen = set()
        for it in arr:
            if it["quote"] in seen:
                continue
            seen.add(it["quote"]); uniq.append(it)
        if len(uniq) < 2 or len(kw) < 2:
            continue
        q = f"王晰在《深夜小酒馆》里说过哪些关于「{kw}」的话？"
        if q in existing_q:
            continue
        uniq = uniq[:3]
        parts = [f"“{i['quote']}”（{i['episode']} · {i['time']}）" for i in uniq]
        new.append({
            "id": f"qa_tavern_{n:02d}",
            "question": q,
            "aliases": [f"王晰 {kw}", f"{kw} 王晰说过"],
            "category": "小酒馆金句",
            "keywords": [kw, "深夜小酒馆", "金句"],
            "answer": ("与「%s」相关的原话有 %d 条：%s。以上为节目原话摘引，时间码由逐字稿定位。"
                       % (kw, len(parts), "；".join(parts))),
            "sources": [i["url"] for i in uniq],
            "verified": True,
            "confidence": "high",
        })
        n += 1
        existing_q.add(q)

    print(f"待新增 {len(new)} 条（情绪/关键词组）")
    for x in new[:5]:
        print("  Q:", x["question"], "| 引用", len(x["sources"]), "条")
    if a.dry_run:
        return 0

    items.extend(new)
    bank["items"] = items
    bank.setdefault("meta", {})["count"] = len(items)
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写入 qa_bank.json：{len(items)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
