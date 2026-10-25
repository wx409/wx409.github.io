#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成统一派生结果：逐碟颤音速率中位数之极差。

为什么要一个派生结果文件：
  页面各自现算，就会出现同一指标多个值（0.27 / 0.39）且互不知情。
  这里把「指标 / 快照 / 纳入作品 / 逐碟中位 / 统计定义 / 结果」一次写死，
  页面只读这一份。

快照纪律：
  - 派生结果必须绑定 snapshots.json 里的 snapshot_id；
  - 同时记录输入指纹（参与计算的歌曲颤音值的 sha256），
    数据变了但快照没更新时，audit_snapshot.py 会报警。
"""
from __future__ import annotations

import hashlib
import json
import statistics as st
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS = ROOT / "data" / "archive_vocal_albums.json"
SNAPS = ROOT / "data" / "snapshots.json"
OUT = ROOT / "data" / "derived" / "vibrato_spread.json"

CURRENT_SNAPSHOT = "snap-2026-10-25-mixed"
PREV_SNAPSHOT = "snap-2026-09-21"


def main() -> None:
    albums = json.loads(ALBUMS.read_text(encoding="utf-8"))
    snaps = {s["snapshot_id"]: s for s in json.loads(SNAPS.read_text(encoding="utf-8"))["snapshots"]}

    by: dict[str, list[float]] = {}
    for s in albums.get("songs", []):
        v = s.get("vibrato_hz")
        if v and s.get("album"):
            by.setdefault(s["album"], []).append(float(v))

    med = {a: round(st.median(v), 2) for a, v in by.items()}
    spread = round(max(med.values()) - min(med.values()), 2)

    payload = json.dumps({a: sorted(by[a]) for a in sorted(by)}, sort_keys=True)
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()[:16]

    out = {
        "schema": "derived/vibrato_spread-v1",
        "metric": "七张专辑与一张数字 EP逐碟颤音速率中位数之极差",
        "definition": "max(逐碟中位) − min(逐碟中位)；颤音速率单位 Hz",
        "snapshot_id": CURRENT_SNAPSHOT,
        "snapshot_date": snaps[CURRENT_SNAPSHOT]["snapshot_date"],
        "status": snaps[CURRENT_SNAPSHOT]["status"],
        "included_albums": sorted(med),
        "album_medians": med,
        "value_hz": spread,
        "input_fingerprint": fingerprint,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "release": {
            "value_hz": 0.27,
            "snapshot_id": PREV_SNAPSHOT,
            "snapshot_date": snaps[PREV_SNAPSHOT]["snapshot_date"],
            "basis": "完整基准（八张同一次运行）",
        },
        "candidate": {
            "value_hz": spread,
            "snapshot_id": CURRENT_SNAPSHOT,
            "snapshot_date": snaps[CURRENT_SNAPSHOT]["snapshot_date"],
            "status": "混合复跑；可比性与重复性未完成",
            "publishable": False,
        },
        "publishable": True,
        "publishable_reason": "仅可作描述性引用（分布与极差），不得解释为时间稳定性；候选值 0.39 仍不可发布",
        "history": [
            {"snapshot_id": PREV_SNAPSHOT, "snapshot_date": snaps[PREV_SNAPSHOT]["snapshot_date"],
             "value_hz": 0.27, "note": "旧完整基准；现有页面仍显示该值"},
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"快照 {out['snapshot_id']}（{out['status']}）")
    print(f"逐碟中位：{med}")
    print(f"极差 = {spread}Hz｜输入指纹 {fingerprint}｜publishable={out['publishable']}")
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
