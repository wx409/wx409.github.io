#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首次全量备份：把 D:\\wx409.github.io 与 E:\\wx 完整镜像到 G:\\网站备份\\full\\<日期>\\

与每周脚本（backup_key_data.py）的分工
  · 每周脚本：只打包「不可再生的关键数据」，几十 MB，快；
  · 本脚本：**首次全量**，含媒体与历史，几百 GB，慢（G 盘实测约 110 MB/s）。

安全口径（沿用站内纪律）
  · 排除凭据：cookie / qqmusic.txt / .env / secrets* / *.dpapi / radio_cookie*
  · 排除缓存：temp、__pycache__、.venv、node_modules、.mplcache、logs
  · 排除日志与临时文件：*.log、*.tmp
  · 目标目录必须带 `.backup_target` 标记且 host 与本机一致（防接错盘）

用法
  python -X utf8 project_b\\backup_full.py --dry          # 只算体积与预计时间
  python -X utf8 project_b\\backup_full.py                # 真跑（robocopy /E，可断点续跑）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DEST_ROOT = Path(r"G:\网站备份")
SOURCES = [(Path(r"D:\wx409.github.io"), "D_wx409.github.io"),
           (Path(r"E:\wx"), "E_wx")]
EXCL_DIRS = ["temp", "__pycache__", ".venv", "node_modules", ".mplcache", "logs",
             "$RECYCLE.BIN", "System Volume Information"]
EXCL_FILES = ["*.log", "*.tmp", "qqmusic.txt", "*cookie*", "*Cookie*", ".env",
              "secrets*", "*.dpapi", "radio_cookie*"]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.1f %s" % (n, unit)
        n /= 1024
    return "%.1f PB" % n


def check_marker() -> bool:
    m = DEST_ROOT / ".backup_target"
    if not m.exists():
        print("！缺少标记文件：%s" % m)
        return False
    txt = m.read_text(encoding="utf-8")
    host = os.environ.get("COMPUTERNAME", "?")
    if "wx409-keydata-backup" not in txt or ("host=" + host) not in txt:
        print("！标记文件不属于本机：%s" % txt.replace("\n", " "))
        return False
    print("标记校验通过：", txt.replace("\n", " "))
    return True


def sizeof(p: Path) -> tuple[int, int]:
    n = s = 0
    for root, dirs, names in os.walk(p):
        dirs[:] = [d for d in dirs if d not in EXCL_DIRS]
        for f in names:
            if any(f.lower().endswith(ext) for ext in (".log", ".tmp")):
                continue
            try:
                s += (Path(root) / f).stat().st_size
                n += 1
            except OSError:
                pass
    return n, s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", default="", help="只备份某个源，如 D 或 E")
    ap.add_argument("--speed", type=float, default=110.0, help="预计速度 MB/s（用于估时）")
    args = ap.parse_args()

    if not DEST_ROOT.exists():
        print("！备份根不存在：%s" % DEST_ROOT)
        return 3
    if not check_marker():
        return 4

    srcs = [(p, name) for p, name in SOURCES if not args.only or str(p)[0].upper() == args.only.upper()]
    total_n = total_s = 0
    for p, name in srcs:
        if not p.exists():
            print("！源不存在：", p)
            return 3
        n, s = sizeof(p)
        total_n += n
        total_s += s
        print("  %-22s %7d 文件  %s" % (name, n, human(s)))
    eta_min = total_s / 1024 / 1024 / args.speed / 60 if total_s else 0
    print("合计 %d 文件 / %s；按 %.0f MB/s 估算约 %.0f 分钟（实际含小文件开销会更久）"
          % (total_n, human(total_s), args.speed, eta_min))
    if args.dry:
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = DEST_ROOT / "full" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".backup_target").write_text(
        "purpose=wx409-full-backup\nhost=%s\ncreated=%s\n" % (os.environ.get("COMPUTERNAME", "?"), stamp),
        encoding="utf-8")

    log = dest / "_robocopy.log"
    for p, name in srcs:
        cmd = ["robocopy", str(p), str(dest / name), "/E", "/R:1", "/W:1", "/XJ", "/NP",
               "/NFL", "/NDL", "/LOG+:%s" % log]
        for d in EXCL_DIRS:
            cmd += ["/XD", d]
        for f in EXCL_FILES:
            cmd += ["/XF", f]
        print("\n▶ robocopy %s -> %s" % (p, dest / name))
        print("  开始时间：%s" % datetime.now().strftime("%H:%M:%S"))
        rc = subprocess.call(cmd)
        print("  结束：%s｜robocopy 返回码 %d（0-7 为正常）" % (datetime.now().strftime("%H:%M:%S"), rc))
        if rc >= 8:
            print("！robocopy 报告错误，请查看 %s" % log)
            return 5
    print("\n完成：%s" % dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
