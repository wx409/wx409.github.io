# -*- coding: utf-8 -*-
"""逐条过门槛：《三级读数制度》音符级校验（该音符 ≥0.2s / HNR ≥5dB / 强度 ≥中位−25dB / 谐波列）。

对工作室中控台两源的最低稳定音候选（南屏晚钟 D#2 78.9Hz、一生中最爱 F2 89.0Hz）
逐条列出音符时长、HNR、强度相对、谐波列判定，给「稳定音（能力口径）/ 触达音」结论。
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(r"D:\wx409.github.io\project_b")))
from acoustic_quality_metrics import decode, framing, hnr_db  # noqa: E402

ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
CASES = [
    ("南屏晚钟", "D#2", "wav_工作室中控台_分析/南屏晚钟/工作室中控台20261014_video1_5353988652270759_stats.json",
     "wav_工作室中控台_分离/南屏晚钟/工作室中控台20261014_video1_5353988652270759/htdemucs/input_ascii/vocals.wav",
     "wav_工作室中控台/南屏晚钟/工作室中控台20261014_video1_5353988652270759.wav"),
    ("一生中最爱", "F2", "wav_工作室中控台_分析/一生中最爱/工作室中控台20261014_video2_5353988652270759_stats.json",
     "wav_工作室中控台_分离/一生中最爱/工作室中控台20261014_video2_5353988652270759/htdemucs/input_ascii/vocals.wav",
     "wav_工作室中控台/一生中最爱/工作室中控台20261014_video2_5353988652270759.wav"),
]


def main() -> int:
    out = []
    for song, note, statp, vocp, mixp in CASES:
        st = json.loads((ANA / statp).read_text(encoding="utf-8"))
        low = st.get("low_stable") or {}
        cands = [n for n in (st.get("lowest_notes") or [])
                 if abs(float(n.get("hz") or 0) - float(low.get("hz") or 0)) < 0.4]
        n0 = cands[0] if cands else {}
        dur = n0.get("dur")
        # 该音符处 HNR（分离轨）
        y, sr = decode(ANA / vocp)
        t0 = float(n0.get("t_start") or 0)
        frame, hop = int(0.05 * sr), int(0.025 * sr)
        seg = y[int(t0 * sr):int((t0 + max(0.25, float(dur or 0.25))) * sr)]
        if len(seg) >= frame:
            fr = framing(seg, frame, min(hop, max(1, len(seg) - frame)))
            hnrs = [hnr_db(fr[i], sr) for i in range(len(fr))]
            hnrs = [h for h in hnrs if np.isfinite(h)]
            note_hnr = round(float(np.median(hnrs)), 2) if hnrs else None
        else:
            note_hnr = None
        # 强度相对（该音符 RMS vs 全曲有声帧中位）
        fr_all = framing(y, frame, hop)
        db_all = 20 * np.log10(np.sqrt((fr_all ** 2).mean(axis=1) + 1e-12) + 1e-12)
        med_db = float(np.median(db_all[db_all >= np.percentile(db_all, 60)]))
        if len(seg) >= frame:
            seg_db = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)
            rel_db = round(float(seg_db - med_db), 2)
        else:
            rel_db = None
        row = {
            "song": song, "note": note, "hz": low.get("hz"), "midi": low.get("midi"),
            "note_dur_s": round(float(dur), 3) if dur else None,
            "gate_dur_ge_0.2s": bool(dur and float(dur) >= 0.2),
            "note_hnr_db": note_hnr, "gate_hnr_ge_5db": bool(note_hnr is not None and note_hnr >= 5.0),
            "intensity_rel_to_median_db": rel_db, "gate_intensity_ge_-25db": bool(rel_db is not None and rel_db >= -25.0),
            "harmonic_check": "见下方谐波列判定（分离轨已过；原始混音另判）",
            "stats_file": statp,
        }
        # 混音谐波列判定：在原始混音上查 2f0/3f0 峰
        ym, srm = decode(ANA / mixp)
        f0 = float(low.get("hz") or 0)
        if f0 > 0:
            segm = ym[int(t0 * srm):int((t0 + max(0.3, float(dur or 0.3))) * srm)]
            if len(segm) > 4096:
                sp = np.abs(np.fft.rfft(segm * np.hanning(len(segm))))
                freqs = np.fft.rfftfreq(len(segm), 1 / srm)
                def band(f):
                    i = np.argmin(np.abs(freqs - f))
                    w = max(1, int(0.03 * f / (freqs[1] - freqs[0])))
                    return float(sp[max(0, i - w):i + w + 1].max())
                h1, h2, h3 = band(f0), band(2 * f0), band(3 * f0)
                base = float(np.median(sp) + 1e-12)
                row["harmonic_ratio"] = {"f0": round(h1 / base, 1), "2f0": round(h2 / base, 1),
                                         "3f0": round(h3 / base, 1),
                                         "verdict": ("2f0 有峰 → 真音" if h2 > 2 * h1 * 0.5 else "2f0 弱 → 需复核")}
                row["gate_harmonic_2f0"] = bool(h2 > base * 3)
        out.append(row)
        print(json.dumps(row, ensure_ascii=False, indent=1))

    # 汇总结论
    for r in out:
        gates = [r["gate_dur_ge_0.2s"], r["gate_hnr_ge_5db"], r["gate_intensity_ge_-25db"],
                 r.get("gate_harmonic_2f0", False)]
        r["all_gates_pass"] = all(gates)
        r["conclusion"] = "稳定音（能力口径）" if all(gates) else "触达音（未过全部门槛）"
    Path(r"E:\wx\论文素材_王晰作传\传播监测\音符级门槛校验_20261015.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== 结论 ===")
    for r in out:
        print(f"{r['song']} {r['note']} {r['hz']}Hz | 时长 {r['note_dur_s']}s | 音符HNR {r['note_hnr_db']} | "
              f"强度 {r['intensity_rel_to_median_db']}dB | 2f0峰 {r.get('gate_harmonic_2f0')} → **{r['conclusion']}**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
