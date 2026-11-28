#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_bili_folders.py —— 修正 B站入库文件的分巡/日期（基于巡演别名 + 覆盖索引）

问题：B站标题常只写「吾」「Cherish珍晰」「肆益」，或完全没有日期，
导致落到了 `未标注/` 或 `日期未知_城市/`。

做法：
  1 别名表把演出名映射到巡次（Cherish/珍晰→一巡；吾→五巡；肆益→四巡；沉响与长歌→六巡；图景→三巡）
  2 缺日期时用 data/coverage_index.json 里 (巡次, 城市) 唯一匹配的场次补日期
  3 移动文件到正确目录，并同步更新 Excel 的 巡次/日期/城市/文件名/目标路径
不删除任何文件；匹配不到就保持原样。
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
XLSX = ROOT / "data" / "最优音频清单.xlsx"
OUT_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
COV = ROOT / "data" / "coverage_index.json"

ALIAS = {
    "一巡": ("Cherish", "珍晰", "一巡"),
    "二巡": ("二巡",),
    "三巡": ("图景", "三巡"),
    "四巡": ("肆益", "四巡"),
    "五巡": ("吾", "五巡"),
    "六巡": ("沉响与长歌", "「回」", "六巡"),
}


def tour_of(title: str) -> str:
    for t, words in ALIAS.items():
        if any(w in title for w in words):
            return t
    return ""


def main():
    cov = json.loads(COV.read_text(encoding="utf-8"))
    shows = cov.get("shows") or []
    by_tc = {}
    for s in shows:
        key = (s.get("tour") or "", s.get("city") or "")
        by_tc.setdefault(key, []).append((s.get("date") or "").replace("-", ""))

    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {k: i for i, k in enumerate(cols)}

    files = [p for p in OUT_ROOT.rglob("*.flac") if p.name.startswith("[B站-")]
    moved = 0
    for p in files:
        # 从路径与文件名还原信息
        rel = p.relative_to(OUT_ROOT)
        parts = rel.parts
        cur_tour, cur_label = parts[0], parts[1]
        name = p.stem
        title = re.sub(r"^\[B站-[^\]]+\]", "", name)
        t = tour_of(title) or (cur_tour if cur_tour in ALIAS else "")
        if not t:
            continue
        d8 = ""
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", title)
        if m:
            d8 = m.group(0)
        city = ""
        for seg in re.split(r"[_\s丨|]", cur_label):
            if seg and not seg.isdigit() and seg not in ("日期未知", "城市未知"):
                city = seg
                break
        if not city:
            for c in sorted({s.get("city") or "" for s in shows}, key=len, reverse=True):
                if c and c in title:
                    city = c
                    break
        if not d8 and city:
            cand = by_tc.get((t, city)) or []
            if len(cand) == 1:
                d8 = cand[0]
        if not d8:
            continue
        new_label = f"{d8}_{city or '城市未知'}"
        if (t, new_label) == (cur_tour, cur_label):
            continue
        dst_dir = OUT_ROOT / t / new_label
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / p.name
        if dst.exists():
            continue
        shutil.move(str(p), str(dst))
        moved += 1
        # 更新 Excel 行
        for row in ws.iter_rows(min_row=2):
            if str(row[idx["原始路径"]].value or "") == "":
                continue
            if str(row[idx["目标路径"]].value or "") == str(p):
                row[idx["巡次"]].value = t
                row[idx["日期"]].value = d8
                row[idx["城市"]].value = city
                row[idx["文件名"]].value = dst.name
                row[idx["目标路径"]].value = str(dst)
                break
        print(f"{p.relative_to(OUT_ROOT)}  ->  {t}/{new_label}/{p.name}")
    wb.save(XLSX)
    print(f"\n移动修正 {moved} 个文件；Excel 已同步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
