# -*- coding: utf-8 -*-
"""批次标记：区分「日最终批」与「白天中间批」，供缺日检测区分「缺日 / 待最终批」。

规则（可复核）：
  · 文件名含 `_quick` → **middle_day**（白天/傍晚中间批，只有收听数或非最终值）
  · 文件名形如 `YYYY.M.D.xlsx`（增补库/download 的日档）→ **final**（当晚 23:5x 的日档）
  · 文件名形如 `YYYY.M.D_HHMM.xlsx`（指数vs 的整点批）→ 22:00 之后视作 final，否则 middle_day
输出：`data/index_batches.json`（按值日期聚合：final / middle 批次列表）
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
OUT = SITE / "data" / "index_batches.json"
DIRS = [Path(r"E:\wx\指数vs"), Path(r"E:\wx\download"),
        Path(r"E:\wx\指数数据库\增补数据库2025.2.22-")]
RE_DATE = re.compile(r"(\d{4})[.\-_](\d{1,2})[.\-_](\d{1,2})(?:_(\d{2})(\d{2}))?")


def main() -> int:
    batches: dict[str, dict] = {}
    for d in DIRS:
        if not d.is_dir():
            continue
        for p in d.glob("*.xlsx"):
            if p.name.startswith("~$"):
                continue
            m = RE_DATE.search(p.name)
            if not m:
                continue
            y, mo, dd, hh, mm = m.groups()
            try:
                fdate = date(int(y), int(mo), int(dd))
            except ValueError:
                continue
            quick = "_quick" in p.name
            late = bool(hh) and int(hh) >= 22
            kind = "middle_day" if (quick or (hh and not late)) else "final"
            # ★ 2026-10-20 修：中间批是「当天实时」的批次 → 值日期＝文件名当天；
            #   只有最终日档（D−1 约定）才减一天。
            value_date = (fdate if kind == "middle_day" else fdate - timedelta(days=1)).isoformat()
            rec = batches.setdefault(value_date, {"final": [], "middle": []})
            rec["final" if kind == "final" else "middle"].append(
                {"file": p.name, "dir": str(d), "mtime": p.stat().st_mtime, "kind": kind})
    # 汇总
    summary = {}
    for day, rec in batches.items():
        summary[day] = {"has_final": bool(rec["final"]), "n_middle": len(rec["middle"]),
                        "final_files": [x["file"] for x in rec["final"]][:3],
                        "middle_files": [x["file"] for x in rec["middle"]][:3]}
    pending = sorted([d for d, v in summary.items() if not v["has_final"] and v["n_middle"]])
    doc = {"schema": 1, "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
           "rule": "`_quick` 或 22 点前的整点批＝middle_day；日档/22 点后整点批＝final；值日期＝文件名−1",
           "n_days": len(summary), "pending_final": pending, "days": summary}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {OUT}｜待最终批 {len(pending)} 天：{pending[-5:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
