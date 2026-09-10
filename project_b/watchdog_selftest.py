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
        w.start_daemon = lambda: (calls.__setitem__("start", calls["start"] + 1) or True)
        w.catch_up = lambda mode, timeout, dry: (calls["catch"].append(mode) or (True, "selftest"))

        def _notify(t, c):
            calls["notify"] += 1
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

    # 4) --check-only → 完全不动手
    _rc, c4 = run_watchdog(["--quiet", "--check-only"], alive=False, no_catchup_expected=False)
    check("--check-only：只读巡检", c4["start"] == 0 and len(c4["catch"]) == 0,
          "start=%d catch=%s" % (c4["start"], c4["catch"]))


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
    print("-" * 68)
    print("通过 %d 项 / 失败 %d 项" % (len(PASS), len(FAIL)))
    if FAIL:
        for f in FAIL:
            print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
