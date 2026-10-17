# -*- coding: utf-8 -*-
"""night_shutdown_gate.py —— 凌晨 01:30 关机闸门（**唯一关机决策点**）

规则（用户 2026-10-17 裁决）：
    关机 ⇔ 该 01:30 所属日期 D 是**周一~周五**，且 D **不是法定放假日**，且 D **不是调休上班日**
    周六 / 周日 / 法定节假日 / 调休日 → **一律不关机**（让大屏 daemon 继续跑）

日历：复用 `E:\\wx\\私有工具\\holiday_cache\\<年>.json`（与 `holiday_skip_sync.py` **同一份缓存**，
      **不另建日历**）；缓存缺失时才走 `holiday_skip_sync.fetch_year()`（同一数据源）补齐。

历史背景：
  · 旧机制＝生成器 23:55 读 `E:\\wx\\shutdown_skip.txt`，**命中即不关机**；
    该文件曾被写入「周一~周五」→ 7×24 全豁免，**从未真正关机**（2026-10-17 诊断）。
  · 现已把决策收到本脚本 + 每日 01:30 计划任务 `wx409_night_shutdown`；
    `shutdown_skip.txt` 改为「周一~周日全列」→ 旧 `schedule_shutdown()` 永不下发，避免两套机制互抢。

用法：
  python -X utf8 project_b\\night_shutdown_gate.py            # 生产：该关则 60 秒后关机
  python -X utf8 project_b\\night_shutdown_gate.py --dry       # 只判定不关机
  python -X utf8 project_b\\night_shutdown_gate.py --at 2026-10-12   # 日期打桩（只判定）
退出码：0＝正常（无论关不关）；2＝参数错误；4＝判定失败（日历不可用，**保守不关机**）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
CACHE_DIR = Path(r"E:\wx\私有工具\holiday_cache")
LOG = Path(r"E:\wx\私有工具\night_shutdown_log.jsonl")
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_calendar(years: list[int]) -> tuple[set[str], set[str], list[str]]:
    """返回 (放假日, 调休上班日, 缺失年份)。只用**既有缓存**，不新建日历。"""
    off, makeup, missing = set(), set(), []
    for y in years:
        p = CACHE_DIR / f"{y}.json"
        if not p.exists():
            missing.append(str(y))
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            missing.append(f"{y}(解析失败)")
            continue
        for x in (doc.get("days") or []):
            d = x.get("date")
            if not d:
                continue
            (off if x.get("isOffDay") else makeup).add(d)
    return off, makeup, missing


def decide(d: date, off: set[str], makeup: set[str]) -> tuple[bool, str]:
    # 顺序：法定节假日 → 调休上班日 → 周末 → 工作日（打桩表要能写出「调休」而非「周末」）
    if d.isoformat() in off:
        return False, "法定节假日"
    if d.isoformat() in makeup:
        return False, "调休上班日（按用户规则：调休一律不关机）"
    if d.weekday() >= 5:
        return False, f"{WD[d.weekday()]}（周末）"
    return True, "普通工作日"


def log_jsonl(rec: dict) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[warn] 写日志失败：{e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", default="", help="日期打桩 YYYY-MM-DD（只判定不关机）")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--delay", type=int, default=60, help="关机前缓冲秒数（默认 60）")
    a = ap.parse_args()

    if a.at:
        try:
            d = date.fromisoformat(a.at)
            stub = True
        except ValueError:
            print(f"[X] --at 日期格式错误：{a.at}")
            return 2
    else:
        d = date.today()          # 01:30 所属日期＝当天
        stub = False

    off, makeup, missing = load_calendar(sorted({d.year, d.year + 1}))
    if missing:
        # 缓存缺该年：尝试用同一数据源补（复用 holiday_skip_sync.fetch_year，不新建日历）
        try:
            sys.path.insert(0, str(SITE / "project_b"))
            from holiday_skip_sync import fetch_year
            for y in (d.year, d.year + 1):
                if str(y) in missing:
                    fetch_year(y)
            off, makeup, missing = load_calendar(sorted({d.year, d.year + 1}))
        except Exception as e:
            print(f"[warn] 补拉日历失败：{e}")

    if missing and not off and not makeup:
        # 日历完全不可用 → **保守不关机**（宁可不关，也不要误关）
        rec = {"at": datetime.now().isoformat(timespec="seconds"), "date": d.isoformat(),
               "weekday": WD[d.weekday()], "shutdown": False,
               "reason": f"日历不可用（缺 {missing}）→ 保守不关机", "stub": stub}
        print(json.dumps(rec, ensure_ascii=False))
        log_jsonl(rec)
        return 4

    shutdown_ok, why = decide(d, off, makeup)
    rec = {"at": datetime.now().isoformat(timespec="seconds"), "date": d.isoformat(),
           "weekday": WD[d.weekday()], "shutdown": shutdown_ok, "reason": why,
           "holiday": d.isoformat() in off, "makeup": d.isoformat() in makeup, "stub": stub}
    print(f"[判定] {d.isoformat()}（{WD[d.weekday()]}）→ {'✅ 关机' if shutdown_ok else '❌ 不关机'}（{why}）")
    log_jsonl(rec)

    if stub or a.dry or not shutdown_ok:
        if not shutdown_ok:
            print("[动作] 不关机，daemon 继续运行")
        else:
            print("[动作] 打桩/dry：未执行关机")
        return 0

    try:
        subprocess.run(["shutdown", "-s", "-t", str(a.delay)], check=False)
        print(f"[动作] 已预约 {a.delay} 秒后关机")
    except Exception as e:
        print(f"[X] 调用关机失败：{e}")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
