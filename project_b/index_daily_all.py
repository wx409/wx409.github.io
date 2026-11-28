#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index_daily_all.py —— 每日指标补全 / 基线口径 / 校准 / 备份 / 分析流水线（单一入口）

为什么要它：
  run_index_daily.bat 里直接写了中文路径（E:\\wx\\论文素材_王晰作传\\基线口径\\...）。
  .bat 必须用 GBK 存，一旦被编辑器按 UTF-8 重存，cmd 就会把中文按单字节拆行，
  命令全部错位（表现为 exit 3、日志不再更新）。改成：bat 只留 ASCII，中文路径收进本脚本。

步骤（任一步失败只记录、不中断，最后汇总退出码）：
  1 index_gap_check.py
  2 index_backfill.py
  3 基线口径/compute_baseline_v1.py
  4 基线口径/generate_year_cards.py
  5 build_calibers.py
  6 index_daily_backup.py
  7 analysis/run_all.ps1
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PY = sys.executable
BASELINE = Path(r"E:\wx\论文素材_王晰作传\基线口径")
LOG_INDEX = ROOT / "temp" / "index_daily.log"
LOG_ANALYSIS = ROOT / "temp" / "analysis_daily.log"


def log(msg):
    LOG_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with LOG_INDEX.open("a", encoding="utf-8", errors="replace") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    print(msg, flush=True)


def run(label, cmd, log_path=None, ok_codes=(0,)):
    start = datetime.now()
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        rc = r.returncode
    except Exception as e:
        out, rc = f"EXC {e!r}", 99
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", errors="replace") as f:
            f.write(out)
            if out and not out.endswith("\n"):
                f.write("\n")
    ok = rc in ok_codes
    mark = "" if ok else " (FAIL)"
    log(f"[{label}] rc={rc}{mark} {int((datetime.now()-start).total_seconds())}s")
    return 0 if ok else rc


def main():
    log("=" * 60)
    log("index_daily_all start")
    rcs = {}

    rcs["gap_check"] = run("gap_check", [PY, "-X", "utf8", str(ROOT / "project_b" / "index_gap_check.py")], ok_codes=(0, 1))
    rcs["backfill"] = run("backfill", [PY, "-X", "utf8", str(ROOT / "project_b" / "index_backfill.py")], ok_codes=(0, 1))

    for name, f in (("baseline", "compute_baseline_v1.py"), ("year_cards", "generate_year_cards.py")):
        p = BASELINE / f
        if p.exists():
            rcs[name] = run(name, [PY, "-X", "utf8", str(p)])
        else:
            log(f"[{name}] 跳过：{p} 不存在")
            rcs[name] = None

    rcs["calibers"] = run("calibers", [PY, "-X", "utf8", str(ROOT / "project_b" / "build_calibers.py")])
    rcs["backup"] = run("backup", [PY, "-X", "utf8", str(ROOT / "project_b" / "index_daily_backup.py")])

    ps1 = ROOT / "analysis" / "run_all.ps1"
    if ps1.exists():
        shell = "pwsh" if subprocess.run(["where", "pwsh"], capture_output=True).returncode == 0 else "powershell"
        rcs["analysis"] = run("analysis", [shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                           "-File", str(ps1)], log_path=LOG_ANALYSIS)
    else:
        log("[analysis] 跳过：run_all.ps1 不存在")
        rcs["analysis"] = None

    bad = {k: v for k, v in rcs.items() if v not in (0, None)}
    log(f"finished: {rcs}")
    return 0 if not bad else 3


if __name__ == "__main__":
    raise SystemExit(main())
