# -*- coding: utf-8 -*-
"""长声表 × 否决台账 反连接（防"被否决的声音"留在长声榜里）。

规则（从严）：
  · 同一曲目 + 同一 Hz（±3%）被台账否决 → 该条 direct_rejected，移出榜单。
  · 同一曲目的**高音**存在否决记录（女和声/器乐等）→ 该条 same_song_suspect（待核），
    仍留档但**不进首屏/不进共识句**，并在 JSON 里标注原因。
产出：就地更新 data/archive_long_notes.json（新增 verdict_check 块 + top 过滤 + top_flagged）
用法：python -X utf8 project_b\\audit_long_notes_verdicts.py [--check]
"""
from __future__ import annotations

import argparse
import json
import statistics as _st
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
LN = D / "archive_long_notes.json"
VD = D / "listening_verdicts.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查不写回（CI/审计用）")
    a = ap.parse_args()

    ln = json.loads(LN.read_text(encoding="utf-8"))
    top = ln.get("top", [])
    items = json.loads(VD.read_text(encoding="utf-8"))["items"]

    rej = [i for i in items if "非王晰" in str(i.get("verdict")) or "不是" in str(i.get("verdict_note"))]
    rej_ref = {}
    for i in rej:                                    # 每曲取被否决读数的最高值作参照
        s = str(i.get("song"))
        h = i.get("verdict_hz")
        if isinstance(h, (int, float)):
            rej_ref[s] = max(rej_ref.get(s, 0.0), float(h))

    flagged, kept = [], []
    for x in top:
        song, hz = str(x.get("song")), x.get("hz")
        direct, suspect = None, None
        if hz:
            for i in rej:
                if str(i.get("song")) == song and isinstance(i.get("verdict_hz"), (int, float)):
                    if abs(float(i["verdict_hz"]) - float(hz)) / float(hz) <= 0.03:
                        direct = i
                        break
            # 同曲存疑：仅当本条与「被否决的读数」处于同一音区（≥ 参照的 0.6 倍，约 1.5 个八度内）
            if not direct and song in rej_ref and float(hz) >= 0.6 * rej_ref[song]:
                suspect = rej_ref[song]
        if direct:
            x["verdict_conflict"] = f"直接冲突：台账否决 {direct.get('verdict')}（{direct.get('verdict_hz')}Hz）"
            flagged.append(x)
        elif suspect:
            x["verdict_conflict"] = (f"同音区存疑：该曲 {suspect:.0f}Hz 读数曾被否决"
                                     f"（{'；'.join(sorted({str(i.get('verdict')) for i in rej if str(i.get('song')) == song}))}），本条待核")
            flagged.append(x)
        else:
            kept.append(x)

    for i, x in enumerate(sorted(kept, key=lambda y: -(y.get("dur_s") or 0)), 1):
        x["rank"] = i

    ln["verdict_check"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rule": "同曲同 Hz（±3%）被否决 → 直接冲突并移榜；同曲高音曾被否决 → 同曲存疑（留档、不进首屏/共识句）",
        "n_total": len(top), "n_kept": len(kept), "n_flagged": len(flagged),
        "flagged": [{k: x.get(k) for k in ("song", "note", "hz", "dur_s", "src", "where", "verdict_conflict")} for x in flagged],
    }
    ln["top_flagged"] = flagged
    ln["top"] = kept
    # 统计口径：**仍按全部条目**（含待核），只额外给出"剔存疑后"的两个数，避免下游 inject 读不到 n_*
    _all = kept + flagged
    _all.sort(key=lambda y: -(y.get("dur_s") or 0))
    _d = [x.get("dur_s") or 0 for x in _all]
    ln["stats"] = {
        "n_ge6s": sum(1 for d in _d if d >= 6), "n_ge8s": sum(1 for d in _d if d >= 8),
        "n_ge10s": sum(1 for d in _d if d >= 10), "n_ge12s": sum(1 for d in _d if d >= 12),
        "n_ge15s": sum(1 for d in _d if d >= 15),
        "median_s": round(_st.median(_d), 1) if _d else 0, "max_s": max(_d) if _d else 0,
        "n_after_verdict_join": len(kept),
        "max_s_after_join": max([x.get("dur_s") or 0 for x in kept], default=0),
    }
    print(f"长声榜 {len(top)} 条 → 保留 {len(kept)}｜移出/待核 {len(flagged)}")
    for x in flagged:
        print(f"  ⚠ {x['song']} {x['note']} {x['hz']}Hz {x['dur_s']}s｜{x['verdict_conflict'][:70]}")
    if kept:
        b = max(kept, key=lambda y: y.get('dur_s') or 0)
        print(f"  保留榜第一：{b['song']} {b['note']} {b['hz']}Hz {b['dur_s']}s（{b['src']}·{b['where']}）")
    if not a.check:
        LN.write_text(json.dumps(ln, ensure_ascii=False, indent=1), encoding="utf-8")
        print("→ 已写回", LN.name)
    assert len(kept) + len(flagged) == len(top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
