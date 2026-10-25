#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据底句生成器（内部工具，不是宣传文案机器）。

纪律（按评审确定，不再扩展）：
  1. 只做「单事实 → 单主张」装配；不做多事实自由组合。
  2. 每条句子必须携带 claim_id / claim_version / snapshot_id / status。
  3. 事实若无绑定主张，或主张非「可用」，不生成可发布句。
  4. 不生成比喻、不生成口语变体（比喻会引入数字回读发现不了的语义错误）。
  5. 三个固定反例见 docs/证据底句生成器_边界.md。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT = D / "quotes_generated.json"


def claim_version(c: dict) -> str:
    key = json.dumps([c.get("can_write"), c.get("scope")], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def main() -> None:
    facts = json.loads((D / "fact_atoms.json").read_text(encoding="utf-8"))["facts"]
    claims = {c["id"]: c for c in json.loads((D / "claims.json").read_text(encoding="utf-8"))["claims"]}

    quotes, skipped = [], []
    for f in facts:
        cid = f.get("claim_id")
        c = claims.get(cid) if cid else None
        if not c or c.get("status") != "可用":
            skipped.append((f["id"], "无主张或不可用"))
            continue
        if f["kind"] == "song_versions":
            text = f'{f["subject"]}：{f["value"]}。'
        else:
            text = f'{f["subject"]}：{f["metric"]}为 {f["value"]}{f["unit"]}（{f["scope"]}）。'
        quotes.append({
            "text": text,
            "fact_ids": [f["id"]],
            "claim_id": cid,
            "claim_version": claim_version(c),
            "snapshot_id": f.get("snapshot") or "",
            "status": c.get("status"),
            "boundary": f["boundary"],
            "sources": [f["source"]],
        })

    out = {"schema": "quotes_generated/v2", "count": len(quotes),
           "skipped": len(skipped), "quotes": quotes}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"底句 {len(quotes)} 条（跳过 {len(skipped)} 条：{', '.join(s[0] for s in skipped[:6])}…）")
    for q in quotes[:5]:
        print(f'  [{q["claim_id"]}@{q["claim_version"]}] {q["text"]}')


if __name__ == "__main__":
    main()
