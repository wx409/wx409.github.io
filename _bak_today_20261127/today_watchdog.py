#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""today_watchdog.py —— 每天多次巡检「今日新入库」是否真跑过；失败则补跑并通知。

判据（不再只看 today.json 的 fresh 标记）：
  1. today.json 的 date 不是今天                → 补跑
  2. 抓取状态缺失 / ok 为假 / 超过 8 小时未更新 → 补跑
  3. bili_daily.json 的 generated_at 早于 4 小时 → 补跑（覆盖晚间投稿）
补跑链：bili_collect.py（多源采集 + 代表性筛选）→ bili_daily_ingest.py → build_today.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
TODAY = DATA / "today.json"
DAILY = DATA / "bili_daily.json"
STATUS = DATA / "bili_fetch_status.json"
sys.path.insert(0, str(ROOT / "project_b"))
import notify  # noqa

FETCH_MAX_AGE_H = 8
DAILY_MAX_AGE_H = 4


def run(script, *args):
    print("run", script, *args, flush=True)
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "project_b" / script), *args]
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def age_hours(stamp):
    """'2026-11-27 10:10' → 距今小时数；解析失败返回 999。"""
    try:
        return (datetime.now() - datetime.strptime(stamp, "%Y-%m-%d %H:%M")).total_seconds() / 3600.0
    except Exception:
        return 999.0


def main():
    today = date.today().isoformat()
    d = read_json(TODAY)
    daily = read_json(DAILY)
    st = read_json(STATUS)

    reasons = []
    if d.get("date") != today:
        reasons.append("today.json 日期是 " + str(d.get("date")))
    if not st:
        reasons.append("没有抓取状态文件")
    elif not st.get("ok"):
        reasons.append("上次抓取失败")
    elif age_hours(st.get("at") or "") > FETCH_MAX_AGE_H:
        reasons.append("抓取已超过 %d 小时未成功" % FETCH_MAX_AGE_H)
    if age_hours(daily.get("generated_at") or "") > DAILY_MAX_AGE_H:
        reasons.append("今日数据已超过 %d 小时未刷新" % DAILY_MAX_AGE_H)

    if not reasons:
        print("healthy", today, "| fetch", st.get("at"), "| daily", daily.get("generated_at"))
        return 0

    print("补跑原因：", "; ".join(reasons), flush=True)
    rc0 = run("bili_collect.py", "--download")
    rc1 = run("bili_daily_ingest.py")
    rc2 = run("build_today.py")
    ok = (rc0 == 0 and rc1 == 0 and rc2 == 0)
    if ok:
        notify.record("今日新入库已补跑",
                      "采集 rc=%s，入库 rc=%s，页面 rc=%s（%s）" % (rc0, rc1, rc2, today),
                      category="今日更新", source="today_watchdog")
        return 0
    notify.record("⚠ 今日新入库补跑失败",
                  "采集 rc=%s；入库 rc=%s；页面 rc=%s；原因：%s" % (rc0, rc1, rc2, "; ".join(reasons)),
                  category="运维告警", source="today_watchdog")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
