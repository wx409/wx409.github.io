#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句子回读校验：每条句子里的数字必须能在它引用的事实里找到；
边界必须存在；事实 id 必须存在。

这是「自动生成」能成立的前提：机器造句子，机器也能验句子。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"


def main() -> None:
    facts = {f["id"]: f for f in json.loads((D / "fact_atoms.json").read_text(encoding="utf-8"))["facts"]}
    quotes = json.loads((D / "quotes_generated.json").read_text(encoding="utf-8"))["quotes"]
    bad = []
    for q in quotes:
        for fid in q["fact_ids"]:
            if fid not in facts:
                bad.append(f"未知事实 {fid}")
        nums = re.findall(r"\d+(?:\.\d+)?", q["text"])
        pool = " ".join(str(facts[i][k]) for i in q["fact_ids"] if i in facts
                        for k in ("value", "scope", "boundary"))
        for n in nums:
            if n not in pool:
                bad.append(f"数字 {n} 不在事实池里：{q['text'][:40]}")
        if not q["boundary"].strip():
            bad.append(f"缺边界：{q['text'][:40]}")
    print(f"句子 {len(quotes)} 条｜事实 {len(facts)} 条｜问题 {len(bad)}")
    for b in bad[:10]:
        print("  ·", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
