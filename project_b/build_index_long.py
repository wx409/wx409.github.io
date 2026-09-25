# -*- coding: utf-8 -*-
"""权威重建 music_index_long.csv（一处变、全局变）。

语义（已核对，非猜测）
--------------------
列：date(YYYY-MM-DD), song(规范名), index
· index = 源里的 **current_index**（与旧长表逐条抽样比对：11/12 命中 current_index，0 命中 yesterday_index）；
· 源里 current_index 非空 56,718 条 = 大屏 success 56718 ✅ 完全吻合；
· 同一 (day, 规范名) 多 uid 时取 **max**（与旧表一致：Besame 2023-01-01 = 438 即主 uid 值）。

为什么重建：旧长表每天仅 18–21 首（残缺子集），权威源每天 214–240 首。
重建后 **19 个消费该长表的脚本全部自动拿到正确数据**（一处变全局变）。

用法：
  python -X utf8 project_b\\build_index_long.py           # 试算
  python -X utf8 project_b\\build_index_long.py --apply    # 写入（自动备份）
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import RAW, canon  # noqa: E402

OUT = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")


def build() -> pd.DataFrame:
    df = pd.read_excel(RAW, usecols=["uid", "data_date", "song_name", "current_index"])
    df["date"] = pd.to_datetime(df["data_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["song"] = df["song_name"].astype(str).apply(lambda x: canon(" ".join(x.split())))
    d = df.dropna(subset=["current_index", "date"])
    g = d.groupby(["date", "song"], as_index=False)["current_index"].max()
    g = g.rename(columns={"current_index": "index"}).sort_values(["date", "song"])
    g["index"] = g["index"].astype(float)
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    new = build()
    print(f"新长表：{len(new)} 行｜日期 {new['date'].nunique()} 天（{new['date'].min()} → {new['date'].max()}）"
          f"｜曲目 {new['song'].nunique()} 首")
    per_day = new.groupby("date")["song"].nunique()
    print(f"  每日曲目数：中位 {int(per_day.median())}（{per_day.min()}–{per_day.max()}）")

    if OUT.exists():
        old = pd.read_csv(OUT, encoding="utf-8-sig")
        print(f"旧长表：{len(old)} 行｜日期 {old['date'].nunique()} 天｜曲目 {old['song'].nunique()} 首")
        opd = old.groupby("date")["song"].nunique()
        print(f"  每日曲目数：中位 {int(opd.median())}（{opd.min()}–{opd.max()}）")
        print(f"→ 行数变化 {len(old)} → {len(new)}（{100*(len(new)-len(old))/len(old):+.0f}%）")

    if not a.apply:
        print("\n[试算] 未写入（加 --apply 执行）")
        return 0
    if OUT.exists():
        bak = OUT.with_name(f"music_index_long.csv.bak_{datetime.now():%Y%m%d_%H%M}")
        shutil.copy2(OUT, bak)
        print("已备份 →", bak.name)
    new.to_csv(OUT, index=False, encoding="utf-8")
    print("已写入", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
