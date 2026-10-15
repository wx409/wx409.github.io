# -*- coding: utf-8 -*-
"""① 回改：两条读数按音符级门槛**退回触达音**（源级 HNR 达标 ≠ 读数够格）
   ② 诊断 raw_latest.xlsx 与 raw_archive 目录（只查不改）"""
import json
from datetime import datetime
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")

# ── ① 回改数据层 ──
GATES = {
    "南屏晚钟": {"note": "D#2 78.9Hz", "dur_s": 0.209, "note_hnr_db": 3.25,
                 "intensity_rel_db": -10.98, "harmonic_2f0": True, "pass_hnr": False},
    "一生中最爱": {"note": "F2 89.0Hz", "dur_s": 0.232, "note_hnr_db": 4.79,
                   "intensity_rel_db": 1.09, "harmonic_2f0": True, "pass_hnr": False},
}
sm = json.loads((SITE / "data" / "song_evidence_master.json").read_text(encoding="utf-8"))
for r in sm["rows"]:
    g = GATES.get(r["song"])
    if not g:
        continue
    key = "dual_source_check" if r["song"] == "南屏晚钟" else "cross_venue_note"
    blk = r.get(key) or {}
    blk["note_level_gate"] = {
        **g, "gates": {"音符时长≥0.2s": g["dur_s"] >= 0.2, "音符HNR≥5dB": g["note_hnr_db"] >= 5,
                       "强度≥中位−25dB": g["intensity_rel_db"] >= -25, "谐波列/2f0 峰": g["harmonic_2f0"]},
        "verdict": "**触达音（未过全部门槛）**——音符级 HNR 未达 5dB",
        "correction": "**撤回升格**：先前据「源级三指标」判「达升格门槛」有误——"
                      "《三级读数制度》要求的是**音符级**（该音符本身 ≥0.2s、HNR ≥5dB、强度 ≥中位−25dB、"
                      "过谐波列）。**源干净 ≠ 读数够格**。该源仍可留作**素材质量优选**，但读数按触达音记。",
    }
    blk["verdict"] = ("**触达/样本级**（音符级门槛未过：HNR 3.25/4.79 < 5dB）；"
                      "中控台源在**素材质量**上明显更干净（噪声底 −63.7/−86.6 dBFS），"
                      "但**不据此升格**")
    r[key] = blk
    r["review_status_live"] = "触达音（未过能力门槛）"
(SITE / "data" / "song_evidence_master.json").write_text(json.dumps(sm, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
print("[数据层] 两条读数已退回触达音并写明撤回理由")

# ── 报告补正 ──
rep = ARCH / "工作室中控台两首点歌_20261015.md"
t = rep.read_text(encoding="utf-8")
add = """
## 五、**更正：升格撤回（音符级门槛校验）**

先前的「中控台源达升格门槛」是据**源级三指标**判断的，**不等于读数够格**。《三级读数制度》要求
**音符级**：该音符本身 ≥0.2s、HNR ≥5dB、强度 ≥中位−25dB，且过谐波列/CREPE 交叉校验。

| 曲 | 读数 | 音符时长 | **音符级 HNR** | 强度相对 | 谐波列(2f0 峰) | 全门槛 | 结论 |
|---|---|---|---|---|---|---|---|
| 南屏晚钟 | D#2 78.9Hz | 0.209s ✅ | **3.25 dB ❌（<5）** | −10.98 dB ✅ | 有峰 ✅ | ❌ | **触达音** |
| 一生中最爱 | F2 89.0Hz | 0.232s ✅ | **4.79 dB ❌（<5）** | +1.09 dB ✅ | 有峰 ✅ | ❌ | **触达音** |

- **结论**：两条读数**均退回触达音**（音符级 HNR 未达 5dB）。中控台源在**素材质量**上确实更干净
  （噪声底 −63.69 / −86.61 dBFS），**但源干净 ≠ 读数够格**，不据此升格。
- 影响：`song_evidence_master` 的 `dual_source_check` / `cross_venue_note` 已加
  `note_level_gate` 与撤回升格说明；该源仍登记为**质量优选素材**（供后续更长片段/更好录音复测）。
"""
if "升格撤回" not in t:
    rep.write_text(t.rstrip() + "\n" + add, encoding="utf-8")
    print("[报告] 已加「五、更正：升格撤回」")

# ── ② 诊断 raw_latest.xlsx ──
RAW = Path(r"E:\wx\index_records\raw_archive\raw_latest.xlsx")
CACHE = SITE / "temp" / "_index_cache.pkl"
diag = {"file": str(RAW)}
if RAW.exists():
    b = RAW.read_bytes()[:8]
    diag.update({"size_bytes": RAW.stat().st_size,
                 "mtime": datetime.fromtimestamp(RAW.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                 "magic_hex": b.hex().upper(),
                 "magic_guess": ("xlsx(zip PK)" if b[:2] == b"PK" else
                                 "xls(OLE D0CF11E0)" if b.hex().upper().startswith("D0CF11E0") else
                                 "文本/CSV" if all(32 <= x < 127 or x in (9, 10, 13) for x in b) else "未知/损坏")})
else:
    diag["exists"] = False
diag["cache"] = ({"exists": True,
                  "mtime": datetime.fromtimestamp(CACHE.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                 if CACHE.exists() else {"exists": False})
d = Path(r"E:\wx\index_records\raw_archive")
if d.exists():
    diag["dir_listing"] = [{"name": p.name, "size_mb": round(p.stat().st_size / 1048576, 1),
                            "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                           for p in sorted(d.glob("*")) if p.is_file()][:20]
alt = Path(r"E:\wx\指数数据库")
if alt.exists():
    diag["alt_sources"] = [{"name": p.name, "size_mb": round(p.stat().st_size / 1048576, 1)}
                           for p in sorted(alt.glob("*"))][:12]
(ARCH / "索引源诊断_20261015.json").write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(diag, ensure_ascii=False, indent=1)[:1200])
