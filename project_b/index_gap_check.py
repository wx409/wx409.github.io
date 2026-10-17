# -*- coding: utf-8 -*-
"""index_gap_check.py —— 指数长表**缺日检测**（数据不断更的第一步）

做什么：
  1. 读 `E:\\wx\\wx_textmine_out\\music_index_long.csv`（唯一长表口径）；
  2. 应有日期区间 = 首个日期 → **最新应当有的日期**（默认＝昨天，可用 --expect-last 覆盖）；
  3. 列出缺口：最近 14 天 + 近 365 天全部缺口（含连续段归并）；
  4. 派生新鲜度：覆盖天数 / 最后日期 / **已连续无缺日天数**（从最后日期往前数连续覆盖）；
  5. 写出 `data/index_freshness.json`（供大屏顶部一行与审计引用，**零手写**）。

用法：
  python -X utf8 project_b\\index_gap_check.py              # 检测+写 JSON
  python -X utf8 project_b\\index_gap_check.py --dry        # 只打印
  python -X utf8 project_b\\index_gap_check.py --expect-last 2026-10-16
退出码：0＝无缺日；1＝有缺日（便于计划任务/上层判断）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
OUT = SITE / "data" / "index_freshness.json"
BATCH = SITE / "data" / "index_batches.json"


def load_dates() -> list[str]:
    import pandas as pd
    df = pd.read_csv(CSV, usecols=["date"])
    return sorted(set(pd.to_datetime(df["date"], errors="coerce")
                      .dt.strftime("%Y-%m-%d").dropna()))


def ranges(days: list[date]) -> list[dict]:
    """把日期列表归并成连续区间。"""
    out = []
    for d in days:
        if out and (d - out[-1]["end"]).days == 1:
            out[-1]["end"] = d
        else:
            out.append({"start": d, "end": d})
    return [{"from": r["start"].isoformat(), "to": r["end"].isoformat(),
             "days": (r["end"] - r["start"]).days + 1} for r in out]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-last", default="", help="应覆盖到的最后日期（默认昨天）")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--recent", type=int, default=14)
    a = ap.parse_args()

    dates = load_dates()
    have = set(dates)
    first = date.fromisoformat(dates[0])
    last_have = date.fromisoformat(dates[-1])
    expect = (date.fromisoformat(a.expect_last) if a.expect_last
              else date.today() - timedelta(days=1))
    cursor = first
    missing = []
    while cursor <= expect:
        iso = cursor.isoformat()
        if iso not in have:
            missing.append(cursor)
        cursor += timedelta(days=1)

    # ★ 2026-10-17：只有「白天中间批」的日期 = **待最终批**，不算缺日（不静默跳过）
    pending_final = []
    try:
        b = json.loads(BATCH.read_text(encoding="utf-8"))
        pend = set(b.get("pending_final") or [])
        pending_final = [d.isoformat() for d in missing if d.isoformat() in pend]
        missing = [d for d in missing if d.isoformat() not in pend]
    except Exception:
        pending_final = []

    recent = [d for d in missing if d >= expect - timedelta(days=a.recent)]
    year = [d for d in missing if d >= expect - timedelta(days=365)]

    # 连续无缺日：从最后有数据日往前数
    streak = 0
    c = last_have
    while c.isoformat() in have:
        streak += 1
        c -= timedelta(days=1)

    doc = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(CSV),
        "caliber": "已发布长表 music_index_long.csv（date,song,index）",
        "first_date": dates[0], "last_date": dates[-1],
        "expect_last": expect.isoformat(),
        "coverage_days": len(dates),
        "rows": None,
        "missing_total": len(missing),
        "missing_recent": [d.isoformat() for d in recent],
        "missing_last_year": [d.isoformat() for d in year],
        "missing_ranges_recent": ranges(recent),
        "missing_ranges_year": ranges(year),
        "streak_no_gap_days": streak,
        "status": "ok" if not missing else "gap",
        "pending_final": pending_final,
        "pending_final_note": "这些日期只有白天/傍晚的中间批，**等当日最终批（23:56 那批）**，不算缺日",
        "headline": (f"最近成功采集：{dates[-1]} ｜ 覆盖 {len(dates)} 天 ｜ 已连续无缺日 {streak} 天"
                     if not missing else
                     f"⚠ 缺日 {len(missing)} 天（最近：{', '.join(d.isoformat() for d in recent) or '—'}）"
                     f"｜覆盖 {len(dates)} 天｜最后数据 {dates[-1]}"),
    }
    try:
        import pandas as pd
        doc["rows"] = int(len(pd.read_csv(CSV)))
    except Exception:
        pass

    print(f"[长表] {CSV}")
    print(f"  首日 {doc['first_date']}｜末日 {doc['last_date']}｜应到 {doc['expect_last']}｜覆盖 {doc['coverage_days']} 天｜行 {doc['rows']}")
    print(f"  缺日合计 {doc['missing_total']} 天；近 {a.recent} 天缺口: {doc['missing_recent'] or '无'}")
    print(f"  近一年缺口（连续段）: {doc['missing_ranges_year'] or '无'}")
    print(f"  {doc['headline']}")

    if not a.dry:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[OK] 已写 {OUT}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
