# -*- coding: utf-8 -*-
"""三份专题深挖（写作素材）——每条含：现象 / 方法 / 原始数字 / 反面证据与限定 / 可直接引用的句子。

选题依据（用户 2026-09-24：没有专家指路，靠范围铺开找可写的）：
  ① 音域的两端与"两支"证据链（能力主线）
  ② 颤音指纹：八年 0.27Hz（能力·声纹，最适合对外一句话）
  ③ 自有 vs 翻唱的音区自觉（创作/选曲主线）

产出：
  · E:\\wx\\论文素材_王晰作传\\专题深挖_三题_写作素材.md（本地）
  · data/topic_deepdives.json（机读，供站内专题页复用）

用法：python -X utf8 project_b\\build_topic_deepdives.py
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\专题深挖_三题_写作素材.md")
OUT_JSON = D / "topic_deepdives.json"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


alb = load(D / "archive_vocal_albums.json").get("songs", [])
tour = load(D / "archive_stage_tour.json")
rows = tour.get("rows", [])
s_ = tour.get("summary", {})
ca = load(D / "cover_analysis.json")
ln = load(D / "archive_long_notes.json")

T = []

# ── ① 音域两端 ───────────────────────────────────────────────────────
lows = sorted([x for x in alb if isinstance(x.get("low_hz"), (int, float))], key=lambda x: x["low_hz"])
b1 = [x for x in lows if str(x.get("low", "")).startswith("B1")]
live_lo = s_.get("lowest", {})
xm = next((r for r in rows if "厦门" in str(r.get("tag")) and str(r.get("low_note")) == "B1"), None)
T.append({
    "id": "range", "title": "音域两端：B1 61.5Hz 与 A#1 57.8Hz 的两支证据",
    "phenomenon": "录音室 72 曲最低稳定音 B1 61.5Hz（《静止了的夜晚》），B1 共 4 首；"
                  "现场层最低 A#1 57.8Hz（签唱会自录存档，谐波列通过）；"
                  "上端录音室 F5 706Hz、现场人耳确认 968Hz（莫斯科《在路上》）。",
    "method": "QQ 320k / 自录 → demucs htdemucs 人声分离 → 自研 numpy YIN 逐帧 F0"
              "（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）→ 音符切分（≥80ms、抖动<0.6 半音）"
              "→ 稳健过滤（时长≥0.15s、HNR≥5dB、rms≥中位−25dB；极值音本身≥0.2s）→ 原始混音谐波列复核。",
    "numbers": {"录音室最低": f"{lows[0]['low']} {lows[0]['low_hz']}Hz（{lows[0]['title']}）",
                "B1 曲目": [x["title"] for x in b1],
                "现场最低": f"{live_lo.get('note')} {live_lo.get('hz')}Hz（{live_lo.get('tag')}）",
                "现场人耳确认最低": (f"{xm.get('low_note')} {xm.get('low_hz')}Hz（{xm.get('tag')}）" if xm else "—"),
                "上端": "录音室 F5 706Hz；现场人耳确认 968Hz（莫斯科）"},
    "counter": "① 现场 A#1 57.8Hz 目前是「谐波列通过」而非人耳确认，引用须带此限定；"
               "② 《向着太阳》曾因 YIN 次谐波误读 D#2，经 CREPE 复核改为 G2 97.8Hz——"
               "说明单引擎读数可能错，必须双引擎+谐波列；③ 低于 Low C 的读数在混音上容易被伴奏 bass 污染。",
    "quotes": ["“他的下限 B1 比男低音标志音 Low C 还低一个半音；现场甚至到过 A#1——两端都在声部标准之外。”",
               "“4 首录音室曲目触及 B1，说明这不是一次意外，而是他四张专辑里的工作音。”"],
})

# ── ② 颤音指纹 ───────────────────────────────────────────────────────
vib = [x["vibrato_hz"] for x in alb if x.get("vibrato_hz")]
by_alb = defaultdict(list)
for x in alb:
    if x.get("vibrato_hz"):
        by_alb[x["album"]].append(x["vibrato_hz"])
av = {k: st.median(v) for k, v in by_alb.items()}
tv = [t.get("vibrato_rate_hz_median") for t in tour.get("by_tour", []) if t.get("vibrato_rate_hz_median")]
T.append({
    "id": "vibrato", "title": "颤音指纹：八年只漂 0.27Hz",
    "phenomenon": f"录音室 72 曲颤音速率中位 {st.median(vib):.2f}Hz；八张专辑各自中位仅 "
                  f"{min(av.values()):.2f}–{max(av.values()):.2f}Hz（漂移 {max(av.values())-min(av.values()):.2f}Hz）；"
                  f"六轮巡演 {min(tv):.2f}–{max(tv):.2f}Hz。",
    "method": "逐音符 F0 轨迹的调制分析（颤音速率＝调制频率，幅度＝音分跨度）；音频同上管线。",
    "numbers": {"整体中位": round(st.median(vib), 2), "专辑间": {k: round(v, 2) for k, v in av.items()},
                "巡演": [round(x, 2) for x in tv]},
    "counter": "① 颤音速率按本站分层属「组内可纵比、跨组谨慎」——修音基本不动速率，但幅度可能受影响；"
               "② 现场比录音室系统性慢 0.2–0.3Hz，属演出状态差异，不是能力下降；"
               "③ 这只说明「稳定性达到可作指纹的程度」，不构成「好/坏」评价。",
    "quotes": ["“一台八年校准误差 0.27Hz 的乐器。”",
               "“颤音速率是人类声带很难长期稳定的指标——八年间几乎不动，稳定到可以作为指纹。”"],
})

# ── ③ 自有 vs 翻唱 ───────────────────────────────────────────────────
ra = ca.get("register_adapt", {})
mv = ca.get("multi_version", {})
T.append({
    "id": "owncover", "title": "音区自觉：给自己的歌 vs 唱别人的歌",
    "phenomenon": f"现场层里自有曲最低音中位 {ra.get('own_live_low_median')}Hz（n={ra.get('own_n')}），"
                  f"翻唱曲 {ra.get('cover_live_low_median')}Hz（n={ra.get('cover_n')}）——"
                  "他给自己的歌写得更低，唱别人的歌时收着。",
    "method": "现场层逐素材最低稳定音 → 按「自有/翻唱」分组取中位（同管线同口径）；"
              "另做同曲跨场多版本方差分析。",
    "numbers": {"自有中位": ra.get("own_live_low_median"), "自有n": ra.get("own_n"),
                "翻唱中位": ra.get("cover_live_low_median"), "翻唱n": ra.get("cover_n"),
                "≥3 版本曲目": mv.get("songs_with_3plus"), "同曲跨场 CV 中位": mv.get("low_cv_median")},
    "counter": "① 两组样本严重不对称（自有 21 vs 翻唱 121），只能当倾向，不能当结论；"
               "② 自有/翻唱的划分依赖「发行归属」，个别曲目存在合作/翻唱界定争议；"
               "③ 现场选曲受场次与点歌影响，不是纯粹的创作选择。",
    "quotes": ["“他给自己写的歌，比唱别人的歌更低——低音是留给作品的签名。”",
               "“唱过 293 首里翻唱 241 首，跨巡保留率仅 2–6%：每一轮巡演几乎换血。”"],
})

OUT_JSON.write_text(json.dumps({"generated_at": "2026-09-24", "topics": T}, ensure_ascii=False, indent=1),
                    encoding="utf-8")
md = ["# 专题深挖 · 三题（写作素材）", "", "> 每题五段：现象 / 方法 / 原始数字 / 反面证据与限定 / 可直接引用的句子。",
      "> 全部数字可复算：数据源 `D:\\wx409.github.io\\data\\`，生成器 `project_b\\build_topic_deepdives.py`。", ""]
for i, t in enumerate(T, 1):
    md += [f"## 专题{i}｜{t['title']}", "",
           f"**现象**：{t['phenomenon']}", "",
           f"**方法**：{t['method']}", "",
           f"**原始数字**：`{json.dumps(t['numbers'], ensure_ascii=False)}`", "",
           f"**反面证据与限定**：{t['counter']}", "",
           "**可引用句**："]
    md += [f"- {q}" for q in t["quotes"]]
    md += [""]
OUT_MD.write_text("\n".join(md), encoding="utf-8")
print(f"三题已生成 → {OUT_JSON}\n           → {OUT_MD}")
for t in T:
    print(f"  · {t['title']}")
