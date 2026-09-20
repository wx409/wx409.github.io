# -*- coding: utf-8 -*-
"""场次覆盖索引：区分「有本地素材」与「已实测入库」两个口径（避免把下载当分析）。

- 口径 A（有实测数据）：站点现场层 data/archive_stage_tour.json 的素材条数
- 口径 B（有本地素材）：扫 场次音频 全部文件路径，按「巡次+城市+年月 → 城市+年月 → 巡次+城市」三级匹配
  证据强度：强（巡次+城市+年月）｜中（城市+年月）｜弱（仅巡次+城市，需人工确认场次）
产出：data/coverage_index.json（供 acoustic-report 与后续分析引用）
用法：python -X utf8 project_b\\build_coverage_index.py
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")


def main() -> int:
    shows = json.loads((DATA / "setlists.json").read_text(encoding="utf-8"))["setlists"]
    cities = sorted({v.get("city", "") for v in shows.values() if v.get("city")}, key=len, reverse=True)

    measured = defaultdict(int)
    for r in json.loads((DATA / "archive_stage_tour.json").read_text(encoding="utf-8")).get("rows", []):
        measured[(r.get("city", ""), str(r.get("date"))[:10])] += 1

    buckets, loose, tour_city = defaultdict(int), defaultdict(int), defaultdict(int)
    n_files = 0
    for dp, _dns, fs in os.walk(BASE):
        for f in fs:
            n_files += 1
            blob = dp + "\\" + f
            city = next((c for c in cities if c in blob), "")
            if not city:
                continue
            tours = {t for t in TOURS if t in blob}
            months = {f"{y}-{m}" for y, m in re.findall(r"(20\d{2})[.\-_](\d{2})(?!\d)", blob)
                      if 1 <= int(m) <= 12}
            for m in months:
                loose[(city, m)] += 1
                for t in tours:
                    buckets[(t, city, m)] += 1
            for t in tours:
                tour_city[(t, city)] += 1

    rows, miss = [], []
    for ds, v in sorted(shows.items()):
        city, tour, ym = v.get("city", ""), v.get("tour", ""), ds[:7]
        m = measured.get((city, ds), 0)
        if buckets.get((tour, city, ym)):
            src, strength = f"巡次+城市+年月（{buckets[(tour, city, ym)]} 文件）", "强"
        elif loose.get((city, ym)):
            src, strength = f"城市+年月（{loose[(city, ym)]} 文件）", "中"
        elif tour_city.get((tour, city)):
            src, strength = f"仅巡次+城市（{tour_city[(tour, city)]} 文件）", "弱"
        else:
            src, strength = "", ""
        row = {"date": ds, "city": city, "tour": tour, "songs": len(v.get("songs", [])),
               "measured_materials": m, "local_evidence": src, "strength": strength}
        (rows if src or m else miss).append(row)

    stat = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "shows_total": len(shows),
        "measured_shows": sum(1 for r in rows if r["measured_materials"]),
        "local_shows": sum(1 for r in rows if r["local_evidence"]),
        "strong": sum(1 for r in rows if r["strength"] == "强"),
        "mid": sum(1 for r in rows if r["strength"] == "中"),
        "weak": sum(1 for r in rows if r["strength"] == "弱"),
        "no_material": len(miss),
        "files_scanned": n_files,
    }
    (DATA / "coverage_index.json").write_text(
        json.dumps({"stat": stat, "shows": rows, "missing": miss}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    print("→ data/coverage_index.json")
    assert stat["shows_total"] == 64
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
