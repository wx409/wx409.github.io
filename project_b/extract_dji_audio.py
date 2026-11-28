#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_dji_audio.py —— 把「自录」里的视频（大疆等）抽出音轨，放进最优音频目录并追加 Excel

规则：
  - 只读源视频，**不移动/不删除**（唯一写操作是写新 flac + 改 Excel）
  - 输出：E:\\wx\\王晰巡演_最优音频\\<巡次>\\<YYYYMMDD_城市>\\[自录视频抽音频]原名.flac
  - 音轨保持原采样率，FLAC 无损压缩（体积约为 WAV 的 50–60%）
  - 若视频没有音轨、或时长 < 10 秒，跳过
  - Excel：读 data/最优音频清单.xlsx，追加到「最优音频」表，级别="A(自录视频抽音频)"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
XLSX = ROOT / "data" / "最优音频清单.xlsx"
SELF = Path(r"E:\wx\自录\王晰巡演素材存档")
FFMPEG = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffmpeg.exe")
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")

TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
""".split()]
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v"}


def parse(text: str):
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
        dur = float((j.get("format") or {}).get("duration") or 0)
        return a, dur
    except Exception:
        return None, 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vids = [p for p in SELF.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXT]
    print(f"视频 {len(vids)} 个")
    # 用覆盖索引补全「日期→城市/巡次」（大疆文件名只有日期，没有城市）
    show_map = {}
    try:
        cov = json.loads((ROOT / "data" / "coverage_index.json").read_text(encoding="utf-8"))
        for s in cov.get("shows") or []:
            d = (s.get("date") or "").replace("-", "")
            if d:
                show_map[d] = (s.get("city") or "", s.get("tour") or "")
    except Exception:
        pass
    rows, done, skipped = [], 0, 0
    for i, v in enumerate(vids, 1):
        a, dur = probe(v)
        if not a or dur < 10:
            print(f"  跳过（无音轨或过短）{v.name}")
            skipped += 1
            continue
        d8, tour, city = parse(str(v.relative_to(SELF)) + " " + v.stem)
        if d8 and (not city or not tour):
            m_city, m_tour = show_map.get(d8, ("", ""))
            city = city or m_city
            tour = tour or m_tour
        tour = tour or "未标注"
        label = f"{d8 or '日期未知'}_{city or '城市未知'}"
        dst_dir = OUT_ROOT / tour / label
        dst = dst_dir / f"[自录视频抽音频]{v.stem}.flac"
        print(f"[{i}/{len(vids)}] {tour}/{label} ← {v.name}  ({dur/60:.1f} min)")
        if args.dry_run:
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            cmd = [str(FFMPEG), "-y", "-loglevel", "error", "-i", str(v), "-vn",
                   "-c:a", "flac", str(dst)]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0 or not dst.exists():
                print("   抽音频失败:", (r.stderr or b"").decode("utf-8", "replace")[:120])
                skipped += 1
                continue
        done += 1
        rows.append({
            "巡次": tour, "日期": d8, "城市": city, "来源": "自录(视频抽音频)",
            "级别": "A(自录视频抽音频)", "文件名": dst.name, "目标路径": str(dst),
            "原始路径": str(v), "大小MB": round(dst.stat().st_size / 1048576, 1),
            "格式": "flac", "采样率": a.get("sample_rate"), "位深": a.get("bits_per_raw_sample"),
            "码率kbps": round(int(a.get("bit_rate") or 0) / 1000) or None, "时长秒": round(dur, 1),
        })

    print(f"\n抽出 {done} 个，跳过 {skipped} 个")
    if args.dry_run or not rows:
        return 0

    # 追加 Excel
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    for r in rows:
        ws.append([r.get(k) for k in cols])
    # 更新汇总页
    ws2 = wb["按巡次汇总"]
    agg = {}
    for row in ws2.iter_rows(min_row=2, values_only=True):
        if row and row[0]:
            agg[row[0]] = [row[1], row[2], row[3]]
    for r in rows:
        a = agg.setdefault(r["巡次"], [0, 0, 0])
        a[0] = (a[0] or 0)
        a[1] = (a[1] or 0) + 1
        a[2] = round((a[2] or 0) + r["大小MB"] / 1024, 2)
    for i, (k, v) in enumerate(agg.items(), start=2):
        ws2.cell(row=i, column=1, value=k)
        ws2.cell(row=i, column=2, value=v[0])
        ws2.cell(row=i, column=3, value=v[1])
        ws2.cell(row=i, column=4, value=v[2])
    wb.save(XLSX)
    print("Excel 已追加:", XLSX)
    (ROOT / "temp" / "dji_audio_rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
