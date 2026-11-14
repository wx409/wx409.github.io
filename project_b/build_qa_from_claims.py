#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO：把 22 条「可引用结论」转成问答（带出处与口径注意），写入 qa_bank + qa_spec。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
CLAIMS = ROOT / "data" / "citable_claims.json"
BANK = ROOT / "data" / "qa_bank.json"
SPEC = ROOT / "data" / "qa_spec.json"
SITE = "https://wx409.github.io"


def main() -> int:
    claims = json.loads(CLAIMS.read_text(encoding="utf-8")).get("claims") or []
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    items = bank.get("items") or []
    have = {x.get("question") for x in items}
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    sits = spec.get("items") or []
    have_spec = {i.get("q") for i in sits}

    new = []
    for c in claims:
        song = c.get("song") or ""
        sent = (c.get("sentence") or "").strip()
        if not song or not sent:
            continue
        q = f"《{song}》的最低稳定音是多少？"
        if c.get("metric", "").find("最高") >= 0:
            q = f"《{song}》的最高稳定音是多少？"
        if q in have:
            continue
        ans = sent
        cav = (c.get("caveat") or "").strip()
        if cav:
            ans += f"\n\n口径提示：{cav}"
        ans += f"\n\n出处：{c.get('source') or '站内声学数据'}；汇总页 {SITE}/vocal.html"
        new.append({
            "id": f"qa_claim_{len(new)+1:02d}",
            "question": q,
            "aliases": [f"{song} 最低音", f"{song} 音域"],
            "category": "声学实测",
            "keywords": [song, "最低稳定音", "音域"],
            "answer": ans,
            "sources": [c.get("source") or f"{SITE}/vocal.html"],
            "verified": True,
            "confidence": "high",
        })

    items.extend(new)
    bank["items"] = items
    bank.setdefault("meta", {})["count"] = len(items)
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")

    added = 0
    for x in new:
        if x["question"] in have_spec:
            continue
        sits.append({"q": x["question"], "a": x["answer"], "dynamic": False})
        added += 1
    spec["items"] = sits
    SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"新增 QA {len(new)} 条 → qa_bank {len(items)} / qa_spec +{added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
