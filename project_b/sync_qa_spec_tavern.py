#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 qa_bank 里「小酒馆金句」类条目同步进 data/qa_spec.json（qa.html 的渲染源）。"""
import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
BANK = ROOT / "data" / "qa_bank.json"
SPEC = ROOT / "data" / "qa_spec.json"

bank = json.loads(BANK.read_text(encoding="utf-8"))
spec = json.loads(SPEC.read_text(encoding="utf-8"))
items = spec.get("items") or []
have = {i.get("q") for i in items}

added = 0
for x in (bank.get("items") or []):
    if x.get("category") != "小酒馆金句":
        continue
    q = x.get("question")
    if not q or q in have:
        continue
    items.append({"q": q, "a": x.get("answer", ""), "dynamic": False})
    have.add(q)
    added += 1

spec["items"] = items
spec["note"] = (spec.get("note") or "") + f"｜小酒馆金句问答 {added} 条（来源：data/tavern_citable.json，带时间码）"
SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"qa_spec 新增 {added} 条，总计 {len(items)} 条")
