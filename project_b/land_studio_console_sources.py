# -*- coding: utf-8 -*-
"""落库：① 来源台账补登工作室中控台两源（四字段）② song_evidence_master 更新多源/跨场
③ 报告 传播监测\\工作室中控台两首点歌_20261015.md。"""
import json
from datetime import datetime
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")
ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析")
LEDGER = ANA / "场次音频" / "来源台账.json"
WEIBO_ID = "5353988652270759"

# ── ① 来源台账：四字段（微博 id / 抓取日期 / 上传者类型 / 与舞台相对位置）──
LED = [
    {"song": "南屏晚钟", "tag": "工作室中控台20261014_video1", "bv": f"weibo:{WEIBO_ID}#video1",
     "title": "王晰工作室 点歌环节📹《南屏晚钟》《一生中最爱》（video1）",
     "owner": "王晰Elvis-晰息相关（工作室官微）", "pubdate": "2026-10-14", "duration_s": 99,
     "audio_kind": "mp4 抽轨（aac 128k）", "bandwidth_kbps": 128,
     "file": r"场次音频\wav_工作室中控台\南屏晚钟\工作室中控台20261014_video1_5353988652270759.wav",
     "size_mb": 8.4, "duration_probe_s": 99.5,
     "source_verdict": "工作室官微·中控台直出（待指标确认）",
     "exclude_hits": [], "tour": "东演双人场（待核）", "city": "北京", "date": "2026-10-14",
     "series": "工作室中控台点歌", "fetched_at": "2026-10-15",
     "note": f"四字段：微博 id **{WEIBO_ID}**｜抓取日期 **2026-10-15**｜"
             f"上传者类型 **工作室（中控台直出，待指标确认）**｜与舞台相对位置 **官方机位**"},
    {"song": "一生中最爱", "tag": "工作室中控台20261014_video2", "bv": f"weibo:{WEIBO_ID}#video2",
     "title": "王晰工作室 点歌环节📹《南屏晚钟》《一生中最爱》（video2）",
     "owner": "王晰Elvis-晰息相关（工作室官微）", "pubdate": "2026-10-14", "duration_s": 102,
     "audio_kind": "mp4 抽轨（aac 128k）", "bandwidth_kbps": 128,
     "file": r"场次音频\wav_工作室中控台\一生中最爱\工作室中控台20261014_video2_5353988652270759.wav",
     "size_mb": 8.6, "duration_probe_s": 102.1,
     "source_verdict": "工作室官微·中控台直出（待指标确认）",
     "exclude_hits": [], "tour": "东演双人场（待核）", "city": "北京", "date": "2026-10-14",
     "series": "工作室中控台点歌", "fetched_at": "2026-10-15",
     "note": f"四字段：微博 id **{WEIBO_ID}**｜抓取日期 **2026-10-15**｜"
             f"上传者类型 **工作室（中控台直出，待指标确认）**｜与舞台相对位置 **官方机位**"},
]
led = json.loads(LEDGER.read_text(encoding="utf-8"))
have = {(x.get("tag"), x.get("bv")) for x in led["items"]}
added = 0
for e in LED:
    if (e["tag"], e["bv"]) not in have:
        led["items"].append(e)
        added += 1
LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"[台账] 新增 {added} 条（合计 {len(led['items'])}）")

# ── ② song_evidence_master：多源/跨场更新 ──
NP = {"studio_console": {"id": f"weibo:{WEIBO_ID}#video1", "noise_floor_dbfs": -63.69,
                         "hnr_db": 6.19, "dynamic_range_db": 9.34, "dur_s": 99.5,
                         "low_stable": "D#2 78.9Hz", "source": "工作室官微·中控台直出",
                         "window": "99.5s（点歌段片段）"},
      "A": {"id": "BV1DtpQ6sE8c", "noise_floor_dbfs": -34.88, "hnr_db": 1.83,
            "dynamic_range_db": 6.48, "dur_s": 203.1, "source": "现场（观众/第三方）"},
      "B": {"id": "BV1GTpn6BEFm", "noise_floor_dbfs": -32.24, "hnr_db": 3.08,
            "dynamic_range_db": 5.28, "dur_s": 191.5, "source": "现场（观众/第三方）"}}
np_delta = {"vs_A": {"noise_floor_db": round(-63.69 - (-34.88), 2), "hnr_db": round(6.19 - 1.83, 2)},
            "vs_B": {"noise_floor_db": round(-63.69 - (-32.24), 2), "hnr_db": round(6.19 - 3.08, 2)}}
YS = {"studio_console_1010": {"id": f"weibo:{WEIBO_ID}#video2", "noise_floor_dbfs": -86.61,
                              "hnr_db": 7.13, "dynamic_range_db": 11.10, "dur_s": 102.1,
                              "low_stable": "F2 89.0Hz", "source": "工作室官微·中控台直出",
                              "window": "102.1s（点歌段片段）"},
      "zhoushan_20260523": {"id": "BV13MVK6uEa9", "noise_floor_dbfs": -56.72, "hnr_db": 4.54,
                            "dynamic_range_db": 12.47, "dur_s": 251.8,
                            "low_stable": "E2 80.7Hz", "source": "现场（二次制作·待听辨）",
                            "window": "整曲 251.8s"}}
ys_delta = {"noise_floor_db": round(-86.61 - (-56.72), 2), "hnr_db": round(7.13 - 4.54, 2)}

sm = json.loads((D / "song_evidence_master.json").read_text(encoding="utf-8"))
for r in sm["rows"]:
    if r["song"] == "南屏晚钟":
        r["dual_source_check"] = {
            "n_sources": 3, "sources": NP, "delta_studio_vs_field": np_delta,
            "threshold": "Δ噪声底 ≤−3dB 或 ΔHNR ≥+3dB 才可论证升格",
            "verdict": ("工作室中控台源**达升格门槛**（Δ噪声底 −28.81/−31.45 dB、ΔHNR +4.36/+3.11 dB）→ "
                        "该源可作**能力口径**引用；两个现场源维持**触达/样本级**"),
            "consistency": ("三源同曲（点歌段），**互不矛盾**：低稳定音分别 D#2 78.9（中控台·片段）/"
                            "现场源见各自 stats；差异主要来自**来源与窗口**（中控台直出 vs 手机实录；"
                            "99.5s 片段 vs 约 200s 现场段），**不评优劣**"),
            "attribution": "极值音归属未定",
            "window_caveat": "中控台源为点歌段**片段**（99.5s），非整曲；与现场源窗口不同，只比分布不比单点",
        }
    if r["song"] == "一生中最爱":
        r["cross_venue_note"] = {
            "sources": YS, "delta": ys_delta,
            "threshold": "Δ噪声底 ≤−3dB 或 ΔHNR ≥+3dB 才可论证升格",
            "verdict": ("中控台源**达升格门槛**（Δ噪声底 −29.89 dB、ΔHNR +2.59 dB → 噪声底一项满足）→ "
                        "可作能力口径引用；三巡舟山源维持**现场/触达级**"),
            "caliber_diff": ("口径与窗口均不同：中控台＝10-10 点歌段片段 102.1s、官方机位；"
                             "舟山＝2026-05-23 个人巡演整曲 251.8s、二次制作，**只比量级**"),
            "low_stable_compare": "中控台 F2 89.0Hz（片段）vs 舟山 E2 80.7Hz（整曲）→ **片段不含更低音**，不可反推整曲差异",
            "attribution": "极值音归属未定",
        }
(D / "song_evidence_master.json").write_text(json.dumps(sm, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
print("[数据层] 南屏晚钟 3 源、一生中最爱 跨场 已更新")

# ── ③ 报告 ──
R = ["# 工作室中控台两首点歌 · 声学分析对比（2026-10-15）", "",
     "> 源：工作室官微 **2026-10-14 18:30** 帖「点歌环节📹《南屏晚钟》《一生中最爱》」"
     f"（微博 id `{WEIBO_ID}`），两个视频**均已下载归档**（video1 1:39 / video2 1:42）。",
     "> 管线：mp4 抽轨 → demucs htdemucs 分离 → 自研 YIN 逐帧 F0；三指标＝自相关 HNR／最低 10% 帧噪声底／"
     "有声帧 P95−P5 动态范围。**归属未定、不评优劣**。", "",
     "## 一、三指标与档位判断", "",
     "| 曲 | 源 | 噪声底 (dBFS) | HNR (dB) | 动态 (dB) | 低稳定音 | 档位 |", "|---|---|---|---|---|---|---|",
     f"| 南屏晚钟 | **工作室中控台**（video1） | **−63.69** | **6.19** | 9.34 | D#2 78.9Hz（片段） | **达升格门槛** |",
     "| 南屏晚钟 | 现场 A `BV1DtpQ6sE8c` | −34.88 | 1.83 | 6.48 | — | 触达/样本级 |",
     "| 南屏晚钟 | 现场 B `BV1GTpn6BEFm` | −32.24 | 3.08 | 5.28 | — | 触达/样本级 |",
     f"| 一生中最爱 | **工作室中控台**（video2） | **−86.61** | **7.13** | 11.10 | F2 89.0Hz（片段） | **达升格门槛** |",
     "| 一生中最爱 | 三巡舟山 `BV13MVK6uEa9` | −56.72 | 4.54 | 12.47 | E2 80.7Hz（整曲） | 现场/触达级 |", "",
     "- **南屏晚钟**：中控台 vs 现场 A **Δ噪声底 −28.81 dB、ΔHNR +4.36 dB**；vs B **−31.45 dB、+3.11 dB** "
     "→ **均远超门槛（≤−3 / ≥+3）** ⇒ 中控台源可作**能力口径**；两个现场源维持触达级。",
     "- **一生中最爱**：中控台 vs 舟山 **Δ噪声底 −29.89 dB（达标）、ΔHNR +2.59 dB（未达 +3）** "
     "⇒ 按门槛「或」条件**达标**，可作能力口径；舟山维持现场级。", "",
     "## 二、南屏晚钟 · 同曲多源一致性", "",
     "- **三源互不矛盾**：均为点歌段同曲；差异主要来自**来源与窗口**（中控台直出 vs 手机实录；"
     "99.5s 片段 vs 约 200s 现场段）→ **只报一致性与差异，不评优劣**。",
     "- **极值音归属未定**；中控台源为**片段**（不含整曲），不可用它反推整曲结论。", "",
     "## 三、一生中最爱 · 跨场对照（只比量级）", "",
     "- 中控台（10-10 点歌段片段 102.1s、官方机位）vs 三巡舟山（2026-05-23 整曲 251.8s、二次制作）："
     "**口径与窗口均不同**。",
     "- 低稳定音：中控台 **F2 89.0Hz**（片段）vs 舟山 **E2 80.7Hz**（整曲）→ "
     "**片段不含更低音，不能反推整曲差异**。", "",
     "## 四、来源台账四字段（已登记）", "",
     f"| 源 | 微博 id | 抓取日期 | 上传者类型 | 与舞台相对位置 |", "|---|---|---|---|---|",
     f"| video1（南屏晚钟） | {WEIBO_ID} | 2026-10-15 | 工作室（中控台直出，待指标确认）→ 指标已确认 | 官方机位 |",
     f"| video2（一生中最爱） | {WEIBO_ID} | 2026-10-15 | 同上 | 官方机位 |", ""]
(ARCH / "工作室中控台两首点歌_20261015.md").write_text("\n".join(R) + "\n", encoding="utf-8")
print("[报告]", ARCH / "工作室中控台两首点歌_20261015.md")
