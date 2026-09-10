# -*- coding: utf-8 -*-
"""watchdog_batches.py —— 大屏采集批次漏批看门狗（自愈 + 告警）

背景（2026-09-09 事故）：
    Windows 更新编排器在 19:29 自动重启电脑（活动时间 08:00-19:00 刚结束），
    重启后无人登录 → 登录态计划任务全部停摆：
      · 守护进程 QQMusicDashboardAutoStart（登录触发）被杀
      · 大屏自身 20:30 / 21:00 / 21:30 极速 + 23:15 / 23:55 全量 全部错过
      · auto_update 21:00 / 次日 00:03 未跑
    结果：增补数据库缺 2026.09.09.xlsx，站点数据停在 9/9 19:21 批次。

本脚本解决"事后无人知晓 + 不自动补"：
    1. 按守护进程源码里的 SCHEDULE 反推"此刻应当已完成的批次"；
    2. 检查产出文件是否落地（指数vs / 增补数据库）；
    3. 若缺失且守护进程已停摆 → 先拉起守护进程，再补跑一次（full 优先）；
    4. 无论补跑成功与否，都写 logs/watchdog_YYYYMMDD.log + 本地通知表告警；
    5. 日终校验：昨天该有的 增补数据库\\YYYY.MM.DD.xlsx 是否生成。

安全设计（不会和正在跑的守护进程打架）：
    · 若 E:\\wx\\qqmusic_dp_edge.log 在最近 --stall-min 分钟内被写过，判定"守护进程活着"，
      只告警、不补跑（避免两个实例同时抓取）；
    · 同一 (日期, 批次) 只补跑一次，状态落 logs/watchdog_state.json（幂等）。

用法：
    python project_b\\watchdog_batches.py                # 正常巡检（可自愈）
    python project_b\\watchdog_batches.py --check-only    # 只查不动（调试/审计）
    python project_b\\watchdog_batches.py --force         # 忽略"守护进程活着"的判定
    python project_b\\watchdog_batches.py --json          # 输出机器可读结果

退出码：0 = 正常；1 = 存在漏批（便于计划任务/CI 观察）；2 = 脚本自身异常。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
STATE = LOGS / "watchdog_state.json"

DAEMON_SRC = Path(r"E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py")
DAEMON_LOG = Path(r"E:\wx\qqmusic_dp_edge.log")
QUICK_DIR = Path(r"E:\wx\指数vs")                       # 极速/非 23:55 全量产出
ADDON_DIR = Path(r"E:\wx\指数数据库\增补数据库2025.2.22-")  # 23:55 全量产出（日档案）
DOWNLOAD_DIR = Path(r"E:\wx\download")                  # 23:55 全量第二落点
TASK_NAME = "QQMusicDashboardAutoStart"

# 守护进程源码解析失败时的兜底（与源码 SCHEDULE 保持一致）
FALLBACK_SCHEDULE = [
    ("8:05", "quick"), ("8:15", "quick"), ("8:25", "quick"),
    ("11:49", "quick"), ("11:59", "quick"), ("12:18", "quick"),
    ("13:09", "quick"),
    ("18:05", "quick"), ("18:15", "quick"), ("18:25", "quick"),
    ("18:39", "quick"), ("18:45", "quick"), ("18:55", "quick"),
    ("19:21", "quick"), ("20:30", "quick"),
    ("21:00", "quick"), ("21:30", "quick"),
    ("23:15", "full"), ("23:55", "full"),
]


# ---------------------------------------------------------------- 基础工具
def now() -> dt.datetime:
    return dt.datetime.now()


def _safe_print(s: str) -> None:
    """控制台可能是 GBK 代码页，✓/✗ 等字符会抛 UnicodeEncodeError —— 降级为替换字符，绝不中断。"""
    try:
        print(s)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "gbk"
        print(s.encode(enc, "replace").decode(enc, "replace"))


def log(msg: str) -> None:
    ts = now().strftime("%H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    _safe_print(line)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / ("watchdog_%s.log" % dt.date.today().strftime("%Y%m%d")),
              "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"done": {}, "alerts": {}}


def save_state(st: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    st["updated_at"] = now().strftime("%Y-%m-%d %H:%M:%S")
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


QUIET = False


def notify(title: str, content: str) -> None:
    if QUIET:
        log("(quiet) 跳过通知: %s" % title)
        return
    try:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify as nf
        nf.send(title, content, category="运维告警")
    except Exception as e:  # 通知失败不影响主流程
        log("notify 失败: %s" % e)


# ---------------------------------------------------------------- 调度表
def read_schedule() -> tuple[list[tuple[str, str]], str]:
    """从守护进程源码解析 SCHEDULE，避免两处口径漂移。"""
    try:
        src = DAEMON_SRC.read_text(encoding="utf-8", errors="ignore")
        block = re.search(r"SCHEDULE\s*=\s*\[(.*?)\]", src, re.S)
        if block:
            pairs = re.findall(r'\(\s*"(\d{1,2}:\d{2})"\s*,\s*"(\w+)"\s*\)', block.group(1))
            if len(pairs) >= 5:
                return [(t, m) for t, m in pairs], str(DAEMON_SRC)
    except Exception as e:
        log("解析守护进程 SCHEDULE 失败，改用兜底表: %s" % e)
    return FALLBACK_SCHEDULE, "fallback"


def slot_time(t_str: str, day: dt.date) -> dt.datetime:
    h, m = t_str.split(":")
    return dt.datetime.combine(day, dt.time(int(h), int(m)))


# ---------------------------------------------------------------- 产出判定
def _mins(t_str: str) -> int:
    h, m = t_str.split(":")
    return int(h) * 60 + int(m)


def _file_minutes(p: Path) -> int | None:
    """从文件名尾部 _HHMM[_c][_quick].xlsx 解析运行时刻（分钟）。"""
    m = re.search(r"_(\d{4})(?:_\d+)?(?:_quick)?\.xlsx$", p.name)
    if not m:
        return None
    hhmm = int(m.group(1))
    return (hhmm // 100) * 60 + (hhmm % 100)


def collect_day_outputs(day: dt.date) -> list[dict]:
    """收集当日全部产出文件（指数vs + 日档案），带运行时刻。"""
    out: list[dict] = []
    stamp = day.strftime("%Y.%m.%d")
    if QUICK_DIR.is_dir():
        for p in sorted(QUICK_DIR.glob(stamp + "*.xlsx")):
            mins = _file_minutes(p)
            if mins is None:
                continue
            out.append({"path": p, "min": mins,
                        "mode": "quick" if p.name.endswith("_quick.xlsx") else "full"})
    for d in (ADDON_DIR, DOWNLOAD_DIR):  # 23:55 日档案（无时刻后缀，视为 23:55）
        p = d / (stamp + ".xlsx")
        if p.exists():
            out.append({"path": p, "min": 23 * 60 + 55, "mode": "full", "daily": True})
    return out


def match_slots(due: list[tuple[str, str]], files: list[dict],
                tol_min: int = 15) -> dict[str, dict]:
    """就近唯一匹配：按"时刻差最小"全局排序认领，避免相邻批次互相顶替。

    返回 {slot: {"ok":bool, "file":Path|None}}。
    """
    res: dict[str, dict] = {t: {"ok": False, "file": None} for t, _ in due}
    pairs = []
    for t_str, mode in due:
        target = _mins(t_str)
        for f in files:
            if f["mode"] != mode:
                continue
            gap = abs(f["min"] - target)
            if gap <= tol_min:
                pairs.append((gap, t_str, f))
    used: set[str] = set()
    for gap, t_str, f in sorted(pairs, key=lambda x: (x[0], x[1])):
        if res[t_str]["ok"] or str(f["path"]) in used:
            continue
        res[t_str] = {"ok": True, "file": f["path"]}
        used.add(str(f["path"]))
    return res


# ---------------------------------------------------------------- 守护进程状态
def daemon_alive(stall_min: int) -> tuple[bool, str]:
    """守护进程是否在活跃工作：日志 mtime + pythonw 进程双重判据。"""
    log_age = None
    try:
        if DAEMON_LOG.exists():
            log_age = (now() - dt.datetime.fromtimestamp(DAEMON_LOG.stat().st_mtime)).total_seconds() / 60
    except Exception:
        pass
    proc = False
    try:
        r = subprocess.run(["tasklist", "/fi", "imagename eq pythonw.exe", "/fo", "csv", "/nh"],
                           capture_output=True, text=True, timeout=20)
        proc = "pythonw" in (r.stdout or "").lower()
    except Exception:
        pass
    if log_age is not None and log_age <= stall_min:
        return True, "日志 %.1f 分钟前有写入" % log_age
    if proc and log_age is not None and log_age <= stall_min * 4:
        return True, "pythonw 存在且日志 %.1f 分钟前有写入" % log_age
    return False, "pythonw=%s 日志%s" % (proc, ("%.0f 分钟前" % log_age) if log_age is not None else "不可读")


def start_daemon() -> bool:
    """拉起守护进程：优先走计划任务，失败则直接 pythonw 启动源码。"""
    try:
        r = subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            log("已通过计划任务拉起守护进程: %s" % TASK_NAME)
            return True
        log("schtasks /Run 失败(%s): %s" % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
    except Exception as e:
        log("schtasks /Run 异常: %s" % e)
    try:
        pyw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pyw if pyw.exists() else sys.executable)
        creation = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen([exe, str(DAEMON_SRC)], cwd=str(DAEMON_SRC.parent),
                         creationflags=creation, close_fds=True)
        log("已直接启动守护进程: %s %s" % (exe, DAEMON_SRC))
        return True
    except Exception as e:
        log("直接启动守护进程失败: %s" % e)
        return False


# ---------------------------------------------------------------- 补跑
def catch_up(mode: str, timeout_min: int, dry: bool) -> tuple[bool, str]:
    """调用守护进程 --once 补跑一次。返回 (成功, 摘要)。"""
    if dry:
        return False, "dry-run（未执行）"
    cmd = [sys.executable, str(DAEMON_SRC), "--once", "--full" if mode == "full" else "--quick"]
    log("补跑执行: %s" % " ".join(cmd))
    try:
        r = subprocess.run(cmd, cwd=str(DAEMON_SRC.parent), capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=timeout_min * 60)
        tail = (r.stdout or r.stderr or "").strip().splitlines()[-6:]
        ok = r.returncode == 0
        log("补跑结束 returncode=%s | %s" % (r.returncode, " / ".join(tail)))
        return ok, "returncode=%s" % r.returncode
    except subprocess.TimeoutExpired:
        log("补跑超时（%d 分钟）" % timeout_min)
        return False, "超时"
    except Exception as e:
        log("补跑异常: %s" % e)
        return False, str(e)


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="只巡检不补跑")
    ap.add_argument("--force", action="store_true", help="忽略守护进程存活判定，强制补跑")
    ap.add_argument("--stall-min", type=int, default=12, help="守护进程日志多久没写视为停摆（分钟）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 结果")
    ap.add_argument("--quick-timeout", type=int, default=20, help="极速补跑超时（分钟）")
    ap.add_argument("--full-timeout", type=int, default=40, help="全量补跑超时（分钟）")
    ap.add_argument("--quiet", action="store_true", help="不写站内通知（仅日志）")
    args = ap.parse_args()

    global QUIET
    QUIET = args.quiet

    schedule, src = read_schedule()
    today = dt.date.today()
    n = now()
    due = [(t, m) for t, m in schedule if slot_time(t, today) <= n]
    files = collect_day_outputs(today)
    matched = match_slots(due, files)
    results, missing = [], []
    for t_str, mode in due:
        hit = matched.get(t_str, {"ok": False, "file": None})
        results.append({"slot": t_str, "mode": mode, "ok": hit["ok"],
                        "file": (hit["file"].name if hit["file"] else None)})
        if not hit["ok"]:
            missing.append((t_str, mode))

    log("巡检 %s | 调度源=%s | 今日应完成 %d 个批次，缺 %d 个"
        % (today.isoformat(), "源码" if src != "fallback" else "兜底", len(due), len(missing)))
    for r in results:
        if not r["ok"]:
            log("  ✗ 缺批次 %s %s" % (r["slot"], r["mode"]))
        else:
            log("  ✓ %s %s → %s" % (r["slot"], r["mode"], r["file"]))

    st = load_state()
    action = "none"
    catch_ok, catch_note = False, ""
    alive, alive_why = daemon_alive(args.stall_min)

    if missing:
        last_slot, last_mode = missing[-1]
        key = "%s|%s" % (today.isoformat(), last_slot)
        log("最近缺失批次: %s %s | 守护进程存活判定=%s（%s）"
            % (last_slot, last_mode, alive, alive_why))
        if not alive:
            if not args.check_only:
                start_daemon()
                catch_ok, catch_note = catch_up(
                    last_mode,
                    args.full_timeout if last_mode == "full" else args.quick_timeout,
                    dry=args.check_only)
                action = "start_daemon+%s" % ("full" if last_mode == "full" else "quick")
                if catch_ok:
                    st.setdefault("done", {})[key] = now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                action = "check-only"
                catch_note = "dry-run"
        elif args.force and not args.check_only:
            catch_ok, catch_note = catch_up(
                last_mode,
                args.full_timeout if last_mode == "full" else args.quick_timeout,
                dry=False)
            action = "force+%s" % ("full" if last_mode == "full" else "quick")
        else:
            action = "alert-only"

        # 告警（同一天只报一次，避免同一批缺失被反复提醒）
        alerted = st.setdefault("alerts", {})
        akey = "missed|%s" % today.isoformat()
        if not alerted.get(akey):
            detail = "\n".join("缺 %s %s" % (s, m) for s, m in missing)
            notify("⚠️ 大屏采集漏批：%s" % today.isoformat(),
                   "应当完成但缺产出的批次：\n%s\n\n守护进程判定：%s（%s）\n处置：%s %s\n"
                   "排查：E:\\wx\\qqmusic_dp_edge.log / logs\\watchdog_%s.log"
                   % (detail, alive, alive_why, action, catch_note,
                      today.strftime("%Y%m%d")))
            alerted[akey] = now().strftime("%Y-%m-%d %H:%M:%S")

    # 日终校验：昨天的日档案是否落地（23:55 全量）
    yest = today - dt.timedelta(days=1)
    y_file = ADDON_DIR / (yest.strftime("%Y.%m.%d") + ".xlsx")
    y_ok = y_file.exists()
    if not y_ok:
        log("✗ 昨日日档案缺失: %s（该日官方指数仍可由今日全量的『昨日音乐指数』列回补）" % y_file.name)
        akey = "dayfile|%s" % yest.isoformat()
        if not st.setdefault("alerts", {}).get(akey):
            notify("⚠️ 指数日档案缺失：%s" % yest.isoformat(),
                   "缺 %s\n说明：该日 23:55 全量批次未执行（多为机器重启后无人登录）。\n"
                   "该日官方指数仍可由次日全量的『昨日音乐指数』列回补，但当日实时收听峰值不可恢复。"
                   % y_file)
            st["alerts"][akey] = now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        log("✓ 昨日日档案存在: %s" % y_file.name)

    save_state(st)
    out = {"date": today.isoformat(), "schedule_source": src, "due": len(due),
           "missing": [{"slot": s, "mode": m} for s, m in missing],
           "daemon_alive": alive, "daemon_reason": alive_why,
           "action": action, "catch_up_ok": catch_ok, "catch_up_note": catch_note,
           "yesterday_dayfile_ok": y_ok}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    log("结果: %s" % json.dumps({k: out[k] for k in
                                 ("missing", "action", "catch_up_ok", "yesterday_dayfile_ok")},
                                ensure_ascii=False))
    return 1 if (missing or not y_ok) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 看门狗自身异常必须显式暴露
        print("[watchdog] 异常: %s" % e, file=sys.stderr)
        sys.exit(2)
