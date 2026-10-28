#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""剩余现场批次：为每场挑「曲目最多的子目录」→ 硬链接到 _staging_现场/<tag> → 逐场分析。

tag 用纯 ASCII（日期+序号），避免 CJK 路径问题；跑完删锁。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(r'E:\wx\论文素材_王晰作传\现场录音-小卡带')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
EXE = Path(r'E:\wx\论文素材_王晰作传\音域分析\批量专辑音域.py')
LOCK = Path(r'D:\wx409.github.io\temp\longjob.lock')
SUMMARY = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json')
DONE_ALBUMS = {'haikou_20191116', 'nanjing_20240127', 'hangzhou_20241221'}


def pick_files(show_dir: Path):
    subs = [d for d in show_dir.iterdir() if d.is_dir()]
    best, best_n = None, 0
    for d in subs:
        fs = [f for f in d.rglob('*') if f.suffix.lower() in ('.wav', '.flac')]
        if len(fs) > best_n:
            best, best_n = d, len(fs)
    if best_n >= 5:
        return [f for f in best.rglob('*') if f.suffix.lower() in ('.wav', '.flac')]
    top = [f for f in show_dir.iterdir() if f.is_file() and f.suffix.lower() in ('.wav', '.flac')]
    return top


def main() -> None:
    shows = sorted([d for d in BASE.iterdir() if d.is_dir()])
    LOCK.write_text(f'batch {datetime.now():%F %T}\n', encoding='utf-8')
    done = set()
    if SUMMARY.exists():
        done = {s['album'] for s in json.loads(SUMMARY.read_text(encoding='utf-8'))['songs']}
    tags = []
    for i, d in enumerate(shows, 1):
        m = d.name[:8]
        tag = f's{i:02d}_{m}'
        if tag in done or tag in DONE_ALBUMS:
            continue
        files = pick_files(d)
        if not files:
            print('跳过（无逐曲音频）', d.name, flush=True)
            continue
        dst = STAGE / tag
        dst.mkdir(parents=True, exist_ok=True)
        for f in files:
            t = dst / f.name
            if t.exists():
                continue
            try:
                os.link(f, t)
            except Exception:
                import shutil
                shutil.copy2(f, t)
        tags.append(tag)
        print(f'备好 {tag}: {len(files)} 首', flush=True)

    for tag in tags:
        print('=== 开始', tag, flush=True)
        r = subprocess.run([sys.executable, '-X', 'utf8', str(EXE),
                            '--root', str(STAGE), '--albums', tag],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        tail = (r.stdout or '').strip().splitlines()[-2:]
        print('\n'.join(tail), flush=True)
        if r.returncode != 0:
            print('失败:', (r.stderr or '')[-200:], flush=True)
    print('批次结束', flush=True)
    if LOCK.exists():
        LOCK.unlink()


if __name__ == '__main__':
    main()
