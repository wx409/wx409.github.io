"""每日断言：长表末日期必须等于昨天（或今天已入库）。
不等则：列出「缺失日」与当天所有候选文件及其列名，写站内通知 + 日志，退出码 1。
用法：python -X utf8 project_b/check_index_freshness.py [--date YYYY-MM-DD]
"""
import argparse
import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LONG = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
CAND_DIRS = [Path(r"E:\wx\index_records\raw_archive"),
             Path(r"E:\wx\download"),
             Path(r"E:\wx\指数数据库\增补数据库2025.2.22-"),
             Path(r"E:\wx\指数vs")]
LOG = ROOT / "temp" / "index_freshness.log"

def last_long_date() -> str:
    if not LONG.exists():
        return ""
    with LONG.open(encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        ds = {row[0] for row in r if row and row[0]}
    return max(ds) if ds else ""

def candidates(d: str):
    """列出可能与日期 d 有关的文件（文件名含 YYYY.MM.DD 或 YYYY-MM-DD），并报列名。"""
    out = []
    keys = {d.replace("-", "."), d.replace(".", "-"), d}
    for base in CAND_DIRS:
        if not base.exists():
            continue
        try:
            files = list(base.glob("*.xlsx")) + list(base.glob("*.xls"))
        except Exception:
            files = []
        for f in files:
            if not any(k in f.name for k in keys):
                continue
            cols = []
            try:
                import openpyxl
                ws = openpyxl.load_workbook(f, read_only=True, data_only=True).active
                first = next(ws.iter_rows(values_only=True), ())
                cols = [str(c) for c in first if c is not None][:6]
            except Exception as e:
                cols = ["<读不出: %s>" % type(e).__name__]
            out.append({"file": str(f), "size": f.stat().st_size,
                        "has_index_col": any("音乐指数" in c for c in cols),
                        "cols": cols})
    return out

def notify(title: str, body: str):
    try:
        sys.path.insert(0, str(ROOT))
        import notify  # type: ignore
        notify.record(title, body)
    except Exception:
        pass

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="", help="期望入库日（默认昨天）")
    a = ap.parse_args()
    expect = a.date or (date.today() - timedelta(days=1)).isoformat()
    last = last_long_date()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = "[%s] expect=%s last=%s" % (date.today().isoformat(), expect, last)
    ok = last >= expect
    print(line, "->", "OK" if ok else "MISSING")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + (" OK\n" if ok else " MISSING\n"))
    if ok:
        return 0
    cands = candidates(expect)
    msg = "长表末日期 %s，缺 %s" % (last or "空", expect)
    print(msg)
    if cands:
        for c in cands:
            tag = "有音乐指数列" if c["has_index_col"] else "无音乐指数列"
            print("  候选 %s（%s）列=%s" % (os.path.basename(c["file"]), tag, c["cols"]))
    else:
        print("  无任何候选文件（文件名不含该日期）")
    # ★ 2026-10-31：缺日不再只报警——有候选文件就自动补录（长表→基线→大屏一条链）
    if cands:
        import subprocess, sys
        print("  自动补录：index_backfill.py")
        rc = subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "index_backfill.py")])
        last2 = last_long_date()
        if last2 >= expect:
            notify("指数缺日已自动补齐：%s" % expect, "原缺 %s；补录后长表末日期 %s（rc=%d）" % (expect, last2, rc))
            print("  补录后最新 %s -> 已补齐" % last2)
            return 0
        notify("指数缺日自动补录未成功：%s" % expect, "补录后末日期仍为 %s（rc=%d），需人工看日志" % (last2, rc))
        return 1

    notify("指数缺日：%s" % expect, msg + "；无候选文件")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
