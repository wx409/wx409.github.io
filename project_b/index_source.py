# -*- coding: utf-8 -*-
"""指数数据单一来源模块（修正版）——用权威全量源，不再用残缺长表。

背景（2026-09-25 用户发现）
--------------------------
`music_index_long.csv`（**每天仅 18–21 首**）是残缺子集；
权威全量源 `E:\\wx\\index_records\\raw_archive\\raw_latest.xlsx`：
  · 276,052 行｜703 uid｜689 曲名｜2023-01-01 → 2026-09-25
  · 每日覆盖约 **240 首**（9 月实测 240/天）
口径（对齐大屏生成器 `compute_monthly`）：
  · 有指数天数 chart_days = `current_index` 非空的天数
  · 峰值 peak_index = `current_index` 最大值
用法：
    from index_source import load, chart_days, daily_series
"""
from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from song_names import canon  # noqa: E402

RAW = Path(r"E:\wx\index_records\raw_archive\raw_latest.xlsx")
CACHE = Path(r"D:\wx409.github.io\temp\_index_cache.pkl")
BS = re.compile(r"B[eé]same\s*Mucho", re.I)


@lru_cache(maxsize=1)
def load() -> pd.DataFrame:
    """全量索引数据（首次读 xlsx 后缓存 parquet，后续秒开）。"""
    if CACHE.exists() and CACHE.stat().st_mtime >= RAW.stat().st_mtime:
        df = pd.read_pickle(CACHE)
    else:
        df = pd.read_excel(RAW, usecols=["uid", "data_date", "song_name", "current_index", "listeners"])
        df["canon"] = df["song_name"].astype(str).apply(lambda x: canon(re.sub(r"\s+", " ", x).strip()))
        df["day"] = pd.to_datetime(df["data_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        df.to_pickle(CACHE)
    return df


def coverage(df: pd.DataFrame | None = None) -> dict:
    df = load() if df is None else df
    per_day = df.groupby("day")["canon"].nunique()
    print(f"[指数源] 行 {len(df)}｜曲名 {df['canon'].nunique()}｜uid {df['uid'].nunique()}｜"
          f"{df['day'].min()} → {df['day'].max()}｜每日歌数 中位 {int(per_day.median())}"
          f"（{per_day.min()}–{per_day.max()}）｜日期 {df['day'].nunique()} 天")
    return {"rows": len(df), "songs": df["canon"].nunique(), "days": df["day"].nunique(),
            "per_day_median": int(per_day.median()), "per_day_min": int(per_day.min()),
            "per_day_max": int(per_day.max()), "from": df["day"].min(), "to": df["day"].max()}


def rows_for(name: str, df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = load() if df is None else df
    c = canon(name)
    return df[df["canon"] == c]


def chart_days(name: str, since: str | None = None, until: str | None = None) -> dict:
    """按大屏口径返回 {tracked_days, chart_days, peak, median, days:[...]}"""
    r = rows_for(name)
    if since:
        r = r[r["day"] >= since]
    if until:
        r = r[r["day"] <= until]
    with_idx = r.dropna(subset=["current_index"])
    return {"tracked_days": int(r["day"].nunique()),
            "chart_days": int(with_idx["day"].nunique()),
            "peak": (float(with_idx["current_index"].max()) if len(with_idx) else None),
            "median": (float(with_idx["current_index"].median()) if len(with_idx) else None),
            "days": sorted(with_idx["day"].unique().tolist())}


def daily_series(name: str) -> list[tuple[str, float]]:
    r = rows_for(name).dropna(subset=["current_index"])
    g = r.groupby("day")["current_index"].max()
    return [(d, float(v)) for d, v in g.items()]


if __name__ == "__main__":
    cov = coverage()
    print(cov)
    for label, since in (("全期", None), ("六巡以来", "2026-06-13"), ("2026-09", "2026-09-01")):
        print(f"  Bésame Mucho {label}: {chart_days('Bésame Mucho', since)}")
