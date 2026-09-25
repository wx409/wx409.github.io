# -*- coding: utf-8 -*-
"""自动生成"不关机日"到 E:\\wx\\shutdown_skip.txt（节假日/调休自动识别，无需手改）。

背景（2026-09-25 用户需求）
--------------------------
QQ 大屏生成器每晚 23:55 后设置次日 01:30 关机，读 `shutdown_skip.txt` 决定是否豁免。
用户规则：**平时周五晚~周日晚都不关机**（即目标日 = 周六/周日/周一 → 不关机），
且**串休/法定节假日也要自动不关机**，不想每次手动改文件。

本脚本：
  1. 从官方节假日数据源（holiday-cn，含**调休上班日**）拉取当年与次年日历，并**本地缓存**（断网可用）；
  2. 为**未来 N 天**逐日计算"是否豁免"：目标日属于 {周六, 周日, 周一} 或属于**法定放假日** → 豁免；
  3. 把结果写入 shutdown_skip.txt 的**受管区块**（AUTO-HOLIDAY:START/END），保留原有注释与手动行；
  4. 打印未来 14 天的验证表。

用法：
  python -X utf8 project_b\\holiday_skip_sync.py            # 同步并打印验证表
  python -X utf8 project_b\\holiday_skip_sync.py --days 120 # 生成窗口（默认 120 天）
  python -X utf8 project_b\\holiday_skip_sync.py --dry      # 只显示将要写入的内容
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKIP_FILE = Path(r"E:\wx\shutdown_skip.txt")
CACHE_DIR = Path(r"E:\wx\私有工具\holiday_cache")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
SOURCES = [
    "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{y}.json",
    "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{y}.json",
]
# 用户规则：目标日（次日 01:30）为这些星期 → 不关机（可用 --skip-weekdays 覆盖）
ISO2PY = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}       # ISO 星期(1=周一) → python weekday
WD_NAME = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
SKIP_WEEKDAYS = {5: "周六", 6: "周日", 0: "周一"}          # 运行时按参数重建
START = "# ==== AUTO-HOLIDAY:START（由 project_b\\holiday_skip_sync.py 自动生成，勿手改）===="
END = "# ==== AUTO-HOLIDAY:END ===="


def fetch_year(y: int) -> dict:
    """取某年节假日数据（带本地缓存，断网回退）。返回 {date: isOffDay} 与原始条目。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{y}.json"
    for tpl in SOURCES:
        url = tpl.format(y=y)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
            data = json.loads(raw.decode("utf-8", "ignore"))
            cache.write_bytes(raw)
            print(f"  [{y}] 已从网络获取并缓存（{len(data.get('days', []))} 条）")
            return data
        except Exception as e:
            print(f"  [{y}] 源不可用 {url.split('/')[2]}：{repr(e)[:60]}")
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        print(f"  [{y}] 使用本地缓存（{len(data.get('days', []))} 条）")
        return data
    print(f"  [{y}] ✗ 无网络且无缓存 → 该年按空处理")
    return {"days": []}


def build(years: list[int]) -> tuple[dict, list[dict]]:
    offdays, all_days = set(), []
    for y in years:
        for x in fetch_year(y).get("days", []):
            d = x.get("date")
            all_days.append(x)
            if x.get("isOffDay") and d:
                offdays.add(d)
    return offdays, all_days


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--skip-weekdays", default="6,7,1",
                    help="目标日为这些星期则不关机（1=周一…7=周日；默认 6,7,1）")
    ap.add_argument("--respect-makeup", action="store_true",
                    help="调休上班日按工作日处理（不豁免）")
    a = ap.parse_args()

    global SKIP_WEEKDAYS
    try:
        SKIP_WEEKDAYS = {ISO2PY[int(x)]: WD_NAME[ISO2PY[int(x)]]
                         for x in str(a.skip_weekdays).split(",") if x.strip()}
    except Exception as e:
        print("  ⚠ --skip-weekdays 解析失败，用默认 周六/周日/周一：", repr(e)[:60])
    print("  不关机星期：", "、".join(SKIP_WEEKDAYS[k] for k in sorted(SKIP_WEEKDAYS)))

    today = date.today()
    years = sorted({today.year, (today + timedelta(days=a.days)).year, today.year + 1})
    print(f"目标：为未来 {a.days} 天生成豁免日｜涉及年份 {years}")
    offdays, all_days = build(years)
    print(f"  法定放假日 {len(offdays)} 天｜调休上班日 {sum(1 for x in all_days if not x.get('isOffDay'))} 天")

    rows, skip_dates = [], []
    for i in range(a.days):
        target = today + timedelta(days=i)
        iso = target.isoformat()
        makeup = any(x.get("date") == iso and not x.get("isOffDay") for x in all_days)
        wk = None if (makeup and a.respect_makeup) else SKIP_WEEKDAYS.get(target.weekday())
        off = iso in offdays
        why = []
        if wk:
            why.append(f"{wk}(周内规则)")
        if off:
            name = next((x.get("name") for x in all_days if x.get("date") == iso and x.get("isOffDay")), "节假日")
            why.append(f"{name}(法定)")
        if makeup:
            why.append("调休上班日")
        skip = bool(why)
        if skip:
            skip_dates.append(target.isoformat())
        rows.append((target, "✅ 不关机" if skip else "❌ 会关机", "＋".join(why) or "工作日"))

    # 组装文件（保留原注释与手动行，只替换受管区块）
    old = SKIP_FILE.read_text(encoding="utf-8") if SKIP_FILE.exists() else ""
    head = old.split(START)[0].rstrip()
    # 兜底：脚本长期未跑时，静态星期行仍生效
    for wd in ("周六", "周日", "周一"):
        if re.search(r"^%s$" % wd, head, re.M) is None:
            head += "\n" + wd
    if START not in old:
        head = old.rstrip() + "\n\n# 目标日（次日 01:30）命中下列日期 → 不关机；本区块由脚本自动维护\n"
    body = [START] + skip_dates + [END]
    new = head + "\n" + "\n".join(body) + "\n"

    print(f"\n将写入 {len(skip_dates)} 个豁免日期（窗口 {today} ~ {today + timedelta(days=a.days - 1)}）")
    print("\n=== 未来 14 天验证表 ===")
    print(f"{'目标日(次日01:30)':<20}{'判定':<12}依据")
    for d, verdict, why in rows[:14]:
        print(f"{d.isoformat():<20}{d.strftime('%a'):<5}{verdict:<12}{why}")

    if a.dry:
        print("\n[dry] 未写入文件")
        return 0
    if SKIP_FILE.exists():
        bak = SKIP_FILE.with_suffix(f".bak_{datetime.now():%Y%m%d_%H%M}.txt")
        shutil.copy2(SKIP_FILE, bak)
        print("\n已备份 →", bak.name)
    SKIP_FILE.write_text(new, encoding="utf-8")
    print("已写入", SKIP_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
