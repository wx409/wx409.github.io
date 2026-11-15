#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「谱子有、站内未测」的曲目批量加入待测清单（调用 添加待测曲目.py）。

用法：python -X utf8 project_b/batch_add_untested.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\wx\论文素材_王晰作传\音域分析")
LIST = Path(r"E:\wx\论文素材_王晰作传\曲谱_网友扒谱\未测曲目.json")
LOG = Path(r"E:\wx\论文素材_王晰作传\音域分析\待测_批量加入日志.txt")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    items = json.loads(LIST.read_text(encoding="utf-8"))["untested"]
    if a.limit:
        items = items[: a.limit]
    ok, fail = [], []
    logs = []
    for i, title in enumerate(items, 1):
        cmd = [sys.executable, "-X", "utf8", "添加待测曲目.py", title]
        if a.dry:
            cmd.append("--dry")
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        tail = (r.stdout or "").strip().splitlines()[-1:] or ["(无输出)"]
        status = "OK" if r.returncode == 0 else "FAIL"
        (ok if r.returncode == 0 else fail).append(title)
        logs.append(f"[{status}] {title} | {tail[0][:120]}")
        print(f"[{i}/{len(items)}] {status} {title}")
    LOG.write_text("\n".join(logs), encoding="utf-8")
    print(f"\n成功 {len(ok)}｜失败 {len(fail)}｜日志 {LOG}")
    if fail:
        print("失败:", fail[:10])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
