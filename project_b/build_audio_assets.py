# -*- coding: utf-8 -*-
"""音频资产台账 —— 逐批次盘点（数量/体量/分析产物/归属场次/新增日期）。

第一性原理：报告里"素材 636 条"是个聚合数，看不到**资产是怎么来的、哪天来的、质量如何**。
传记写作需要的是可追溯的素材账本：哪批素材、什么时候进库、多少条已分析、归属哪一场。

产出：
  · data/audio_assets.json（机读：批次清单 + 汇总，**不含本地绝对路径**）
  · E:\\wx\\论文素材_王晰作传\\音域分析\\音频资产台账.md（本地人读，含今日新增置顶）

用法：python -X utf8 project_b\\build_audio_assets.py [--since 20260924]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析")
SITE = Path(__file__).resolve().parent.parent
OUT_JSON = SITE / "data" / "audio_assets.json"
OUT_MD = AUD / "音频资产台账.md"
EXT = {".wav", ".mp3", ".m4a", ".flac"}


def batch_of(p: Path) -> str:
    rel = p.relative_to(AUD)
    parts = rel.parts
    return parts[1] if len(parts) > 1 else "(根目录)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="", help="新增统计起点 YYYYMMDD（默认今日）")
    a = ap.parse_args()
    since_ts = datetime.strptime(a.since or datetime.now().strftime("%Y%m%d"), "%Y%m%d").timestamp()

    stat = json.loads((SITE / "data" / "archive_stage_tour.json").read_text(encoding="utf-8"))
    by_batch = defaultdict(lambda: {"n": 0, "mb": 0.0, "new": 0, "newmb": 0.0, "newest": 0})
    for p in AUD.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXT:
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        b = by_batch[batch_of(p)]
        b["n"] += 1
        b["mb"] += st.st_size / 2**20
        b["newest"] = max(b["newest"], st.st_mtime)
        if st.st_mtime >= since_ts:
            b["new"] += 1
            b["newmb"] += st.st_size / 2**20

    # 分析产物
    stats_by = defaultdict(int)
    for p in AUD.rglob("*_stats.json"):
        stats_by[batch_of(p)] += 1

    rows = []
    for k, v in sorted(by_batch.items(), key=lambda x: -x[1]["mb"]):
        if k.endswith("_分离") or "htdemucs" in k:
            continue                                   # 分离中间产物单列，不进主表
        rows.append({
            "batch": k, "files": v["n"], "mb": round(v["mb"], 1),
            "stats": stats_by.get(k, 0),
            "new_files": v["new"], "new_mb": round(v["newmb"], 1),
            "newest": datetime.fromtimestamp(v["newest"]).strftime("%Y-%m-%d") if v["newest"] else "",
        })

    tot_files = sum(r["files"] for r in rows)
    tot_mb = sum(r["mb"] for r in rows)
    tot_new = sum(r["new_files"] for r in rows)
    tot_newmb = sum(r["new_mb"] for r in rows)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "since": datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d"),
        "batches": len(rows), "files": tot_files, "gb": round(tot_mb / 1024, 2),
        "new_files": tot_new, "new_mb": round(tot_newmb, 1),
        "stats_total": sum(stats_by.values()),
        "stage_rows": stat["summary"]["n_materials"],
        "claimable": stat["summary"].get("n_claimable"),
        "claimable_soft": stat["summary"].get("n_claimable_soft"),
    }
    OUT_JSON.write_text(json.dumps({"summary": summary, "batches": rows}, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    md = [f"# 音频资产台账（{datetime.now():%Y-%m-%d %H:%M}）", "",
          f"- 采集批次 **{summary['batches']}** 个｜音频文件 **{tot_files}** 个｜**{summary['gb']} GB**"
          f"｜分析产物 `_stats.json` **{summary['stats_total']}** 个",
          f"- **新增（自 {summary['since']}）**：{tot_new} 个 / {tot_newmb:.1f} MB",
          f"- 现场层入库 **{summary['stage_rows']}** 条｜可主张 **{summary['claimable']}**"
          f"｜弱可主张（HNR<5dB）**{summary['claimable_soft']}**", "",
          "| 批次 | 文件 | 体量(MB) | 已分析 | 新增文件 | 新增MB | 最新日期 |", "|---|---|---|---|---|---|---|"]
    for r in rows[:40]:
        md.append(f"| {r['batch']} | {r['files']} | {r['mb']} | {r['stats']} | "
                  f"{r['new_files'] or ''} | {r['new_mb'] or ''} | {r['newest']} |")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
