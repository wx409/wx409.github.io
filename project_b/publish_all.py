#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish_all.py —— “重建与把关”统一入口：导航 + 三个审计"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PY = sys.executable


def run(script, *args):
    print("==", script, *args, flush=True)
    r = subprocess.run([PY, "-X", "utf8", str(ROOT / script), *args], cwd=str(ROOT))
    return r.returncode


def main():
    rc = 0
    quick = "--quick" in sys.argv
    steps = [
        ("project_b/build_nav.py",),
        ("project_b/audit_nav.py",),
        ("project_b/audit_jsonld.py",),
    ]
    if not quick:
        steps.append(("project_b/audit_caliber.py",))
    for step in steps:
        rc = max(rc, run(*step))
    print("== 重建与把关完成，退出码", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
