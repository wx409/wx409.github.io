#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量删除《从现在 到未来》：数据层递归清理 + 备份 + 删除日志。

只删标题匹配这首歌的键/条目；其余结构不动。原始文件先备份到 data/_deleted_backup/。
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
DATA = ROOT / 'data'
BACKUP = DATA / '_deleted_backup' / '从现在到未来'
BACKUP.mkdir(parents=True, exist_ok=True)

VARIANTS = ('从现在到未来', '从现在 到未来', '从现在　到未来')
FILES = [
    'audio_assets.json', 'netease_catalog.json', 'netease_only.json',
    'phrase_bank.json', 'phrase_index.json', 'qq_singer_songs.json',
    'singles_inventory.json', 'song_playable.json',
    'research/singles_analysis.json', 'research/singles_bpm.json',
]


def match(s) -> bool:
    if not isinstance(s, str):
        return False
    return any(v in s for v in VARIANTS)


def prune(obj, path=''):
    """递归删除匹配条目，返回 (新对象, 删除记录)。"""
    removed = []
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = str(k)
            if match(ks):
                removed.append(f'{path}/{ks} (key)')
                continue
            nv, rm = prune(v, f'{path}/{ks}')
            out[k] = nv
            removed += rm
        return out, removed
    if isinstance(obj, list):
        out = []
        for i, v in enumerate(obj):
            if isinstance(v, (dict, str)) and match(json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v):
                # 只删"条目本身说的就是这首歌"的；避免误删引用它的长文本
                if isinstance(v, dict):
                    names = [str(v.get(k, '')) for k in ('name', 'title', 'song', '歌曲名称', '歌名')]
                    if any(match(n) for n in names):
                        removed.append(f'{path}[{i}] {names[:2]}')
                        continue
                elif match(v):
                    removed.append(f'{path}[{i}] {v[:30]}')
                    continue
            nv, rm = prune(v, f'{path}[{i}]')
            out.append(nv)
            removed += rm
        return out, removed
    return obj, removed


def main() -> None:
    log = {"song": "从现在 到未来", "at": datetime.now().isoformat(timespec='seconds'), "files": []}
    for rel in FILES:
        p = DATA / rel
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        if not any(v in raw for v in VARIANTS):
            continue
        bak = BACKUP / rel.replace('/', '__')
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, bak)
        obj = json.loads(raw)
        new, removed = prune(obj)
        p.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding='utf-8')
        log['files'].append({"file": rel, "removed": removed, "count": len(removed)})
        print(f'{rel}: 删除 {len(removed)} 处')
    (DATA / '_deleted_backup' / '从现在到未来_删除日志.json').write_text(
        json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')

    # 音频文件挪到备份区
    moved = []
    for base in (DATA.parent / '单曲音频', DATA.parent / '音域分析' / '网易云补_单曲'):
        pass
    for base in (Path(r'E:\wx\论文素材_王晰作传\单曲音频'), Path(r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲')):
        if not base.exists():
            continue
        for f in base.rglob('*'):
            if f.is_file() and f.suffix.lower() in ('.mp3', '.wav', '.flac') and match(f.stem):
                dst = BACKUP / 'audio' / f.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dst))
                moved.append(str(f))
    print('音频移至备份', len(moved), '个')


if __name__ == '__main__':
    main()
