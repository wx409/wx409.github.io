# -*- coding: utf-8 -*-
"""常设守卫：已定案的 show_blocks 必须在 stage.html「一之二」小节里按块数渲染。

判定（任一不满足即红灯 exit 1）：
  1. 数据层 data/show_blocks/*.json 中，任一场次 listening_status=已定案 或 blocks 非空
     → stage.html 必须存在「<h2>一之二、双人场次（块级）」小节；
  2. 该场次小节内的表格行数（<td>bNN</td>）必须等于 blocks 数；
  3. 小节内不得出现占位句「待听辨定案」（已定案却仍占位 = 切换失败）。
背景：2026-10-12 自动部署只跑聚合器 → 覆盖注入结果，整节被冲掉（audit_live 未覆盖此风险）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
SB = SITE / "data" / "show_blocks"
STAGE = SITE / "stage.html"


def main() -> int:
    if not STAGE.exists():
        print("!! stage.html 不存在"); return 1
    h = STAGE.read_text(encoding="utf-8")
    need = []
    for f in sorted(SB.glob("*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        bl = j.get("blocks") or []
        if bl or str(j.get("listening_status")) == "已定案":
            need.append(((j.get("show") or {}).get("date") or f.stem, len(bl), f.name))
    if not need:
        print("  （无已定案场次，跳过）"); return 0
    hits = [m.start() for m in re.finditer(r"<h2>一之二", h)]
    if not hits:
        print(f"  ✗ 数据层有 {len(need)} 个已定案场次，但 stage.html 缺「一之二、双人场次（块级）」小节")
        return 1
    secs = []
    for i, p in enumerate(hits):
        e = h.find("<h2>", p + 10)
        secs.append(h[p:e if e > 0 else len(h)])
    bad = []
    for date, n, fn in need:
        sec = next((s for s in secs if n and len(re.findall(r"<td>b\d\d</td>", s)) == n), None)
        if sec is None:
            rows = max((len(re.findall(r"<td>b\d\d</td>", s)) for s in secs), default=0)
            bad.append(f"{date}：块 {n}，页面最多见 {rows} 行")
    print(f"  数据层已定案 {len(need)} 场｜stage 小节 {len(secs)} 个｜行数校验{'通过 ✅' if not bad else '失败'}")
    for b in bad:
        print("   ✗", b)
    if bad:
        return 1
    if any("待听辨定案" in s for s in secs):
        print("   ✗ 小节内仍有占位句（已定案却占位）"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
