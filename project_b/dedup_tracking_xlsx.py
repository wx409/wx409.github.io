#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收听人数（追踪链接表）按链接 mid 去重。

背景：同一首歌可能被登记多行（演唱者写法不同，如「王晰/弦子」与「王晰」），
链接是同一个 mid → 属于重复行，会让追踪池/榜单重复计数。
注意：**不能按歌名去重**——同名不同 mid 可能是不同版本（Live / 离别版 / 伴奏）。

用法：
  python -X utf8 project_b\\dedup_tracking_xlsx.py            # 只报告（dry-run）
  python -X utf8 project_b\\dedup_tracking_xlsx.py --write    # 备份后写回
"""
from __future__ import annotations

import argparse
import re
import shutil
import time
from pathlib import Path

import openpyxl

XLSX = Path(r"E:\wx\收听人数（2026.7.24）.xlsx")


def mid_of(link: str) -> str:
    m = re.search(r"[?&]mid=([0-9A-Za-z]+)", str(link or ""))
    return m.group(1) if m else ""


def score(row: tuple) -> int:
    name = str(row[1] or "")
    singer = str(row[2] or "")
    honor = row[5]
    status = str(row[8] or "")
    s = 0
    if "在用" in status:
        s += 4
    if "/" in singer:
        s += 2
    if honor not in (None, ""):
        s += 1
    if "(Live)" not in name and "（Live）" not in name:
        s += 2
    if str(row[6] or "") == name or not row[6]:
        s += 1
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(XLSX))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    p = Path(a.xlsx)
    wb = openpyxl.load_workbook(p)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    groups: dict[str, list[int]] = {}
    for i, r in enumerate(rows, start=2):
        mid = mid_of(r[3])
        if mid:
            groups.setdefault(mid, []).append(i)

    drop: list[tuple[int, str]] = []
    for mid, idxs in groups.items():
        if len(idxs) < 2:
            continue
        idxs.sort(key=lambda i: (-score(rows[i - 2]), i))
        keep = idxs[0]
        for i in idxs[1:]:
            drop.append((i, mid))

    print("总行数 %d｜唯一 mid %d｜重复 mid %d｜待删 %d 行"
          % (len(rows), len(groups), sum(1 for v in groups.values() if len(v) > 1), len(drop)))
    for i, mid in sorted(drop):
        r = rows[i - 2]
        print("  删第 %d 行：%s｜%s｜%s" % (i, r[1], r[2], mid))

    # 伴奏/纯音乐提示（不自动删）
    for i, r in enumerate(rows, start=2):
        n = str(r[1] or "")
        if any(k in n for k in ("伴奏", "纯音乐", "Instrumental", "inst.")):
            print("  提示：第 %d 行是伴奏/纯音乐：%s（%s）" % (i, n, r[2]))

    if not a.write:
        print("\n[dry-run] 加 --write 才会写回（会先备份）")
        return 0
    bak = p.with_name(p.stem + "_bak_" + time.strftime("%Y%m%d_%H%M%S") + p.suffix)
    shutil.copy2(p, bak)
    for i, _ in sorted(drop, reverse=True):
        ws.delete_rows(i, 1)
    wb.save(p)
    print("\n已写回 %s｜备份 %s" % (p, bak.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
