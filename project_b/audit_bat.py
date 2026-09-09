#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批处理体检（audit_bat.py）：把「bat 被写坏」这类事故变成可自动发现的问题。

历史教训（都在本项目真实发生过）：
  1. `python -c` 写 bat 时路径里的 `\\a`/`\\v` 被转义成 BEL(\\x07)，菜单文本变成控制字符；
  2. GBK 文件被当二进制/UTF-8 处理 → 中文变乱码；
  3. 写入时多出一个 CR（`\\r\\r\\n`）→ `goto menu` 的目标变成 `menu\\r`，命令失败；
  4. echo 文本里出现半角 `| > &` → 被 cmd 当重定向/管道执行，命令报"语法不正确"。

本脚本对 `操作中心.bat`（及其他 GBK 批处理）做上述四类检查 + goto 目标完整性检查。

用法：
  python project_b/audit_bat.py
  python project_b/audit_bat.py --file 某个.bat
退出码：0=通过；1=有问题。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "操作中心.bat"

BANNED_IN_ECHO = re.compile(r"[|><&]")


def check(path: Path) -> list[str]:
    problems: list[str] = []
    raw = path.read_bytes()

    # 1) 编码：必须能按 GBK 解码（中文批处理的约定）
    try:
        text = raw.decode("gbk")
    except UnicodeDecodeError as e:
        problems.append(f"GBK 解码失败（{e}）——批处理必须保持 GBK 编码")
        text = raw.decode("gbk", errors="replace")

    # 2) 控制字符
    if b"\x07" in raw:
        problems.append(f"发现 BEL 字符(\\x07) ×{raw.count(bytes([7]))}——路径里的 \\a 被转义，必须逐行重写")
    dbl = raw.count(b"\r\r")
    if dbl > 0:
        problems.append(f"发现双回车(\\r\\r) ×{dbl}——会让 goto 目标带上 CR 而失败")
    if raw.count(b"\r\n") != raw.count(b"\n"):
        problems.append("存在裸 LF（非 CRLF 结尾）——批处理应统一 CRLF")

    lines = text.splitlines()

    # 3) echo 文本里的半角危险字符
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.lower().startswith("echo") and BANNED_IN_ECHO.search(s):
            # 允许 bat 转义写法 ^< ^> ^|
            if not re.search(r"\^[|><&]", s):
                problems.append(f"第 {i} 行 echo 含半角 | > & 且未转义: {s[:70]}")

    # 4) goto 目标完整性（含 `if "%op%"=="56" goto xxx` 这类行内跳转）
    labels = {m.group(1).lower() for m in re.finditer(r"^\s*:([A-Za-z_][\w]*)", text, re.M)}
    for i, ln in enumerate(lines, 1):
        for m in re.finditer(r"\bgoto\s+:?([A-Za-z_][\w]*)", ln, re.I):
            if m.group(1).lower() not in labels:
                problems.append(f"第 {i} 行 goto {m.group(1)} —— 找不到对应标签")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="批处理体检")
    ap.add_argument("--file", default=str(DEFAULT))
    args = ap.parse_args()
    p = Path(args.file)
    if not p.exists():
        print(f"[FAIL] 文件不存在: {p}")
        sys.exit(1)

    problems = check(p)
    print("=" * 68)
    print(f"批处理体检：{p.name}（{p.stat().st_size} 字节）")
    print("=" * 68)
    if problems:
        for x in problems:
            print("  [FAIL]", x)
        print(f"\n结论：{len(problems)} 个问题——修好再发布。")
        sys.exit(1)
    print("  [OK] GBK 编码正常｜无 BEL｜无双回车｜行尾统一 CRLF｜echo 无半角危险符｜goto 目标齐全")
    print("\n结论：通过 ✅")


if __name__ == "__main__":
    main()
