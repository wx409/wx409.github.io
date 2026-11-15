#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音批量下载：读 video_ids.txt，逐条用 yt-dlp（带本地 cookie）下载。

用法：
  python -X utf8 project_b/douyin_download.py --limit 1     # 先试 1 条
  python -X utf8 project_b/douyin_download.py               # 全部
产出：E:\\wx\\论文素材_王晰作传\\抖音\\<日期>_<id>.mp4 + _download_log.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

IDS = Path(r"E:\wx\论文素材_王晰作传\抖音\video_ids.txt")
COOK = Path(r"E:\wx\论文素材_王晰作传\抖音\douyin_cookies.txt")
OUT = Path(r"E:\wx\论文素材_王晰作传\抖音")
LOG = OUT / "_download_log.json"


def main() -> int:
    limit = 0
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    if not IDS.exists():
        print("缺 video_ids.txt：", IDS)
        return 2
    ids = [l.strip() for l in IDS.read_text(encoding="utf-8").splitlines() if l.strip().isdigit()]
    if limit:
        ids = ids[:limit]
    print(f"待下载 {len(ids)} 条")

    ok, fail = [], []
    for i, vid in enumerate(ids, 1):
        url = f"https://www.douyin.com/video/{vid}"
        cmd = ["yt-dlp", "--cookies", str(COOK), "--no-warnings",
               "--merge-output-format", "mp4",
               "-o", str(OUT / "%(upload_date>%Y%m%d|unknown)s_%(id)s.%(ext)s"), url]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok.append(vid)
            print(f"[{i}/{len(ids)}] OK {vid}")
        else:
            fail.append(vid)
            tail = (r.stderr or "").strip().splitlines()[-1:] or [""]
            print(f"[{i}/{len(ids)}] FAIL {vid} | {tail[0][:80]}")

    rec = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "ok": len(ok), "fail": len(fail),
           "ok_ids": ok, "fail_ids": fail}
    LOG.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n成功 {len(ok)}｜失败 {len(fail)}｜日志 {LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
