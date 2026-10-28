#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""巡次归一 + 音频体检。

1) 以长表为唯一口径，为 37 个现场录音文件夹生成「日期 + 巡次 + 场次」新名（支持 --apply 重命名）
2) 逐场音频体检：格式/采样率/声道/时长/峰值/削波占比（抽样 5 秒估算）
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
import openpyxl
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
LONG = Path(r'E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx')
BASE = Path(r'E:\wx\论文素材_王晰作传\现场录音-小卡带')
OUT = Path(r'D:\wx409.github.io\data')
AUDIO_EXT = ('.flac', '.wav', '.mp3', '.m4a', '.ape')


def norm_date(s: str) -> str:
    m = re.match(r'(\d{4})[-/.]?(\d{1,2})[-/.]?(\d{1,2})', str(s))
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ''


def load_tours():
    wb = openpyxl.load_workbook(LONG, read_only=True)
    ws = wb['合并长表']
    tours = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        d = norm_date(r[1]) if r[1] else ''
        if not d:
            continue
        tour = (str(r[0]).strip() if r[0] else '')
        scene = (str(r[2]).strip() if r[2] else '')
        tours.setdefault(d, {"tour": tour, "scene": scene})
    return tours


def safe(name: str) -> str:
    # Windows 非法字符只这几个；ASCII 引号转中文引号，避免出现下划线
    name = name.replace('"', '“', 1).replace('"', '”')
    name = re.sub(r'[\\/:*?<>|]', '·', name)
    return re.sub(r'[·]{2,}', '·', name).strip('· ')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='真正重命名文件夹')
    args = ap.parse_args()

    tours = load_tours()
    dirs = sorted([d for d in BASE.iterdir() if d.is_dir()])
    mapping = []
    for d in dirs:
        m = re.match(r'^(\d{8})', d.name)
        if not m:
            continue
        day = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}"
        info = tours.get(day, {})
        tour = info.get('tour') or ''
        scene = info.get('scene') or ''
        city = scene if scene and scene not in ('nan', 'None') else ''
        if not city:
            mm = re.search(r'(?:王晰)?[^巡]*?(?:音乐会|签唱会|分享会)(.*?)$', d.name[8:])
            city = (mm.group(1).strip() if mm else d.name[8:]).replace('王晰', '')
        new = safe(f"{m.group(1)} {tour}·{city}".replace('··', '·'))
        mapping.append({"date": day, "old": d.name, "tour": tour, "scene": city, "new": new})

    (OUT / 'audio_folder_mapping.json').write_text(
        json.dumps({"count": len(mapping), "items": mapping}, ensure_ascii=False, indent=1), encoding='utf-8')
    for x in mapping:
        print(f"  {x['old'][:34]:34s} → {x['new']}")

    if args.apply:
        for x in mapping:
            src, dst = BASE / x['old'], BASE / x['new']
            if src.exists() and not dst.exists():
                src.rename(dst)
        print('重命名完成')

    # 音频体检
    rows = []
    for d in sorted([d for d in BASE.iterdir() if d.is_dir()]):
        files = [f for f in d.rglob('*') if f.is_file() and f.suffix.lower() in AUDIO_EXT]
        srs, fmts, durs, peaks, clips = set(), set(), 0.0, [], 0
        for f in files:
            try:
                info = sf.info(str(f))
            except Exception:
                continue
            srs.add(info.samplerate); fmts.add(info.subtype); durs += info.duration
            try:
                data, sr = sf.read(str(f), frames=int(5 * info.samplerate), dtype='float32', always_2d=True)
                a = np.abs(data).max()
                peaks.append(20 * np.log10(a + 1e-12))
                clips += int((np.abs(data) > 0.999).sum())
            except Exception:
                pass
        rows.append({"folder": d.name, "files": len(files), "minutes": round(durs / 60, 1),
                     "sr": ';'.join(map(str, sorted(srs))), "format": ';'.join(sorted(fmts)),
                     "peak_dbfs_max": round(max(peaks), 1) if peaks else None,
                     "clip_samples": clips})
    with open(OUT / 'audio_probe.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f'体检完成：{len(rows)} 场 → data/audio_probe.csv')


if __name__ == '__main__':
    main()
