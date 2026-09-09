#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指数数据源完整性守卫（check_index_integrity.py）

背景（2026-09-09）：指数长表曾因上游 `00_build_matrix.py` 的两处缺陷而系统性丢数据——
① 千分位逗号（`1,679`）导致 ≥1000 的观测被整行丢弃；② 表头乱码导致整份日文件被跳过。
修复后必须防止**再次回退**：本脚本用「特征阈值 + 脚本指纹 + 站点/源头一致性」三重检查，
任何一项异常即退出码 1，可在部署流水线里自动拦截。

检查项：
  1. 长表健康度：行数 / 天数 / ≥1000 观测数（缺陷版特征：行数 ~3.95万、≥1000 仅 ~600、天数 1234）
  2. 最新日期新鲜度（默认 ≤10 天）
  3. 构建脚本指纹：`00_build_matrix.py` 的 sha256 与登记值一致（变更即提醒确认修复仍在）
  4. 站点与源头一致：`data/archive_baseline.json` 的年度值 == `基线口径/dashboard_baseline.json`
  5. 原始库覆盖：报告原始库缺失天数（采集端缺口，非缺陷）

用法：
  python project_b/check_index_integrity.py
  python project_b/check_index_integrity.py --update-fingerprint   # 确认脚本变更后重新登记
退出码：0=通过；1=异常（需人工确认）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
RAW = Path(r"E:\wx\wx_textmine_out\music_index_raw_long.csv")
BUILDER = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
BASE_JSON = Path(r"E:\wx\论文素材_王晰作传\基线口径\dashboard_baseline.json")
SITE_BASE = ROOT / "data" / "archive_baseline.json"
FINGERPRINT = Path(__file__).resolve().parent / "index_builder_fingerprint.json"

# 缺陷版特征（2026-09-09 实测：行数 39548 / 天数 1234 / ≥1000 仅 603）
MIN_ROWS = 42000
MIN_DAYS = 1260
MIN_ROWS_GE1000 = 4000
MAX_FRESH_DAYS = 10

problems: list[str] = []
warns: list[str] = []


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    global CSV
    ap = argparse.ArgumentParser(description="指数数据源完整性守卫")
    ap.add_argument("--update-fingerprint", action="store_true", help="重新登记构建脚本指纹")
    ap.add_argument("--csv", default=str(CSV), help="指定长表路径（自检/演练用）")
    args = ap.parse_args()
    CSV = Path(args.csv)

    print("=" * 68)
    print("指数数据源完整性守卫")
    print("=" * 68)

    # ---- 1) 长表健康度 ----
    if not CSV.exists():
        problems.append(f"长表不存在: {CSV}")
    else:
        d = pd.read_csv(CSV, parse_dates=["date"])
        rows, days = len(d), d["date"].nunique()
        ge1000 = int((d["index"] >= 1000).sum())
        print(f"[info] 长表：{rows} 行 / {days} 天 / ≥1000 的观测 {ge1000} 条")
        if rows < MIN_ROWS:
            problems.append(f"行数 {rows} < 阈值 {MIN_ROWS}（疑似回退到缺陷版构建）")
        if days < MIN_DAYS:
            problems.append(f"天数 {days} < 阈值 {MIN_DAYS}（疑似表头乱码缺陷复现，整份文件被跳过）")
        if ge1000 < MIN_ROWS_GE1000:
            problems.append(f"≥1000 的观测仅 {ge1000} 条 < 阈值 {MIN_ROWS_GE1000}（疑似千分位逗号缺陷复现）")
        last = d["date"].max().date()
        lag = (date.today() - last).days
        print(f"[info] 最新日期 {last}（距今 {lag} 天）")
        if lag > MAX_FRESH_DAYS:
            warns.append(f"最新日期 {last} 距今 {lag} 天，超过 {MAX_FRESH_DAYS} 天，请检查采集")

    # ---- 2) 构建脚本指纹 ----
    if BUILDER.exists():
        h = sha256(BUILDER)
        print(f"[info] 构建脚本指纹 {h[:16]}…  {BUILDER.name}")
        if args.update_fingerprint:
            FINGERPRINT.write_text(json.dumps({
                "path": str(BUILDER), "sha256": h,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "note": "2026-09-09 修复千分位逗号 + 表头乱码两处缺陷后的指纹",
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[OK] 已登记指纹 -> {FINGERPRINT}")
        elif FINGERPRINT.exists():
            reg = json.loads(FINGERPRINT.read_text(encoding="utf-8"))
            if reg.get("sha256") != h:
                warns.append("构建脚本已变更（指纹不符）——请确认千分位逗号修复（to_num）与表头模糊匹配（pick_cols）仍在；"
                             "确认后运行 --update-fingerprint 重新登记")
            else:
                print("[OK] 构建脚本指纹与登记值一致")
        else:
            warns.append("尚未登记构建脚本指纹，请运行 --update-fingerprint")
        # 关键修复点是否仍在
        src = BUILDER.read_text(encoding="utf-8", errors="replace")
        for token, desc in (("to_num", "千分位逗号修复 to_num()"),
                            ('replace(",", "")', "逗号清洗"),
                            ("pick_cols", "表头模糊匹配 pick_cols()")):
            if token not in src:
                problems.append(f"构建脚本缺少关键修复：{desc}（token `{token}`）")
    else:
        problems.append(f"构建脚本不存在: {BUILDER}")

    # ---- 3) 站点与源头一致 ----
    if BASE_JSON.exists() and SITE_BASE.exists():
        a = json.loads(BASE_JSON.read_text(encoding="utf-8"))
        b = json.loads(SITE_BASE.read_text(encoding="utf-8"))
        va = {x["year"]: x["mean"] for x in a.get("annual", [])}
        vb = {x["year"]: x["mean"] for x in b.get("annual", [])}
        if va != vb:
            problems.append(f"站点年度指数与源头不一致：站点 {vb} vs 源头 {va}（请重跑 compute_baseline_v1.py）")
        else:
            print(f"[OK] 站点年度指数与源头一致：{vb}")

    # ---- 4) 原始库覆盖 ----
    if RAW.exists():
        r = pd.read_csv(RAW, parse_dates=["date"])
        cov = json.loads((RAW.with_name("music_index_raw_coverage.json")).read_text(encoding="utf-8")) \
            if RAW.with_name("music_index_raw_coverage.json").exists() else {}
        miss = cov.get("missing_days", [])
        print(f"[info] 原始库：{r['date'].nunique()} 天 / {len(r)} 行；采集端缺失 {len(miss)} 天（不可回补）")
    else:
        warns.append("原始库长表不存在（可运行操作中心 65 重建）")

    print("-" * 68)
    for w in warns:
        print("[warn]", w)
    if problems:
        for p in problems:
            print("[FAIL]", p)
        print(f"\n结论：{len(problems)} 项异常 —— 指数数据源可能已回退，禁止对外引用，先修再发布。")
        sys.exit(1)
    print("结论：指数数据源完整 ✅")


if __name__ == "__main__":
    main()
