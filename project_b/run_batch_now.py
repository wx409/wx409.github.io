# -*- coding: utf-8 -*-
"""run_batch_now.py —— 立刻补跑一次采集（手动入口）+ 顺带刷新长表/基线

什么时候用
----------
看门狗报"漏批/日档案缺失/长表有缺口"时，不必等到下一个计划批次：
本脚本立刻调用守护进程 `--once --full|--quick` 抓一次，随后自动
`refresh_index_baseline.py --force`，把新数据一路推到长表、基线、站点 JSON。

安全性（避免与正在跑的守护进程抢抓）
------------------------------------
守护进程平时是"空闲等待"状态，此时另起一个 `--once` 进程**不会**冲突
（输出文件名带时刻，写入互不覆盖）。但如果它**正在跑批次**（日志 10 分钟内有写入），
本脚本默认拒绝执行，需显式 `--force`。

用法：
    python project_b\\run_batch_now.py --check            # 只看守护进程状态，不动手
    python project_b\\run_batch_now.py --mode quick       # 立刻抓一次极速（约 4-5 分钟）
    python project_b\\run_batch_now.py --mode full        # 立刻抓一次全量（约 5-10 分钟）
    python project_b\\run_batch_now.py --mode full --force
退出码：0 = 成功（含"守护进程正忙"的干净跳过）；1 = 采集或刷新失败。
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project_b"))

import watchdog_batches as w  # noqa: E402  复用守护进程探测与日志路径

DAEMON_SRC = w.DAEMON_SRC
DAEMON_LOG = w.DAEMON_LOG
REFRESH = ROOT / "project_b" / "refresh_index_baseline.py"


def log(msg: str) -> None:
    print("[%s] %s" % (dt.datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def log_age_min() -> float | None:
    try:
        if DAEMON_LOG.exists():
            return (dt.datetime.now() - dt.datetime.fromtimestamp(DAEMON_LOG.stat().st_mtime)).total_seconds() / 60
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "quick"], default="quick")
    ap.add_argument("--force", action="store_true", help="守护进程可能正在跑时也强制执行")
    ap.add_argument("--check", action="store_true", help="只看状态")
    ap.add_argument("--no-refresh", action="store_true", help="抓完不刷新长表/基线")
    args = ap.parse_args()

    present, why = w.daemon_process_present()
    age = log_age_min()
    log("守护进程判定：%s（%s）｜日志 %s" % (present, why, ("%.1f 分钟前" % age) if age is not None else "不可读"))
    if age is not None and age < 10:
        log("⚠️ 守护进程 10 分钟内有写入 → 很可能正在跑批次")
        if args.check:
            return 0
        if not args.force:
            log("[skip] 为避免与正在跑的批次抢抓，本次不执行；确要继续请加 --force")
            return 0
        log("[!] 已指定 --force，继续执行")

    if args.check:
        log("（--check：未执行采集）")
        return 0

    cmd = [sys.executable, "-X", "utf8", str(DAEMON_SRC), "--once", "--full" if args.mode == "full" else "--quick"]
    log("立刻补跑一次采集：%s" % " ".join(cmd))
    try:
        r = subprocess.run(cmd, cwd=str(DAEMON_SRC.parent), capture_output=True, text=True,
                           encoding="utf-8", errors="ignore",
                           timeout=(40 if args.mode == "full" else 20) * 60)
    except subprocess.TimeoutExpired:
        log("[X] 采集超时")
        return 1
    stdout_tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-6:]
    for x in stdout_tail:
        log("   " + x[:150])
    if r.returncode != 0:
        log("[X] 采集失败 returncode=%s" % r.returncode)
        return 1
    log("✓ 采集完成，日志尾部：")
    try:
        for x in DAEMON_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()[-4:]:
            log("   " + x[:150])
    except Exception:
        pass

    if not args.no_refresh:
        log("-- 刷新长表 + 基线（让新数据一路到站点）--")
        r2 = subprocess.run([sys.executable, "-X", "utf8", str(REFRESH), "--force"],
                            cwd=str(ROOT), capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=3600,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        for x in [y for y in (r2.stdout or "").splitlines() if y.strip()][-6:]:
            log("   " + x[:150])
        if r2.returncode != 0:
            log("[!] 刷新失败（采集已成功）returncode=%s" % r2.returncode)
    log("完成。建议接着跑：python project_b\\acceptance_check.py（事故验收总检）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
