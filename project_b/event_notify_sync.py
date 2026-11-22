#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""event_notify_sync.py —— 把近期/未来演出写入“演出动态”通知（避免只有孤零零一条）"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
import notify  # noqa

ACT = ROOT / "data" / "activity_master.json"
STATE = ROOT / "temp" / "event_notify_state.json"
NOTI = ROOT / "data" / "notifications.json"


def main():
    rows = json.loads(ACT.read_text(encoding="utf-8")).get("rows") or []
    today = date.today()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    existing = ""
    try:
        items = json.loads(NOTI.read_text(encoding="utf-8")).get("items") or []
        existing = [x for x in items if x.get("category") == "演出动态"]
    except Exception:
        existing = []
    n = 0
    for x in rows:
        ds = str(x.get("date") or "")[:10]
        city = str(x.get("city") or "")
        title = str(x.get("title") or "")
        try:
            d = date.fromisoformat(ds)
        except Exception:
            continue
        if not (today - timedelta(days=30) <= d <= today + timedelta(days=90)):
            continue
        key = "%s|%s|%s" % (ds, city, title[:20])
        if state.get(key):
            continue
        if any((ds in (it.get("title") or "") and city in (it.get("title") or "")) for it in existing):
            state[key] = True
            continue
        content = "%s｜%s｜%s\n%s" % (ds, city, x.get("kind") or "", (x.get("note") or "")[:300])
        notify.record("📣 演出：%s %s · %s" % (ds, city, title[:40]),
                      content, category="演出动态", source="activity_master")
        state[key] = True
        n += 1
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print("新增演出动态", n)


if __name__ == "__main__":
    raise SystemExit(main())
