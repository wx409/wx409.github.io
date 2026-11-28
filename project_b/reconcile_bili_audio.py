#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconcile_bili_audio.py —— 让「最优音频」里的 B站文件与 Excel 记录一致

规则：
  - Excel 里登记了目标路径的 B站 FLAC → 保留
  - 目录里存在、但 Excel 没有对应记录（历史遗留 / 双重前缀 / .flac.flac）→ 删除
  - 只动 [B站- 开头的文件，别的一概不碰
先打印清单，加 --apply 才真删。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
XLSX = ROOT / "data" / "最优音频清单.xlsx"
AUD = Path(r"E:\wx\王晰巡演_最优音频")


def main():
    apply = "--apply" in sys.argv
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    i_path = cols.index("目标路径")
    kept = {str(r[i_path]) for r in ws.iter_rows(min_row=2, values_only=True) if r[i_path]}
    print(f"Excel 登记 {len(kept)} 条")

    orphans = []
    for p in AUD.rglob("*.flac"):
        if not p.name.startswith("[B站-"):
            continue
        if str(p) in kept:
            continue
        orphans.append(p)
    print(f"孤儿文件 {len(orphans)} 个：")
    total = 0
    for p in orphans:
        mb = p.stat().st_size / 1048576
        total += mb
        print(f"  {mb:8.1f} MB  {p.relative_to(AUD)}")
        if apply:
            p.unlink()
    print(f"合计 {total/1024:.2f} GB" + ("（已删除）" if apply else "（未删除，加 --apply 执行）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
