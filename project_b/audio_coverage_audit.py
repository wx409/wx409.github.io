#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audio_coverage_audit.py —— 一到六巡音频完成度：每场有什么级别、还缺什么

级别（第一性原理：信息量从高到低）
  S 真无损自录：小卡带（44.1k/16bit WAV、ALAC 2232k）、ZOOM/大疆自录（最高 96k/24bit）、中控台直出
  A 高码率 B站音轨（≥190 kbps AAC）
  B 普通 B站音轨（<190 kbps）或录音笔直出
  C 只有官方直传 m4a（中位 131 kbps，未复制）

输出：
  data/audio_coverage_status.json / .md
  控制台打印：每巡 场次 / 有 S / 有 A / 只有 B / 全无
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
AUD = Path(r"E:\wx\王晰巡演_最优音频")
XLSX = DATA / "最优音频清单.xlsx"
COV = DATA / "coverage_index.json"
TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡")


def level_of(src: str, lvl_text: str) -> str:
    s = (src or "") + " " + (lvl_text or "")
    if any(k in s for k in ("小卡带", "自录", "中控台", "ZOOM", "大疆")):
        if "视频抽音频" in s:
            return "S"
        return "S"
    if "B站" in s:
        m = re.search(r"(\d+)\s*kbps", s)
        if m and int(m.group(1)) >= 190:
            return "A"
        return "B"
    if "录音笔" in s or "FLAC" in s:
        return "B"
    return "C"


def norm_date(s):
    d = re.sub(r"\D", "", str(s or ""))
    return d[:8] if len(d) >= 8 else ""


def main():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}
    by_show = defaultdict(lambda: defaultdict(int))     # (tour,date8) -> level -> count
    for r in ws.iter_rows(min_row=2, values_only=True):
        tour = str(r[idx["巡次"]] or "")
        d8 = norm_date(r[idx["日期"]])
        src = str(r[idx["来源"]] or "")
        lv = level_of(src, str(r[idx["级别"]] or ""))
        by_show[(tour, d8)][lv] += 1

    cov = json.loads(COV.read_text(encoding="utf-8"))
    shows = [s for s in (cov.get("shows") or []) if (s.get("tour") or "") in TOURS]
    rows, stats = [], defaultdict(lambda: defaultdict(int))
    for s in shows:
        tour, d8 = s.get("tour"), norm_date(s.get("date"))
        have = by_show.get((tour, d8)) or {}
        best = "无"
        for lv in ("S", "A", "B", "C"):
            if have.get(lv):
                best = lv
                break
        stats[tour][best] += 1
        rows.append({"tour": tour, "city": s.get("city"), "date": d8,
                     "best": best, "levels": dict(have)})
    out = {"generated_at": "", "shows": rows,
           "summary": {t: dict(stats[t]) for t in TOURS}}
    (DATA / "audio_coverage_status.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("巡次  场次  S无损  A(≥190k)  B(<190k)  全无")
    for t in TOURS:
        d = stats[t]
        total = sum(d.values())
        print(f"{t}  {total:4}  {d.get('S',0):4}  {d.get('A',0):8}  {d.get('B',0):7}  {d.get('无',0):4}")
    missing = [r for r in rows if r["best"] == "无"]
    print(f"\n完全没有音频的场次 {len(missing)} 个：")
    for r in missing[:20]:
        print(f"  {r['tour']} {r['date']} {r['city']}")
    weak = [r for r in rows if r["best"] in ("B", "C")]
    print(f"\n只有低码率的场次 {len(weak)} 个：")
    for r in weak[:20]:
        print(f"  {r['tour']} {r['date']} {r['city']}  {r['levels']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
