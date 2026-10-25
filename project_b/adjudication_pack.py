#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三判据：24 窗抽样 + 裁决材料包 + 空白表单（不伪造听辨）。

用法：
  python -X utf8 project_b/adjudication_pack.py sample
  python -X utf8 project_b/adjudication_pack.py materials
  python -X utf8 project_b/adjudication_pack.py summary
  python -X utf8 project_b/adjudication_pack.py verify

纪律：
  · 只读 exp-20261025-01；不改 40 段清单与原始逐帧
  · 候选 A/B 隐藏引擎名，映射另存
  · 裁决字段一律 pending（无真实听者）
  · 不输出全站误差率、不启用 80/60 阈值
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
EXP = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01')
ADJ = EXP / 'adjudication'
SEED = 20261026
TARGET = 24

CATS = ['octave', 'one_sided', 'nonoctave', 'agree_high', 'agree_mid', 'agree_low']


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def classify(r) -> str:
    """互斥分类（阈值写死，抽样前确定）：八度≥5% > 单方有声占比≥15% > 非八度≥20% > 一致率分组。"""
    if not r.get('comparable'):
        return 'not_comparable'
    one_ratio = (r['frames_yin_only'] + r['frames_praat_only']) / max(1, r['frames_both'])
    if r['octave_pct'] >= 5:
        return 'octave'
    if one_ratio >= 0.15:
        return 'one_sided'
    if r['nonoctave_pct'] >= 20:
        return 'nonoctave'
    if r['agree_pct'] >= 80:
        return 'agree_high'
    if r['agree_pct'] >= 60:
        return 'agree_mid'
    return 'agree_low'


def cmd_sample() -> None:
    man = load(EXP / 'segment_manifest.json')
    cmp_rows = {r['segment_id']: r for r in load(EXP / 'comparison.json')['rows']}
    items = [i for i in man['items'] if cmp_rows.get(i['segment_id'], {}).get('comparable')]
    random.seed(SEED)
    for layer in ('录音室人声轨', '现场混音'):
        random.shuffle(items) if False else None
    by_layer = {l: [i for i in items if i['layer'] == l] for l in ('录音室人声轨', '现场混音')}
    for l in by_layer:
        random.shuffle(by_layer[l])

    picked, used = [], set()
    notes = []
    per_layer_quota = {'录音室人声轨': 12, '现场混音': 12}
    for layer, quota in per_layer_quota.items():
        pool = by_layer[layer]
        # 每类先取 2 个
        for cat in CATS:
            got = [i for i in pool if classify(cmp_rows[i['segment_id']]) == cat and i['segment_id'] not in used]
            take = got[:2]
            for i in take:
                picked.append((layer, cat, i, 'primary'))
                used.add(i['segment_id'])
            if len(take) < 2:
                notes.append({"layer": layer, "category": cat, "available": len(got),
                              "took": len(take), "reason": "该类窗口不足，按括号内实际数量取；缺口用同层替补"})
        # 补足配额
        rest = [i for i in pool if i['segment_id'] not in used]
        need = quota - sum(1 for p in picked if p[0] == layer)
        for i in rest[:max(0, need)]:
            picked.append((layer, classify(cmp_rows[i['segment_id']]), i, 'substitute'))
            used.add(i['segment_id'])
            notes.append({"layer": layer, "segment_id": i['segment_id'], "reason": "替补：该层类别配额不足"})

    picked = picked[:TARGET]
    # 候选映射（隐藏引擎名）
    mapping = {}
    rows = []
    for n, (layer, cat, i, kind) in enumerate(picked, 1):
        r = cmp_rows[i['segment_id']]
        agree = r['agree_pct']
        grp = 'high' if agree >= 80 else ('mid' if agree >= 60 else 'low')
        adj_id = f"adj-{n:02d}"
        swap = (n % 2 == 0)
        mapping[adj_id] = {"candidate_A": "Praat" if swap else "YIN",
                           "candidate_B": "YIN" if swap else "Praat"}
        rows.append({
            "adjudication_id": adj_id, "segment_id": i['segment_id'], "layer": layer,
            "category": cat, "agree_group": grp, "agree_pct": agree,
            "octave_pct": r['octave_pct'], "nonoctave_pct": r['nonoctave_pct'],
            "frames_both": r['frames_both'],
            "frames_yin_only": r['frames_yin_only'], "frames_praat_only": r['frames_praat_only'],
            "selection_kind": kind,
            "rule": f"分层随机 + 类别配额（seed={SEED}）；一致率分组 high≥80/mid60-80/low<60 仅作内部分组",
        })
    ADJ.mkdir(parents=True, exist_ok=True)
    (ADJ / 'adjudication_manifest.json').write_text(json.dumps({
        "experiment_id": man['experiment_id'], "status": "exploratory", "publishable": False,
        "source": "exp-20261025-01", "seed": SEED, "windows": len(rows),
        "note": "抽样单位为已有 6s 分析窗口；不与旧结果比较",
        "items": rows, "shortfall_notes": notes}, ensure_ascii=False, indent=1), encoding='utf-8')
    (ADJ / 'candidate_mapping.private.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"抽样 {len(rows)} 窗；替补/不足记录 {len(notes)} 条")
    for r in rows[:6]:
        print(' ', r['adjudication_id'], r['segment_id'], r['layer'], r['category'], r['agree_pct'])


def read_frames(name, sid):
    f = EXP / 'raw' / name / f'{sid}.jsonl'
    d = {}
    for line in f.read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            d[round(r['t_global'], 3)] = r['f0_hz']
    return d


def cmd_materials() -> None:
    man = {i['segment_id']: i for i in load(EXP / 'segment_manifest.json')['items']}
    adj = load(ADJ / 'adjudication_manifest.json')['items']
    mat = ADJ / 'materials'
    mat.mkdir(parents=True, exist_ok=True)
    made = 0
    for r in adj:
        sid = r['segment_id']
        it = man[sid]
        a = read_frames('yin', sid)
        b = read_frames('praat', sid)
        common = sorted(set(a) & set(b))
        pairs = [(t, a[t], b[t]) for t in common if a[t] and b[t]]
        if pairs:
            if r['category'] in ('octave', 'nonoctave'):
                t, fa, fb = max(pairs, key=lambda p: abs(np.log2(p[1] / p[2])))
            elif r['category'] == 'one_sided':
                cand = [t for t in common if bool(a[t]) != bool(b[t])]
                t = cand[0] if cand else pairs[0][0]
                fa, fb = a.get(t), b.get(t)
            else:
                t, fa, fb = pairs[len(pairs) // 2]
        else:
            t, fa, fb = (common[0] if common else it['start_s']), a.get(common[0]) if common else None, None
        # 谐波列：输入音频在该时刻的谱峰
        x, sr = sf.read(it['input_path'], dtype='float32', always_2d=True)
        m = x.mean(axis=1)
        a0 = max(0, int((t - 0.05) * sr))
        seg = m[a0:a0 + int(0.1 * sr)]
        win = np.hanning(len(seg))
        sp = np.abs(np.fft.rfft(seg * win))
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        band = (f > 40) & (f < 1200)
        peaks = [(float(f[i]), float(20 * np.log10(sp[i] + 1e-9))) for i in np.where(band)[0]]
        peaks.sort(key=lambda z: -z[1])
        top = peaks[:8]
        def support(cand):
            if not cand:
                return None
            out = []
            for k in (1, 2, 3, 4, 6):
                target = cand * k
                near = [p for p in peaks if abs(p[0] - target) < max(3.0, target * 0.03)]
                out.append({"harmonic": k, "expected_hz": round(target, 1),
                            "peak_hz": round(near[0][0], 1) if near else None,
                            "db": round(near[0][1], 1) if near else None})
            return out
        d = mat / r['adjudication_id']
        d.mkdir(parents=True, exist_ok=True)
        # 片段（前后各 1s）
        a1 = max(0, int((it['start_s'] - 1) * sr)); b1 = int((it['end_s'] + 1) * sr)
        sf.write(str(d / 'clip_context.wav'), m[a1:b1], sr)
        (d / 'harmonics.json').write_text(json.dumps({
            "adjudication_id": r['adjudication_id'], "segment_id": sid, "layer": r['layer'],
            "t_global": round(t, 3), "candidate_A_f0": round(fa, 2) if fa else None,
            "candidate_B_f0": round(fb, 2) if fb else None,
            "top_peaks": [{"hz": round(p[0], 1), "db": round(p[1], 1)} for p in top],
            "support_A": support(fa), "support_B": support(fb),
            "input_type": it['input_type'], "input_path": it['input_path'],
            "window": [it['start_s'], it['end_s']]}, ensure_ascii=False, indent=1), encoding='utf-8')
        (d / 'f0_tracks.csv').write_text(
            't_global,candidate_A_hz,candidate_B_hz\n' +
            '\n'.join(f'{t},{a.get(t) or ""},{b.get(t) or ""}' for t in common), encoding='utf-8')
        (d / 'form.json').write_text(json.dumps({
            "adjudication_id": r['adjudication_id'],
            "attribution": {"target_singer": None, "not_target_singer": None,
                            "accompaniment_or_other_voice": None, "unclear": None,
                            "status": "pending"},
            "f0_verdict": {"candidate_A_more_reasonable": None, "candidate_B_more_reasonable": None,
                           "both_reasonable_small_difference": None, "both_unreliable": None,
                           "unresolved": None, "status": "pending"},
            "evidence_used": [], "reason": "", "reviewer": "", "review_date": "",
            "confidence_or_unjudgeable_reason": "pending human review"}, ensure_ascii=False, indent=1),
            encoding='utf-8')
        made += 1
    print(f"材料包 {made} 窗 -> {mat}")


def cmd_summary() -> None:
    adj = load(ADJ / 'adjudication_manifest.json')['items']
    forms = []
    for r in adj:
        p = ADJ / 'materials' / r['adjudication_id'] / 'form.json'
        forms.append(load(p) if p.exists() else {})
    pending = sum(1 for f in forms if f.get('f0_verdict', {}).get('status') == 'pending')
    by_cat = {}
    for r in adj:
        by_cat.setdefault(r['category'], 0)
        by_cat[r['category']] += 1
    out = {
        "experiment_id": "exp-20261025-01", "status": "exploratory", "publishable": False,
        "windows": len(adj), "pending_reviews": pending, "completed_reviews": len(adj) - pending,
        "by_category": by_cat,
        "by_layer": {l: sum(1 for r in adj if r['layer'] == l) for l in ('录音室人声轨', '现场混音')},
        "verdicts": {"note": "全部 pending：无真实听者，不生成裁决统计"},
        "not_computable": ["YIN更合理/Praat更合理的分子", "共同可疑/共同错误计数",
                           "八度分歧中各引擎更合理计数"],
        "scope": "仅这 24 个裁决窗口；不输出全站误差率，不启用 80/60 阈值",
        "sampling_note": ("24 窗为目的性分层抽样（八度→单方有声→非八度→一致率优先级）。"
                          "类别计数只描述裁决样本的构成，不用于估计两层的分歧发生率。"),
        "layer_comparison_note": ("若要描述两层的分歧差异，应引用完整 40 段的 comparison 结果，"
                                  "并标明只描述本批 40 段；不能用 24 窗的目的性抽样比例替代。"),
        "limitations": [
            "录音室窗口的输入为分离人声，谐波列基于该输入；原始混音未映射，需人工听辨补足",
            "本批 40 段中没有符合预设条件的 agree_low 窗口，已在 shortfall_notes 记录",
            "所有裁决字段为 pending：无真实听者，不生成裁决统计",
            "双引擎一致率是否具有筛查价值，必须等待实际裁决；当前不作判断",
        ],
    }
    (ADJ / 'adjudication_summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['by_category'], ensure_ascii=False))
    print('pending', pending, '/', len(adj))


def cmd_verify() -> None:
    adj = load(ADJ / 'adjudication_manifest.json')['items']
    man = {i['segment_id'] for i in load(EXP / 'segment_manifest.json')['items']}
    ok = sum(1 for r in adj if r['segment_id'] in man)
    mats = sum(1 for r in adj if (ADJ / 'materials' / r['adjudication_id'] / 'harmonics.json').exists())
    print(f"窗口可回溯 {ok}/{len(adj)}｜材料包 {mats}/{len(adj)}")
    print(f"候选映射条数 {len(load(ADJ / 'candidate_mapping.private.json'))}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'sample'
    {'sample': cmd_sample, 'materials': cmd_materials,
     'summary': cmd_summary, 'verify': cmd_verify}[cmd]()
