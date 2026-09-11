# -*- coding: utf-8 -*-
"""raw_archive 保留策略执行器（幂等，可反复跑）。

背景：QQ 大屏每次 rebuild 都会把「合并 + 校准后的全量数据集」（约 27 万行）导出成
`E:\\wx\\index_records\\raw_archive\\raw_YYYYMMDD_HHMMSS_PID.xlsx`（约 58MB），一天 5 份。
2026-09-11 体检：**93.88 GB / 1611 份**，而它的一手来源（`E:\\wx\\指数vs` 0.03GB、
`增补数据库` 0.04GB、`download` 0.01GB）全部完整保留 → raw_archive 是纯派生副本。

规则（默认）：
  · 最近 7 天：全部保留
  · 更早：每天只保留最后一份（当日终批）
  · 其他删除；删除前写清单到 temp/raw_archive_清理清单_<日期>.json（可追溯）

用法：
  python -X utf8 project_b/prune_raw_archive.py                # 只试算（默认）
  python -X utf8 project_b/prune_raw_archive.py --apply        # 执行
  python -X utf8 project_b/prune_raw_archive.py --apply --keep-full-days 14
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW = Path(r"E:\wx\index_records\raw_archive")
MANIFEST_DIR = ROOT / "temp"


def collect() -> list[tuple[str, int, float]]:
    out = []
    if not RAW.is_dir():
        return out
    for f in os.listdir(RAW):
        p = RAW / f
        if p.is_file():
            st = p.stat()
            out.append((f, st.st_size, st.st_mtime))
    out.sort(key=lambda x: x[2], reverse=True)
    return out


def plan(files, keep_full_days: int):
    by_day: dict[str, list] = {}
    for f, sz, m in files:
        by_day.setdefault(time.strftime("%Y-%m-%d", time.localtime(m)), []).append((f, sz, m))
    days = sorted(by_day, reverse=True)
    keep, drop = [], []
    for i, d in enumerate(days):
        items = by_day[d]                     # 已按时间倒序
        if i < keep_full_days:
            keep += items
        else:
            keep.append(items[0])             # 当日最后一份
            drop += items[1:]
    return days, keep, drop


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正删除（默认只试算）")
    ap.add_argument("--keep-full-days", type=int, default=7)
    a = ap.parse_args()

    files = collect()
    if not files:
        print(f"[--] raw_archive 不存在或为空：{RAW}")
        return 0
    days, keep, drop = plan(files, a.keep_full_days)
    keep_gb = sum(x[1] for x in keep) / 1024**3
    drop_gb = sum(x[1] for x in drop) / 1024**3
    print(f"raw_archive：{len(files)} 份 / {sum(x[1] for x in files)/1024**3:.2f} GB｜覆盖 {len(days)} 天（{days[-1]} ~ {days[0]}）")
    print(f"规则：最近 {a.keep_full_days} 天全留 + 更早每日 1 份")
    print(f"保留 {len(keep)} 份（{keep_gb:.2f} GB）｜删除 {len(drop)} 份（{drop_gb:.2f} GB）")
    if not a.apply:
        print("[试算] 未删除任何文件（加 --apply 执行）")
        return 0

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    mf = MANIFEST_DIR / f"raw_archive_清理清单_{datetime.now():%Y%m%d_%H%M}.json"
    deleted, failed = 0, 0
    for f, sz, m in drop:
        try:
            (RAW / f).unlink()
            deleted += 1
        except OSError:
            failed += 1
    mf.write_text(json.dumps({
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rule": f"last {a.keep_full_days} days full + 1/day older",
        "kept": [x[0] for x in keep], "deleted": [x[0] for x in drop],
        "deleted_count": deleted, "failed": failed, "reclaimed_gb": round(drop_gb, 2),
        "source_note": "一手来源完整保留：E:\\wx\\指数vs / 增补数据库2025.2.22- / download；本目录为可重算的合并导出",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] 已删除 {deleted} 份（失败 {failed}）｜回收 {drop_gb:.2f} GB｜清单 {mf.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
