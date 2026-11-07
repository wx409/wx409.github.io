# -*- coding: utf-8 -*-
"""从最新一份 raw 全量快照构造 song × date 面板（一次读盘，落 parquet 缓存）。

为什么不用网页 JSON：dashboard_data.json 的 song_index.points 每曲中位 0 个点
（已被压缩成稀疏采样），无法做窗口分析。raw 一份 148 MB 已含 2023-01-01 起
1284 个日期、292,773 条（曲 × 日），是最省事的稠密底座。

输出 analysis/out/raw_panel.parquet
  列：uid, date, name, index, listeners, peak_listeners, src_file
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

RAW_DIR = Path(r"E:\wx\index_records\raw_archive")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
TARGET = OUT / "raw_panel.parquet"
MANIFEST = OUT / "raw_panel.manifest.json"


def latest_raw():
    files = sorted(RAW_DIR.glob("raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise SystemExit("raw_archive 里没有 raw_*.json")
    return files[0]


def main():
    src = latest_raw()
    digest = hashlib.sha256()
    with open(src, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)

    if TARGET.exists() and MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if m.get("sha256") == digest.hexdigest():
            print(f"缓存命中：{TARGET.name}（源 {src.name} 未变）")
            return

    with open(src, encoding="utf-8") as f:
        recs = json.load(f)

    df = pd.DataFrame({
        "uid": [r.get("uid") for r in recs],
        "date": [str(r.get("data_date"))[:10] for r in recs],
        "name": [r.get("display_name") or (r.get("song_name") or "").split("\n")[0] for r in recs],
        "index": pd.to_numeric([r.get("current_index") for r in recs], errors="coerce"),
        "listeners": pd.to_numeric([r.get("listeners") for r in recs], errors="coerce"),
        "peak_listeners": pd.to_numeric([r.get("peak_listeners") for r in recs], errors="coerce"),
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["uid", "date"]).sort_values(["uid", "date"]).reset_index(drop=True)
    df.to_parquet(TARGET, index=False)

    MANIFEST.write_text(json.dumps({
        "src_file": str(src), "sha256": digest.hexdigest(),
        "rows": int(len(df)), "dates": int(df["date"].nunique()),
        "uids": int(df["uid"].nunique()), "names": int(df["name"].nunique()),
        "date_min": str(df["date"].min().date()), "date_max": str(df["date"].max().date()),
        "built_at": pd.Timestamp.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"源：{src.name} | 行 {len(df):,} | 日期 {df['date'].nunique()} | "
          f"uid {df['uid'].nunique()} | 曲名 {df['name'].nunique()}")
    print("缺失率：index %.1f%% / listeners %.1f%%" % (
        df["index"].isna().mean() * 100, df["listeners"].isna().mean() * 100))


if __name__ == "__main__":
    main()
