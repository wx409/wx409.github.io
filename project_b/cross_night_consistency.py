# -*- coding: utf-8 -*-
"""同曲跨夜一致性（判断七第五块砖）——**单一写入者**。

输出 data/archive_cross_night.json 的 `versions`：
  v1 长块 vs 8 秒窗      → comparable=False（历史留痕）
  v2 分离人声 vs 原始混音 → comparable=False（留痕）
  v3 分离人声 vs 分离人声（同规格 8 秒窗）→ **可比版**
映射：data/cross_night_block_map.json（显式块→曲，禁隐式猜）。
纪律：只报差异与一致性，不评优劣；未达上站门槛只落数据层。
用法：python -X utf8 project_b/cross_night_consistency.py
"""

import io, json, re, sys
from pathlib import Path
import numpy as np
import soundfile as sf

SITE = Path(r"D:\wx409.github.io")
ROOT = Path(r"E:\wx\论文素材_王晰作传\音域分析")
sys.path.insert(0, str(ROOT))
from vocal_metrics import yin_f0  # noqa
SR, HOP, FRAME, FMIN, FMAX = 22050, 512, 2048, 55.0, 1100.0
WIN, STEP = 8.0, 30.0
B09 = ROOT / "场次音频" / "沉响20261009_v4_块"
V10 = ROOT / "场次音频" / "沉响20261010_分离"
MIX10 = ROOT / "场次音频" / "wav"
CLIPS10 = ROOT / "听辨样本" / "沉响20261010_块级"

# ── 显式映射（落数据文件，禁隐式猜）：10-09 块 → 曲名 ──
MAP = SITE / "data" / "cross_night_block_map.json"
if not MAP.exists():
    MAP.write_text(json.dumps({
        "schema": 1, "note": "10-09 块 → 曲名（人耳定案 + 直拍同刻对齐；**显式维护，禁隐式猜**）",
        "blocks": {"b05": "敕勒歌", "b06": "乌兰巴托的夜"},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
block_song = json.loads(MAP.read_text(encoding="utf-8"))["blocks"]


def met(y, sr):
    p = yin_f0(y, sr, FMIN, FMAX, FRAME, HOP)
    f0, v = np.asarray(p["f0"], float), np.asarray(p["voiced"], bool)
    ok = v & np.isfinite(f0)
    if ok.sum() < 15:
        return None
    seg = f0[ok]
    stab = float(np.median(np.abs(np.diff(seg)))) * 100 if len(seg) > 5 else 0.0
    zc = np.sum(np.diff(np.sign(seg - np.median(seg))) != 0)
    return {"stability_cents_median": round(stab, 2), "intonation_cents_median": round(abs(stab - 7), 2),
            "vibrato_hz_median": round(zc / 2 / (len(seg) * HOP / sr), 2)}


def windows(path, song=None):
    y, sr = sf.read(str(path), dtype="float32", always_2d=True); y = y.mean(axis=1)
    out, t = [], 4.0
    while t + WIN < len(y) / sr:
        m = met(y[int(t * sr):int((t + WIN) * sr)], sr)
        if m:
            m["t"] = round(t, 1); out.append(m)
        t += STEP
    return out


def med(ws):
    return {k: round(float(np.median([w[k] for w in ws])), 2)
            for k in ("stability_cents_median", "intonation_cents_median", "vibrato_hz_median")} if ws else None


# 10-09 分离人声 8 秒窗（按块→曲归并）
w09 = {}
for f in sorted(B09.glob("b*_*.wav")):
    key = f.stem.split("_")[0]
    s = block_song.get(key)
    if not s:
        continue
    ws = windows(f)
    if ws:
        w09[s] = {"metrics": med(ws), "n": len(ws), "block": key}
# 10-10：分离人声窗 + 原始混音窗（v2 用）
w10_sep, w10_mix = [], []
for v in sorted(V10.glob("*_vocals.wav")):
    w10_sep += windows(v)
for m in sorted(MIX10.glob("全场_第二场_*/*.wav")):
    w10_mix += windows(m)[:40]          # 抽样，控制耗时
rows3, rows2 = [], []
for s, a in w09.items():
    rows3.append({"song": s, "block_1009": a["block"], "n_win_1009": a["n"], "n_win_1010": len(w10_sep),
                  "metrics_1009": a["metrics"], "metrics_1010": med(w10_sep)})
    rows2.append({"song": s, "n_win_1009": a["n"], "n_win_1010": len(w10_mix),
                  "metrics_1009": a["metrics"], "metrics_1010_mix": med(w10_mix)})

OUT = SITE / "data" / "archive_cross_night.json"
prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
v1rows = ((prev.get("versions") or {}).get("v1_longblock_vs_8s", {}) or {}).get("rows") \
    or prev.get("rows") or []
cn = {
    "schema": 3, "generator": "project_b/cross_night_consistency.py（**单一写入者**）",
    "discipline": "只报差异与一致性，不评优劣；不可比就写不可比，不硬凑",
    "versions": {
        "v1_longblock_vs_8s": {"comparable": False,
                               "why": "10-09 长块 vs 10-10 8 秒窗——窗口径不同", "rows": v1rows},
        "v2_sep_vs_mix_8s": {"comparable": False,
                             "why": "输入类型不同：10-09 为分离人声、10-10 为原始混音", "rows": rows2},
        "v3_sep_vs_sep_8s": {"comparable": bool(rows3),
                             "why": "两侧均为分离人声；同规格 win8s/hop30s/fmin55/fmax1100/frame2048/hop512"
                                    if rows3 else "缺一侧窗数据",
                             "rows": rows3,
                             "n_win_1010_sep": len(w10_sep),
                             "confound": "设备/机位/观众噪声/PA 直达声比例不同；样本为 8 秒窗中位"},
    },
    "review_status": "数据层（未上站）：观众实录 8 秒窗，未达上站门槛",
}
OUT.write_text(json.dumps(cn, ensure_ascii=False, indent=1), encoding="utf-8")
print("v3 可比曲目 =", len(rows3))
for r in rows3:
    print("  ", r["song"], "10-09", r["metrics_1009"], "| 10-10", r["metrics_1010"])
print("v2 行数", len(rows2), "| v1 行数", len(v1rows), "| 结构 versions =", list(cn["versions"]))
