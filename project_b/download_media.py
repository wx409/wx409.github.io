# -*- coding: utf-8 -*-
"""声音素材下载器：B站（yt-dlp）+ 微博（yt-dlp）+ 通用直链。

- 媒体落 E:\\wx\\声音素材库\\media\\<series_id>\\，文件名带出处 id，便于回溯
- 下载完把实际文件名与大小写回 manifest 的 local_files 字段（幂等：已存在则跳过）
- 只下载到本地；不入 git、不上线

用法：
  python -X utf8 project_b\download_media.py --only yytsg_bili
  python -X utf8 project_b\download_media.py --all
  python -X utf8 project_b\download_media.py --list
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = r'E:\wx\声音素材库'
MANIFEST = os.path.join(LIB, 'manifest', 'media_manifest.json')
MEDIA = os.path.join(LIB, 'media')
FFMPEG = None

# 控制台默认 GBK 时，打印 ▶/✔ 等符号会 UnicodeEncodeError 中断整个下载（2026-09-14 踩过）。
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def ffmpeg_path():
    global FFMPEG
    if FFMPEG is None:
        try:
            import imageio_ffmpeg
            FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            FFMPEG = ''
    return FFMPEG


def load():
    with io.open(MANIFEST, encoding='utf-8') as f:
        return json.load(f)


def save(doc):
    doc['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    io.open(MANIFEST, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))


def ytdlp(url, outdir, name_tmpl, extra=None):
    """用 yt-dlp 下载；音频优先 m4a（体积小、转写够用）。"""
    os.makedirs(outdir, exist_ok=True)
    cmd = [sys.executable, '-m', 'yt_dlp',
           '--no-warnings', '--ignore-errors', '--no-overwrites',
           '-f', 'bestaudio/best',
           '-o', os.path.join(outdir, name_tmpl),
           '--print', 'after_move:filepath',
           url]
    if extra:
        cmd[1:1] = extra
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    files = [x.strip() for x in (r.stdout or '').splitlines() if x.strip()]
    return r.returncode, files, (r.stderr or '')[-500:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    doc = load()
    items = doc['items']
    if a.list:
        for x in items:
            n = len(x.get('local_files') or [])
            print('  %-24s %-10s files=%d %s' % (x['id'], x['platform'], n,
                                                 (x.get('verified') or {}).get('title', x['title'])[:40]))
        return 0

    targets = [x for x in items if (a.all or x['id'] == a.only)]
    if not targets:
        print('没有匹配项。用 --list 看 id。')
        return 1

    done_total = 0
    for x in targets:
        if x['platform'] not in ('bilibili', 'weibo'):
            print('⏭ %-24s 平台 %s 不支持 yt-dlp，跳过（需专用采集器）' % (x['id'], x['platform']))
            continue
        if not x.get('url'):
            print('⏭ %-24s 无 URL，跳过' % x['id'])
            continue
        outdir = os.path.join(MEDIA, x['id'])
        print('▶ %s → %s' % (x['id'], outdir))
        rc, files, err = ytdlp(x['url'], outdir, '%(playlist_index|)s%(title).80s [%(id)s].%(ext)s')
        print('  exit=%d 产出 %d 个文件' % (rc, len(files)))
        for f in files[:12]:
            print('   ', os.path.basename(f))
        if err.strip():
            print('  stderr:', err.strip()[:200])
        # 记录实际产物
        got = []
        for root, _dirs, fs in os.walk(outdir):
            for f in fs:
                p = os.path.join(root, f)
                got.append({'file': os.path.relpath(p, LIB).replace('\\', '/'),
                            'size_mb': round(os.path.getsize(p) / 1e6, 1)})
        x['local_files'] = sorted(got, key=lambda z: z['file'])
        x['downloaded_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        if x['local_files']:
            x['status'] = 'downloaded'
        done_total += len(x['local_files'])
        save(doc)
    print('\n[OK] 本次落盘文件 %d 个' % done_total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
