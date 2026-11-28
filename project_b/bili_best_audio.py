#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_best_audio.py —— 把巡检出的高码率 B 站视频收进「最优音频」目录并登记 Excel

流程（每条候选）：
  1 download_bilibili.py 下载视频到临时目录（默认 temp/bili_audio_stage）
  2 ffmpeg 抽音轨 → FLAC（无损压缩，保留原采样率）
  3 放到 E:\\wx\\王晰巡演_最优音频\\<巡次>\\<YYYYMMDD_城市>\\[B站-<来源UP>]标题.flac
  4 追加 Excel（data/最优音频清单.xlsx）一行：来源/级别/原始视频/码率/采样率/时长

质量门槛：视频码率 ≥ --min-mbps（默认 3.0 Mbps）才收；音频按 FLAC 原样保存。
只读取巡检结果 data/bili_up_audit.json，不删除任何原文件。

用法：
  python -X utf8 project_b/bili_best_audio.py --dry-run
  python -X utf8 project_b/bili_best_audio.py --per-up 2 --min-mbps 3
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
AUDIT = DATA / "bili_up_audit.json"
XLSX = DATA / "最优音频清单.xlsx"
OUT_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
STAGE = ROOT / "temp" / "bili_audio_stage"
FFMPEG = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffmpeg.exe")
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")

TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
""".split()]


def parse(text):
    date8 = ""
    for pat in (r"(20\d{2})(\d{2})(\d{2})", r"(20\d{2})[.\-_/年](\d{1,2})[.\-_/月](\d{1,2})"):
        for m in re.finditer(pat, text):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                date8 = f"{y}{mo:02d}{d:02d}"
                break
        if date8:
            break
    tour = next((x for x in TOURS if x in text), "")
    city = next((c for c in sorted(CITIES, key=len, reverse=True) if c in text), "")
    return date8, tour, city


def probe(path: Path):
    try:
        r = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_streams", "-show_format",
                            "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
        j = json.loads(r.stdout or "{}")
        a = next((s for s in (j.get("streams") or []) if s.get("codec_type") == "audio"), None)
        return a, float((j.get("format") or {}).get("duration") or 0)
    except Exception:
        return None, 0.0


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name)[:90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--per-up", type=int, default=2)
    ap.add_argument("--min-mbps", type=float, default=3.0)
    ap.add_argument("--max", type=int, default=20, help="本次最多处理多少条")
    args = ap.parse_args()

    if not AUDIT.exists():
        print("没有巡检结果:", AUDIT); return 2
    doc = json.loads(AUDIT.read_text(encoding="utf-8"))
    cands = [c for c in (doc.get("candidates") or []) if (c.get("v_kbps") or 0) / 1000 >= args.min_mbps]
    cands.sort(key=lambda c: (c.get("v_kbps") or 0), reverse=True)
    picked, seen_up = [], {}
    for c in cands:
        up = c.get("up") or "?"
        if seen_up.get(up, 0) >= args.per_up:
            continue
        seen_up[up] = seen_up.get(up, 0) + 1
        picked.append(c)
        if len(picked) >= args.max:
            break

    print(f"候选 {len(cands)} 条（≥{args.min_mbps} Mbps），本次取 {len(picked)} 条")
    if not picked:
        return 0
    if args.dry_run:
        for c in picked:
            print(f"  {(c['v_kbps'])/1000:5.2f} Mbps {c['bvid']} {c['title'][:50]}")
        return 0

    STAGE.mkdir(parents=True, exist_ok=True)
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    existing = {r[7] for r in ws.iter_rows(min_row=2, values_only=True) if r and r[7]}   # 原始路径列
    added = 0

    for c in picked:
        bv = c["bvid"]
        txt = STAGE / f"{bv}.txt"
        txt.write_text(bv, encoding="utf-8")
        print(f"\n下载 {bv} ({c['v_kbps']} kbps) {c['title'][:40]}", flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "download_bilibili.py"),
                            str(txt), "--out", str(STAGE)], cwd=str(ROOT))
        if r.returncode != 0:
            print("  下载失败，跳过"); continue
        mp4 = next((p for p in STAGE.glob(f"{bv}_*.mp4")), None)
        if not mp4:
            print("  没找到下载的 mp4，跳过"); continue
        a, dur = probe(mp4)
        if not a:
            print("  无音轨，跳过"); continue
        d8, tour, city = parse(c["title"])
        tour = tour or "未标注"
        label = f"{d8 or '日期未知'}_{city or '城市未知'}"
        dst_dir = OUT_ROOT / tour / label
        dst = dst_dir / f"[B站-{safe(c['up'])}]{safe(c['title'])}.flac"
        dst_dir.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            rr = subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(mp4),
                                 "-vn", "-c:a", "flac", str(dst)], capture_output=True)
            if rr.returncode != 0 or not dst.exists():
                print("  抽音频失败"); continue
        row = {
            "巡次": tour, "日期": d8, "城市": city, "来源": f"B站-{c['up']}",
            "级别": f"B(B站高码率 {c['v_kbps']/1000:.1f}Mbps)",
            "文件名": dst.name, "目标路径": str(dst), "原始路径": str(mp4),
            "大小MB": round(dst.stat().st_size / 1048576, 1), "格式": "flac",
            "采样率": a.get("sample_rate"), "位深": a.get("bits_per_raw_sample"),
            "码率kbps": round(int(a.get("bit_rate") or 0) / 1000) or None, "时长秒": round(dur, 1),
        }
        if str(mp4) in existing:
            continue
        ws.append([row.get(k) for k in cols])
        existing.add(str(mp4))
        added += 1
        print(f"  -> {dst.relative_to(OUT_ROOT)}")

    # 汇总页重算
    ws2 = wb["按巡次汇总"]
    agg = {}
    for r in ws2.iter_rows(min_row=2, values_only=True):
        if r and r[0]:
            agg[r[0]] = [r[1] or 0, r[2] or 0, r[3] or 0]
    for row in ws.iter_rows(min_row=2, values_only=True):
        pass
    wb.save(XLSX)
    print(f"\n完成：新增 {added} 条；Excel={XLSX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
