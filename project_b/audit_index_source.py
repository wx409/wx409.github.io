# -*- coding: utf-8 -*-
"""指数数据源覆盖审计：长表 vs 权威全量源（防"用了残缺子集"复发）。

背景：2026-09-25 发现旧长表每天仅 18–21 首、曲目 210 首，而权威源有 594 首
     → 基于长表的分析结论全部偏了。本审计守住这条线。
退出码：0 = 覆盖达标；1 = 覆盖不足（需跑 操作中心 198 重建长表）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import RAW, canon  # noqa: E402

LONG = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
THRESHOLD = 0.95


def main() -> int:
    src = pd.read_excel(RAW, usecols=["data_date", "song_name", "current_index"])
    src["date"] = pd.to_datetime(src["data_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    src["song"] = src["song_name"].astype(str).apply(lambda x: canon(" ".join(x.split())))
    s = src.dropna(subset=["current_index", "date"])
    s_pairs = set(map(tuple, s[["date", "song"]].drop_duplicates().values))
    s_days = set(s["date"].unique())
    print(f"源：行 {len(s)}｜(日,曲) 组合 {len(s_pairs)}｜日期 {len(s_days)}")

    long = pd.read_csv(LONG, encoding="utf-8-sig")
    l_pairs = set(map(tuple, long[["date", "song"]].drop_duplicates().values))
    l_days = set(long["date"].astype(str).unique())
    inter = len(s_pairs & l_pairs)
    days_inter = len(s_days & l_days)
    cov = inter / len(s_pairs) if s_pairs else 1.0
    dcov = days_inter / len(s_days) if s_days else 1.0
    print(f"长表：行 {len(long)}｜(日,曲) 组合 {len(l_pairs)}｜日期 {len(l_days)}")
    print(f"覆盖：记录 {cov*100:.1f}%（交集 {inter}/{len(s_pairs)}）｜日期 {dcov*100:.1f}%（{days_inter}/{len(s_days)}）")

    per_src = s.groupby("date")["song"].nunique().median()
    per_long = long.groupby("date")["song"].nunique().median()
    print(f"每日曲目数中位：源 {int(per_src)}｜长表 {int(per_long)}")

    bad = []
    if cov < THRESHOLD:
        bad.append(f"记录覆盖 {cov*100:.1f}% < {THRESHOLD*100:.0f}%")
    if len(s_days - l_days) > 5:
        bad.append(f"缺 {len(s_days - l_days)} 个日期")
    if per_long < per_src * 0.5:
        bad.append(f"每日曲目数中位 {int(per_long)} 远低于源 {int(per_src)}")
    if bad:
        print("\n[FAIL] " + "；".join(bad))
        print("→ 跑「操作中心 198」从权威源重建 music_index_long.csv")
        return 1
    print("\n[OK] 长表覆盖达标（与权威源一致）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
