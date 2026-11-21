#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演出日自动收集观众发帖（微博搜索 + 小红书；B站另跑）。

读 data/activity_master.json 当天是否有演出 → 有则对每个城市跑
project_b/collect_show_feedback.py --date <date> --city <city> --skip-bili。

用法：
  python -X utf8 project_b\\show_day_social.py --dry
  python -X utf8 project_b\\show_day_social.py --date 2026-11-20 --slot pm
  python -X utf8 project_b\\show_day_social.py --slot am   # 次日早晨补后劲

幂等：同一 (date, slot) 跑过则跳过（temp\\show_day_social_state.json）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACT = ROOT / "data" / "activity_master.json"
LOG = ROOT / "temp" / "show_day_social.log"
STATE = ROOT / "temp" / "show_day_social_state.json"
COLLECT = ROOT / "project_b" / "collect_show_feedback.py"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def shows_on(d: str) -> list[dict]:
    rows = json.loads(ACT.read_text(encoding="utf-8")).get("rows") or []
    return [x for x in rows if str(x.get("date")) == d]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--slot", choices=["am", "pm"], default="pm")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    target = a.date or date.today().isoformat()
    if a.slot == "am" and not a.date:
        target = (date.today() - timedelta(days=1)).isoformat()  # 早上补的是昨天
    shows = shows_on(target)
    if not shows:
        log("%s 无已登记演出（slot=%s），跳过" % (target, a.slot))
        return 0

    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    key = "%s|%s" % (target, a.slot)
    if state.get(key):
        log("%s 已跑过（%s），跳过" % (key, state[key]))
        return 0

    cities = sorted({str(x.get("city") or "").strip() for x in shows if x.get("city")})
    log("%s 检出 %d 场：%s（slot=%s）" % (target, len(shows), "、".join(cities) or "城市待补", a.slot))
    for x in shows:
        city = str(x.get("city") or "").strip()
        if not city:
            continue
        title = str(x.get("title") or "").strip()
        cmd = [sys.executable, "-X", "utf8", str(COLLECT),
               "--date", target, "--city", city, "--skip-bili"]
        if title:
            cmd += ["--title", title]
        if a.dry:
            log("[dry] " + " ".join(cmd))
            continue
        log("开始收集：%s %s" % (city, title))
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        tail = (r.stdout or "")[-400:]
        log("完成 %s rc=%d%s" % (city, r.returncode, (" | " + tail.replace("\n", " ")) if tail else ""))

    if not a.dry:
        state[key] = datetime.now().strftime("%Y-%m-%d %H:%M")
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
