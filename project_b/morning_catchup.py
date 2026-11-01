"""开机补跑：早上 8:20 之后才开机时，把错过时间的任务补上

逻辑：查 Windows 计划任务的「上次运行时间」
  - 若不是今天，且现在已过它该跑的时刻 → 立即补跑
  - 是今天 → 跳过（不重复跑）
触发方式：登录时（wx409_morning_catchup，延迟 2 分钟）
"""
import datetime as dt
import subprocess
import sys

TASKS = [
    # (计划任务名, 该跑的时刻 HH:MM, 补跑命令)
    ("wx409_interview_daily", "08:20",
     [sys.executable, "-X", "utf8", r"D:\wx409.github.io\project_b\interview_daily.py"]),
    ("wx409_index_daily", "09:10",
     [r"D:\wx409.github.io\run_index_daily.bat"]),
    ("wx409_social_daily", "09:30",
     [r"D:\wx409.github.io\run_social_daily.bat"]),
    ("wx409_index_freshness", "09:40",
     [sys.executable, "-X", "utf8", r"D:\wx409.github.io\project_b\check_index_freshness.py"]),
    ("wx409_tour_pool_daily", "10:00",
     [sys.executable, "-X", "utf8", r"E:\wx\论文素材_王晰作传\音域分析\轨迹\补搜巡演曲目.py", "--limit", "12"]),
]

def last_run(task):
    try:
        r = subprocess.run(["schtasks", "/query", "/tn", task, "/fo", "list", "/v"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in (r.stdout or "").splitlines():
            if "上次运行时间" in line or "Last Run Time" in line:
                v = line.split(":", 1)[1].strip()
                for fmt in ("%Y/%m/%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
                    try:
                        return dt.datetime.strptime(v, fmt)
                    except Exception:
                        pass
    except Exception:
        pass
    return None

now = dt.datetime.now()
print("现在", now.strftime("%Y-%m-%d %H:%M"))
for name, hhmm, cmd in TASKS:
    h, m = map(int, hhmm.split(":"))
    due = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now < due:
        print("  未到点，跳过", name)
        continue
    lr = last_run(name)
    if lr and lr.date() == now.date():
        print("  今天已跑", name, lr.strftime("%H:%M"))
        continue
    print("  补跑", name, "（上次", lr.strftime("%Y-%m-%d %H:%M") if lr else "未知", "）")
    try:
        rc = subprocess.call(cmd, timeout=3600)
        print("    rc=%d" % rc)
    except Exception as e:
        print("    失败", type(e).__name__)
print("补跑检查结束")
