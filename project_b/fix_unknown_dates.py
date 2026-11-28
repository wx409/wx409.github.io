#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_unknown_dates.py —— 把 `日期未知_城市` 的音频按「巡次+城市」回填日期并归位

为什么需要：
  B站标题常写「2025.5.24」「CHERISH——珍晰2020…」等，8 位日期正则抓不到，
  文件就落到了 `日期未知_城市`；覆盖统计按日期匹配，于是那些整场没被算进去。

规则：
  1 先从文件名/路径找日期（支持 2025.5.24 / 2025年5月24日 / 纯8位）
  2 找不到 → 用 data/coverage_index.json 里 (巡次, 城市) 的场次日期：
     唯一 → 直接用；多个 → 用文件名里的年份筛选
  3 移动文件到 <巡次>/<YYYYMMDD_城市>/，同步更新 Excel 的目标路径/日期/城市/文件名
不删除任何文件。
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
XLSX = ROOT / "data" / "最优音频清单.xlsx"
OUT = Path(r"E:\wx\王晰巡演_最优音频")
COV = ROOT / "data" / "coverage_index.json"


def norm_city(c):
    """去掉「（生日场）（返场·金沙湖）」这类后缀，避免日期回填时对不上。"""
    return re.sub(r"[（(].*?[)）]", "", str(c or "")).strip()


def find_date(text):
    for pat in (r"(20\d{2})(\d{2})(\d{2})",
                r"(20\d{2})[.\-_/年](\d{1,2})[.\-_/月](\d{1,2})"):
        for m in re.finditer(pat, text):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y}{mo:02d}{d:02d}"
    return ""


def main():
    cov = json.loads(COV.read_text(encoding="utf-8"))
    by_tc = {}
    city_raw = {}
    for s in cov.get("shows") or []:
        by_tc.setdefault((s.get("tour") or "", norm_city(s.get("city"))), []).append((s.get("date") or "").replace("-", ""))
        d = (s.get("date") or "").replace("-", "")
        if d:
            city_raw[d] = s.get("city") or ""

    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}

    moved = 0
    for p in list(OUT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(OUT)
        if len(rel.parts) < 2:
            continue
        tour, label = rel.parts[0], rel.parts[1]
        if not label.startswith("日期未知"):
            continue
        city = norm_city(label.split("_", 1)[1]) if "_" in label else ""
        if city in ("城市未知", ""):
            continue
        d8 = find_date(p.name)
        if not d8:
            cands = by_tc.get((tour, city)) or []
            if len(cands) == 1:
                d8 = cands[0]
            elif cands:
                years = set(re.findall(r"(20\d{2})", p.name))
                pick = [c for c in cands if c[:4] in years]
                if len(pick) == 1:
                    d8 = pick[0]
                else:
                    # 多场同城：用标题里的特征词（生日/返场/收官/加场/首场）区分
                    KW = ("生日", "返场", "收官", "加场", "首场", "跨年", "元旦")
                    hints = [k for k in KW if k in p.name]
                    if hints:
                        pick2 = [c for c in cands
                                 if any(k in (city_raw.get(c) or "") for k in hints)]
                        if len(pick2) == 1:
                            d8 = pick2[0]
        if not d8:
            continue
        dst_dir = OUT / tour / f"{d8}_{city}"
        dst = dst_dir / p.name
        if dst.exists():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dst))
        moved += 1
        for row in ws.iter_rows(min_row=2):
            if str(row[idx["目标路径"]].value or "") == str(p):
                row[idx["日期"]].value = d8
                row[idx["城市"]].value = city
                row[idx["文件名"]].value = dst.name
                row[idx["目标路径"]].value = str(dst)
                break
        print(f"{rel}  ->  {tour}/{d8}_{city}/{p.name[:40]}")
    wb.save(XLSX)
    print(f"\n回填并移动 {moved} 个文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
