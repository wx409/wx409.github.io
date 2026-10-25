#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""现场条目三态映射：可形成结论 / 只能描述素材 / 待核 / 排除。

三态只回答"这个条目为什么在页面上"，不另造证据等级（M/S 与主张体系继续沿用）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage_tour.json"
EXC = ROOT / "data" / "live_exclusions.json"
OUT = ROOT / "data" / "stage_states.json"


def main() -> None:
    rows = json.loads(SRC.read_text(encoding="utf-8"))["rows"]
    ex = json.loads(EXC.read_text(encoding="utf-8")).get("items", [])
    items, counts = [], {"claimable": 0, "descriptive": 0, "pending": 0, "excluded": 0}
    for r in rows:
        tag = str(r.get("tag") or "")
        verify = str(r.get("verify") or "")
        review = str(r.get("review_status") or "")
        hit = next((e for e in ex if e.get("match") and e["match"] in tag), None)
        if hit or "否决" in verify:
            state, reason = "excluded", (hit or {}).get("reason") or "人耳否决"
        elif any(k in review for k in ("待判", "待复核", "未复核")) or "待" in verify:
            state, reason = "pending", "归属或复核未完成"
        elif r.get("claimable"):
            state, reason = "claimable", "过复核门槛且可引用"
        else:
            state, reason = "descriptive", "有录音与读数，但未达可引用门槛"
        counts[state] += 1
        items.append({
            "entry_id": f"stage:{r.get('tag')}",
            "song": r.get("song") or "",
            "date": r.get("date") or "",
            "city": r.get("city") or "",
            "state": state,
            "reason": reason,
            "in_stats": state == "claimable",
            "in_publish": state == "claimable",
        })
    OUT.write_text(json.dumps({"schema": "stage_states/v1", "counts": counts, "items": items},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("三态计数:", counts, "| 总计", sum(counts.values()))


if __name__ == "__main__":
    main()
