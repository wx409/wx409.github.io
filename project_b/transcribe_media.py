# -*- coding: utf-8 -*-
"""声音素材批量转写（faster-whisper，GPU）。

- 输入：E:\\wx\\声音素材库\\media\\**\\*（.m4a/.aac/.mp3/.wav/.mp4，含从微博下载的）
        + project_b 下载器落下的其他媒体
- 模型：本地缓存的 faster-whisper-large-v3-turbo（GPU float16；无 CUDA 回退 CPU int8）
- 产出：E:\\wx\\声音素材库\\transcripts\\<id>\\<name>.txt        可读全文
        E:\\wx\\声音素材库\\transcripts\\<id>\\<name>.segments.json 带时间戳分段（机读）
- 幂等：已有 .txt 且非空则跳过
- 媒体原件不入 git；转写稿整理后可作为语料入库

用法：
  python -X utf8 project_b\transcribe_media.py --list
  python -X utf8 project_b\transcribe_media.py --all
  python -X utf8 project_b\transcribe_media.py --only yytsg_bili
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = r'E:\wx\声音素材库'
MEDIA = os.path.join(LIB, 'media')
TRANS = os.path.join(LIB, 'transcripts')
MANIFEST = os.path.join(LIB, 'manifest', 'media_manifest.json')
MODEL_PATH = r'E:\work\代码\录音转写\models\faster-whisper-large-v3-turbo'
MODEL_NAME = MODEL_PATH if os.path.isdir(MODEL_PATH) else 'mobiuslabsgmbh/faster-whisper-large-v3-turbo'
EXTS = ('.m4a', '.aac', '.mp3', '.wav', '.mp4', '.flac', '.ogg')


def log(*a):
    print(*a, flush=True)


def files_of(series_dir):
    out = []
    for root, _dirs, fs in os.walk(series_dir):
        for f in fs:
            if f.lower().endswith(EXTS):
                out.append(os.path.join(root, f))
    return sorted(out)


def load_model():
    from faster_whisper import WhisperModel
    try:
        import torch
        use_cuda = torch.cuda.is_available()
    except Exception:
        use_cuda = False
    if use_cuda:
        log('  加载模型（GPU float16）:', MODEL_NAME)
        return WhisperModel(MODEL_NAME, device='cuda', compute_type='float16')
    log('  加载模型（CPU int8）:', MODEL_NAME)
    return WhisperModel(MODEL_NAME, device='cpu', compute_type='int8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--only', default=None)
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    os.makedirs(TRANS, exist_ok=True)
    series = sorted(d for d in os.listdir(MEDIA) if os.path.isdir(os.path.join(MEDIA, d)))
    if a.only:
        series = [d for d in series if d == a.only]

    if a.list:
        for s in series:
            fs = files_of(os.path.join(MEDIA, s))
            done = 0
            for f in fs:
                if os.path.exists(os.path.join(TRANS, s, os.path.splitext(os.path.basename(f))[0] + '.txt')):
                    done += 1
            log('  %-24s 媒体 %3d | 已转写 %3d' % (s, len(fs), done))
        return 0

    todo = []
    for s in series:
        for f in files_of(os.path.join(MEDIA, s)):
            base = os.path.splitext(os.path.basename(f))[0]
            txt = os.path.join(TRANS, s, base + '.txt')
            if os.path.exists(txt) and os.path.getsize(txt) > 0:
                continue
            todo.append((s, f, base))
    log('=' * 70)
    log('待转写 %d 个文件' % len(todo))
    log('=' * 70)
    if not todo:
        log('[OK] 无待转写文件')
        return 0
    if not (a.all or a.only):
        log('（加 --all 开始转写）')
        return 0

    model = load_model()
    ok = fail = 0
    t0 = time.time()
    for i, (s, f, base) in enumerate(todo, 1):
        os.makedirs(os.path.join(TRANS, s), exist_ok=True)
        log('[%d/%d] %s / %s' % (i, len(todo), s, os.path.basename(f)))
        try:
            ts = time.time()
            # 2026-09-14 实测教训：这批素材（低音人声 + 背景乐）用 vad_filter=True 会被
            # 判成静音而滤掉正文 —— 133 秒音频只出 3 段/21 字；关闭 VAD 后 28 段/205 字。
            # 故全库统一 **vad_filter=False**，靠 faster-whisper 自身的静音切分。
            segs, info = model.transcribe(
                f, language='zh', beam_size=5, vad_filter=False,
                condition_on_previous_text=False)
            rows = []
            for seg in segs:
                t = (seg.text or '').strip()
                if t:
                    rows.append({'start': round(float(seg.start), 2),
                                 'end': round(float(seg.end), 2), 'text': t})
            txt = '\n'.join(r['text'] for r in rows)
            io.open(os.path.join(TRANS, s, base + '.txt'), 'w', encoding='utf-8').write(txt)
            io.open(os.path.join(TRANS, s, base + '.segments.json'), 'w', encoding='utf-8').write(
                json.dumps({'schema': 'media_transcript v1', 'series': s,
                            'media': os.path.relpath(f, LIB).replace('\\', '/'),
                            'model': MODEL_NAME, 'language': info.language,
                            'duration_s': round(info.duration or 0, 1),
                            'transcribed_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'n_segments': len(rows), 'segments': rows},
                           ensure_ascii=False, indent=1))
            log('    ✔ %d 段 / %d 字 / %.1fs' % (len(rows), len(txt), time.time() - ts))
            ok += 1
        except Exception as e:
            log('    ✗ 失败:', str(e)[:160])
            fail += 1
    log('=' * 70)
    log('[OK] 成功 %d / 失败 %d | 总耗时 %.1f 分钟' % (ok, fail, (time.time() - t0) / 60))
    return 0


if __name__ == '__main__':
    sys.exit(main())
