# -*- coding: utf-8 -*-
import subprocess, sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
py = sys.executable
steps = [
    "project_b/build_upcoming.py",
    "project_b/build_danmaku_timeline.py",
    "project_b/build_moments.py",
    "project_b/make_quote_cards.py",
    "project_b/build_content_calendar.py",
    "project_b/build_ammo.py",
    "project_b/build_llms_pages.py",
    "project_b/inject_analytics.py",
]
for s in steps:
    r = subprocess.run([py, "-X", "utf8", str(ROOT / s)], cwd=str(ROOT))
    print(s, "rc", r.returncode, flush=True)
files = ["data/upcoming.json", "data/danmaku_timeline.json", "data/moments.json", "data/content_calendar.json",
         "moments.html", "ammo.html", "assets/share/quotes"]
subprocess.run(["git", "-C", str(ROOT), "add"] + files)
r = subprocess.run(["git", "-C", str(ROOT), "commit", "-m", "自动刷新：瞬间库/金句卡/内容日历/弹药库"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("commit", r.returncode, (r.stdout or "").strip()[:120])
if r.returncode == 0:
    subprocess.run(["git", "-C", str(ROOT), "push", "origin", "main"])
