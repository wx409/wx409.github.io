# -*- coding: utf-8 -*-
"""verify_index_date_shift.py —— 核查 music_index_long.csv 的日期是否整体后移一天

背景
----
守护进程源码 `E:\\wx\\QQ音乐大屏生成器_GEO优化版_源码.py` 第 834-838 行明确写着：
    # 指数口径校准：某日的官方指数 = 次日抓到的「昨日音乐指数」；
    y["data_date"] = y["data_date"] - pd.Timedelta(days=1)

即：文件（抓取日 D）里的「昨日音乐指数」= **D-1 的官方指数**。
而基线构建脚本 `E:\\wx\\wx_textmine\\00_build_matrix.py` 的注释与实现是
    "列口径：文件名日期 = 值日期；取『昨日音乐指数』"
—— 把 D-1 的官方值挂到了 **D** 这一行。

本脚本用三种独立证据交叉验证到底哪个是对的，并量化影响：
  A. 列语义证据：文件 D 的「昨日音乐指数」 vs 文件 D-1 的「音乐指数」（近终批值，应高度接近但不完全相等）
  B. 守护进程口径证据：raw_archive 合并表里 data_date=D 的 current_index vs 文件 D+1 的「昨日音乐指数」
  C. 影响量化：两种映射下的日期范围 / 行数 / 年度日均 / 单日样本

用法：
    python project_b\\verify_index_date_shift.py            # 打印结论
    python project_b\\verify_index_date_shift.py --json     # 机器可读
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ADDON = Path(r"E:\wx\指数数据库\增补数据库2025.2.22-")
ARCHIVED = ADDON / "archived"
RAW_ARCHIVE = Path(r"E:\wx\index_records\raw_archive")
REPO = Path(r"D:\wx409.github.io")


def parse_date(name: str) -> dt.date | None:
    m = re.search(r"(?:^|[^\d])(\d{4})[._-]?(\d{1,2})[._-]?(\d{1,2})(?:[^\d]|$)", name)
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def to_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "").replace("人正在听", "").strip()
    if s in ("", "nan", "None", "-", "—"):
        return None
    try:
        x = float(s)
    except (TypeError, ValueError):
        return None
    return x if x == x and x > 0 else None


def collect() -> dict[dt.date, Path]:
    best: dict[dt.date, Path] = {}
    for folder in (ARCHIVED, ADDON):
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("*.xlsx")):
            if p.name.startswith("~$"):
                continue
            d = parse_date(p.name)
            if d and (d not in best or p.stat().st_mtime > best[d].stat().st_mtime):
                best[d] = p
    return best


def read_file(p: Path) -> dict[str, tuple[float | None, float | None]]:
    """返回 {歌曲: (昨日音乐指数, 音乐指数)}"""
    df = pd.read_excel(p)
    cols = list(df.columns)
    nc = next((c for c in cols if "歌曲" in str(c)), cols[1] if len(cols) > 1 else None)
    yc = next((c for c in cols if "昨日音乐指数" in str(c)), None)
    cc = next((c for c in cols if str(c).strip() == "音乐指数"), None)
    out: dict[str, tuple[float | None, float | None]] = {}
    if nc is None:
        return out
    for _, r in df.iterrows():
        nm = str(r.get(nc)).strip()
        if not nm or nm in ("nan", "None"):
            continue
        out[nm] = (to_num(r.get(yc)) if yc else None, to_num(r.get(cc)) if cc else None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sample-days", type=int, default=30, help="证据A抽样天数（取最近N天）")
    args = ap.parse_args()

    files = collect()
    days = sorted(files)
    report: dict = {"files": len(days), "date_min": days[0].isoformat(),
                    "date_max": days[-1].isoformat()}

    # ---------- 证据 A：列语义 ----------
    a_tot = a_match = 0
    a_gap = []
    samples = []
    for d in days[-args.sample_days:]:
        prev = [x for x in days if x < d]
        if not prev:
            continue
        cur = read_file(files[d])
        pre = read_file(files[prev[-1]])
        for nm, (y, _c) in cur.items():
            if y is None or nm not in pre or pre[nm][1] is None:
                continue
            a_tot += 1
            gap = abs(y - pre[nm][1])
            a_gap.append(gap)
            if gap < 0.5:
                a_match += 1
            if len(samples) < 5 and gap > 0:
                samples.append({"file_D": d.isoformat(), "song": nm,
                                "file_D_昨日指数": y, "file_D-1_音乐指数": pre[nm][1], "差": gap})
    report["evidence_A"] = {
        "比对条数": a_tot,
        "完全相等条数": a_match,
        "完全相等占比": round(a_match / a_tot * 100, 1) if a_tot else None,
        "差值中位数": round(float(pd.Series(a_gap).median()), 1) if a_gap else None,
        "差值P90": round(float(pd.Series(a_gap).quantile(0.9)), 1) if a_gap else None,
        "说明": "文件D的『昨日音乐指数』与文件D-1的『音乐指数』高度接近但不全等——"
                "因为后者是当日 23:5x 的准终值，前者是次日官方定稿值。",
        "样例": samples,
    }

    # ---------- 证据 B：守护进程合并表 ----------
    b_tot = b_match = 0
    b_samples = []
    raws = sorted(RAW_ARCHIVE.glob("raw_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if raws:
        try:
            raw = pd.read_excel(raws[0])
            if {"data_date", "song_name", "current_index"} <= set(raw.columns):
                raw["data_date"] = pd.to_datetime(raw["data_date"]).dt.date
                for d in days[-12:-1]:
                    nxt = [x for x in days if x > d]
                    if not nxt:
                        continue
                    f_next = read_file(files[nxt[0]])
                    sub = raw[raw["data_date"] == d]
                    for _, r in sub.iterrows():
                        nm = str(r["song_name"]).strip()
                        if nm not in f_next or f_next[nm][0] is None:
                            continue
                        b_tot += 1
                        if abs(float(r["current_index"]) - f_next[nm][0]) < 0.5:
                            b_match += 1
                        elif len(b_samples) < 5:
                            b_samples.append({"date": d.isoformat(), "song": nm,
                                              "守护进程current_index": float(r["current_index"]),
                                              "文件D+1_昨日指数": f_next[nm][0]})
        except Exception as e:
            report["evidence_B_error"] = str(e)[:200]
    report["evidence_B"] = {
        "raw_file": raws[0].name if raws else None,
        "比对条数": b_tot,
        "与文件D+1昨日指数相等条数": b_match,
        "相等占比": round(b_match / b_tot * 100, 1) if b_tot else None,
        "说明": "守护进程合并表的 data_date=D 官方指数，应当等于文件 D+1 的『昨日音乐指数』。",
        "样例": b_samples,
    }

    # ---------- 证据 C：影响量化 ----------
    def build(shift: int) -> dict[str, list[float]]:
        """shift=0 现状（date=文件日）；shift=-1 修正（date=文件日-1）"""
        per_day: dict[str, list[float]] = defaultdict(list)
        for d in days:
            data = read_file(files[d])
            target = (d + dt.timedelta(days=shift)).isoformat()
            for nm, (y, _c) in data.items():
                if y is not None:
                    per_day[target].append(y)
        return per_day

    def annual(per_day: dict[str, list[float]]) -> list[dict]:
        years: dict[str, list[float]] = defaultdict(list)
        for d, vals in per_day.items():
            if len(vals) >= 2:
                years[d[:4]].append(sum(vals) / len(vals))
        return [{"year": y, "valid_days": len(v), "mean": round(sum(v) / len(v), 1),
                 "median": round(float(pd.Series(v).median()), 1)}
                for y, v in sorted(years.items())]

    cur, fixed = build(0), build(-1)
    report["evidence_C"] = {
        "现状口径(文件名日=值日)": {
            "日期范围": [min(cur), max(cur)],
            "有效日数": sum(1 for v in cur.values() if len(v) >= 2),
            "年度": annual(cur),
        },
        "修正口径(文件名日-1=值日)": {
            "日期范围": [min(fixed), max(fixed)],
            "有效日数": sum(1 for v in fixed.values() if len(v) >= 2),
            "年度": annual(fixed),
        },
    }
    # 单日样本：最新文件日的取值差异
    d_last = days[-1]
    report["evidence_C"]["最新文件"] = {
        "文件名": files[d_last].name,
        "现状口径落到": d_last.isoformat(),
        "修正口径落到": (d_last - dt.timedelta(days=1)).isoformat(),
        "该值实际是哪天": (d_last - dt.timedelta(days=1)).isoformat(),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print("=" * 78)
        print("指数长表日期偏移核查  |  文件 %d 个  %s ~ %s"
              % (report["files"], report["date_min"], report["date_max"]))
        print("=" * 78)
        ea = report["evidence_A"]
        print("[证据A 列语义] 比对 %s 条，完全相等 %s 条（%s%%），差值中位 %s / P90 %s"
              % (ea["比对条数"], ea["完全相等条数"], ea["完全相等占比"],
                 ea["差值中位数"], ea["差值P90"]))
        for s in ea["样例"]:
            print("   %s %s: 文件D昨日=%s vs 文件D-1当日=%s (差 %s)"
                  % (s["file_D"], s["song"], s["file_D_昨日指数"],
                     s["file_D-1_音乐指数"], s["差"]))
        eb = report["evidence_B"]
        print("[证据B 守护进程口径] %s" % eb.get("说明"))
        if eb.get("比对条数"):
            print("   比对 %s 条，与文件D+1昨日指数相等 %s 条（%s%%）"
                  % (eb["比对条数"], eb["与文件D+1昨日指数相等条数"], eb["相等占比"]))
        ec = report["evidence_C"]
        for k in ("现状口径(文件名日=值日)", "修正口径(文件名日-1=值日)"):
            print("[证据C %s] %s 有效日 %d" % (k, ec[k]["日期范围"], ec[k]["有效日数"]))
            for r in ec[k]["年度"]:
                print("   %s 有效日 %4d 日均 %8.1f 中位 %8.1f"
                      % (r["year"], r["valid_days"], r["mean"], r["median"]))
        print("[结论] 见 temp\\指数长表日期偏移核查_20260910.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
