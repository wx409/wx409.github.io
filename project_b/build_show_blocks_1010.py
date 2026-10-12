# -*- coding: utf-8 -*-
"""10-10 块级生成（由听辨回填驱动）。

输入：听辨样本\沉响20261010_块级\ 的 37 条片段 + 回填文件
      data/show_blocks/沉响与长歌_20261010_听辨回填.txt
输出：data/show_blocks/沉响与长歌_20261010.json 的 blocks
口径：沿用 10-09 的「四判据 + 一 QC」与块级**分布型**指标；
      **极值音（最低/最高稳定音）一律 `归属未定`，不写入任何极值主张**。

校验（硬性）：回填 <37 条且未标「剩余按未定处理」→ **拒绝生成**，占位句继续保留。
用法：python -X utf8 project_b\\build_show_blocks_1010.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
RF = SITE / "data" / "show_blocks" / "沉响与长歌_20261010_听辨回填.txt"
OUT = SITE / "data" / "show_blocks" / "沉响与长歌_20261010.json"
NEED = 37
WHO = ("王晰", "傲日其愣", "双人重叠", "观众", "不确定")


def parse(rf: Path):
    rows = []
    if not rf.exists():
        return rows, False
    waive = False
    for ln in rf.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "剩余按未定处理" in s:
            waive = True
            continue
        parts = [x.strip() for x in s.split("|")]
        if len(parts) >= 4 and parts[0] and all(parts[1:4]):
            rows.append({"no": parts[0], "sing_or_talk": parts[1], "voice": parts[2],
                         "who": parts[3], "note": parts[4] if len(parts) > 4 else ""})
    return rows, waive


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rows, waive = parse(RF)
    ok = len(rows) >= NEED or waive
    print(f"[块级生成] 回填 {len(rows)}/{NEED} 条｜豁免标记={'有' if waive else '无'}"
          f"｜{'✅ 可生成' if ok else '⛔ 拒绝生成（回填不完整）→ 占位句保留'}")
    if not ok:
        return 2
    groups = {}
    for r in rows:
        if r["voice"].startswith("无人声") or r["sing_or_talk"].startswith("说"):
            continue
        groups.setdefault(r["who"], []).append(r["no"])
    print(f"[块级生成] 将生成 {len(groups)} 组块（按回填归属分组合并），"
          f"归属分布：{ {k: len(v) for k, v in groups.items()} }")
    print("[块级生成] 极值音：**一律 归属未定**，不写入任何极值主张（口径见 calibers）")
    if a.dry:
        print("[--dry] 不写正式产物")
        return 0
    if not OUT.exists():
        print("!! 缺 10-10 站点数据文件，先跑 inject 链路"); return 1
    d = json.loads(OUT.read_text(encoding="utf-8"))
    print("（正式写入：需接入 10-09 的四判据+QC 指标管线，本步骤留待回填完成后执行）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
