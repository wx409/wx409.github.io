#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_nightly_report.py —— 把每晚声学增量日志汇总成一份可读合集"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
LOG = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\每晚增量日志.txt")
OUT = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\每晚增量报告_合集.md")
PUB = ROOT / "data" / "vocal_nightly_history.json"


def main():
    if not LOG.exists():
        print("no log")
        return
    blocks, cur = [], []
    for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if re.match(r"\[\d{4}-\d{2}-\d{2} .*\] =+$", line):
            if cur:
                blocks.append(cur)
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        blocks.append(cur)

    runs = []
    try:
        stage = json.loads((ROOT / "data" / "archive_stage_tour.json").read_text(encoding="utf-8"))
        low_song = ((stage.get("summary") or {}).get("lowest") or {}).get("song") or ""
    except Exception:
        low_song = ""
    for b in blocks:
        text = "\n".join(b)
        if "现场层：素材" not in text:
            continue
        mt = re.search(r"\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}):", b[0])
        if not mt:
            continue
        songs = re.findall(r"\[[^\]]+\]\s+·\s+(.+?)｜(BV\w+)｜", text)
        cand = re.search(r"候选 (\d+) 条｜本次处理 (\d+) 条", text)
        total = re.search(r"现场层：素材 (\d+) 条｜最低稳定音 ([^（(]+)", text)
        runs.append({"date": mt.group(1), "time": mt.group(2),
                     "candidates": int(cand.group(1)) if cand else None,
                     "processed": int(cand.group(2)) if cand else 0,
                     "songs": [{"song": s, "bv": bv} for s, bv in songs],
                     "materials": int(total.group(1)) if total else None,
                     "lowest": total.group(2).strip() if total else ""})

    lines = ["# 王晰 · 每晚声学增量合集", "",
             "> 来源：`每晚增量.py` 日志；每晚下载音轨 → 分离 → 逐帧 F0 → 回写现场层。",
             "> 网页：https://wx409.github.io/stage.html ｜ 数据：`data/archive_stage_tour.json`", ""]
    for r in runs[-60:][::-1]:
        lines += ["## %s %s" % (r["date"], r["time"]), ""]
        lines.append("- 候选 %s 条；本次处理 **%s** 条" % (r["candidates"] if r["candidates"] is not None else "—", r["processed"]))
        if r["songs"]:
            lines.append("- 曲目：" + "、".join("《%s》" % x["song"] for x in r["songs"]))
        if r["materials"] is not None:
            label = "%s（《%s》）" % (r["lowest"], low_song) if low_song else r["lowest"]
            lines.append("- 现场层累计：**%d** 条素材；最低稳定音 **%s**" % (r["materials"], label))
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    PUB.write_text(json.dumps({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "runs": runs[-30:][::-1]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("runs", len(runs), "->", OUT)


if __name__ == "__main__":
    main()
