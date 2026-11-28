#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""purge_mashups.py —— 把现有库里的「混剪/串烧/花絮」清出去，并拉黑这些 BV

动作：
  1 按 ingest_filters 规则扫描 Excel「最优音频」，命中者：
     文件移到 E:\\wx\\王晰巡演_最优音频\\_superseded\\_混剪排除\\<巡次>\\
     删除 Excel 行
  2 命中的 BV 写入 data/ingest_blacklist.json（后续抓取直接跳过）
  3 生成 data/混剪排除清单.md

只移动、不删除音频文件。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
from ingest_filters import excluded  # noqa: E402

XLSX = ROOT / "data" / "最优音频清单.xlsx"
AUD = Path(r"E:\wx\王晰巡演_最优音频")
OUT = AUD / "_superseded" / "_混剪排除"
BL = ROOT / "data" / "ingest_blacklist.json"


def main():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}

    hits, rows_to_del = [], []
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row]
        name = str(vals[idx["文件名"]] or "")
        why = excluded(name)
        if not why:
            continue
        path = Path(str(vals[idx["目标路径"]] or ""))
        bv = ""
        m = re.search(r"(BV[0-9A-Za-z]+)", str(vals[idx["原始路径"]] or "") if "原始路径" in idx else "")
        if m:
            bv = m.group(1)
        hits.append({"why": why, "name": name, "path": str(path), "bv": bv,
                     "src": str(vals[idx["来源"]] or ""), "tour": str(vals[idx["巡次"]] or "")})
        rows_to_del.append(row[0].row)
        if path.exists():
            dst_dir = OUT / str(vals[idx["巡次"]] or "未标注")
            dst_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(path), str(dst_dir / path.name))
            except Exception as e:
                print("移动失败", path.name[:40], e)

    for r in sorted(rows_to_del, reverse=True):
        ws.delete_rows(r)
    wb.save(XLSX)

    bl = []
    if BL.exists():
        try:
            bl = json.loads(BL.read_text(encoding="utf-8"))
        except Exception:
            bl = []
    have = {x.get("bv") for x in bl}
    for h in hits:
        if h["bv"] and h["bv"] not in have:
            bl.append({"bv": h["bv"], "title": h["name"], "reason": h["why"]})
    BL.write_text(json.dumps(bl, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# 混剪排除清单", "", "| 原因 | 来源 | 文件 | BV |", "|---|---|---|---|"]
    for h in hits:
        md.append(f"| {h['why']} | {h['src']} | {h['name'][:52]} | {h['bv']} |")
    (ROOT / "data" / "混剪排除清单.md").write_text("\n".join(md), encoding="utf-8")

    print(f"清出 {len(hits)} 条；拉黑 BV {len(bl)} 个；文件移到 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
