#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""today_watchdog.py —— 每天中午检查“今日新入库”是否真的更新；失败则补跑并通知"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
TODAY = ROOT / "data" / "today.json"
sys.path.insert(0, str(ROOT / "project_b"))
import notify  # noqa


def run(script):
    print("run", script, flush=True)
    return subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / script)], cwd=str(ROOT)).returncode


def main():
    today = date.today().isoformat()
    try:
        d = json.loads(TODAY.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    if d.get("date") == today and d.get("fresh"):
        print("today fresh", d.get("date"), d.get("updated_at"))
        return 0
    print("today stale", d.get("date"), "->", today)
    rc1 = run("bili_daily_ingest.py")
    rc2 = run("build_today.py")
    if rc1 == 0 and rc2 == 0:
        notify.record("今日新入库已补跑", "bili_daily_ingest + build_today 已完成（%s）" % today,
                      category="今日更新", source="today_watchdog")
        return 0
    notify.record("⚠ 今日新入库补跑失败", "bili_daily_ingest rc=%s；build_today rc=%s；today.json 仍为 %s" %
                  (rc1, rc2, d.get("date")), category="运维告警", source="today_watchdog")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
