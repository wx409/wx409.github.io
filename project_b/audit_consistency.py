#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_consistency.py —— 汇总 vs 明细 一致性审计（防"未复核值被当结论"）。

为什么需要（第一性原理）：
  本项目有多个"汇总数字"分布在 4-5 个页面（stage / voice / vocal / llms.txt）。
  它们的口径是**最低音只取已复核读数**（未复核不作能力依据）——这是对的；
  但页面很容易**隐去"未复核里还有更低值"**，于是出现"汇总写 E2、明细里却有 B1"的
  前后矛盾（2026-09-16 实际发生过）。
  逐个页面人工核不可持续 → 由一个审计脚本从**单一数据源**（data/*.json）派生后核对。

判据（对每个汇总位点）：
  1. 若"全部读数的最低"比"已复核的最低"更低 → 该位点**必须披露**该更低值（页面有标记）
  2. 若数据源已标记 lowest_pending_under=True → 页面须出现披露文案
  3. llms.txt 不得把 未复核/待复核 读数写成结论句

退出码：0 通过；1 发现问题（部署链会把关）。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GOOD = ("谐波列复核通过", "双引擎一致", "人耳确认", "已取证", "✅", "🟡")
DISCLOSE = ("未复核中另有更低", "未过者最低")          # 页面披露文案


def jl(name):
    p = DATA / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def page(name):
    p = ROOT / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def is_good(v) -> bool:
    return bool(v) and any(g in str(v) for g in GOOD)


def main() -> int:
    problems = []

    def note(pos, ok, detail=""):
        # 只在失败时打印 detail（成功时打 detail 会让人误以为有问题）
        print(f"  [{'OK  ' if ok else 'FAIL'}] {pos}" + (f" — {detail}" if (detail and not ok) else ""))
        if not ok:
            problems.append(f"{pos}：{detail}")

    print("-" * 74)
    print("汇总 vs 明细 一致性审计（源 data/*.json → 页面）")

    # ── 1) 现场层巡次汇总 ──
    t = jl("archive_stage_tour.json") or {}
    rows = t.get("rows") or []
    tpage = page("stage.html")
    for x in t.get("by_tour") or []:
        tour = x.get("tour")
        g = [r for r in rows if r.get("tour") == tour and r.get("low_hz")]
        lo_all = min(g, key=lambda r: r["low_hz"], default=None)
        lo_ok = min([r for r in g if is_good(r.get("a3_final_note"))],
                    key=lambda r: r["low_hz"], default=None)
        if not (lo_all and lo_ok):
            continue
        lower_exists = lo_all["low_hz"] < lo_ok["low_hz"] - 0.5
        flagged = bool(x.get("lowest_pending_under"))
        note(f"巡次汇总 {tour}：已复核 {lo_ok.get('low_note')}"
             + (f" / 未复核最低 {lo_all.get('low_note')}" if lower_exists else ""),
             (not lower_exists) or flagged,
             "" if (not lower_exists) or flagged else "数据源未标记 lowest_pending_under")
    # 页面须含披露文案（若任一巡次需要）
    need = any(x.get("lowest_pending_under") for x in (t.get("by_tour") or []))
    if need:
        note("stage.html 含披露文案", any(k in tpage for k in DISCLOSE),
             "数据源有未复核更低值，但页面无披露文案")

    # ── 2) 对照层 / 录音室层 / 音域脉络 ──
    for name, src, pagefile in (("对照层摘要", "archive_stage.json", "stage.html"),
                                ("录音室汇总", "archive_vocal_albums.json", "voice.html")):
        d = jl(src) or {}
        s = d.get("summary") or {}
        if not s.get("lowest"):
            continue
        lo = s["lowest"]
        items = [x for x in (d.get("items") or d.get("songs") or []) if x.get("lowest_hz")]
        lower = [x for x in items if x["lowest_hz"] < (lo.get("hz") or 1e9) - 0.5]
        note(f"{name}（{src}）", not lower,
             (f"存在更低的未复核读数 {min(lower, key=lambda x: x['lowest_hz'])['lowest_note']}"
              if lower else ""))

    lin = jl("vocal_lineage.json") or {}
    items = lin.get("items") or []
    note("音域脉络逐条带状态", all(i.get("status") for i in items) if items else True,
         "有条目缺 status 字段")

    # ── 3) llms.txt 不得把未复核写成结论 ──
    lp = ROOT / "llms.txt"
    if lp.exists():
        txt = lp.read_text(encoding="utf-8", errors="replace")
        bad = re.findall(r"[^\n]*(?:未复核|待复核)[^\n]*", txt)
        # 允许出现在"待补/说明"句里，但不允许与"最低音/最高音/能力"同句
        bad = [b for b in bad if re.search(r"最低音|最高音|能力|结论|跨度中位", b)]
        note("llms.txt 未把未复核当结论", not bad,
             ("；".join(b.strip()[:60] for b in bad[:2]) if bad else ""))

    print("-" * 74)
    if problems:
        print(f"结论：发现 {len(problems)} 处一致性风险 —— 必须修。")
        for p in problems:
            print("   -", p)
        return 1
    print("结论：汇总与明细一致（未复核读数均已披露、未被当结论）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
