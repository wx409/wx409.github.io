# -*- coding: utf-8 -*-
"""从微博（yt-dlp）取 ELLE007 晚安图书馆 8 期的真实发布日期，写回 voice_corpus。

不推算、不猜测：日期来源是平台自身的 upload_date 元数据。
产出：E:\wx\声音素材库\manifest\elle_dates.json（供 build_voice_corpus 读取）
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIB = r'E:\wx\声音素材库'
OUT = os.path.join(LIB, 'manifest', 'elle_dates.json')

POSTS = [
    ('elle_wanan', '4693045729824142', '发刊词'),
    ('elle_p1', '4695935270257911', '第1期'),
    ('elle_p2', '4708598360051220', '第2期'),
    ('elle_p3', '4722751702567391', '第3期'),
    ('elle_p4', '4746303512512402', '第4期'),
    ('elle_p5', '5258305620151102', '第5期'),
    ('elle_p6', '5266261169672160', '第6期'),
    ('elle_p7', '5287004691764499', '第7期'),
]
UID = '2827620084'

out = {}
for sid, mid, label in POSTS:
    url = 'https://weibo.com/%s/%s' % (UID, mid)
    r = subprocess.run([sys.executable, '-m', 'yt_dlp', '--skip-download',
                        '--print', '%(upload_date)s|%(title)s', url],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    line = ''
    for ln in (r.stdout or '').splitlines():
        if '|' in ln and re.match(r'\d{8}', ln.strip()):
            line = ln.strip()
    if line:
        d, title = line.split('|', 1)
        date = '%s-%s-%s' % (d[:4], d[4:6], d[6:8])
        out[sid] = {'date': date, 'title': title.strip(), 'post_id': mid, 'label': label,
                    'source_url': url, 'date_source': 'weibo upload_date (yt-dlp)'}
        print('  %-12s %-10s %s  %s' % (sid, label, date, title.strip()[:38]))
    else:
        out[sid] = {'date': '', 'title': '', 'post_id': mid, 'label': label,
                    'source_url': url, 'date_source': 'unavailable'}
        print('  %-12s %-10s ✗ 未取到' % (sid, label))

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
print('\n[写]', OUT)
ok = sum(1 for v in out.values() if v['date'])
print('[OK] 取到日期 %d / %d' % (ok, len(out)))
