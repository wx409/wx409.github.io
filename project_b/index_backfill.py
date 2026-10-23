# -*- coding: utf-8 -*-
"""index_backfill.py —— 指数长表**自动补采**（能补则补，补不到如实报「来源均无」）

机制（与 00_build_matrix.py 同一约定）：
  · 长表日期 = **文件名日期 − 1 天**（文件名是"采集日"，值属"昨日"）；
  · 因此要补 `2026-10-15`，需要的是 **`2026.10.16` 的文件**；
  · 数据源目录（first-wins 去重，与 00_build_matrix 一致）：
      E:\\wx\\指数数据库\\增补数据库2025.2.22-\\archived、同目录散文件、E:\\wx\\download、E:\\wx\\指数vs
  · 日期前导零/分隔符不统一（`2026.10.6` vs `2026.10.06`）与**千分位逗号**都由
    `00_build_matrix.py` 的 `parse_date()` / `to_num()` 统一处理（本脚本只负责找文件+触发重建）。

用法：
  python -X utf8 project_b\\index_backfill.py            # 只补最近 30 天缺口
  python -X utf8 project_b\\index_backfill.py --all       # 补全部历史缺口
  python -X utf8 project_b\\index_backfill.py --dry       # 只报告，不重建
  python -X utf8 project_b\\index_backfill.py --rebuild-only
退出码：0＝无缺口或已补成功；1＝仍有缺口（含来源均无）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
MATRIX = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
STORES = [Path(r"E:\wx\指数数据库\增补数据库2025.2.22-\archived"),
          Path(r"E:\wx\指数数据库\增补数据库2025.2.22-"),
          Path(r"E:\wx\download"),
          Path(r"E:\wx\指数vs")]
OUT = SITE / "data" / "index_backfill.json"
DATE_RE = re.compile(r"(\d{4})[._\-](\d{1,2})[._\-](\d{1,2})")


def files_by_date() -> dict[str, list[str]]:
    """把各来源的文件按「值日期（文件名−1天）」索引。"""
    idx: dict[str, list[str]] = {}
    for root in STORES:
        if not root.is_dir():
            continue
        for p in root.glob("*.xlsx"):
            if p.name.startswith("~$"):
                continue
            m = DATE_RE.search(p.name) or re.search(r"archived_(\d{4})(\d{2})(\d{2})", p.name)
            if not m:
                continue
            y, mo, d = (int(x) for x in m.groups())
            try:
                value_date = (date(y, mo, d) - timedelta(days=1)).isoformat()
            except ValueError:
                continue
            idx.setdefault(value_date, []).append(str(p))
    return idx


def has_index_col(path: str) -> bool:
    """文件是否含指数列（`指数vs` 的 quick 批次只有收听人数，**没有指数列** → 不可用于补日）。"""
    try:
        import pandas as pd
        cols = list(pd.read_excel(path, nrows=0).columns)
    except Exception:
        return False
    return any("音乐指数" in str(c) for c in cols)




def same_day_override(d: str) -> str:
    """缺日 d 若存在同名日档（文件日期＝d）且含『音乐指数』列 → 写入 day_overrides 并返回文件路径。"""
    import json as _json
    from datetime import date as _date
    from pathlib import Path as _P
    ovp = _P(r"E:\wx\index_records\day_overrides.json")
    ov = {}
    if ovp.exists():
        try:
            ov = _json.loads(ovp.read_text(encoding="utf-8"))
        except Exception:
            ov = {}
    want = _date.fromisoformat(d)
    for root in STORES:
        if not root.is_dir():
            continue
        for f in root.glob("*.xlsx"):
            if f.name.startswith("~$"):
                continue
            m = DATE_RE.search(f.name)
            if not m:
                continue
            try:
                if _date(int(m.group(1)), int(m.group(2)), int(m.group(3))) != want:
                    continue
            except ValueError:
                continue
            if not has_index_col(str(f)):
                continue
            ov[f.name] = {"column": "音乐指数", "as_date": d,
                          "note": "自动登记（backfill 自愈）：当日文件含『音乐指数』列＝当日值"}
            ovp.parent.mkdir(parents=True, exist_ok=True)
            ovp.write_text(_json.dumps(ov, ensure_ascii=False, indent=1), encoding="utf-8")
            return str(f)
    return ""


def gaps(expect_last: str = "") -> list[str]:
    sys.path.insert(0, str(SITE / "project_b"))
    import index_gap_check as g
    dates = g.load_dates()
    have = set(dates)
    first = date.fromisoformat(dates[0])
    expect = (date.fromisoformat(expect_last) if expect_last
              else date.today() - timedelta(days=1))
    out, c = [], first
    while c <= expect:
        if c.isoformat() not in have:
            out.append(c.isoformat())
        c += timedelta(days=1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--rebuild-only", action="store_true")
    ap.add_argument("--expect-last", default="")
    ap.add_argument("--recent", type=int, default=30)
    a = ap.parse_args()

    expect = a.expect_last or (date.today() - timedelta(days=1)).isoformat()
    before = gaps(expect)
    target = before if a.all else [d for d in before
                                   if d >= (date.fromisoformat(expect) - timedelta(days=a.recent)).isoformat()]
    idx = files_by_date()
    found, absent = [], []
    for d in target:
        cand = idx.get(d) or []
        if not cand:
            _hit = same_day_override(d)
            if _hit:
                print(f"  [自愈] {d}：发现同日文件 {_hit}（含音乐指数列）→ 已登记 override")
                found.append(d)      # 已登记 override，重建时会按 D 导入
                continue
        # ★ 2026-10-17 修：`指数vs` 的 quick 批次只有「当前收听人数」、**无指数列** →
        #   不能算"可补"。必须至少有一个带「音乐指数」列的文件才算可补。
        usable = [p for p in cand if has_index_col(p)]
        (found if usable else absent).append(d)
        if usable:
            idx[d] = usable
    print(f"[缺口] 合计 {len(before)} 天；本次处理 {len(target)} 天")
    print(f"[可补] {len(found)} 天：{found[:10]}{' …' if len(found) > 10 else ''}")
    print(f"[缺源] {len(absent)} 天：{absent[:10]}{' …' if len(absent) > 10 else ''}")

    rec = {"generated_at": datetime.now().isoformat(timespec="seconds"),
           "expect_last": expect, "gaps_before": len(before), "handled": len(target),
           "findable": found, "missing_no_source": absent,
           "rebuild": None}

    if a.rebuild_only or (found and not a.dry):
        print("[重建] 运行 00_build_matrix.py …")
        r = subprocess.run([sys.executable, "-X", "utf8", str(MATRIX)], capture_output=True,
                           text=True, encoding="utf-8", errors="ignore", cwd=str(MATRIX.parent))
        tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-3:]
        for t in tail:
            print("   ", t[:140])
        rec["rebuild"] = {"rc": r.returncode, "tail": tail}
        if r.returncode != 0:
            print("[X] 重建失败 → 不覆盖既有长表？注意：00_build_matrix 只在成功时写出")
            rec["error"] = (r.stderr or "")[-400:]

    after = gaps(expect)
    rec["gaps_after"] = len(after)
    rec["remaining_recent"] = after[-10:]
    print(f"[结果] 缺口 {len(before)} → {len(after)} 天；仍缺（近10）: {after[-10:]}")

    if absent:
        print("[报告] 以下缺日**来源均无**（不造假、不补零）：")
        for d in absent:
            print(f"   缺日：{d}（来源均无：需要 {date.fromisoformat(d) + timedelta(days=1)} 的采集文件）")

    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {OUT}")
    return 0 if not after else 1


if __name__ == "__main__":
    raise SystemExit(main())
