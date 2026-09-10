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
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")  # 指数长表（供新鲜度校验）
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


# ---------------------------------------------------------------- 长表新鲜度
def newest_dayfile_date() -> dt.date | None:
    """增补数据库里最新的日档案日期（文件名 YYYY.MM.DD.xlsx）。"""
    if not ADDON_DIR.is_dir():
        return None
    days = []
    for p in ADDON_DIR.glob("*.xlsx"):
        try:
            days.append(dt.date(*[int(x) for x in p.stem.split(".")[:3]]))
        except Exception:
            continue
    return max(days) if days else None


def long_table_scan(window_days: int = 8) -> dict:
    """扫描长表：返回最新日期 + **最近窗口内的内部空洞**。

    为什么查空洞：只看"最新日期滞后几天"会漏掉**中间缺一天**的情形
    （例：修正映射下若缺 2026.09.09.xlsx，则 2026-09-08 一直缺，但最新日期照常前进）。
    """
    if not LONG_CSV.exists():
        return {"max": None, "gaps": []}
    dates: set[str] = set()
    try:
        import csv
        with open(LONG_CSV, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                d = (r.get("date") or "").strip()
                if d:
                    dates.add(d)
    except Exception:
        return {"max": None, "gaps": []}
    if not dates:
        return {"max": None, "gaps": []}
    mx = max(dates)
    mn = min(dates)
    mxd = dt.date.fromisoformat(mx)
    mnd = dt.date.fromisoformat(mn)
    # 窗口不越过长表起点（否则会把"数据开始之前"误报成缺失）
    window = []
    for k in range(1, window_days):
        d = mxd - dt.timedelta(days=k)
        if d < mnd:
            break
        window.append(d.isoformat())
    return {"max": mxd, "gaps": [d for d in window if d not in dates]}


def long_table_max_day() -> dt.date | None:
    """指数长表里最新的日期。"""
    return long_table_scan()["max"]


# ---------------------------------------------------------------- 守护进程状态
def _ps_int(cmd: str, timeout: int = 40) -> int | None:
    """跑一段 PowerShell 并取整数结果；失败/非数字返回 None。"""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        return int(out) if out.isdigit() else None
    except Exception:
        return None


def daemon_process_present() -> tuple[bool | None, str]:
    """守护进程是否在运行 —— **多信号合成**，任一信号显示"存在"即判存活。

    返回 (True/False/None, 说明)；None = 所有探测手段都不可用。

    信号：
      1. CIM 查 Win32_Process 命令行含守护进程源码名（最权威，但受限会话可能不完整 —— 
         沙箱里实测会返回 0 条而不是报错，所以**不能单独采信**）
      2. Get-Process pythonw 计数（守护进程以 pythonw 常驻；本机仅守护进程用 pythonw）
      3. tasklist 命中 pythonw

    教训（2026-09-10）：① 日志 mtime 不能当存活判据（守护进程 08:30→11:49 这类空档
    日志长时间不写）；② 单信号"0 个进程"不能当死亡判据，否则会重复拉起实例
    （当天真发生过一次：误判 → 起了第二个 pythonw）。
    """
    signals: list[tuple[str, bool | None, str]] = []

    n_cim = _ps_int("(Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' or Name='python.exe'\" "
                    "-ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*QQ音乐大屏生成器*' } "
                    "| Measure-Object).Count")
    n_pw = _ps_int("(Get-Process pythonw -ErrorAction SilentlyContinue | Measure-Object).Count", timeout=30)
    try:
        r = subprocess.run(["tasklist", "/fi", "imagename eq pythonw.exe", "/fo", "csv", "/nh"],
                           capture_output=True, text=True, timeout=20)
        hit = "pythonw" in (r.stdout or "").lower()
        n_tl: bool | None = True if hit else (False if r.returncode == 0 else None)
    except Exception:
        n_tl = None

    cim = None if n_cim is None else n_cim > 0
    pw = None if n_pw is None else n_pw > 0
    signals += [("CIM命令行匹配", cim, "匹配 %s 个" % ("?" if n_cim is None else n_cim)),
                ("pythonw计数", pw, "pythonw %s 个" % ("?" if n_pw is None else n_pw)),
                ("tasklist", n_tl, "命中" if n_tl else ("未命中" if n_tl is False else "不可用"))]

    detail = "；".join("%s=%s(%s)" % (k, {True: "在", False: "无", None: "?"}[v], d)
                       for k, v, d in signals)

    # 任一信号显示"存在" → 存活（保守，避免重复实例）
    if cim or pw or (n_tl is True):
        return True, detail
    # 两个**可靠**信号（CIM 命令行 + pythonw 计数）都判"无" → 认定无进程
    if cim is False and pw is False:
        return False, detail
    # 其余（可靠信号不可用）→ 未知，调用方保守处理
    return None, detail


def daemon_alive(stall_min: int) -> tuple[bool, str]:
    """存活判定：**进程存在 = 存活**（优先）；只有确认无进程时，才用日志新鲜度兜底。"""
    log_age = None
    try:
        if DAEMON_LOG.exists():
            log_age = (now() - dt.datetime.fromtimestamp(DAEMON_LOG.stat().st_mtime)).total_seconds() / 60
    except Exception:
        pass
    age_txt = ("%.1f 分钟前" % log_age) if log_age is not None else "不可读"

    present, why = daemon_process_present()
    if present is True:
        return True, "进程存在（%s）；日志 %s" % (why, age_txt)
    if present is False:
        if log_age is not None and log_age <= stall_min:
            return True, "无进程但日志 %s 刚写过（可能刚退出）" % age_txt
        return False, "无进程（%s）；日志 %s" % (why, age_txt)
    # 探测不可用 → 保守视为存活，宁可漏补也不重复拉起实例
    return True, "探测不可用（%s），保守视为存活；日志 %s" % (why, age_txt)


def start_daemon(allow_direct_spawn: bool = False) -> bool:
    """拉起守护进程：只走计划任务（Task Scheduler 的 IgnoreNew 天然防重复实例）。

    直接 pythonw 启动仅在前一层失败且显式给出 --allow-direct-spawn 时使用 ——
    否则在"其实还活着、只是日志没更新"的情况下会造出第二个实例，两边同时抓取、
    同时重建看板甚至同时 push。
    """
    present, why = daemon_process_present()
    if present is True:
        log("守护进程已在运行（%s），跳过拉起" % why)
        return True

    try:
        r = subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            log("已通过计划任务拉起守护进程: %s" % TASK_NAME)
            return True
        log("schtasks /Run 失败(%s): %s" % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
    except Exception as e:
        log("schtasks /Run 异常: %s" % e)

    if not allow_direct_spawn:
        log("跳过直接 pythonw 拉起（需要 --allow-direct-spawn 才允许；"
            "直接拉起不经过计划任务，易造成重复实例）")
        return False
    present2, why2 = daemon_process_present()
    if present2 is not False:
        log("直接拉起前复查：%s → 放弃（避免重复实例）" % why2)
        return False
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
    ap.add_argument("--no-catchup", action="store_true",
                    help="只拉起守护进程+告警，不在此进程内补跑（供 auto_update 调用，避免超时）")
    ap.add_argument("--allow-direct-spawn", action="store_true",
                    help="计划任务拉起失败时允许直接 pythonw 启动（默认禁止，避免重复实例）")
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
                start_daemon(args.allow_direct_spawn)
                if args.no_catchup:
                    action = "start_daemon"
                    catch_note = "已拉起守护进程；本次不补跑（--no-catchup，交由守护进程自行执行下一批）"
                    log(catch_note)
                else:
                    catch_ok, catch_note = catch_up(
                        last_mode,
                        args.full_timeout if last_mode == "full" else args.quick_timeout,
                        dry=False)
                    action = "start_daemon+%s" % ("full" if last_mode == "full" else "quick")
                    if catch_ok:
                        st.setdefault("done", {})[key] = now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                action = "check-only"
                catch_note = "dry-run"
        elif args.force and not args.check_only and not args.no_catchup:
            catch_ok, catch_note = catch_up(
                last_mode,
                args.full_timeout if last_mode == "full" else args.quick_timeout,
                dry=False)
            action = "force+%s" % ("full" if last_mode == "full" else "quick")
        else:
            action = "alert-only"

        # 告警门槛：只在"严重"时打扰 —— 守护进程停摆 / 缺全量批次 / 单日缺≥3批。
        # 单个极速批次因前一批超时被跳过属正常（如启动重建吃掉 8:05），只写日志。
        critical = (not alive) or any(m == "full" for _, m in missing) or len(missing) >= 3
        alerted = st.setdefault("alerts", {})
        akey = "missed|%s" % today.isoformat()
        if critical and not alerted.get(akey):
            detail = "\n".join("缺 %s %s" % (s, m) for s, m in missing)
            notify("⚠️ 大屏采集漏批：%s" % today.isoformat(),
                   "应当完成但缺产出的批次：\n%s\n\n守护进程判定：%s（%s）\n处置：%s %s\n"
                   "排查：E:\\wx\\qqmusic_dp_edge.log / logs\\watchdog_%s.log"
                   % (detail, alive, alive_why, action, catch_note,
                      today.strftime("%Y%m%d")))
            alerted[akey] = now().strftime("%Y-%m-%d %H:%M:%S")
        elif missing and not critical:
            log("漏批未达告警门槛（非全量、少于3批、守护进程存活）→ 只记日志")

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

    # 长表新鲜度校验（2026-09-10 新增）
    # 修正映射口径：长表最新日期 应 == 最新日档案日期 − 1。滞后 >1 天说明
    # "日档案已更新但长表/基线没跟着刷" —— 这正是 deploy_all 步骤里缺的那一环。
    nf = newest_dayfile_date()
    scan = long_table_scan()
    lt = scan["max"]
    gaps = scan["gaps"]
    lag = (nf - lt).days if (nf and lt) else None
    fresh_ok = (lag is not None and lag <= 1)
    if lag is None:
        log("长表新鲜度：无法判定（日档案或长表不可读）")
    elif fresh_ok:
        log("✓ 长表新鲜度：长表最新 %s ｜ 日档案最新 %s ｜ 滞后 %d 天"
            % (lt.isoformat(), nf.isoformat(), lag))
    else:
        log("✗ 长表滞后 %d 天（长表最新 %s ｜ 日档案最新 %s）→ 需跑指数长表+基线刷新"
            % (lag, lt.isoformat(), nf.isoformat()))
        akey = "longtable|%s" % today.isoformat()
        if not st.setdefault("alerts", {}).get(akey):
            notify("⚠️ 指数长表滞后 %d 天" % lag,
                   "长表最新 %s，但日档案最新 %s（期望长表到 %s）。\n"
                   "原因：deploy_all 步骤里没有指数长表/基线刷新 —— 请运行\n"
                   "  python project_b\\refresh_index_baseline.py --force\n"
                   "（或操作中心 64 → 45/44）"
                   % (lt.isoformat(), nf.isoformat(), (nf - dt.timedelta(days=1)).isoformat()))
            st["alerts"][akey] = now().strftime("%Y-%m-%d %H:%M:%S")

    # 内部空洞（只滞后看不出来：缺的那天在最新日期之前）
    if gaps:
        log("✗ 长表最近窗口内缺 %d 天: %s" % (len(gaps), "、".join(gaps)))
        akey = "longtable_gap|%s" % today.isoformat()
        if not st.setdefault("alerts", {}).get(akey):
            notify("⚠️ 指数长表有缺口：%s" % "、".join(gaps),
                   "长表最新 %s，但下列日期没有数据：%s\n"
                   "最常见原因：那一天的日档案缺失（当日 23:55 全量未执行），"
                   "而修正映射下该天的官方值只能由「次日」日档案提供。\n\n"
                   "处理：① 若有备份，把对应的 YYYY.MM.DD.xlsx 拷进\n"
                   "     E:\\wx\\指数数据库\\增补数据库2025.2.22-\\ ；\n"
                   "   ② 找不到备份时，用准终值备用：\n"
                   "     python project_b\\extract_fallback_day.py --date <缺的日期> --install-as-day <次日日期>\n"
                   "   ③ 之后跑 python project_b\\refresh_index_baseline.py --force"
                   % (lt.isoformat() if lt else "?", "、".join(gaps)))
            st["alerts"][akey] = now().strftime("%Y-%m-%d %H:%M:%S")
        fresh_ok = False
    else:
        log("✓ 长表最近窗口无缺口")

    save_state(st)
    out = {"date": today.isoformat(), "schedule_source": src, "due": len(due),
           "missing": [{"slot": s, "mode": m} for s, m in missing],
           "daemon_alive": alive, "daemon_reason": alive_why,
           "action": action, "catch_up_ok": catch_ok, "catch_up_note": catch_note,
           "yesterday_dayfile_ok": y_ok,
           "long_table_max": lt.isoformat() if lt else None,
           "newest_dayfile": nf.isoformat() if nf else None,
           "long_table_lag_days": lag, "long_table_fresh": fresh_ok,
           "long_table_gaps": gaps}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    log("结果: %s" % json.dumps({k: out[k] for k in
                                 ("missing", "action", "catch_up_ok", "yesterday_dayfile_ok",
                                  "long_table_lag_days", "long_table_gaps")},
                                ensure_ascii=False))
    return 1 if (missing or not y_ok or not fresh_ok) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 看门狗自身异常必须显式暴露
        print("[watchdog] 异常: %s" % e, file=sys.stderr)
        sys.exit(2)
