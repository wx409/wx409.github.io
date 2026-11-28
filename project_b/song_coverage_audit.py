#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song_coverage_audit.py —— 按「歌曲」核对一到六巡的音频覆盖（含整场/半场覆盖逻辑）

关键逻辑（用户明确）：**一个整场或半场录影/录音，覆盖它里面所有曲目**；
不能因为"没有这首歌的单曲文件"就说该曲缺失。

输入：
  E:\\wx\\index_records\\历次巡演歌单\\王晰巡演歌单长表_单一事实源.xlsx（逐曲长表，含「备注」里的上半场/下半场）
  音频目录：E:\\wx\\王晰巡演_最优音频（FLAC）与 场次音频（m4a/wav，含官方直传）
覆盖判定（按优先级）：
  1 单曲文件：该场次存在文件名/标题含该曲目的文件
  2 半场覆盖：该场次有标「上半场/下半场」的文件，且该曲备注属于同一半场
  3 整场覆盖：该场次有「全场/整场/完整」文件
输出：data/song_coverage_status.json / .md，并打印按巡次统计与真实缺口
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
XLSX = Path(r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx")
AUD_DIRS = [Path(r"E:\wx\王晰巡演_最优音频"),
            Path(r"E:\wx\王晰巡演_视频源"),
            Path(r"E:\wx\论文素材_王晰作传\现场录音-小卡带"),
            Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")]
TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡")
HALF_UP = ("上半场", "上半")
HALF_DOWN = ("下半场", "下半")
FULL = ("全场", "整场", "完整", "全程")


def norm(s: str) -> str:
    return re.sub(r"[\s，,。、·・\-—_]+", "", str(s or ""))


def date8(s) -> str:
    d = re.sub(r"\D", "", str(s or ""))
    return d[:8]


DUR_CACHE = ROOT / "temp" / "audio_dur_cache.json"
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")


def dur_of(path):
    """音频时长（秒），带缓存：判定"整场/半场"比文件名可靠。"""
    try:
        cache = json.loads(DUR_CACHE.read_text(encoding="utf-8")) if DUR_CACHE.exists() else {}
    except Exception:
        cache = {}
    key = str(path)
    if key in cache:
        return float(cache[key])
    d = 0.0
    try:
        r = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_format", "-of", "json", key],
                           capture_output=True, text=True, timeout=60)
        d = float((json.loads(r.stdout or "{}").get("format") or {}).get("duration") or 0)
    except Exception:
        d = 0.0
    cache[key] = round(d, 1)
    DUR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DUR_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return d


def load_songs():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb["合并长表"]
    rows = list(ws.iter_rows(values_only=True))
    head = [str(c or "") for c in rows[0]]
    idx = {h: i for i, h in enumerate(head)}
    out = []
    for r in rows[1:]:
        tour_raw = str(r[idx["巡次"]] or "")
        tour = next((t for t in TOURS if tour_raw.startswith(t)), "")
        if not tour:
            continue
        out.append({
            "tour": tour, "date": date8(r[idx["日期"]]), "city": str(r[idx["场次"]] or ""),
            "no": r[idx["场次内序号"]], "song": str(r[idx["曲目"]] or "").strip(),
            "note": str(r[idx["备注"]] or ""), "norm_song": str(r[idx["数据层归一名"]] or r[idx["曲目"]] or "").strip(),
        })
    return out


def scan_files():
    """返回 [{"path","date8","city","text","song_hint"}]"""
    out = []
    for root in AUD_DIRS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in (".flac", ".wav", ".m4a", ".mp3", ".mp4"):
                continue
            if "htdemucs" in str(p) or "input_ascii" in p.name:
                continue
            rel = str(p.relative_to(root))
            m = re.search(r"(20\d{2})(\d{2})(\d{2})", rel + " " + p.name)
            out.append({"path": p, "rel": rel, "date8": m.group(0) if m else "",
                        "text": p.stem, "city": ""})
    return out


def main():
    songs = load_songs()
    files = scan_files()
    by_date = defaultdict(list)
    for f in files:
        if f["date8"]:
            by_date[f["date8"]].append(f)

    # 每场：全/半场文件标记
    show_level = defaultdict(lambda: {"full": 0, "half": set(), "per_song": 0})
    detail = []
    for s in songs:
        fs = by_date.get(s["date"], [])
        # 场次级判定（用户逻辑）：该场有整套录音（全场/整场/完整，或上半场+下半场都在）
        # → 该场每一首歌都算"有音频"，只是定位粒度不同，不能因为没有单曲文件就判缺失
        has_up = any(any(k in f["text"] for k in HALF_UP) for f in fs)
        has_down = any(any(k in f["text"] for k in HALF_DOWN) for f in fs)
        long_full = any((f.get("dur") or 0) >= 2400 for f in fs)
        long_half = any(1200 <= (f.get("dur") or 0) < 2400 for f in fs)
        show_whole = (any(any(k in f["text"] for k in FULL) for f in fs) or (has_up and has_down)
                      or long_full or (long_half and not long_full))
        song_n = norm(s["song"])
        base = norm(s["norm_song"])
        hit_kind = "full_show" if show_whole else ""
        hit_file = next((f["rel"] for f in fs if any(k in f["text"] for k in FULL)), "") if show_whole else ""
        for f in fs:
            t = norm(f["text"])
            if song_n and (song_n in t or (base and base in t)):
                hit_kind, hit_file = "per_song", f["rel"]
                break
        if not hit_kind:
            halves = [x for x in fs if any(k in x["text"] for k in HALF_UP + HALF_DOWN)]
            has_full = any(any(k in x["text"] for k in FULL) for x in fs)
            if not s["note"] and halves and not has_full:
                hit_kind, hit_file = "half_unknown", halves[0]["rel"]
        if not hit_kind:
            for f in fs:
                t = norm(f["text"])
                if any(k in f["text"] for k in FULL):
                    hit_kind, hit_file = "full_show", f["rel"]
                    break
                is_up = any(k in f["text"] for k in HALF_UP)
                is_down = any(k in f["text"] for k in HALF_DOWN)
                if s["note"] and ("上半" in s["note"] and is_up or "下半" in s["note"] and is_down):
                    hit_kind, hit_file = "half_show", f["rel"]
                    break
        detail.append({**s, "cover": hit_kind or "none", "file": hit_file})

    # 统计
    stat = defaultdict(lambda: defaultdict(int))
    for d in detail:
        stat[d["tour"]][d["cover"]] += 1
    print("巡次   曲目数   单曲   半场覆盖   整场覆盖   缺口")
    total_missing = 0
    for t in TOURS:
        s = stat[t]
        n = sum(s.values())
        miss = s.get("none", 0)
        total_missing += miss
        print(f"{t}   {n:5}   {s.get('per_song',0):4}   {s.get('half_show',0):8}   {s.get('full_show',0):8}   {miss:4}")

    missing = [d for d in detail if d["cover"] == "none"]
    (DATA / "song_coverage_status.json").write_text(
        json.dumps({"summary": {t: dict(stat[t]) for t in TOURS},
                    "missing_count": len(missing),
                    "missing": [{"tour": m["tour"], "date": m["date"], "city": m["city"],
                                 "song": m["song"], "no": m["no"]} for m in missing]},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n真实缺口（无单曲也无整/半场覆盖）{len(missing)} 首：")
    shown = 0
    for m in missing:
        if shown >= 30:
            break
        print(f"  {m['tour']} {m['date']} {m['city']}  #{m['no']} {m['song']}")
        shown += 1
    print(f"\n覆盖方式分布：", {t: dict(stat[t]) for t in TOURS})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
