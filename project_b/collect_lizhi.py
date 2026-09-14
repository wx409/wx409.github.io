# -*- coding: utf-8 -*-
"""荔枝FM「王晰的低音时间」采集器（vodapi，免登录）。

接口（从 Next.js JS 包中挖出）：
  https://m.lizhi.fm/vodapi/user/<userId>?pageNo=N&pageSize=M   → 剧集清单
产出一为元数据 data/radio_lizhi.json，可选下载音频。

用法：python -X utf8 project_b\collect_lizhi.py [--download]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = r'E:\wx\声音素材库'
MEDIA = os.path.join(LIB, 'media')
UID = '2519182403760091180'
HOST = 'https://m.lizhi.fm'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
      'Referer': 'https://www.lizhi.fm/'}


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25)
    return json.loads(r.read().decode('utf-8', 'replace'))


def find_audio_url(item):
    """在返回结构里找音频直链（字段名可能是 audioUrl/url/playUrl 等）。"""
    for k in ('audioUrl', 'audio_url', 'url', 'playUrl', 'play_url', 'src', 'voiceUrl'):
        v = item.get(k)
        if isinstance(v, str) and v.startswith('http'):
            return v
    for k, v in item.items():
        if isinstance(v, dict):
            r = find_audio_url(v)
            if r:
                return r
    return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--pages', type=int, default=20)
    a = ap.parse_args()

    # 主播信息
    info = get('%s/vodapi/user/infoById?userId=%s' % (HOST, UID))
    usr = info.get('user') or {}
    print('主播: %s | 声音数(平台声明): %s | 播放 %s | 粉丝 %s'
          % (usr.get('userName'), usr.get('voiceCount'), usr.get('playCount'), usr.get('fansCount')))
    print('签名: %s' % usr.get('signature'))

    # 逐页取清单
    items, seen = [], set()
    for pno in range(1, a.pages + 1):
        try:
            d = get('%s/vodapi/user/%s?pageNo=%d&pageSize=50' % (HOST, UID, pno))
        except Exception as e:
            print('  第 %d 页失败: %s' % (pno, str(e)[:60]))
            break
        data = d.get('data') or []
        new = 0
        for it in data:
            vi = it.get('voiceInfo') or {}
            vp = it.get('voicePlayProperty') or {}
            vx = it.get('voiceExProperty') or {}
            vid = str(vi.get('voiceId') or '')
            if not vid or vid in seen:
                continue
            seen.add(vid)
            new += 1
            ct = vi.get('createTime')
            items.append({
                'voiceId': vid,
                'title': vi.get('name'),
                'duration_s': vi.get('duration'),
                'createTime': (datetime.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M')
                               if isinstance(ct, (int, float)) and ct else ''),
                'playCnt': vx.get('replayCount'),
                'likeCnt': vx.get('laudedCount'),
                'commentCount': vx.get('commentCount'),
                'cover': vi.get('imageUrl'),
                'audioUrl': vp.get('trackUrl') or '',
                'url': 'https://www.lizhi.fm/voice/%s' % vid,
            })
        print('  第 %d 页: %d 条（新增 %d，累计 %d）' % (pno, len(data), new, len(items)))
        if not data or new == 0:
            break

    print('\n共取回 %d 条' % len(items))
    for x in items[:6]:
        print('  %s | %-40s | %ss | %s' % (x['createTime'], str(x['title'])[:40],
                                            x['duration_s'], '有直链' if x['audioUrl'] else '无直链'))

    doc = {
        'schema': 'radio_lizhi v1',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'note': '荔枝FM「王晰的低音时间」剧集清单（vodapi，免登录）；音频仅本地留存',
        'anchor': usr.get('userName'), 'userId': UID, 'band': usr.get('band'),
        'declared_voice_count': usr.get('voiceCount'),
        'fetched_count': len(items),
        'voices': items,
    }
    p = os.path.join(ROOT, 'data', 'radio_lizhi.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))
    print('\n[写]', p)

    if not a.download:
        return 0
    outdir = os.path.join(MEDIA, 'lizhi_diyin')
    os.makedirs(outdir, exist_ok=True)
    ok = fail = 0
    for i, x in enumerate(items, 1):
        u = x.get('audioUrl')
        if not u:
            fail += 1
            continue
        safe = ''.join(c for c in str(x['title'] or x['voiceId']) if c not in '\\/:*?"<>|')[:44]
        dest = os.path.join(outdir, '%02d_%s.m4a' % (i, safe))
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            ok += 1
            continue
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180)
            with io.open(dest, 'wb') as w:
                while True:
                    b = r.read(1 << 16)
                    if not b:
                        break
                    w.write(b)
            ok += 1
            print('  ✔ %2d %s (%.1f MB)' % (i, safe[:34], os.path.getsize(dest) / 1e6))
        except Exception as e:
            fail += 1
            print('  ✗ %2d %s | %s' % (i, safe[:30], str(e)[:50]))
    print('\n[OK] 下载 %d / 失败 %d' % (ok, fail))
    return 0


if __name__ == '__main__':
    sys.exit(main())
