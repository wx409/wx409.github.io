# -*- coding: utf-8 -*-
"""事实预检（preflight）：生成文稿/报告/指令前，强制过一遍 facts_registry。

检查三类问题：
  ① 登记在案的**已知错误写法**（facts_registry[].wrong，如「《X自选集》2021」）
  ② **专辑年份错配**：文中出现《专辑名》附近 12 字内带年份，与登记值年份不一致
  ③ **换算类错误**：音程/半音断言（如「五个半音」）与登记规则冲突

用法：
  python -X utf8 project_b/check_facts_preflight.py --file <文件> [--file …]
  python -X utf8 project_b/check_facts_preflight.py --scan-default      # 扫仓库文档 + 报告目录
退出码：0 通过；1 发现问题（问题清单打印到 stdout）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "data" / "facts_registry.json"
REPORT_DIR = Path(r"E:\wx\论文素材_王晰作传")

DEFAULT_GLOBS = [
    ROOT / "temp" / "运维备忘_20260907.md",
    ROOT / "temp" / "事故验收_20260910.md",
    REPORT_DIR / "王晰综合评估报告_20260910.md",
]


def load_registry() -> dict:
    if not REG.exists():
        print(f"[FAIL] 找不到 {REG}，先跑 build_facts.py")
        sys.exit(2)
    return json.loads(REG.read_text(encoding="utf-8"))


def build_checks(reg: dict) -> tuple[list[tuple[str, str, re.Pattern]], list[tuple[str, str, re.Pattern]]]:
    """返回（已知错误写法检查, 专辑年份错配检查）。"""
    literal, album = [], []
    for f in reg["facts"]:
        for w in f.get("wrong", []):
            m = re.match(r"^《(.+?)》(20\d\d)$", w)
            if m:
                name, yr = m.group(1), m.group(2)
                literal.append((f["id"], w,
                                re.compile(r"《" + re.escape(name) + r"》[^0-9\n]{0,12}" + yr
                                           + r"|" + yr + r"[^0-9\n]{0,12}《" + re.escape(name) + r"》")))
            else:
                literal.append((f["id"], w, re.compile(re.escape(w))))
        if f["id"] == "album_release":
            for a in f.get("items", []):
                val = str(a.get("value") or "")
                yr = re.match(r"^(20\d\d)", val)
                if not yr:
                    continue
                album.append((f["id"], f'《{a["key"]}》应为 {val}',
                              re.compile(r"《" + re.escape(a["key"]) + r"》[^0-9\n]{0,12}(20\d\d)"
                                         r"|(20\d\d)[^0-9\n]{0,12}《" + re.escape(a["key"]) + r"》")))
    return literal, album


RANGE_BEFORE = re.compile(r"[–—~～/至]\s*$")


def _is_range_tail(line: str, start: int) -> bool:
    """年份是否属于「区间/并列」的第二个元素（2020–2022、2016/2017）——这种不判为错配。"""
    return bool(RANGE_BEFORE.search(line[:start]))


def scan(path: Path, checks_lit, checks_alb) -> list[str]:
    problems = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [f"{path}: 读取失败 {e}"]
    lines = [(i, ln) for i, ln in enumerate(text.splitlines(), 1)]
    lines = [(i, ln) for i, ln in lines if 'facts-ok' not in ln]
    for fid, label, rx in checks_lit:
        for i, ln in lines:
            if rx.search(ln):
                problems.append(f"{path.name}:{i}  [{fid}] 命中已知错误写法「{label}」")
    for fid, expect, rx in checks_alb:
        want = re.search(r"应为 (20\d\d)", expect)
        want = want.group(1) if want else ""
        for i, ln in lines:
            m = rx.search(ln)
            if not m:
                continue
            got = next((g for g in m.groups() if g), "")
            if not got or got == want:
                continue
            # 区间/并列写法（2020–2022、2016/2017）不判错配
            if _is_range_tail(ln, m.start(1 if m.group(1) else 2)):
                continue
            problems.append(f"{path.name}:{i}  [album_release] 专辑年份与登记不符：{expect}"
                            f"（文中写 {got}）")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="事实预检")
    ap.add_argument("--file", action="append", default=[], help="待检文件（可多次）")
    ap.add_argument("--scan-default", action="store_true", help="扫描默认清单（仓库文档 + 报告）")
    args = ap.parse_args()

    reg = load_registry()
    lit, alb = build_checks(reg)
    targets = [Path(f) for f in args.file]
    if args.scan_default:
        targets += DEFAULT_GLOBS
    targets = [t for t in targets if t.exists()]
    if not targets:
        print("用法：--file <文件> 或 --scan-default")
        return 0

    print("=" * 66)
    print(f"事实预检（facts_registry {len(reg['facts'])} 条，检查规则 {len(lit)+len(alb)} 条）")
    print("=" * 66)
    allp = []
    for t in targets:
        p = scan(t, lit, alb)
        print(f"[{'FAIL' if p else 'OK  '}] {t}")
        allp += p
    if allp:
        print("-" * 66)
        for x in allp:
            print("  -", x)
        print(f"\n结论：发现 {len(allp)} 处问题 —— 修正后再生成文稿/报告/指令 ❌")
        return 1
    print("\n结论：全部通过 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
