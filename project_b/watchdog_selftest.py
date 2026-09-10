# -*- coding: utf-8 -*-
"""watchdog_selftest.py —— 漏批看门狗自测（不触碰真实状态、不启动/不补跑真实批次）

验证四件事：
  1. 调度表解析：能从守护进程源码读出 SCHEDULE（含 full/quick 两类）
  2. 文件名时刻解析：`2026.09.09_1921_quick.xlsx` → 19:21
  3. 就近唯一匹配：相邻批次不会互相顶替，缺批能被准确识别
  4. 自愈分支：
     · 守护进程"停摆"时 → 先 start_daemon()，再按最新缺失批次的模式 catch_up()
     · --no-catchup 时 → 只 start_daemon()，不 catch_up()
     · 守护进程"存活"时 → 既不拉起也不补跑（避免与正在跑的实例打架）

用法：python project_b\\watchdog_selftest.py      # 退出码 0=全部通过
"""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watchdog_batches as w  # noqa: E402

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))


def test_schedule():
    sched, src = w.read_schedule()
    modes = {m for _t, m in sched}
    check("调度表解析", len(sched) >= 15 and modes == {"quick", "full"},
          "%d 个批次；模式=%s；来源=%s" % (len(sched), sorted(modes), "源码" if src != "fallback" else "兜底"))


def test_file_minutes():
    cases = {
        "2026.09.09_1921_quick.xlsx": 19 * 60 + 21,
        "2026.09.09_2315.xlsx": 23 * 60 + 15,
        "2026.09.08.xlsx": None,
        "2026.09.09_1921_2.xlsx": 19 * 60 + 21,
    }
    ok = True
    detail = []
    for name, want in cases.items():
        got = w._file_minutes(Path(name))
        detail.append("%s→%s" % (name, got))
        if got != want:
            ok = False
    check("文件名时刻解析", ok, "；".join(detail))


def test_matching():
    # 构造：8:05 无产出、8:15 与 8:25 各有产出（模拟"某批被跳过"的真实情形）
    files = [
        {"path": Path("E:/x/2026.09.10_0815_quick.xlsx"), "min": 8 * 60 + 15, "mode": "quick"},
        {"path": Path("E:/x/2026.09.10_0825_quick.xlsx"), "min": 8 * 60 + 25, "mode": "quick"},
        {"path": Path("E:/x/2026.09.10.xlsx"), "min": 23 * 60 + 55, "mode": "full", "daily": True},
    ]
    due = [("8:05", "quick"), ("8:15", "quick"), ("8:25", "quick"), ("23:15", "full"), ("23:55", "full")]
    m = w.match_slots(due, files)
    check("就近唯一匹配：8:05 不冤枉、8:15/8:25 各归其位",
          (not m["8:05"]["ok"]) and m["8:15"]["file"].name == "2026.09.10_0815_quick.xlsx"
          and m["8:25"]["file"].name == "2026.09.10_0825_quick.xlsx",
          "8:05=%s 8:15=%s 8:25=%s" % (m["8:05"]["ok"], m["8:15"]["file"].name if m["8:15"]["file"] else None,
                                        m["8:25"]["file"].name if m["8:25"]["file"] else None))
    check("23:55 日档案可被认领、23:15 无产出判缺",
          m["23:55"]["ok"] and not m["23:15"]["ok"])


def run_watchdog(argv, alive, no_catchup_expected):
    """在打桩环境下跑一次 main()，返回调用记录。"""
    calls = {"start": 0, "catch": [], "notify": 0}
    orig = {
        "daemon_alive": w.daemon_alive,
        "start_daemon": w.start_daemon,
        "catch_up": w.catch_up,
        "collect_day_outputs": w.collect_day_outputs,
        "notify": w.notify,
        "STATE": w.STATE,
        "QUIET": w.QUIET,
    }
    tmp = Path(tempfile.mkdtemp()) / "state.json"
    try:
        w.STATE = tmp
        w.collect_day_outputs = lambda day: []          # 今天所有批次都"缺"
        w.daemon_alive = lambda stall: (alive, "selftest")

        def _start(allow_direct_spawn=False):
            calls["start"] += 1
            calls["start_allow_spawn"] = allow_direct_spawn
            return True
        w.start_daemon = _start
        w.catch_up = lambda mode, timeout, dry: (calls["catch"].append(mode) or (True, "selftest"))

        def _notify(t, c, desktop=None):
            calls["notify"] += 1
            if desktop:
                calls.setdefault("desktop", []).append(desktop)
        w.notify = _notify

        old_argv = sys.argv
        sys.argv = ["watchdog_batches.py"] + argv
        try:
            rc = w.main()
        finally:
            sys.argv = old_argv
    finally:
        for k, v in orig.items():
            setattr(w, k, v)
    return rc, calls


def test_selfheal():
    # 1) 守护进程停摆 + 允许补跑 → 拉起 + 补跑（最新缺失批次模式）
    _rc, c1 = run_watchdog(["--quiet"], alive=False, no_catchup_expected=False)
    check("停摆分支：先拉起守护进程", c1["start"] == 1, "start=%d" % c1["start"])
    check("停摆分支：执行补跑一次", len(c1["catch"]) == 1, "catch=%s" % c1["catch"])
    check("补跑模式取最新缺失批次", c1["catch"] and c1["catch"][0] in ("quick", "full"))

    # 2) --no-catchup → 只拉起，不补跑
    _rc, c2 = run_watchdog(["--quiet", "--no-catchup"], alive=False, no_catchup_expected=True)
    check("--no-catchup：拉起但不补跑", c2["start"] == 1 and len(c2["catch"]) == 0,
          "start=%d catch=%s" % (c2["start"], c2["catch"]))

    # 3) 守护进程存活 → 既不拉起也不补跑（避免双实例抢抓）
    _rc, c3 = run_watchdog(["--quiet"], alive=True, no_catchup_expected=False)
    check("存活分支：不拉起、不补跑", c3["start"] == 0 and len(c3["catch"]) == 0,
          "start=%d catch=%s" % (c3["start"], c3["catch"]))

    # 3b) 桌面告警通道：严重漏批时必须带上 desktop 文案（站内通知之外的第二通道）
    check("停摆分支：告警带桌面文案（桌面留痕）",
          bool(c1.get("desktop")), "desktop=%s" % (c1.get("desktop") or [])[:1])

    # 4) --check-only → 完全不动手
    _rc, c4 = run_watchdog(["--quiet", "--check-only"], alive=False, no_catchup_expected=False)
    check("--check-only：只读巡检", c4["start"] == 0 and len(c4["catch"]) == 0,
          "start=%d catch=%s" % (c4["start"], c4["catch"]))


def test_liveness():
    """存活判定矩阵：进程存在优先；探测不可用时保守视为存活（绝不重复拉起）。"""
    import os
    import tempfile as _tf
    tmp = Path(_tf.mkdtemp()) / "fake_daemon.log"
    tmp.write_text("x", encoding="utf-8")
    orig_log, orig_present, orig_runs = w.DAEMON_LOG, w.daemon_process_present, w.subprocess.run
    cases = [
        # (进程探测, 日志年龄分钟, 期望存活, 说明)
        (True, 999, True, "进程在、日志很旧（守护进程空档期常态）→ 仍算存活"),
        (False, 1, True, "无进程但日志刚写过 → 算存活（可能刚退出）"),
        (False, 999, False, "无进程且日志很旧 → 判停摆"),
        (None, 999, True, "探测手段不可用 → 保守视为存活"),
    ]
    try:
        for present, age_min, want, label in cases:
            os.utime(tmp, (time.time() - age_min * 60, time.time() - age_min * 60))
            w.DAEMON_LOG = tmp
            w.daemon_process_present = lambda p=present: (p, "selftest")
            got, why = w.daemon_alive(12)
            check("存活判定：" + label, got == want, "got=%s（%s）" % (got, why[:60]))
    finally:
        w.DAEMON_LOG, w.daemon_process_present, w.subprocess.run = orig_log, orig_present, orig_runs


def test_start_guard():
    """拉起守卫：已有进程不重复拉起；计划任务失败且未授权时不得直接 spawn。"""
    import subprocess as _sp
    orig_present, orig_run, orig_popen = w.daemon_process_present, w.subprocess.run, _sp.Popen
    popen_calls = []

    class _FakeRun:
        def __init__(self, rc):
            self.returncode = rc
            self.stdout = ""
            self.stderr = "selftest fail"

    try:
        # A) 进程已存在 → 直接返回 True，且不调用 schtasks / Popen
        w.daemon_process_present = lambda: (True, "selftest")
        w.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应调用 schtasks"))
        _sp.Popen = lambda *a, **k: popen_calls.append(a)
        r = w.start_daemon(allow_direct_spawn=False)
        check("拉起守卫：已有进程 → 不重复拉起", r is True and not popen_calls,
              "ret=%s popen=%d" % (r, len(popen_calls)))

        # B) 无进程 + schtasks 失败 + 未授权直接 spawn → 返回 False 且不 spawn
        calls = {"n": 0}
        w.daemon_process_present = lambda: (False, "selftest")
        w.subprocess.run = lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1) or _FakeRun(1))
        popen_calls.clear()
        r = w.start_daemon(allow_direct_spawn=False)
        check("拉起守卫：计划任务失败且未授权 → 不直接 spawn", r is False and not popen_calls,
              "ret=%s schtasks调用=%d popen=%d" % (r, calls["n"], len(popen_calls)))

        # C) 无进程 + 授权直接 spawn → 允许（复查仍为"无进程"）
        calls["n"] = 0
        popen_calls.clear()
        r = w.start_daemon(allow_direct_spawn=True)
        check("拉起守卫：显式授权后才允许直接 spawn", r is True and len(popen_calls) == 1,
              "ret=%s popen=%d" % (r, len(popen_calls)))
    finally:
        w.daemon_process_present, w.subprocess.run = orig_present, orig_run
        _sp.Popen = orig_popen


def test_multi_signal():
    """多信号合成：CIM 说 0（沙箱/受限会话常见）但 pythonw 计数为 1 → 必须判存活。"""
    orig_ps, orig_run = w._ps_int, w.subprocess.run
    seq = {"n": 0}

    def fake_ps(cmd, timeout=40):
        # 第 1 次 = CIM 匹配（沙箱返回 0），第 2 次 = pythonw 计数（1）
        seq["n"] += 1
        return 0 if seq["n"] == 1 else 1
    try:
        w._ps_int = fake_ps
        w.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError("tasklist 不可用"))
        present, why = w.daemon_process_present()
        check("多信号合成：CIM=0 但 pythonw=1 → 判存活", present is True, why[:100])
        seq["n"] = 0

        def fake_ps_all_zero(cmd, timeout=40):
            return 0
        w._ps_int = fake_ps_all_zero
        present2, why2 = w.daemon_process_present()
        check("多信号合成：全部为 0 → 判无进程", present2 is False, why2[:100])

        def fake_ps_none(cmd, timeout=40):
            return None
        w._ps_int = fake_ps_none
        present3, why3 = w.daemon_process_present()
        check("多信号合成：全部不可用 → 返回 None（保守）", present3 is None, why3[:100])
    finally:
        w._ps_int, w.subprocess.run = orig_ps, orig_run


def test_longtable_gap():
    """长表新鲜度/空洞检查：只滞后看不出"中间缺一天"，必须能识别内部空洞。"""
    import tempfile as _tf
    orig = w.LONG_CSV
    tmp = Path(_tf.mkdtemp()) / "long.csv"
    try:
        with open(tmp, "w", encoding="utf-8-sig") as f:
            f.write("date,song,index\n")
            for d, songs in (("2026-09-05", 3), ("2026-09-06", 3), ("2026-09-07", 3), ("2026-09-09", 3)):
                for i in range(songs):
                    f.write("%s,歌%d,%d\n" % (d, i, 100 + i))
        w.LONG_CSV = tmp
        scan = w.long_table_scan()
        check("长表扫描：最新日期正确", scan["max"] == dt.date(2026, 9, 9), str(scan["max"]))
        check("长表扫描：识别内部空洞 2026-09-08",
              scan["gaps"] == ["2026-09-08"], str(scan["gaps"]))

        with open(tmp, "a", encoding="utf-8-sig") as f:
            for i in range(3):
                f.write("2026-09-08,歌%d,%d\n" % (i, 200 + i))
        scan2 = w.long_table_scan()
        check("补齐后空洞消失", scan2["gaps"] == [], str(scan2["gaps"]))
    finally:
        w.LONG_CSV = orig


if __name__ == "__main__":
    print("=" * 68)
    print("漏批看门狗自测（不触碰真实状态）")
    print("=" * 68)
    print("[1] 调度表与文件名解析")
    test_schedule()
    test_file_minutes()
    print("[2] 批次匹配")
    test_matching()
    print("[3] 自愈分支")
    test_selfheal()
    print("[4] 存活判定与拉起守卫（2026-09-10 重复实例事故后新增）")
    test_liveness()
    test_multi_signal()
    test_start_guard()
    print("[5] 长表新鲜度与内部空洞（2026-09-10 补缺口后新增）")
    test_longtable_gap()
    print("-" * 68)
    print("通过 %d 项 / 失败 %d 项" % (len(PASS), len(FAIL)))
    if FAIL:
        for f in FAIL:
            print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
