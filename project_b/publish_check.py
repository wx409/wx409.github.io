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
    ("稳定缺条件", r"(?<!不代表跨场)(?<!不表示跨场)(?<!不直接表示跨场)稳定(?!.{0,12}(音分|条件|范围|素材|性))"),
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




def numeric_check(text: str, claim: dict):
    """把草稿里的数字与主张 scope 对齐；并检查是否丢了边界句。"""
    issues, warns = [], []
    sc = claim.get("scope") or {}
    pairs = [
        ("版本总数", sc.get("total_versions"), r"(\d+)\s*(?:个)?版"),
        ("纳入数", sc.get("included"), r"(\d+)\s*个?纳入"),
        ("未纳入数", sc.get("excluded"), r"(\d+)\s*个?未纳入"),
        ("极差", sc.get("range_semitones"), r"极差约?\s*([\d.]+)\s*半音"),
    ]
    for name, want, pat in pairs:
        if want is None:
            continue
        m = re.search(pat, text)
        if not m:
            continue
        got = float(m.group(1))
        if abs(got - float(want)) > 0.011:
            issues.append(f"{name}：草稿 {got} ≠ 主张 {want}")
    # 边界句：主张要求“只描述分布/不表示稳定性”时，草稿应带这类限定
    need = bool(sc.get("range_semitones"))
    has = any(k in text for k in ("只描述", "不直接", "不代表", "不表示", "不是稳定性"))
    if need and not has:
        warns.append("缺边界句：该数字不能单独表示跨场稳定性，建议补“只描述读数分布”")
    return issues, warns

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

    if not case:
        _claims = json.loads((ROOT / "data" / "claims.json").read_text(encoding="utf-8"))["claims"]
        _hit = next((c for c in _claims if c.get("song") and c["song"] in text), None)
        if _hit:
            case = {"id": _hit["id"], "quote": (_hit.get("can_write") or [""])[0],
                    "source": "", "object": "", "boundary": "", "status": _hit.get("status"),
                    "claim_id": _hit["id"]}
    if case and case.get("claim_id"):
        cid = case["claim_id"]
        cl = next((c for c in json.loads((ROOT / "data" / "claims.json")
                                         .read_text(encoding="utf-8"))["claims"]
                   if c["id"] == cid), None)
        if cl:
            n_iss, n_warn = numeric_check(text, cl)
            if n_iss:
                red.extend([("数据不一致", x) for x in n_iss])
            yellow.extend([("边界", x) for x in n_warn])
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
        print(f"\n[引用原文] {case.get('quote', '')}")
        print(f"[来源] {case.get('source', '')}")
        print(f"[对象] {case.get('object', '')}")
        print(f"[边界] {case.get('boundary', '')}")
        print(f"[状态] {case.get('status', '')}")
    if not red and not yellow:
        print("\n[GREEN] 未命中措辞红线（仅代表没越界，不代表内容正确）")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
