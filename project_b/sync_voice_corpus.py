# -*- coding: utf-8 -*-
"""把声音素材转写稿同步进 wx_textmine 语料库（幂等）。

- 命名约定：`<YYYY-MM-DD>_<HHMM>_<系列key>_<NNN>.txt`（与 工作室微博/百家号/少城时代 同构）
- 同时给 01_ingest.py 的 classify() 加 voice_media 源（本次已加 少城时代，这里再加声音素材）
- 只写文本；媒体原件留在 E:\\wx\\声音素材库

用法：python -X utf8 project_b\sync_voice_corpus.py [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'voice_corpus.json')
CORPUS = r'E:\wx\wx_textmine_corpus\声音素材'

# 系列 key → 语料文件名里用的短名（避免空格/斜杠）
SHORT = {
    'yytsg_bili': '音乐图书馆',
    'xwntj_bili': '晰望你听见',
    'netease_dj_792978415': '低音时间网易云',
    'xmly_544193351': '喜马拉雅想念雪',
    'xmly_283181641': '喜马拉雅万物千景',
    'xmly_623231068': '喜马拉雅从前慢',
    'weibo_kangyi_jiashu': '微博抗疫家书',
    'weibo_520_shencongwen': '微博520情书',
    'lizhi_diyin': '低音时间荔枝',
    'qq_citywalk': '城市漫行',
    'elle_wanan': 'ELLE晚安图书馆发刊词',
}
for i in range(1, 8):
    SHORT['elle_p%d' % i] = 'ELLE晚安图书馆第%d期' % i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    doc = json.loads(io.open(SRC, encoding='utf-8').read())
    items = doc.get('items') or []
    os.makedirs(CORPUS, exist_ok=True)
    exist = set(os.listdir(CORPUS))
    # ⚠️ 必须**按内容判重**：早先按"下一个可用序号"判重会每次都新建 _002/_003…
    # （2026-09-14 踩过：连跑两次把 98 个文件变成 196 个）。
    # 这里用「正文前 120 字去空白」做指纹，指纹相同即视为已入库。
    def fp(t):
        return re.sub(r'\s+', '', str(t or ''))[:120]

    existing_fp = {}
    used = defaultdict(int)
    for f in exist:
        m = re.match(r'^(\d{4}-\d{2}-\d{2})_(\d{4})_(.+)_(\d{3})\.txt$', f)
        if m:
            used[(m.group(1), m.group(2), m.group(3))] = max(
                used[(m.group(1), m.group(2), m.group(3))], int(m.group(4)))
        try:
            existing_fp[fp(io.open(os.path.join(CORPUS, f), encoding='utf-8').read())] = f
        except Exception:
            pass

    added = []
    skipped_dup = 0
    for x in sorted(items, key=lambda z: (z.get('series') or '', z.get('episode') or 0)):
        series = x.get('series') or 'unknown'
        short = SHORT.get(series, re.sub(r'[\\/:*?"<>|\s]+', '_', x.get('series_name') or series)[:14])
        date = (x.get('date') or '')[:10]
        if not re.match(r'\d{4}-\d{2}-\d{2}$', date):
            date = '1900-01-01'          # 未知日期用占位，便于后续补
        hm = '0000'
        text = x.get('text') or ''
        if not text.strip():
            continue
        if fp(text) in existing_fp:
            skipped_dup += 1
            continue
        key = (date, hm, short)
        used[key] += 1
        fn = '%s_%s_%s_%03d.txt' % (date, hm, short, used[key])
        added.append((fn, text))
        existing_fp[fp(text)] = fn
        exist.add(fn)

    print('语料条目 %d ｜ 目录已有 %d ｜ 需新增 %d' % (len(items), len(exist) - len(added), len(added)))
    for fn, _t in added[:8]:
        print('   +', fn)
    if len(added) > 8:
        print('   …另有 %d 个' % (len(added) - 8))
    if a.check:
        return 1 if added else 0
    for fn, text in added:
        io.open(os.path.join(CORPUS, fn), 'w', encoding='utf-8').write(text)
    print('[OK] 已写入 %d 个 txt → %s' % (len(added), CORPUS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
