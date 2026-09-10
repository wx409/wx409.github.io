# -*- coding: utf-8 -*-
"""index_date_mapping_toggle.py —— 指数长表"日期映射"口径开关（改/查/回滚 00_build_matrix.py）

背景
----
日档案 `YYYY.MM.DD.xlsx` 的「昨日音乐指数」= **文件名日期的前一天**的官方值。
但 `E:\\wx\\wx_textmine\\00_build_matrix.py` 把该值挂到**文件名日期**那一行 →
长表日期整体晚一天（证据见 temp\\指数长表日期偏移核查_20260910.md 与 影子验证报告）。

本脚本提供**一处改动**的开关（改的是生产脚本，所以带备份、语法校验与回滚）：
    --status   查看当前映射（源码标记 + 长表运行期证据）
    --dry-run  只显示将要插入的代码（不写入）
    --apply    备份 → 插入"减一天"逻辑 → py_compile 校验 → 打印 diff
    --revert   从最近一次备份恢复

⚠️ 该文件位于 E:\\wx\\wx_textmine\\（仓库外）。在受限会话中写入可能被拒绝，
   可在普通 PowerShell 里运行：python -X utf8 project_b\\index_date_mapping_toggle.py --apply

改完之后必须按顺序重跑（见 rebuild_after_backfill.py）：
    00_build_matrix.py → compute_baseline_v1.py → 操作中心 45/44 → 65/66 → 39
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
MARKER = "昨日音乐指数属于前一天"
TARGET_LINE = "d = parse_date(base)"


def read_lines() -> list[str]:
    return SRC.read_text(encoding="utf-8").split("\n")


def find_target(lines: list[str]) -> tuple[int, str]:
    for i, ln in enumerate(lines):
        if TARGET_LINE in ln and not ln.strip().startswith("#"):
            indent = ln[:len(ln) - len(ln.lstrip())]
            return i, indent
    raise SystemExit("[X] 未找到目标行 `%s`，源文件结构可能已变，请人工确认" % TARGET_LINE)


def is_patched(lines: list[str]) -> bool:
    return any(MARKER in ln for ln in lines)


def status() -> int:
    lines = read_lines()
    patched = is_patched(lines)
    i, indent = find_target(lines)
    print("源文件: %s" % SRC)
    print("目标行: 第 %d 行  %s" % (i + 1, lines[i].strip()))
    print("当前映射: %s" % ("修正口径（文件名日-1 = 值日）" if patched else "现状口径（文件名日 = 值日）"))
    baks = sorted(SRC.parent.glob(SRC.name + ".bak_*"))
    print("可用备份: %d 个%s" % (len(baks), ("，最近 %s" % baks[-1].name) if baks else ""))
    return 0


def make_diff(old: str, new: str) -> str:
    return "\n".join(difflib.unified_diff(old.split("\n"), new.split("\n"),
                                          fromfile="00_build_matrix.py（改前）",
                                          tofile="00_build_matrix.py（改后）", lineterm="", n=3))


def apply(dry: bool) -> int:
    lines = read_lines()
    if is_patched(lines):
        print("[i] 已是修正口径，无需改动")
        return 0
    i, indent = find_target(lines)
    insert = [
        "%sif d:  # %s" % (indent, MARKER),
        "%s    d = (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()" % indent,
    ]
    new_lines = lines[:i + 1] + insert + lines[i + 1:]
    old_text, new_text = "\n".join(lines), "\n".join(new_lines)
    print(make_diff(old_text, new_text))
    if dry:
        print("\n[i] --dry-run：未写入。去掉 --dry-run 即应用。")
        return 0

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = SRC.with_name(SRC.name + ".bak_" + stamp)
    shutil.copy2(SRC, bak)
    print("\n[i] 已备份 -> %s" % bak)
    SRC.write_text(new_text, encoding="utf-8")

    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "py_compile", str(SRC)],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        SRC.write_text(old_text, encoding="utf-8")
        print("[X] 语法校验失败，已自动回滚：%s" % (r.stderr or "")[:300])
        return 1
    print("[OK] 已应用并语法校验通过（备份: %s）" % bak.name)
    print("[i] 后续：python project_b\\rebuild_after_backfill.py")
    return 0


def revert() -> int:
    baks = sorted(SRC.parent.glob(SRC.name + ".bak_*"))
    if not baks:
        print("[X] 没有可用备份")
        return 1
    bak = baks[-1]
    shutil.copy2(bak, SRC)
    print("[OK] 已从 %s 恢复" % bak.name)
    return status()


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true", help="查看当前映射（默认）")
    g.add_argument("--dry-run", action="store_true", help="只显示将要插入的代码")
    g.add_argument("--apply", action="store_true", help="应用修正（带备份与语法校验）")
    g.add_argument("--revert", action="store_true", help="从最近备份回滚")
    args = ap.parse_args()

    if not SRC.exists():
        print("[X] 源文件不存在: %s" % SRC)
        return 2
    if args.apply:
        return apply(dry=False)
    if args.dry_run:
        return apply(dry=True)
    if args.revert:
        return revert()
    return status()


if __name__ == "__main__":
    sys.exit(main())
