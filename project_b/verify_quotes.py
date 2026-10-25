#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""底句回读校验：数字有出处 + 主张绑定有效 + 不做多事实组合 + 快照必填。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"


def main() -> None:
    facts = {f["id"]: f for f in json.loads((D / "fact_atoms.json").read_text(encoding="utf-8"))["facts"]}
    claims = {c["id"]: c for c in json.loads((D / "claims.json").read_text(encoding="utf-8"))["claims"]}
    quotes = json.loads((D / "quotes_generated.json").read_text(encoding="utf-8"))["quotes"]
    bad = []
    for q in quotes:
        cid = q.get("claim_id")
        c = claims.get(cid) if cid else None
        if not c:
            bad.append(f"未绑定主张：{q['text'][:30]}")
            continue
        if c.get("status") != "可用":
            bad.append(f"主张非可用却进入发布句：{cid}")
        if not q.get("snapshot_id"):
            bad.append(f"缺快照：{q['text'][:30]}")
        if len(q["fact_ids"]) != 1:
            bad.append(f"出现多事实组合：{q['text'][:30]}")
        for fid in q["fact_ids"]:
            f = facts.get(fid)
            if not f:
                bad.append(f"未知事实 {fid}")
                continue
            if f.get("claim_id") != cid:
                bad.append(f"事实 {fid} 绑定的主张与句子不一致")
        pool = " ".join(str(facts[i][k]) for i in q["fact_ids"] if i in facts
                        for k in ("value", "scope", "boundary"))
        for n in re.findall(r"\d+(?:\.\d+)?", q["text"]):
            if n not in pool:
                bad.append(f"数字 {n} 不在事实池：{q['text'][:30]}")
        if not q.get("boundary", "").strip():
            bad.append(f"缺边界：{q['text'][:30]}")
    print(f"底句 {len(quotes)}｜问题 {len(bad)}")
    for b in bad[:10]:
        print("  ·", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
