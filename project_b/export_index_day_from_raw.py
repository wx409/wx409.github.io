# -*- coding: utf-8 -*-
"""把 10-16 的指数读数从 raw_archive（10-17 采集）导出为**标准日档**，供长表补日。

背景：`00_build_matrix.py` 的约定是「文件名日期 − 1 天 = 值日期」。
  · `2026.10.16.xlsx` → 值日期 10-15（已导入，对得上 raw 的 10-15 值：南屏晚钟 162 等）
  · 因此 **10-16 需要 `2026.10.17.xlsx`**。当天 `指数vs` 只有 quick 批次（无指数列），
    但 daemon 在 **10-17 14:52** 的全量采集已拿到 10-16 的「昨日指数」，存在
    `raw_archive/raw_20261017_145227_9988.xlsx` / `raw_latest.xlsx`。
本脚本：从 raw_latest 取 `data_date=2026-10-16` 且 current_index 非空的行，
导出为 `E:\\wx\\指数数据库\\增补数据库2025.2.22-\\2026.10.17.xlsx`（列名与既有日档一致），
**不做任何插值/伪造**；文件里写不清的都不写。
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAW = Path(r"E:\wx\index_records\raw_archive\raw_latest.xlsx")
OUT = Path(r"E:\wx\指数数据库\增补数据库2025.2.22-") / "2026.10.17.xlsx"
TARGET = "2026-10-16"


def main() -> int:
    df = pd.read_excel(RAW, usecols=["data_date", "song_name", "current_index", "listeners"])
    df["d"] = pd.to_datetime(df["data_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    sub = df[(df["d"] == TARGET) & df["current_index"].notna()].copy()
    if sub.empty:
        print(f"[X] raw_archive 里没有 {TARGET} 的指数读数 → 无法导出（不伪造）")
        return 1
    out = pd.DataFrame({
        "序号": range(1, len(sub) + 1),
        "歌曲名称": sub["song_name"].astype(str),
        "演唱者": "王晰",
        "昨日音乐指数": sub["current_index"].astype(float),
        "音乐指数": sub["current_index"].astype(float),
        "当前收听人数": sub["listeners"],
        "状态": "成功",
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(OUT, index=False)
    print(f"[OK] 导出 {OUT}")
    print(f"     行 {len(out)}｜值日期 {TARGET}（文件名 2026.10.17 → 长表日期＝文件名−1）")
    print("     示例：", out[["歌曲名称", "昨日音乐指数"]].head(3).to_dict("records"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
