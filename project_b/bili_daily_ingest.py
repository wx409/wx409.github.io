#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_daily_ingest.py —— 每日 B站官方空间：新视频 → 转写 → 声学测量 → 今日数据"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
VID = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")
CURATED = Path(r"E:\wx\论文素材_王晰作传\B站\精选")     # bili_collect.py 按代表性标准下载到这里
TRANS = Path(r"E:\wx\私有工具\video_transcripts\bili_official")
MEASURE = Path(r"E:\wx\私有工具\bili_measure")
STATE = ROOT / "data" / "bili_ingest_state.json"
OUT = ROOT / "data" / "bili_daily.json"
FETCH_STATUS = ROOT / "data" / "bili_fetch_status.json"

SONG = ("直拍", "现场", "live", "Live", "歌曲", "唱", "点歌", "多听有益", "哭砂", "微醺", "小河", "甩啦")
BAD = ("专访", "访谈", "纪录片", "幕后", "花絮", "特辑", "hi，", "Vlog", "预告", "reaction", "盘点", "采访")


def is_song(title):
    return any(k in title for k in SONG) and not any(k in title for k in BAD)


def transcript_quotes(bvid):
    f = next(iter(TRANS.glob(bvid + "_*.txt")), None)
    if not f:
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        if any(k in line for k in ("低音", "声音", "唱法", "稳", "嗓子")):
            out.append(re.sub(r"^\[[^\]]+\]\s*", "", line).strip())
    return out[:2]


def main():
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    files = sorted(list(VID.glob("*.mp4")) + (list(CURATED.glob("*.mp4")) if CURATED.exists() else []))
    # 现有转写/测量回填，避免首次跑重做全部
    if not state:
        for f in files:
            bv = f.name.split("_", 1)[0]
            state[bv] = {"file": f.name, "first_seen": date.today().isoformat(),
                         "transcribed": bool(list(TRANS.glob(bv + "_*.txt"))), "measured": False}
        old = json.loads((ROOT / "data" / "bili_live_measurements_2026.json").read_text(encoding="utf-8")).get("tracks", [])
        for x in old:
            if x["bvid"] in state:
                state[x["bvid"]]["measured"] = True

    new = []
    for f in files:
        bv = f.name.split("_", 1)[0]
        if bv not in state:
            state[bv] = {"file": f.name, "first_seen": date.today().isoformat(),
                         "transcribed": False, "measured": False}
            new.append(bv)

    # 转写：脚本会跳过已有的，只处理新增
    if any(not state[bv]["transcribed"] for bv in state):
        subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "transcribe_bili_official.py")], cwd=str(ROOT))
        for bv in state:
            if list(TRANS.glob(bv + "_*.txt")):
                state[bv]["transcribed"] = True

    # 声学：只对“歌”候选；每日新增才测
    for f in files:
        bv = f.name.split("_", 1)[0]
        if state[bv].get("measured") or not is_song(f.name):
            continue
        print("measure", bv, f.name, flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "measure_bili_track.py"), "--bvid", bv], cwd=str(ROOT))
        if r.returncode == 0:
            state[bv]["measured"] = True

    items = []
    title_map = {}
    try:
        cand = json.loads((ROOT / "data" / "bili_candidates.json").read_text(encoding="utf-8"))
        title_map = {x.get("bvid"): x.get("title") for x in (cand.get("items") or []) if x.get("bvid")}
    except Exception:
        pass
    for bv, st in state.items():
        if st.get("first_seen") != date.today().isoformat():
            continue
        raw_name = st.get("file", bv)
        title = title_map.get(bv) or re.sub(r"^BV\w+_", "", raw_name)
        title = re.sub(r"\.mp4$", "", title).replace("_", " ").strip()
        m = None
        mf = MEASURE / (bv + ".json")
        if mf.exists():
            try:
                mm = json.loads(mf.read_text(encoding="utf-8"))
                m = {"low": mm.get("low_stable"), "span": mm.get("span_octaves"),
                     "stability": mm.get("stability_cents_median")}
            except Exception:
                pass
        if not m:
            old = json.loads((ROOT / "data" / "bili_live_measurements_2026.json").read_text(encoding="utf-8")).get("tracks", [])
            m = next(({"low": x["low_stable"], "span": x["span_octaves"], "stability": x["stability_cents"]}
                      for x in old if x["bvid"] == bv), None)
        items.append({"bvid": bv, "title": title, "song": is_song(title),
                      "measured": m, "quotes": transcript_quotes(bv)})

    # 抓取状态：让页面能区分「确实没有新视频」和「抓取失败没确认」
    fetch_ok, fetch_note, fetch_at = None, "", ""
    try:
        st = json.loads(FETCH_STATUS.read_text(encoding="utf-8"))
        fetch_ok = bool(st.get("ok"))
        fetch_at = st.get("at") or ""
        bad = [s.get("name", "") + ":" + str(s.get("error") or s.get("count")) for s in (st.get("sources") or []) if not s.get("ok")]
        fetch_note = ("部分来源失败 -> " + "; ".join(bad[:3])) if bad else ""
    except Exception:
        fetch_note = "没有抓取状态文件（bili_fetch_status.json）"

    doc = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "date": date.today().isoformat(),
           "new_count": len(items), "measured_count": sum(1 for x in items if x["measured"]), "items": items,
           "fetch_ok": fetch_ok, "fetch_at": fetch_at, "fetch_note": fetch_note}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print("daily", len(items), "measured", doc["measured_count"])


if __name__ == "__main__":
    main()
