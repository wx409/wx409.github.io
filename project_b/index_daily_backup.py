# -*- coding: utf-8 -*-
"""index_daily_backup.py —— 指数链路每日快照（不覆盖旧快照）

备份对象（缺一不可，缺则如实记录为 missing，不静默）：
  · E:\\wx\\wx_textmine_out\\music_index_long.csv      （长表，唯一指数口径）
  · D:\\wx409.github.io\\data\\archive_baseline.json     （站点基线）
  · D:\\wx409.github.io\\dashboard\\dashboard_data.json  （大屏数据出口）
落点：`E:\\wx\\backups\\指数\\<YYYY-MM-DD>\\`，**同日重复运行不覆盖已有文件**（只补缺）。
保留：默认 60 天（`--keep`），清理只删**本脚本命名格式**的旧日期目录。

用法：
  python -X utf8 project_b\\index_daily_backup.py [--keep 60] [--dry]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(r"E:\wx\backups\指数")
FILES = {
    "music_index_long.csv": Path(r"E:\wx\wx_textmine_out\music_index_long.csv"),
    "archive_baseline.json": Path(r"D:\wx409.github.io\data\archive_baseline.json"),
    "dashboard_data.json": Path(r"D:\wx409.github.io\dashboard\dashboard_data.json"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=60)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    day = datetime.now().strftime("%Y-%m-%d")
    dest = ROOT / day
    rec = {"at": datetime.now().isoformat(timespec="seconds"), "dest": str(dest), "files": {}, "skipped": []}
    if not a.dry:
        dest.mkdir(parents=True, exist_ok=True)

    for name, src in FILES.items():
        if not src.exists():
            rec["files"][name] = "missing"
            print(f"[缺] {src} 不存在 → 记为 missing（不静默）")
            continue
        tgt = dest / name
        if tgt.exists():
            rec["skipped"].append(name)
            print(f"[=] 已存在，跳过（不覆盖）：{tgt}")
            continue
        if a.dry:
            print(f"[dry] {src} → {tgt}")
            continue
        shutil.copy2(src, tgt)
        rec["files"][name] = {"size": tgt.stat().st_size,
                              "sha_prefix": __import__("hashlib").sha256(tgt.read_bytes()).hexdigest()[:16]}
        print(f"[OK] {name} → {tgt}（{tgt.stat().st_size:,} B）")

    # 清旧（只删符合 YYYY-MM-DD 命名的目录）
    removed = []
    if not a.dry and ROOT.exists():
        cutoff = datetime.now().date() - timedelta(days=a.keep)
        for d in ROOT.iterdir():
            if not d.is_dir():
                continue
            try:
                dd = datetime.strptime(d.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if dd < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                removed.append(d.name)
    if removed:
        print(f"[清理] 删除 {len(removed)} 个超过 {a.keep} 天的旧快照：{removed[:5]}")
    rec["removed"] = removed
    rec["keep_days"] = a.keep

    if not a.dry:
        (RH := ROOT / "backup_log.jsonl")
        with RH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
