# -*- coding: utf-8 -*-
"""喜马拉雅音频下载器（走 www.ximalaya.com/revision/play/tracks 公开接口取直链）。

- 只下载到本地 E:\\wx\\声音素材库\\media\\<id>\\，不入 git、不上线
- 元数据（名称/时长/专辑/创建月/直链）写回 manifest 的 verified 字段
- 无 src 的条目（如节目形态）记录为 no_direct_url，并给出替代方案

用法：python -X utf8 project_b\download_ximalaya.py [--ids 544193351,283181641] [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = r'E:\wx\声音素材库'
MANIFEST = os.path.join(LIB, 'manifest', 'media_manifest.json')
MEDIA = os.path.join(LIB, 'media')

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
      'Referer': 'https://www.ximalaya.com/'}

# manifest 里的 id → 喜马拉雅 trackId
XM = {
    'xmly_544193351': '544193351',
    'xmly_283181641': '283181641',
    'xmly_382124733': '382124733',
    'xmly_623231068': '623231068',
}


def tracks(ids):
    u = 'https://www.ximalaya.com/revision/play/tracks?trackIds=' + ','.join(ids)
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
    return json.loads(r.read().decode('utf-8', 'replace'))


def dl(url, dest):
    import ssl
    url = url.replace('http://', 'https://', 1)
    req = urllib.request.Request(url, headers=UA)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r, io.open(dest, 'wb') as w:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            w.write(b)
    return os.path.getsize(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', default=None, help='manifest id 列表（逗号分隔）；默认全部喜马拉雅项')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    doc = json.loads(io.open(MANIFEST, encoding='utf-8').read())
    items = doc['items']
    want = set(a.ids.split(',')) if a.ids else set(XM)
    todo = [x for x in items if x['id'] in want and x['id'] in XM]

    info = tracks([XM[x['id']] for x in todo])
    by_id = {str(t.get('trackId')): t for t in
             (info.get('data') or {}).get('tracksForAudioPlay') or []}

    total = 0
    for x in todo:
        t = by_id.get(XM[x['id']])
        if not t:
            x['verified'] = dict(x.get('verified') or {}, error='接口未返回该 trackId')
            continue
        x['verified'] = {
            'trackName': t.get('trackName'), 'duration_s': t.get('duration'),
            'albumName': t.get('albumName'), 'albumId': t.get('albumId'),
            'createTime': t.get('createTime'), 'updateTime': t.get('updateTime'),
            'isPaid': t.get('isPaid'), 'src': t.get('src'),
        }
        if not t.get('src'):
            x['status'] = 'no_direct_url'
            x['blocked_reason'] = ('平台未返回直链：该条目为节目形态或付费专辑曲目 '
                                   '（专辑曲目列表接口返回 0 首，需喜马拉雅登录态）')
            print('⏭ %-20s 无直链（需登录/付费）: %s'
                  % (x['id'], str(t.get('trackName'))[:40]))
            continue
        outdir = os.path.join(MEDIA, x['id'])
        os.makedirs(outdir, exist_ok=True)
        ext = '.m4a' if '.m4a' in t['src'] else '.aac'
        fname = '%s_%s%s' % (x['id'], t.get('trackName', 'audio').replace('/', '_')[:40], ext)
        dest = os.path.join(outdir, fname)
        if a.check:
            print('  [check] %s → %s' % (x['id'], os.path.basename(dest)))
            continue
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print('  ⏭ 已存在 %s (%.1f MB)' % (os.path.basename(dest), os.path.getsize(dest) / 1e6))
        else:
            n = dl(t['src'], dest)
            print('  ✔ %s (%.1f MB, %s 秒)' % (os.path.basename(dest), n / 1e6, t.get('duration')))
            total += n
        x['local_files'] = [{'file': os.path.relpath(dest, LIB).replace('\\', '/'),
                             'size_mb': round(os.path.getsize(dest) / 1e6, 1)}]
        x['status'] = 'downloaded'
        x['downloaded_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    if not a.check:
        doc['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        io.open(MANIFEST, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))
    print('\n[OK] 本次下载 %.1f MB' % (total / 1e6))
    return 0


if __name__ == '__main__':
    sys.exit(main())
