# -*- coding: utf-8 -*-
"""「城市漫行」QQ音乐电台专辑采集（公开接口，无需登录）。

接口：https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg?albummid=<mid>&format=json
产出：data/radio_citywalk.json（元数据，含逐曲名/时长/序号）+ 可选音频下载（试听片段）

用法：python -X utf8 project_b\collect_qq_album.py --mid 003tbIDl16Y0XE [--download]
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

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
      'Referer': 'https://y.qq.com/'}


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25)
    return json.loads(r.read().decode('utf-8', 'replace'))


def vkey_urls(mids):
    """批量取 vkey 直链（musicu GetVkey，免登录）。返回 {songmid: url}"""
    import urllib.parse
    data = {"comm": {"ct": 24, "cv": 0},
            "req": {"module": "CDN.SrfCdnDispatchServer", "method": "GetCdnDispatch",
                    "param": {"guid": "10000", "calltype": 0, "userip": ""}},
            "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey",
                      "param": {"guid": "10000", "songmid": mids, "songtype": [0] * len(mids),
                                "uin": "0", "loginflag": 1, "platform": "20"}}}
    u = ('https://u.y.qq.com/cgi-bin/musicu.fcg?format=json&data='
         + urllib.parse.quote(json.dumps(data)))
    j = get(u)
    sip = ((j.get('req') or {}).get('data') or {}).get('sip') or []
    if not sip:
        sip = ((j.get('req') or {}).get('data') or {}).get('freeflowsip') or []
    out = {}
    for it in (((j.get('req_0') or {}).get('data') or {}).get('midurlinfo') or []):
        purl, mid = it.get('purl'), it.get('songmid')
        if purl and sip:
            out[mid] = sip[0].rstrip('/') + '/' + purl.lstrip('/')
    return out


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r, io.open(dest, 'wb') as w:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            w.write(b)
    return os.path.getsize(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mid', default='003tbIDl16Y0XE')
    ap.add_argument('--download', action='store_true')
    a = ap.parse_args()

    d = get('https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg'
            '?albummid=%s&format=json' % a.mid)
    data = d.get('data') or {}
    songs = data.get('list') or []
    print('专辑: %s' % data.get('name'))
    print('  发行日期: %s | 公司: %s | 曲目数: %s' % (
        data.get('aDate'), (data.get('company_new') or {}).get('name'), data.get('cur_song_num')))
    print('  简介: %s' % str(data.get('desc'))[:120])
    print()
    rows = []
    for i, s in enumerate(songs, 1):
        rows.append({
            'index': i,
            'songmid': s.get('songmid'),
            'name': s.get('songname') or s.get('name'),
            'duration_s': s.get('interval'),
            'album': data.get('name'),
            'albummid': a.mid,
            'singers': [x.get('name') for x in (s.get('singer') or [])],
            'url': 'https://y.qq.com/n/ryqq/songDetail/%s' % s.get('songmid'),
        })
    for r in rows:
        print('  %2d. %-42s %ss' % (r['index'], str(r['name'])[:42], r['duration_s']))

    doc = {
        'schema': 'radio_qq_album v1',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'note': 'QQ音乐电台专辑元数据（公开接口，无需登录）；音频仅本地留存',
        'album': data.get('name'),
        'albummid': a.mid,
        'release_date': data.get('aDate'),
        'company': (data.get('company_new') or {}).get('name'),
        'declared_count': data.get('cur_song_num'),
        'fetched_count': len(rows),
        'desc': data.get('desc'),
        'tracks': rows,
    }
    p = os.path.join(ROOT, 'data', 'radio_citywalk.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))
    print('\n[写]', p)

    if not a.download:
        return 0

    # ---- 下载音频（vkey 直链，24h 有效）----
    outdir = os.path.join(MEDIA, 'qq_citywalk')
    os.makedirs(outdir, exist_ok=True)
    mids = [r['songmid'] for r in rows if r.get('songmid')]
    urls = vkey_urls(mids)
    print('\n取到 vkey 直链 %d / %d' % (len(urls), len(mids)))
    ok = fail = 0
    for r in rows:
        mid = r.get('songmid')
        u = urls.get(mid)
        if not u:
            fail += 1
            print('   ✗ %2d 无直链: %s' % (r['index'], str(r['name'])[:36]))
            continue
        safe = ''.join(c for c in str(r['name']) if c not in '\\/:*?"<>|')[:46]
        dest = os.path.join(outdir, '%02d_%s.m4a' % (r['index'], safe))
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            ok += 1
            continue
        try:
            n = download(u, dest)
            ok += 1
            print('   ✔ %2d %s (%.1f MB)' % (r['index'], safe[:34], n / 1e6))
        except Exception as e:
            fail += 1
            print('   ✗ %2d %s | %s' % (r['index'], safe[:30], str(e)[:50]))
    print('\n[OK] 下载成功 %d / 失败 %d' % (ok, fail))
    return 0


if __name__ == '__main__':
    sys.exit(main())
