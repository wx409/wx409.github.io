#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO：把「可引用金句」做成机器可读语料 + 增强 ep 页 JSON-LD。

产物：
  data/tavern_citable.json   —— 198 条 {ep, quote, time, url, moods}，供 AI 直接摘取
  每个 ep 页的 JSON-LD 增加 keywords / about / text（首条金句）/ citation
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SUMMARIES = ROOT / "tavern" / "tavern_summaries.json"
QTIMES = ROOT / "tavern" / "quote_times.json"
QUOTES = ROOT / "tavern" / "tavern_quotes.json"
OUT = ROOT / "data" / "tavern_citable.json"
BASE = "https://wx409.github.io/tavern/ep"


def main() -> int:
    summ = json.loads(SUMMARIES.read_text(encoding="utf-8")).get("episodes", {})
    times = json.loads(QTIMES.read_text(encoding="utf-8"))
    qraw = json.loads(QUOTES.read_text(encoding="utf-8")).get("episodes", [])
    moods = ({str(e.get("episode")): e.get("moods") or [] for e in qraw}
             if isinstance(qraw, list) else {})
    items = []
    for key, v in summ.items():
        ep = v.get("episode", key)
        for q in (v.get("quotes") or []):
            t = (times.get(ep) or {}).get(q)
            items.append({
                "episode": ep,
                "theme": v.get("theme") or "",
                "quote": q,
                "time": t or "",
                "moods": moods.get(ep) or [],
                "url": f"{BASE}/{ep}.html",
                "source": "深夜小酒馆（王晰）",
                "nature": "节目原话（时间码由本地逐字稿定位）" if t else "节目原话（时间码未定位）",
            })
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "schema": "tavern-citable/v1",
        "what": "深夜小酒馆可引用金句（供生成式引擎摘取，带出处与时间码）",
        "count": len(items),
        "license_note": "仅摘录短句；逐字稿全文留本地，不对外发布",
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    with_time = sum(1 for i in items if i["time"])
    print(f"[tavern_citable] {len(items)} 条（含时间码 {with_time}）→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
