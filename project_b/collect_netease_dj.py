# -*- coding: utf-8 -*-
"""网易云 DJ 电台采集器（走 music.163.com 公开 api 路径，登录态可选）。

- 列表：/api/dj/program/byradio?radioId=<id>&limit=100
- 音频：/api/song/enhance/player/url?ids=[songId]&br=128000（返回直链，可能受版权/地区限制）
- 产出：data/radio_netease_dj_<radioId>.json（元数据）+ media/ 下音频（能下的）
- 只本地留存，不入 git

用法：python -X utf8 project_b\collect_netease_dj.py --radio 792978415 [--download]
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
MEDIA = os.path.join(LIB, 'media')
MANIFEST = os.path.join(LIB, 'manifest', 'media_manifest.json')

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
      'Referer': 'https://music.163.com/'}


def api(path):
    r = urllib.request.urlopen(urllib.request.Request(
        'https://music.163.com' + path, headers=UA), timeout=25)
    return json.loads(r.read().decode('utf-8', 'replace'))


def song_url(sid):
    d = api('/api/song/enhance/player/url?ids=[%s]&br=128000' % sid)
    for x in (d.get('data') or []):
        if x.get('url'):
            return x['url'], x.get('size'), x.get('type')
    return None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--radio', default='792978415')
    ap.add_argument('--download', action='store_true')
    a = ap.parse_args()

    d = api('/api/dj/program/byradio?radioId=%s&limit=200&offset=0' % a.radio)
    progs = d.get('programs') or []
    print('电台 %s | count=%s | 取回 %d 期' % (a.radio, d.get('count'), len(progs)))

    out = []
    for p in progs:
        ms = p.get('mainSong') or {}
        out.append({
            'programId': p.get('id'),
            'name': p.get('name'),
            'songId': ms.get('id'),
            'duration_ms': p.get('duration'),
            'createTime': (datetime.fromtimestamp((p.get('createTime') or 0) / 1000)
                           .strftime('%Y-%m-%d') if p.get('createTime') else None),
            'serialNum': p.get('serialNum'),
            'coverUrl': p.get('coverUrl'),
            'artists': [x.get('name') for x in (ms.get('artists') or [])],
        })
    out.sort(key=lambda x: (x.get('createTime') or '', x.get('serialNum') or 0))
    for x in out[:5]:
        print('   %s #%s %s (%s 秒)' % (x['createTime'], x['serialNum'],
                                        str(x['name'])[:40],
                                        int((x['duration_ms'] or 0) / 1000)))

    doc = {
        'schema': 'radio_netease_dj v1',
        'radio_id': a.radio,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'note': '网易云音乐 DJ 电台（饭制存档）元数据；音频仅本地留存',
        'declared_count': d.get('count'),
        'fetched_count': len(out),
        'programs': out,
    }
    p = os.path.join(ROOT, 'data', 'radio_netease_dj_%s.json' % a.radio)
    io.open(p, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))
    print('[写]', p)

    if not a.download:
        return 0

    outdir = os.path.join(MEDIA, 'netease_dj_%s' % a.radio)
    os.makedirs(outdir, exist_ok=True)
    ok = fail = 0
    for i, x in enumerate(out, 1):
        if not x.get('songId'):
            continue
        dest = os.path.join(outdir, '%02d_%s.m4a' % (
            x.get('serialNum') or i, str(x['name']).replace('/', '_')[:44]))
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            ok += 1
            continue
        u, size, typ = song_url(x['songId'])
        if not u:
            fail += 1
            print('   ⏭ #%s 无直链: %s' % (x.get('serialNum'), str(x['name'])[:32]))
            continue
        try:
            req = urllib.request.Request(u.replace('http://', 'https://', 1), headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r, io.open(dest, 'wb') as w:
                while True:
                    b = r.read(1 << 16)
                    if not b:
                        break
                    w.write(b)
            ok += 1
            print('   ✔ #%s %s (%.1f MB)' % (x.get('serialNum'),
                                             os.path.basename(dest)[:40],
                                             os.path.getsize(dest) / 1e6))
        except Exception as e:
            fail += 1
            print('   ✗ #%s %s' % (x.get('serialNum'), str(e)[:60]))
    print('\n[OK] 下载成功 %d / 失败 %d' % (ok, fail))
    return 0


if __name__ == '__main__':
    sys.exit(main())
