# -*- coding: utf-8 -*-
"""dashboard_watchdog.py —— 大屏 daemon 看门狗（进程消失→拉起 + 站内通知）

背景（2026-10-17 诊断）：`QQMusicDashboardAutoStart` 只在**登录时**启动；Windows Update
23:29 强制重启后无人登录 → daemon 15 小时未运行、大屏停更。本看门狗由计划任务
`wx409_dashboard_watchdog`（每 10 分钟）或 SYSTEM 启动任务调用，负责：
  1. 进程检查：命令行含 `QQ音乐大屏生成器` 的 python/pythonw 是否在跑；
  2. 不在 → 用 `pythonw` 拉起（绝对路径 + cwd=E:\\wx），记日志 + 站内通知；
  3. 顺带报告大屏数据文件的新鲜度（`D:\\wx409.github.io\\dashboard\\dashboard_data.json` mtime 距现在分钟数），
     仅当「进程在跑但数据 >120 分钟未更新」时再通知一次（防刷屏：同一状态 6 小时内只通知一次）。
  4. **不用外部服务**；通知复用 project_b/notify.py（本地表格 + notifications.html）。

用法：
  python -X utf8 project_b\\dashboard_watchdog.py            # 检查并在需要时拉起
  python -X utf8 project_b\\dashboard_watchdog.py --dry       # 只看不拉起
退出码：0＝无需动作/已拉起；1＝拉起失败
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
GEN_DIR = Path(r"E:\wx")
GEN = GEN_DIR / "QQ音乐大屏生成器_GEO优化版_源码.py"
PYW = Path(r"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\pythonw.exe")
DATA = SITE / "dashboard" / "dashboard_data.json"
STATE = SITE / "temp" / "dashboard_watchdog_state.json"
LOG = SITE / "temp" / "dashboard_watchdog.log"
MARK = "QQ音乐大屏生成器"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def notify(title: str, body: str) -> None:
    try:
        sys.path.insert(0, str(SITE / "project_b"))
        import notify as n
        n.record(title, body)
        log("已写站内通知")
    except Exception as e:
        log(f"站内通知失败（不致命）：{e}")


def find_daemon() -> list[int]:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' "
                            "-and $_.Name -match 'python' } | Select-Object -ExpandProperty ProcessId" % MARK],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore")
        return [int(x) for x in (r.stdout or "").split() if x.strip().isdigit()]
    except Exception as e:
        log(f"进程查询失败：{e}")
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    s = state()
    pids = find_daemon()
    age = None
    if DATA.exists():
        age = round((datetime.now() - datetime.fromtimestamp(DATA.stat().st_mtime)).total_seconds() / 60, 1)

    if pids:
        log(f"daemon 在运行（PID {pids}）；dashboard_data.json 距上次更新 {age} 分钟")
        if age is not None and age > 120:
            key = "stale"
            if s.get(key) != datetime.now().strftime("%Y-%m-%d %H"):
                # 同一状态每小时最多通知一次
                notify("⚠ 大屏数据超过 120 分钟未更新",
                       f"daemon 进程在（PID {pids}），但 dashboard_data.json 已 {age} 分钟未更新。"
                       "可能正在全量采集（约 4 分钟）或卡住，请查看 E:\\wx\\qqmusic_dp_edge.log。")
                s[key] = datetime.now().strftime("%Y-%m-%d %H")
                save(s)
        return 0

    log("daemon **不在运行**")
    if a.dry:
        log("（dry）不拉起")
        return 0
    if not GEN.exists() or not PYW.exists():
        log(f"[X] 缺文件：GEN={GEN.exists()} PYW={PYW.exists()}")
        notify("⚠ 大屏 daemon 拉起失败（缺文件）", f"GEN 存在={GEN.exists()}；pythonw 存在={PYW.exists()}")
        return 1
    try:
        p = subprocess.Popen([str(PYW), str(GEN)], cwd=str(GEN_DIR),
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log(f"已拉起 daemon（PID {p.pid}）")
        notify("🔄 大屏 daemon 已被看门狗拉起",
               f"检测到 daemon 不在运行，已用 pythonw 拉起（PID {p.pid}）。"
               f"此前 dashboard_data.json 距上次更新 {age} 分钟。")
        s["last_restart"] = datetime.now().isoformat(timespec="seconds")
        save(s)
        return 0
    except Exception as e:
        log(f"[X] 拉起失败：{e}")
        notify("⚠ 大屏 daemon 拉起失败", f"错误：{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
