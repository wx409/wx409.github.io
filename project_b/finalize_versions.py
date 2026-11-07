#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声学收尾三件：sub-B1 排除清单 · 父视频待登记工单 · 版本清单（回答「现在最新是哪一版」）。

产出
  data/sub_b1_exclusions.json   低于 B1(61.0Hz) 的读数清单（按三级读数制度不进引用）
  data/source_worklist.json     需要按父视频补登记的场次
  data/acoustic_versions.json   声学资产版本表（每份文件 + sha256 前 12 位 + 生成时间）
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
B1_HZ = 61.0
OUT_SUB = ROOT / "data" / "sub_b1_exclusions.json"
OUT_WL = ROOT / "data" / "source_worklist.json"
OUT_VER = ROOT / "data" / "acoustic_versions.json"


def sha12(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main() -> int:
    tour = json.loads((ROOT / "data" / "archive_stage_tour.json").read_text(encoding="utf-8"))
    ap = json.loads((ROOT / "data" / "approach_all.json").read_text(encoding="utf-8"))
    bf = json.loads((ROOT / "data" / "source_backfill.json").read_text(encoding="utf-8"))

    # ① sub-B1：现场层里低于 B1(61.0Hz) 的读数
    rows = [r for r in tour["rows"] if r.get("low_hz") and r["low_hz"] < B1_HZ]
    by_status = Counter(r.get("review_status") or "未复核" for r in rows)
    sub = {
        "schema": "sub-b1-exclusions/v1",
        "rule": "最低稳定音 < 61.0Hz（低于 B1）→ 属低音带读数：不进汇总、不进统计、不进引用句",
        "n": len(rows),
        "by_status": dict(by_status),
        "items": [{"tag": (r.get("tag") or "")[:60], "song": r.get("song") or "",
                   "tour": r.get("tour") or "", "city": r.get("city") or "",
                   "date": r.get("date") or "", "low_note": r.get("low_note"),
                   "low_hz": r["low_hz"], "review_status": r.get("review_status") or ""}
                  for r in sorted(rows, key=lambda x: x["low_hz"])],
        "generated_at": date.today().isoformat(),
    }
    OUT_SUB.write_text(json.dumps(sub, ensure_ascii=False, indent=1), encoding="utf-8")
    print("sub-B1 读数 %d 条｜分布：%s" % (len(rows), dict(by_status)))

    # ② 父视频待登记：来源未命中素材的场次
    misses = bf.get("miss") or []
    shows = Counter()
    for m in misses:
        if not isinstance(m, dict):
            continue
        tag = (m.get("tag") or "").strip()
        key = re.sub(r"_p\d+_.*$", "", tag)
        key = re.sub(r"^【[^】]*】", "", key).strip()
        shows[key] += 1
    wl = {"schema": "source-worklist/v1",
          "task": "为每个场次登记父视频 BV（其全部 P 段继承来源类型）",
          "n_shows": len(shows), "n_materials": len(misses),
          "shows": [{"show": k, "materials": v} for k, v in shows.most_common()],
          "generated_at": date.today().isoformat()}
    OUT_WL.write_text(json.dumps(wl, ensure_ascii=False, indent=1), encoding="utf-8")
    print("待登记场次 %d 个（覆盖 %d 条素材）" % (len(shows), len(misses)))

    # ③ 版本表
    artifacts = [
        ("页面", "acoustic-report.html"),
        ("页面", "voice.html"),
        ("页面", "stage.html"),
        ("数据", "data/archive_stage_tour.json"),
        ("数据", "data/archive_vocal_albums.json"),
        ("数据", "data/citable_claims.json"),
        ("数据", "data/approach_all.json"),
        ("数据", "data/variance_pooled.json"),
        ("数据", "data/variance_bootstrap.json"),
        ("数据", "data/measurement_audit.json"),
        ("数据", "data/block_analysis.json"),
        ("数据", "data/setlist_effect.json"),
        ("文档", "docs/技术说明_声学分析_20261107.md"),
    ]
    ver = {"schema": "acoustic-versions/v1",
           "version": "acoustic-2026-11-07",
           "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "note": "声学分析当前唯一口径版本：页面以 acoustic-report.html 为准，"
                   "数据以 data/*.json 为准，方法与边界以技术说明为准",
           "calibers": ["f0_files = 2412", "approach_window = ±0.5 半音 / ≥0.15s",
                        "最低稳定音 = B1 61.5Hz（静止了的夜晚）"],
           "artifacts": []}
    for kind, rel in artifacts:
        p = ROOT / rel
        if p.exists():
            ver["artifacts"].append({"kind": kind, "path": rel,
                                     "bytes": p.stat().st_size,
                                     "sha256_12": sha12(p)})
    OUT_VER.write_text(json.dumps(ver, ensure_ascii=False, indent=1), encoding="utf-8")
    print("版本表已写：%d 份资产" % len(ver["artifacts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
