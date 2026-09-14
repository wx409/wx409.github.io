# -*- coding: utf-8 -*-
"""转写稿 ASR 错字校正（幂等）。

2026-09-14 发现：faster-whisper 把「王晰」听成「王熙」共 63 次、「晰哥」听成「西哥」1 次。
低音人声 + 背景乐场景下，生僻字人名是典型 ASR 弱点。

- 治本：transcribe_media.py 已加 initial_prompt 热词
- 治标：本脚本对已产出转写稿做定向替换（只改确证错字，不做模糊匹配）

用法：python -X utf8 project_b\fix_asr_names.py [--check]
"""
from __future__ import annotations

import argparse
import io
import os
import sys

TRANS = r'E:\wx\声音素材库\transcripts'

# 只收**确证**的错字；宁少不错（模糊替换会伤原文）
FIXES = [
    ('王熙', '王晰'),
    ('西哥', '晰哥'),
    ('低音炮', '低音炮'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    total_files = total_hits = 0
    for root, _d, fs in os.walk(TRANS):
        if 'fulltext' in root:
            continue
        for f in fs:
            if not f.endswith('.txt'):
                continue
            p = os.path.join(root, f)
            t = io.open(p, encoding='utf-8').read()
            new = t
            n = 0
            for a_, b_ in FIXES:
                if a_ != b_ and a_ in new:
                    n += new.count(a_)
                    new = new.replace(a_, b_)
            if n:
                total_files += 1
                total_hits += n
                print('  %-52s %d 处' % (os.path.relpath(p, TRANS)[:52], n))
                if not a.check:
                    io.open(p, 'w', encoding='utf-8').write(new)
    print('\n文件 %d 个 / 替换 %d 处%s' % (total_files, total_hits,
                                       '（check 模式未写入）' if a.check else ''))
    return 1 if (a.check and total_hits) else 0


if __name__ == '__main__':
    sys.exit(main())
