#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_merge_ingest.py —— 视频与音频一次到位（合并原来的「日报抓取」和「一~六巡音频补全」）

对每个视频做完整六步，而不是两套流程各跑一半：
  1. 读视频信息（标题/UP/发布日期）        —— 视频侧
  2. 抽出 16k 单声道 wav 存进场次音频目录   —— 音频侧
  3. 归档登记到「来源台账.json」            —— 让 coverage_index 认得这条音频
  4. 转写（faster-whisper，已转写则跳过）
  5. 声学测量（F0/跨度/稳定性）
  6. 重建 coverage_index.json（一到六巡覆盖）

推断规则（写入台账时保留 infer 字段，便于回溯）：
  曲名  《…》里最短的一段；否则取标题中已知曲库命中；否则「未标注」
  巡次  标题/路径含 一巡…六巡 或 巡演名关键词（Cherish/图景/肆益/沉响与长歌/吾…）
  城市  匹配 data/cities.json 里的城市名
  日期  8 位数字，或 YYYY-MM-DD，或 YYYY年M月D日；都没有则用发布日期

用法：
  python -X utf8 project_b/bili_merge_ingest.py                 # 处理 精选 目录里未登记的视频
  python -X utf8 project_b/bili_merge_ingest.py --limit 2
  python -X utf8 project_b/bili_merge_ingest.py --bv BV1v3sN6qEuq
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
LEDGER = AUD / "来源台账.json"
CURATED = Path(r"E:\wx\论文素材_王晰作传\B站\精选")
OFFICIAL = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")
TRANS = Path(r"E:\wx\私有工具\video_transcripts\bili_official")
MEASURE = Path(r"E:\wx\私有工具\bili_measure")

TOUR_WORDS = {
    "一巡": ["一巡", "Cherish", "珍晰"],
    "二巡": ["二巡"],
    "三巡": ["三巡"],
    "四巡": ["四巡", "肆益", "图景"],
    "五巡": ["五巡", "吾"],
    "六巡": ["六巡", "沉响与长歌"],
    "签唱会": ["签唱"],
}

FFMPEG_CANDIDATES = [
    Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffmpeg.exe"),
    Path(r"D:\DSH\demos\ffmpeg.exe"),
]


def find_ffmpeg():
    for p in FFMPEG_CANDIDATES:
        if p.exists():
            return str(p)
    w = shutil.which("ffmpeg")
    return w or ""


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def jsave(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def known_songs():
    """曲库：albums.json 的 songs + 台账里出现过的 song。"""
    songs = set()
    for it in (jload(DATA / "albums.json", {}).get("songs") or []):
        t = (it.get("title") or "").strip()
        if t:
            songs.add(t)
    for it in (jload(LEDGER, {}).get("items") or []):
        s = (it.get("song") or "").strip()
        if s and s != "未标注":
            songs.add(s)
    return songs


def cities():
    j = jload(DATA / "cities.json", {})
    out = set()
    if isinstance(j, dict):
        for k, v in j.items():
            if isinstance(v, str):
                out.add(v)
            elif isinstance(v, dict):
                n = v.get("name") or v.get("city")
                if n:
                    out.add(str(n))
    elif isinstance(j, list):
        for v in j:
            if isinstance(v, str):
                out.add(v)
            elif isinstance(v, dict) and (v.get("name") or v.get("city")):
                out.add(str(v.get("name") or v.get("city")))
    out |= {"北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "重庆",
            "长沙", "苏州", "无锡", "宁波", "青岛", "天津", "厦门", "郑州", "沈阳", "哈尔滨"}
    return out


def valid_date8(y, m, d):
    try:
        y, m, d = int(y), int(m), int(d)
    except Exception:
        return ""
    if not (2000 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        return ""
    return f"{y}{m:02d}{d:02d}"


def pick_date8(raw):
    """从标题里挑一个合法日期：8 位连续 > 带分隔符 > 中文年月日。
    必须校验月份/日，否则 '2021-2023' 这种年份区间会被误读成 20212023。"""
    for m in re.finditer(r"(20\d{2})(\d{2})(\d{2})", raw):
        got = valid_date8(m.group(1), m.group(2), m.group(3))
        if got:
            return got
    for m in re.finditer(r"(20\d{2})[-_./](\d{1,2})[-_./](\d{1,2})", raw):
        got = valid_date8(m.group(1), m.group(2), m.group(3))
        if got:
            return got
    for m in re.finditer(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", raw):
        got = valid_date8(m.group(1), m.group(2), m.group(3))
        if got:
            return got
    return ""


def infer(text, song_pool, city_pool):
    raw = text or ""
    d = pick_date8(raw)

    tour = ""
    for name, words in TOUR_WORDS.items():
        if any(w in raw for w in words):
            tour = name
            break

    city = ""
    for c in sorted(city_pool, key=len, reverse=True):
        if c and c in raw:
            city = c
            break

    song = ""
    brackets = re.findall(r"[《【]([^》】]{2,20})[》】]", raw)
    if brackets:
        pool_hit = [b for b in brackets if b in song_pool]
        song = (pool_hit or sorted(brackets, key=len))[0]
    if not song:
        for s in sorted(song_pool, key=len, reverse=True):
            if s and s in raw:
                song = s
                break
    return {"song": song or "未标注", "tour": tour, "city": city, "date8": d or ""}


def ledger_has(bv):
    for it in (jload(LEDGER, {}).get("items") or []):
        if it.get("bv") == bv:
            return True
    return False


def extract_wav(ffmpeg, src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-vn",
           "-ac", "1", "-ar", "16000", str(dst)]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and dst.exists()


def run_py(script, *args):
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "project_b" / script), *args]
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def process(video: Path, ffmpeg, song_pool, city_pool):
    bv = video.name.split("_", 1)[0]
    if ledger_has(bv):
        print("skip(已登记)", bv)
        return False
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("dl", str(ROOT / "project_b" / "download_bilibili.py"))
        dl = importlib.util.module_from_spec(spec); spec.loader.exec_module(dl)
        info = dl.fetch_view(bv)
    except Exception as e:
        print("!! 取信息失败", bv, str(e)[:80])
        info = None

    title = (info or {}).get("title") or video.stem.split("_", 1)[-1]
    owner = (info or {}).get("owner") or ""
    pubdate = (info or {}).get("pubdate") or ""
    duration = (info or {}).get("duration") or 0
    guess = infer(title + " " + video.name, song_pool, city_pool)
    infer_src = "title+filename"
    if not guess["date8"] and pubdate:
        guess["date8"] = str(pubdate).replace("-", "")[:8]
        infer_src = "pubdate"

    tag = f"{guess['tour'] or '未标巡'}{guess['city'] or ''}{guess['date8'] or '00000000'}"
    song_dir = AUD / re.sub(r'[\\/:*?"<>|\s]+', "_", guess["song"])
    wav = song_dir / f"{tag}_{bv}.wav"

    ok = extract_wav(ffmpeg, video, wav)
    if not ok:
        print("!! 抽音频失败", bv)
        return False

    led = jload(LEDGER, {"schema": 1, "items": []})
    led.setdefault("items", []).append({
        "song": guess["song"], "tag": tag, "bv": bv, "title": title, "owner": owner,
        "pubdate": pubdate, "duration_s": int(duration or 0),
        "audio_kind": "video_extract", "file": str(wav.relative_to(AUD.parent)),
        "size_mb": round(wav.stat().st_size / 1048576, 2),
        "source_verdict": "B站自动抓取（视频同时抽音频）",
        "infer": {"tour": guess["tour"], "city": guess["city"], "date8": guess["date8"], "src": infer_src},
    })
    led["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    jsave(LEDGER, led)
    print(f"[合并入库] {bv} | {guess['song']} | {tag} | {wav.name}")

    # 转写 + 测量（已有则跳过）
    run_py("transcribe_bili_official.py")
    run_py("measure_bili_track.py", "--bvid", bv)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--bv", default="", help="只处理某个 BV")
    ap.add_argument("--dir", default="", help="指定视频目录（默认 精选 + 官方空间）")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("!! 找不到 ffmpeg，无法抽音频"); return 2
    song_pool, city_pool = known_songs(), cities()
    dirs = [Path(args.dir)] if args.dir else [CURATED, OFFICIAL]
    vids = []
    for d in dirs:
        if d.exists():
            vids += sorted(d.glob("*.mp4"))
    if args.bv:
        vids = [v for v in vids if v.name.startswith(args.bv)]
    if args.limit:
        vids = vids[: args.limit]
    print(f"待处理视频 {len(vids)} 个；ffmpeg={ffmpeg}")

    done = 0
    for v in vids:
        if process(v, ffmpeg, song_pool, city_pool):
            done += 1
    print(f"合并入库完成 {done} 个")

    rc = run_py("build_coverage_index.py")
    print("coverage_index 重建 rc=", rc)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
