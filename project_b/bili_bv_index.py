#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_bv_index.py —— B站来源索引：每个 BV 对应的巡次/城市/音频文件/视频文件（有就记，没下就标）

目的（用户要求）：**留下 BV 号**。将来如果要视频，能按 BV 回 bilibili.com/video/<BV> 找原视频。
产出：
  data/bili_bv_index.md   人看的表
  data/bili_bv_index.json 程序用
  Excel「最优音频」新增 BV 列（B站行填 BV，其它留空）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
XLSX = DATA / "最优音频清单.xlsx"
AUD = Path(r"E:\wx\王晰巡演_最优音频")
VID = Path(r"E:\wx\王晰巡演_视频源")


def main():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    head = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(head)}
    if "BV" not in head:
        ws.cell(row=1, column=len(head) + 1, value="BV")
        head.append("BV")
        idx["BV"] = len(head) - 1

    # 已下载的视频：按 BV 建索引
    vids = {}
    if VID.exists():
        for p in VID.rglob("*.mp4"):
            m = re.search(r"(BV[0-9A-Za-z]+)", p.name)
            if m:
                vids[m.group(1)] = str(p)

    rows, n = [], 0
    for r in ws.iter_rows(min_row=2):
        src = str(r[idx["来源"]].value or "")
        if not src.startswith("B站-"):
            continue
        raw = str(r[idx["原始路径"]].value or "")
        m = re.search(r"(BV[0-9A-Za-z]+)", raw) or re.search(r"(BV[0-9A-Za-z]+)", str(r[idx["目标路径"]].value or ""))
        bv = m.group(1) if m else ""
        if bv and not r[idx["BV"]].value:
            r[idx["BV"]].value = bv
            n += 1
        rows.append({
            "BV": bv,
            "url": f"https://www.bilibili.com/video/{bv}" if bv else "",
            "UP": src.replace("B站-", ""),
            "巡次": r[idx["巡次"]].value, "日期": r[idx["日期"]].value, "城市": r[idx["城市"]].value,
            "音频文件": str(r[idx["目标路径"]].value or ""),
            "视频文件": vids.get(bv, ""),
            "级别": r[idx["级别"]].value,
        })
    wb.save(XLSX)
    print(f"补齐 BV 列 {n} 行；B站 记录 {len(rows)} 条，其中已下载视频 {sum(1 for x in rows if x['视频文件'])} 条")

    md = ["# B站 来源索引（按 BV）", "",
          f"> 共 {len(rows)} 条；回原视频：`https://www.bilibili.com/video/<BV>`",
          "> 「视频文件」为空 = 当时只取了音频；需要视频时按 BV 重下即可（`bili_best_fetch.py --bv <BV> --video max`）", "",
          "| BV | 巡次 | 日期 | 城市 | 音轨级别 | UP | 视频文件 |", "|---|---|---|---|---|---|---|"]
    for x in sorted(rows, key=lambda y: (str(y["巡次"]), str(y["日期"]))):
        md.append(f"| [{x['BV']}]({x['url']}) | {x['巡次'] or ''} | {x['日期'] or ''} | {x['城市'] or ''} | "
                  f"{x['级别'] or ''} | {x['UP']} | {'有' if x['视频文件'] else '未下载'} |")
    (DATA / "bili_bv_index.md").write_text("\n".join(md), encoding="utf-8")
    (DATA / "bili_bv_index.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写出 data/bili_bv_index.md / .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
