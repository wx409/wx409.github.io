# -*- coding: utf-8 -*-
"""power_schedule.py —— 自动关机档位（配套 QQ音乐大屏生成器的 shutdown_skip.txt 机制）

机制：大屏生成器每晚 23:55 全量采集后，按 E:\\wx\\shutdown_skip.txt 决定次日 01:30 是否关机。
      本脚本只改「档位」（E:\\wx\\shutdown_skip_config.txt），豁免日由 holiday_skip_sync.py 生成。

档位：
  normal  周一~周五 01:30 关机；周六/周日 + 法定节假日 不关机（默认）
  all     长期不关机（窗口内所有日期豁免）
  status  只预览：当前档位 + 未来 14 天判定（不写任何文件）

用法：python -X utf8 project_b\\power_schedule.py normal|all|status
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CFG = Path(r"E:\wx\shutdown_skip_config.txt")
SYNC = Path(__file__).resolve().parent / "holiday_skip_sync.py"
MODES = ("normal", "all")


def read_mode() -> str:
    try:
        for line in CFG.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line.startswith("mode"):
                return line.split("=", 1)[1].strip().lower()
    except Exception:
        pass
    return "normal"


def set_mode(mode: str) -> None:
    old = CFG.read_text(encoding="utf-8") if CFG.exists() else ""
    lines, seen = [], False
    for line in old.splitlines():
        if line.split("#")[0].strip().startswith("mode"):
            lines.append("mode = " + mode)
            seen = True
        else:
            lines.append(line)
    if not seen:
        lines.insert(0, "mode = " + mode)
    CFG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] 档位已写入 %s：mode = %s" % (CFG, mode))


def run_sync(dry: bool) -> int:
    cmd = [sys.executable, "-X", "utf8", str(SYNC)] + (["--dry"] if dry else [])
    return subprocess.call(cmd)


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if mode == "status":
        print("[i] 当前档位：mode = %s" % read_mode())
        print("[i] 关机时刻：01:30（大屏生成器源码内固定，非本文件可调）")
        return run_sync(dry=True)
    if mode not in MODES:
        print("[X] 用法：python -X utf8 project_b\\power_schedule.py normal|all|status")
        return 2
    set_mode(mode)
    rc = run_sync(dry=False)
    print("[i] 生效时点：今晚 23:55 大屏生成器采集后读取豁免文件；已运行的 daemon 无需重启。")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
