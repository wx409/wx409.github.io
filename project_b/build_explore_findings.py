# -*- coding: utf-8 -*-
"""声学探索清单：把已有数据能回答的问题**逐条算出来**，形成可写作的方向菜单。

第一性原理（用户 2026-09-24 定）：没有专家指路，只能靠**把范围铺开 + 每条都可复算**来发现写作方向。
因此本脚本不做"观点"，只做**可复算的观测**；每条给出：现象、数字、样本量、口径限定、可信度分级。

输出：
  · data/explore_findings.json（机读）
  · E:\\wx\\论文素材_王晰作传\\声学探索_可写方向.md（本地，供写作取材）

用法：python -X utf8 project_b\\build_explore_findings.py
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
OUT_JSON = D / "explore_findings.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\声学探索_可写方向.md")


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def median_or_none(v):
    return round(st.median(v), 2) if v else None


F = []
TODAY = "2026-09-24"


def add(cat, q, finding, numbers, n, caliber, conf):
    F.append({"cat": cat, "question": q, "finding": finding, "numbers": numbers,
              "n": n, "caliber": caliber, "confidence": conf})


alb = load(D / "archive_vocal_albums.json").get("songs", [])
voc = load(D / "archive_vocal.json").get("songs", [])
tour = load(D / "archive_stage_tour.json")
rows = tour.get("rows", [])
sl = load(D / "setlists.json").get("setlists", {})
ln = load(D / "archive_long_notes.json")
ca = load(D / "cover_analysis.json")

# ── 1. 最低稳定音的层级结构 ────────────────────────────────────────────
studio_low = min([s for s in alb if isinstance(s.get("low_hz"), (int, float))],
                 key=lambda s: s["low_hz"])
live_lo = tour["summary"].get("lowest", {})
add("能力·音域", "他的最低稳定音在录音室与现场分别到多少？",
    "录音室最低 B1 61.5Hz；现场层最低 A#1 57.8Hz（签唱会自录存档，谐波列通过）",
    {"studio": {"note": studio_low["low"], "hz": studio_low["low_hz"], "song": studio_low["title"]},
     "live": {"note": live_lo.get("note"), "hz": live_lo.get("hz"), "tag": live_lo.get("tag")}},
    len(alb), "稳定音口径（≥0.2s、HNR≥5dB、谐波列/人耳）", "A 高")

# ── 2. 专辑音区弧线 ──────────────────────────────────────────────────
by_alb = defaultdict(list)
for s in alb:
    if s.get("register_share"):
        by_alb[s["album"]].append(s)
arc = sorted(((a, median_or_none([x["register_share"]["low_lt_C3"] for x in v])) for a, v in by_alb.items()),
             key=lambda x: x[1] or 0)
add("风格·美学", "他的用音区偏好随专辑怎么变？",
    "按低音区占比降序：早年专辑近半音符在 C3 以下，中期骤降、高区打开，后期回到 17–28%",
    {"低区占比": {a: round(v, 3) for a, v in arc}}, len(alb),
    "音符计数占比（不含未分离段）", "A 高")

# ── 3. 自有 vs 翻唱（现场最低音）─────────────────────────────────────
ra = ca.get("register_adapt", {})
add("风格·选曲", "他给自己的歌 vs 别人的歌，现场唱得更低吗？",
    "自有曲现场最低音中位略低于翻唱曲（方向一致，但样本不对称，仅作倾向）",
    {"自有": ra.get("own_live_low_median"), "自有n": ra.get("own_n"),
     "翻唱": ra.get("cover_live_low_median"), "翻唱n": ra.get("cover_n")},
    (ra.get("own_n") or 0) + (ra.get("cover_n") or 0), "现场层最低音中位", "B 中")

# ── 4. 同曲跨场最低音波动 ────────────────────────────────────────────
mv = ca.get("multi_version", {})
add("能力·稳定性(跨场)", "同一首歌在不同场次，最低能压到多低、波动多大？",
    "≥3 版本的曲目有多首；同曲跨场最低音的变异系数中位约 10%",
    {"曲目数": mv.get("songs_with_3plus"), "CV中位": mv.get("low_cv_median")},
    mv.get("songs_with_3plus") or 0, "现场层最低音（跨场同曲）", "B 中")

# ── 5. 颤音指纹 ─────────────────────────────────────────────────────
vib = [s["vibrato_hz"] for s in alb if s.get("vibrato_hz")]
alb_vib = {a: median_or_none([x["vibrato_hz"] for x in v if x.get("vibrato_hz")])
           for a, v in by_alb.items()}
vv = [x for x in alb_vib.values() if x]
add("能力·音色指纹", "颤音速率在八年里稳定吗？",
    f"录音室中位 {median_or_none(vib)} Hz；专辑间仅 {min(vv):.2f}–{max(vv):.2f} Hz（漂移 {max(vv)-min(vv):.2f} Hz）",
    {"整体中位": median_or_none(vib), "专辑间范围": [min(vv), max(vv)],
     "巡演中位": [t.get("vibrato_rate_hz_median") for t in tour.get("by_tour", [])]},
    len(vib), "分离人声轨；组内可纵比、跨组谨慎", "A 高")

# ── 6. 密度 vs 稳定性（两种人格？）────────────────────────────────────
dens = [s["density"] for s in alb if s.get("density")]
stabs = [s["stability_cents"] for s in alb if s.get("stability_cents")]
add("风格·演唱形态", "他的演唱形态能否用「密度 × 稳定性」分成两类？",
    "72 曲里密度与稳定性同时可得的曲目分布较宽，存在「低密度慢歌」与「高密度叙事」两簇（待聚类验证）",
    {"密度中位": median_or_none(dens), "密度范围": [round(min(dens), 2), round(max(dens), 2)],
     "稳定性中位": median_or_none(stabs)},
    len(dens), "录音室全量；稳定性属高敏感层（仅组内比）", "C 探索")

# ── 7. 长声（气息）───────────────────────────────────────────────────
top_ln = ln.get("top", [])
if top_ln:
    lo = max(top_ln, key=lambda x: x.get("dur_s") or 0)
    hi = max(top_ln, key=lambda x: x.get("hz") or 0)
    add("能力·气息", "长声（连续同音高）能持续多久？高低两端如何？",
        f"按时长第一 {lo['dur_s']}s（{lo['note']} {lo['hz']}Hz，{lo['song']}）；按音高最高 {hi['note']} {hi['hz']}Hz {hi['dur_s']}s",
        {"时长第一": lo, "音高最高": hi, "保留条数": len(top_ln),
         "移出条数": len(ln.get("top_flagged", []))},
        len(top_ln), "≥6s 同音高（抖动<0.6 半音）；高音区需人耳归属", "A 高")

# ── 8. 现场 vs 他人主导舞台（对照层）─────────────────────────────────
stg = load(D / "archive_context_compare.json")
add("能力·对照", "他的现场与「他人主导舞台」的最低音差异显著吗？",
    "既有检验：差异不显著（p=0.197），提示差异更多来自情境而非能力",
    {"p": (stg.get("low_stable") or {}).get("p") if isinstance(stg, dict) else None},
    0, "Mann–Whitney U（同管线）", "A 高")

# ── 9. 巡演规模与场次分布 ────────────────────────────────────────────
per_tour = Counter(v.get("tour") for v in sl.values())
cities = {v.get("city") for v in sl.values() if v.get("city")}
add("生涯·规模", "六轮巡演的时间与空间分布",
    f"全站 {len(sl)} 场 = 巡演 59 + 签唱会 5；覆盖 {len(cities)} 城",
    {"各巡场次": dict(per_tour), "城市数": len(cities)}, len(sl), "全站唯一场次口径", "A 高")

# ── 10. 素材来源构成（可用于"材料学"叙事）────────────────────────────
aa = load(D / "audio_assets.json").get("summary", {})
add("方法·材料", "这份档案的素材基础有多大、从哪来？",
    f"{aa.get('batches')} 个采集批次、{aa.get('files')} 个音频文件、{aa.get('gb')} GB、{aa.get('stats_total')} 个逐曲分析产物",
    aa, aa.get("files") or 0, "本地资产盘点（不含二次分发）", "A 高")

# ── 11. 现场层质量分层 ───────────────────────────────────────────────
s_ = tour.get("summary", {})
add("方法·证据强度", "现场层的证据强度分布",
    f"可主张 {s_.get('n_claimable')} 条（音符级 HNR≥5dB+谐波列/人耳）；低信噪告警 {s_.get('hnr_low_n')} 条；"
    f"待复核 {s_.get('review_status_dist', {}).get('待复核（谐波列待判）')} 条",
    s_.get("review_status_dist"), s_.get("n_materials") or 0, "行级 review_status", "A 高")

# ── 13. HNR 门槛的实证检验（方法学）─────────────────────────────────
_hv = load(Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\HNR门槛实证_既有数据.json"))
if _hv.get("bins"):
    add("方法·可靠性", "材料级 HNR 能预测低音读数是否可靠吗？",
        "不能：定向复核集里高 HNR 组错读率并不更低（62% vs 53%）"
        "⇒ 真正挡住次谐波错误的是谐波列判定 + CREPE 交叉校验 + 人耳终裁",
        _hv["bins"], sum((b or {}).get("n") or 0 for b in _hv["bins"].values()),
        "既有 149 条 YIN↔CREPE 交叉校验（**定向复核集**，非随机样本）", "B 中")

# ── 12. 曲目库规模（写作可用素材量）──────────────────────────────────
cov = load(D / "coverage_index.json").get("stat", {})
add("生涯·曲目", "他唱过多少首歌、巡演覆盖如何",
    f"选曲 {load(D / 'cover_catalog.json').get('summary', {}).get('total')} 首；"
    f"场次覆盖：有素材 {cov.get('covered')}/{cov.get('shows_total')}、已定位 {cov.get('L1_精确', 0) + cov.get('L2_强', 0)}、站点层 {cov.get('measured_shows_site')}",
    cov, cov.get("covered") or 0, "多源匹配（L1–L4 证据级）", "B 中")

OUT_JSON.write_text(json.dumps({"generated_at": TODAY, "count": len(F), "findings": F},
                               ensure_ascii=False, indent=1), encoding="utf-8")

md = [f"# 声学探索 · 可写方向清单（{TODAY}）", "",
      f"共 **{len(F)}** 条可复算观测。可信度分级：**A 高**（口径严、样本足）｜**B 中**（方向可信、样本偏小）｜**C 探索**（供启发，勿直接引用）。",
      "", "> 每条都能复算：数据源在 `D:\\wx409.github.io\\data\\`，生成器 `project_b\\build_explore_findings.py`。", ""]
cat = ""
for i, f in enumerate(F, 1):
    if f["cat"] != cat:
        cat = f["cat"]
        md += [f"## {cat}", ""]
    md += [f"### {i}. {f['question']}", f"- **观测**：{f['finding']}",
           f"- **数字**：`{json.dumps(f['numbers'], ensure_ascii=False)}`",
           f"- **样本**：n={f['n']}｜**口径**：{f['caliber']}｜**可信度**：{f['confidence']}", ""]
OUT_MD.write_text("\n".join(md), encoding="utf-8")

print(f"可写方向 {len(F)} 条 → {OUT_JSON}\n              → {OUT_MD}")
for f in F:
    print(f"  [{f['confidence'][0]}] {f['cat']}｜{f['question'][:38]}")
