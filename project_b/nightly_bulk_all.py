#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nightly_bulk_all.py —— 周末批量增量（把中文路径从 .bat 里挪出来）

原 run_nightly_bulk.bat 里含中文路径（E:\\wx\\论文素材_王晰作传\\音域分析\\轨迹\\每晚增量.py），
.bat 按 UTF-8 存时 cmd.exe 会按 GBK 拆行导致命令错位（曾出现 0x800704C7/命令找不到）。
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PY = sys.executable
INCREMENT = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\每晚增量.py")
LOG = ROOT / "temp" / "nightly_bulk.log"


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", errors="replace") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    print(msg, flush=True)


def run(label, cmd):
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        with LOG.open("a", encoding="utf-8", errors="replace") as f:
            f.write(out)
            if out and not out.endswith("\n"):
                f.write("\n")
        log(f"[{label}] rc={r.returncode}")
        return r.returncode
    except Exception as e:
        log(f"[{label}] EXC {e!r}")
        return 99


def main():
    log("=" * 50)
    log("nightly_bulk_all start")
    rcs = []
    if INCREMENT.exists():
        rcs.append(run("increment", [PY, "-X", "utf8", str(INCREMENT), "--limit", "24", "--video-limit", "0"]))
    else:
        log(f"[increment] 跳过：{INCREMENT} 不存在")
    # B站补全：先扫 9 个 UP 的未收录（wbi 签名），再抓最高音质音视频（大会员）
    for name, args_ in (("bili_scan_missing.py", []),
                        ("bili_best_fetch.py", ["--from-missing", "--top", "6"])):
        p = ROOT / "project_b" / name
        if p.exists():
            rcs.append(run(name, [PY, "-X", "utf8", str(p)] + args_))
        else:
            log(f"[{name}] 跳过：不存在")

    for name in ("build_edit_list.py", "build_nightly_report.py"):
        p = ROOT / "project_b" / name
        if p.exists():
            rcs.append(run(name, [PY, "-X", "utf8", str(p)]))
        else:
            log(f"[{name}] 跳过：不存在")
    bad = [r for r in rcs if r != 0]
    log(f"finished rcs={rcs}")
    return 0 if not bad else 3


if __name__ == "__main__":
    raise SystemExit(main())
