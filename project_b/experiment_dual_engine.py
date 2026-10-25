#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双引擎分歧诊断 · 新实验（方案2）：先清单，再测量，再比较。

用法：
  python -X utf8 project_b/experiment_dual_engine.py manifest
  python -X utf8 project_b/experiment_dual_engine.py praat
  python -X utf8 project_b/experiment_dual_engine.py yin
  python -X utf8 project_b/experiment_dual_engine.py compare
  python -X utf8 project_b/experiment_dual_engine.py verify

纪律：
  · 清单先于引擎；清单未通过完整性检查不跑
  · 选窗不读任何引擎的 F0 结果；只用能量（与演唱相关性高）
  · 两引擎独立读同一输入、同一窗口，各自保存逐帧原始输出
  · status=exploratory, publishable=false；不与旧 69.1%/58.5% 做增减比较
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'E:\wx\论文素材_王晰作传\音域分析')
EXP = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01')
SR, WIN, HOP, FRAME = 22050, 6.0, 512, 2048
FMIN, FMAX, TOL = 50.0, 1100.0, 50.0
SEED = 20261025
N_STUDIO, N_STAGE = 20, 20


# ── 通用 ─────────────────────────────────────────────
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def load_mono(path: Path):
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(m) - 1, int(len(m) * SR / sr))
        m = np.interp(idx, np.arange(len(m)), m).astype('float32')
        sr = SR
    return m, sr


def pick_window(mono: np.ndarray, sr: int) -> float:
    """能量最大 6s 窗口（只用能量，不读 F0）。"""
    step = int(0.5 * sr)
    win = int(WIN * sr)
    best, bs = -1.0, 0.0
    for s in range(0, max(1, len(mono) - win), step):
        e = float(np.mean(mono[s:s+win] ** 2))
        if e > best:
            best, bs = e, s / sr
    return round(bs, 2)


def cmd_manifest() -> None:
    random.seed(SEED)
    studio = [p for p in BASE.glob('分离_专辑/**/vocals.wav')
              if '舞台对照' not in str(p) and 'htdemucs' in str(p)]
    stage = [p for p in BASE.glob('场次音频/**/*.wav')
             if '分离' not in str(p) and 'vocals' not in p.name
             and 'input_ascii' not in p.name and p.stat().st_size > 300_000]
    random.shuffle(studio)
    random.shuffle(stage)

    items, used_songs = [], set()
    for p in studio:
        if sum(1 for i in items if i['input_type'] == 'separated_vocal') >= N_STUDIO:
            break
        song = p.parent.parent.parent.name
        album = p.parent.parent.parent.parent.name
        if song in used_songs:
            continue
        m, sr = load_mono(p)
        if len(m) < WIN * sr * 2:
            continue
        st = pick_window(m, sr)
        used_songs.add(song)
        items.append({"segment_id": f"stu-{len(items)+1:02d}", "layer": "录音室人声轨",
                      "identity": f"{album}/{song}", "source_path": str(p),
                      "input_path": str(p), "input_type": "separated_vocal",
                      "start_s": st, "end_s": round(st + WIN, 2),
                      "selection_rule": "vocal-stem max-energy 6s window",
                      "selection_basis": "仅用能量，不读任何引擎 F0"})

    used_show = set()
    for p in stage:
        if sum(1 for i in items if i['input_type'] == 'stage_mix') >= N_STAGE:
            break
        if p.stem in used_show:
            continue
        m, sr = load_mono(p)
        if len(m) < WIN * sr * 2:
            continue
        st = pick_window(m, sr)
        used_show.add(p.stem)
        items.append({"segment_id": f"live-{len(items)-N_STUDIO:02d}", "layer": "现场混音",
                      "identity": p.stem, "source_path": str(p), "input_path": str(p),
                      "input_type": "stage_mix", "start_s": st, "end_s": round(st + WIN, 2),
                      "selection_rule": "mix max-energy 6s window",
                      "selection_basis": "仅用能量，不读任何引擎 F0"})

    # 完整性检查
    problems = []
    if len(items) != N_STUDIO + N_STAGE:
        problems.append(f"段数 {len(items)} != 40")
    if len({i['segment_id'] for i in items}) != len(items):
        problems.append("segment_id 重复")
    for i in items:
        if not Path(i['source_path']).exists():
            problems.append(f"{i['segment_id']} 源文件不存在")
        if i['end_s'] - i['start_s'] != WIN:
            problems.append(f"{i['segment_id']} 窗口长度 != {WIN}")
    if problems:
        print('清单不合格：', problems)
        sys.exit(1)

    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / 'segment_manifest.json').write_text(json.dumps({
        "experiment_id": EXP.name, "status": "exploratory", "publishable": False,
        "note": "与上一轮 40 段不是同一批窗口；旧结果仅作不可复核的历史记录",
        "seed": SEED, "window_s": WIN, "fmin": FMIN, "fmax": FMAX,
        "segments": len(items), "items": items}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"清单已生成：{len(items)} 段（录音室 {N_STUDIO} / 现场 {N_STAGE}）")
    for i in items[:3]:
        print(' ', i['segment_id'], i['layer'], i['identity'], i['start_s'])


def load_manifest():
    p = EXP / 'segment_manifest.json'
    if not p.exists():
        print('缺少 segment_manifest.json，先跑 manifest'); sys.exit(1)
    return json.loads(p.read_text(encoding='utf-8'))


def read_window(item):
    m, sr = load_mono(Path(item['input_path']))
    a = int(item['start_s'] * sr)
    seg = m[a:a + int(WIN * sr)]
    return seg, sr


def cmd_praat() -> None:
    import parselmouth
    man = load_manifest()
    out = EXP / 'raw' / 'praat'
    out.mkdir(parents=True, exist_ok=True)
    meta = {"engine": "Praat via parselmouth", "method": "Sound.to_pitch (autocorrelation)",
            "version": getattr(parselmouth, '__version__', '?'),
            "params": {"pitch_floor": FMIN, "pitch_ceiling": FMAX,
                       "time_step_s": round(HOP / SR, 5), "win_s": WIN},
            "input_type_note": "每段输入与清单 input_path 完全一致（与 YIN 同一文件、同一窗口）",
            "status": "exploratory", "publishable": False, "segments": []}
    ok = fail = 0
    for it in man['items']:
        seg, sr = read_window(it)
        fp = sha256_bytes(seg.astype('float32').tobytes())
        try:
            snd = parselmouth.Sound(seg.astype('float64'), sampling_frequency=sr)
            pitch = snd.to_pitch(time_step=HOP / sr, pitch_floor=FMIN, pitch_ceiling=FMAX)
            n = pitch.get_number_of_frames()
            rows = []
            for i in range(1, n + 1):
                t = (i - 1) * HOP / sr
                v = pitch.get_value_at_time(t)
                voiced = bool(v and v == v and v > 0)
                rows.append({"t_global": round(it['start_s'] + t, 4),
                             "f0_hz": round(float(v), 3) if voiced else None,
                             "voiced": voiced})
            (out / f"{it['segment_id']}.jsonl").write_text(
                '\n'.join(json.dumps(r, ensure_ascii=False) for r in rows), encoding='utf-8')
            meta['segments'].append({"segment_id": it['segment_id'], "input_sha256": fp,
                                     "frames": len(rows), "status": "ok"})
            ok += 1
        except Exception as e:
            meta['segments'].append({"segment_id": it['segment_id'], "input_sha256": fp,
                                     "frames": 0, "status": "failed", "error": repr(e)})
            fail += 1
    (EXP / 'runs').mkdir(parents=True, exist_ok=True)
    (EXP / 'runs' / 'praat_run.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"Praat 原始测量：成功 {ok}｜失败 {fail}｜输出 {out}")


def yin_frame(x, sr, fmin, fmax, thresh=0.15):
    tau_min, tau_max = int(sr / fmax), min(int(sr / fmin), len(x) // 2)
    d = np.zeros(tau_max + 1)
    for tau in range(1, tau_max + 1):
        diff = x[:len(x) - tau] - x[tau:]
        d[tau] = np.dot(diff, diff)
    cmnd = np.ones(tau_max + 1)
    run = 0.0
    for tau in range(1, tau_max + 1):
        run += d[tau]
        cmnd[tau] = d[tau] * tau / run if run > 0 else 1.0
    tau = None
    for t in range(tau_min, tau_max):
        if cmnd[t] < thresh:
            while t + 1 < tau_max and cmnd[t + 1] < cmnd[t]:
                t += 1
            tau = t
            break
    if tau is None:
        tau = int(np.argmin(cmnd[tau_min:tau_max])) + tau_min
    if tau <= 0 or tau >= tau_max:
        return 0.0
    a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
    den = a - 2 * b + c
    shift = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return sr / (tau + shift) if (tau + shift) > 0 else 0.0


def cmd_yin() -> None:
    man = load_manifest()
    out = EXP / 'raw' / 'yin'
    out.mkdir(parents=True, exist_ok=True)
    meta = {"engine": "自研 numpy YIN", "method": "cumulative-mean normalized difference",
            "version": "yin-v2", "params": {"fmin": FMIN, "fmax": FMAX, "frame": FRAME,
                                            "hop": HOP, "sr": SR, "win_s": WIN},
            "note": "生产管线 fmin=55；本实验两引擎统一 50 以便可比",
            "status": "exploratory", "publishable": False, "segments": []}
    ok = fail = 0
    for it in man['items']:
        seg, sr = read_window(it)
        fp = sha256_bytes(seg.astype('float32').tobytes())
        try:
            win = np.hanning(FRAME)
            rows = []
            for i in range(0, len(seg) - FRAME, HOP):
                fr = seg[i:i+FRAME] * win
                if np.sqrt(np.mean(fr ** 2)) < 0.005:
                    rows.append({"t_global": round(it['start_s'] + i / sr, 4),
                                 "f0_hz": None, "voiced": False})
                    continue
                f = yin_frame(fr, sr, FMIN, FMAX)
                rows.append({"t_global": round(it['start_s'] + i / sr, 4),
                             "f0_hz": round(float(f), 3) if f > 0 else None, "voiced": bool(f > 0)})
            (out / f"{it['segment_id']}.jsonl").write_text(
                '\n'.join(json.dumps(r, ensure_ascii=False) for r in rows), encoding='utf-8')
            meta['segments'].append({"segment_id": it['segment_id'], "input_sha256": fp,
                                     "frames": len(rows), "status": "ok"})
            ok += 1
        except Exception as e:
            meta['segments'].append({"segment_id": it['segment_id'], "input_sha256": fp,
                                     "frames": 0, "status": "failed", "error": repr(e)})
            fail += 1
    (EXP / 'runs').mkdir(parents=True, exist_ok=True)
    (EXP / 'runs' / 'yin_run.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"YIN 原始测量：成功 {ok}｜失败 {fail}｜输出 {out}")


def cmd_compare() -> None:
    man = load_manifest()
    pmeta = json.loads((EXP / 'runs' / 'praat_run.json').read_text(encoding='utf-8'))
    ymeta = json.loads((EXP / 'runs' / 'yin_run.json').read_text(encoding='utf-8'))
    psha = {s['segment_id']: s['input_sha256'] for s in pmeta['segments']}
    ysha = {s['segment_id']: s['input_sha256'] for s in ymeta['segments']}
    rows = []
    for it in man['items']:
        sid = it['segment_id']
        if psha.get(sid) != ysha.get(sid):
            rows.append({"segment_id": sid, "layer": it['layer'], "comparable": False,
                         "reason": "input_sha256 不一致"})
            continue
        def load(name):
            f = EXP / 'raw' / name / f'{sid}.jsonl'
            d = {}
            for line in f.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    r = json.loads(line)
                    d[round(r['t_global'], 3)] = r['f0_hz']
            return d
        a, b = load('yin'), load('praat')
        common = sorted(set(a) & set(b))
        both = [(a[t], b[t]) for t in common if a[t] and b[t]]
        if not both:
            rows.append({"segment_id": sid, "layer": it['layer'], "comparable": False,
                         "reason": "无双方有声帧"})
            continue
        o = np.array([x for x, _ in both]); p = np.array([y for _, y in both])
        cents = 1200 * np.log2(o / p)
        near = np.abs(cents) <= TOL
        ratio = o / p
        octv = (np.abs(ratio - 2) < .06) | (np.abs(ratio - .5) < .06) | \
               (np.abs(ratio - 4) < .1) | (np.abs(ratio - .25) < .05)
        rows.append({
            "segment_id": sid, "layer": it['layer'], "comparable": True,
            "frames_both": len(both),
            "frames_yin_only": sum(1 for t in common if a[t] and not b[t]),
            "frames_praat_only": sum(1 for t in common if b[t] and not a[t]),
            "agree_pct": round(float(near.mean()) * 100, 1),
            "octave_pct": round(float((octv & ~near).mean()) * 100, 1),
            "nonoctave_pct": round(float((~near & ~octv).mean()) * 100, 1),
            "abs_cents_median": round(float(np.median(np.abs(cents))), 1),
            "abs_cents_p90": round(float(np.percentile(np.abs(cents), 90)), 1),
        })
    def agg(layer):
        sub = [r for r in rows if r['layer'] == layer and r.get('comparable')]
        if not sub:
            return {"segments": 0}
        return {"segments": len(sub),
                "agree_pct_median": round(float(np.median([r['agree_pct'] for r in sub])), 1),
                "octave_pct_median": round(float(np.median([r['octave_pct'] for r in sub])), 1),
                "nonoctave_pct_median": round(float(np.median([r['nonoctave_pct'] for r in sub])), 1),
                "abs_cents_median": round(float(np.median([r['abs_cents_median'] for r in sub])), 1)}
    out = {"experiment_id": EXP.name, "status": "exploratory", "publishable": False,
           "note": "仅描述本批 40 段；不与上一轮 69.1%/58.5% 做增减比较",
           "summary": {l: agg(l) for l in ('录音室人声轨', '现场混音')}, "rows": rows}
    (EXP / 'comparison.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['summary'], ensure_ascii=False, indent=1))
    print('覆盖：', sum(1 for r in rows if r.get('comparable')), '/', len(rows))


def cmd_verify() -> None:
    man = load_manifest()
    sid = man['items'][0]['segment_id']
    f = EXP / 'raw' / 'praat' / f'{sid}.jsonl'
    print('可复跑样例:', sid, '| 文件存在:', f.exists())
    print('帧数:', len(f.read_text(encoding='utf-8').splitlines()) if f.exists() else 0)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: manifest|praat|yin|compare|verify'); sys.exit(1)
    {'manifest': cmd_manifest, 'praat': cmd_praat, 'yin': cmd_yin,
     'compare': cmd_compare, 'verify': cmd_verify}[sys.argv[1]]()
