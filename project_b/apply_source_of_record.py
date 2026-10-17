# -*- coding: utf-8 -*-
"""落库「音源口径」：两晚点歌 4 首位王晰独唱，**测量源唯一＝王晰工作室微博视频（中控台直出）**。

产物：
  1. `data/song_source_of_record.json` —— 口径事实源（4 首 → 工作室帖子/视频序号/抓取日/机位）
  2. 台账 `来源台账.json` 补登 10-12 帖的两段视频（哭砂/亲密爱人），并清理重复条目
  3. 现场层 `archive_stage_tour.json` 行内标注 `source_of_record` / `corroboration_only`
  4. `song_evidence_master.json` 内写 `source_of_record`（含 missing_studio_source 检查）

规则：
  · 这 4 首的主读数**只能**来自上述 4 段工作室视频；
  · 其它源（B站/小红书 1-1 视角/观众侧）一律 `corroboration_only=true`，**不进主读数字段**；
  · 缺工作室版本 → `missing_studio_source=true` 并从汇总剔除，**不得用其它源顶替**。

用法：python -X utf8 project_b/apply_source_of_record.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析")
LEDGER = ANA / "场次音频" / "来源台账.json"
POLICY = D / "song_source_of_record.json"

POST_A = "5353266315265746"   # 10-12 18:40《哭砂》《亲密爱人》
POST_B = "5353988652270759"   # 10-14 18:30《南屏晚钟》《一生中最爱》

RECORDS = [
    {"song": "亲密爱人", "night": "2026-10-09", "note_id": POST_A, "video_index": 2,
     "tag": "工作室中控台20261012_video2_5353266315265746",
     "file": r"场次音频\wav_工作室中控台\亲密爱人\工作室中控台20261012_video2_5353266315265746.wav"},
    {"song": "哭砂", "night": "2026-10-09", "note_id": POST_A, "video_index": 1,
     "tag": "工作室中控台20261012_video1_5353266315265746",
     "file": r"场次音频\wav_工作室中控台\哭砂\工作室中控台20261012_video1_5353266315265746.wav"},
    {"song": "南屏晚钟", "night": "2026-10-10", "note_id": POST_B, "video_index": 1,
     "tag": "工作室中控台20261014_video1_5353988652270759",
     "file": r"场次音频\wav_工作室中控台\南屏晚钟\工作室中控台20261014_video1_5353988652270759.wav"},
    {"song": "一生中最爱", "night": "2026-10-10", "note_id": POST_B, "video_index": 2,
     "tag": "工作室中控台20261014_video2_5353988652270759",
     "file": r"场次音频\wav_工作室中控台\一生中最爱\工作室中控台20261014_video2_5353988652270759.wav"},
]
COMMON = {"source_type": "工作室·中控台直出", "fetched_at": "2026-10-15",
          "camera": "官方机位", "corroboration_only": False}


def main() -> int:
    doc = {
        "schema": 1,
        "policy": ("两晚点歌 4 首（王晰独唱）**测量源唯一**＝王晰工作室微博视频（中控台直出）；"
                   "观众侧素材（B站/小红书 1-1 视角等）一律 corroboration_only，不进主读数；"
                   "缺工作室版本 → missing_studio_source 并从汇总剔除，**不得用其它源顶替**"),
        "decided_at": "2026-10-17",
        "records": [{**r, **COMMON, "bv": f"weibo:{r['note_id']}#video{r['video_index']}",
                     "verified_by": "ASR 唱词核对（video1=哭砂 / video2=亲密爱人；"
                                    "南屏晚钟/一生中最爱 由帖文顺序＋此前实测）"}
                    for r in RECORDS],
    }
    POLICY.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {POLICY}（{len(doc['records'])} 条）")

    # ── 台账：补登 10-12 两段 + 清理重复 tag ──
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    items = led["items"]
    seen, dedup = set(), []
    for it in items:
        key = (it.get("tag"), it.get("bv"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(it)
    led["items"] = dedup
    have = {(x.get("tag"), x.get("bv")) for x in dedup}
    added = 0
    for r in RECORDS:
        tag = r["tag"]
        bv = f"weibo:{r['note_id']}#video{r['video_index']}"
        for it in dedup:                       # 已有（tag 可能带/不带 hash）→ 补字段
            if it.get("bv") == bv:
                it.update({"source_type": COMMON["source_type"], "note_id": r["note_id"],
                           "video_index": r["video_index"], "camera": "官方机位",
                           "corroboration_only": False})
        if (tag, bv) in have or any(it.get("bv") == bv for it in dedup):
            continue
        dedup.append({
            "song": r["song"], "tag": tag, "bv": bv,
            "title": f"王晰工作室 点歌环节（{r['song']}，video{r['video_index']}）",
            "owner": "王晰Elvis-晰息相关（工作室官微）", "pubdate": "2026-10-12",
            "audio_kind": "mp4 抽轨（aac 128k）", "source_verdict": "工作室官微·中控台直出",
            "source_type": COMMON["source_type"], "note_id": r["note_id"],
            "video_index": r["video_index"], "camera": "官方机位",
            "corroboration_only": False, "tour": "工作室中控台（点歌段）",
            "date": r["night"], "series": "工作室中控台点歌", "fetched_at": "2026-10-15",
            "file": r["file"], "note": "音源口径：本曲唯一测量源（中控台直出）",
        })
        added += 1
    # 其它源（同曲）标 corroboration_only
    four = {r["song"] for r in RECORDS}
    for it in led["items"]:
        if it.get("song") in four and it.get("source_type") != COMMON["source_type"]:
            it["corroboration_only"] = True
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[台账] 去重 {len(items) - len(dedup)} 条；新增 {added} 条；合计 {len(led['items'])}")

    # ── 现场层标注 ──
    st = json.loads((D / "archive_stage_tour.json").read_text(encoding="utf-8"))
    rec_by_tag = {r["tag"]: r for r in RECORDS}
    n_open = n_corr = 0
    for row in st.get("rows") or []:
        tag = str(row.get("tag") or "")
        song = row.get("song")
        if tag in rec_by_tag:
            r = rec_by_tag[tag]
            row["source_of_record"] = {"source_type": COMMON["source_type"], "note_id": r["note_id"],
                                       "video_index": r["video_index"],
                                       "fetched_at": COMMON["fetched_at"], "camera": "官方机位",
                                       "bv": f"weibo:{r['note_id']}#video{r['video_index']}"}
            row["corroboration_only"] = False
            n_open += 1
        elif song in four:
            row["corroboration_only"] = True
            n_corr += 1
    (D / "archive_stage_tour.json").write_text(json.dumps(st, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    print(f"[现场层] 标注主源 {n_open} 行；其余 {n_corr} 行标 corroboration_only")

    # ── master：source_of_record + missing 检查 ──
    sm = json.loads((D / "song_evidence_master.json").read_text(encoding="utf-8"))
    by = {r["song"]: r for r in sm["rows"]}
    for r in RECORDS:
        row = by.get(r["song"])
        if row is None:
            continue
        std = [x for x in (st.get("rows") or []) if x.get("tag") == r["tag"]]
        row["source_of_record"] = {
            "source_type": COMMON["source_type"], "note_id": r["note_id"],
            "video_index": r["video_index"], "fetched_at": COMMON["fetched_at"],
            "camera": "官方机位", "bv": f"weibo:{r['note_id']}#video{r['video_index']}",
            "night": r["night"], "source_tag": r["tag"],
            "measured": ({"low_note": std[0].get("low_note"), "low_hz": std[0].get("low_hz"),
                          "review_status": std[0].get("review_status")} if std else None),
            "missing_studio_source": not bool(std),
        }
        row["corroboration_policy"] = ("其它源仅作一致性旁证（corroboration_only=true），"
                                       "**不进主读数字段**；缺工作室版本不得顶替")
    (D / "song_evidence_master.json").write_text(json.dumps(sm, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    miss = [r["song"] for r in RECORDS if not any(x.get("tag") == r["tag"] for x in (st.get("rows") or []))]
    print(f"[master] 已写 4 首 source_of_record；missing_studio_source: {miss or '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
