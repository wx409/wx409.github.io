#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布前措辞检查：把「证据到哪里，话就说到哪里」做成一条命令。

用法：
  python -X utf8 project_b/publish_check.py --text "要发的文案"
  python -X utf8 project_b/publish_check.py --file 文案.md
  python -X utf8 project_b/publish_check.py --case P1-duoting-c2 --text "..."

规则来自 data/publishable.json（red_lines）与各 case 的 boundary：
  RED    —— 直接拦住：跨全部场次、机制解释、排名、修音断言
  YELLOW —— 提醒加边界：C2/稳定/精确 Hz 缺限定词
  GREEN  —— 没命中就放行（不等于内容正确，只说明没越过措辞线）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "data" / "publishable.json"

RED = [
    ("全称断言", r"(所有|每一|全部)(个)?(现场|场次|演出)|场场"),
    ("修音断言", r"(没|无|零)(有)?修音|完全没修"),
    ("机制解释", r"(气息|气流|声带闭合|共鸣腔|声道|共振峰)(?!.{0,6}(未测|没有测))"),
    ("排名/比较", r"(碾压|吊打|天花板|最强|第一人|比.{1,8}强)"),
    ("越级证明", r"证明了?(他|其|王晰).{0,10}(唱功|能力|地位|实力)"),
]
YELLOW = [
    ("音级缺限定", r"(?<!目标)(?<!低音段)C2(?!.{0,10}(附近|左右|音级))"),
    ("稳定缺条件", r"稳定(?!.{0,12}(音分|条件|范围|素材))"),
    ("精确 Hz 缺方法", r"\d{2,3}\.\d\s*(Hz|赫兹)(?!.{0,12}(方法|参数|读数|约))"),
    ("音分缺精度说明", r"\d+(\.\d+)?\s*音分(?!.{0,12}(误差|读数|中位|精度))"),
]


def load():
    return json.loads(PUB.read_text(encoding="utf-8"))


def check(text: str, cases: list[dict], case_id: str | None = None):
    red, yellow = [], []
    for name, pat in RED:
        for m in re.finditer(pat, text):
            red.append((name, m.group(0)))
    for name, pat in YELLOW:
        for m in re.finditer(pat, text):
            yellow.append((name, m.group(0)))
    case = next((c for c in cases if c["id"] == case_id), None)
    return red, yellow, case


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--case", default="")
    a = ap.parse_args()

    if a.file:
        text = Path(a.file).read_text(encoding="utf-8")
    elif a.text:
        text = a.text
    else:
        print("用法：--text 或 --file [--case P1-duoting-c2]")
        sys.exit(1)

    doc = load()
    red, yellow, case = check(text, doc["cases"], a.case or None)

    print(f"字数 {len(text)}｜RED {len(red)}｜YELLOW {len(yellow)}")
    if red:
        print("\n[RED] 必须删或改：")
        for name, frag in red:
            print(f"  · {name}：{frag}")
    if yellow:
        print("\n[YELLOW] 建议补边界：")
        for name, frag in yellow:
            print(f"  · {name}：{frag}")
    if case:
        print(f"\n[引用原文] {case['quote']}")
        print(f"[来源] {case['source']}")
        print(f"[对象] {case['object']}")
        print(f"[边界] {case['boundary']}")
        print(f"[状态] {case['status']}")
    if not red and not yellow:
        print("\n[GREEN] 未命中措辞红线（仅代表没越界，不代表内容正确）")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
