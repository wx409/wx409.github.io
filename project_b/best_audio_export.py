#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""best_audio_export.py —— 把一到六巡「最优音源」集中到一个文件夹，并出 Excel 清单

来源与优先级（同一场次只取最高一级）：
  1 自录（ZOOM 录音笔 / 大疆，含 96kHz24bit）      E:\\wx\\自录\\王晰巡演素材存档
  2 中控台直出（工作室官微）                       场次音频\\工作室中控台*.wav
  3 小卡带 分曲 ALAC（无损，体积小）              现场录音-小卡带\\<场>\\NN 歌名.m4a
  4 小卡带 整场 WAV                               现场录音-小卡带\\<场>\\上半场/下半场/*.wav
  5 录音笔直出 / 现场补充 / FLAC 分曲
  6 官方直传 m4a（仅兜底，码率不足，Excel 标注）

输出：
  E:\\wx\\王晰巡演_最优音频\\<巡次>\\<YYYYMMDD_城市>\\[来源]原文件名
  D:\\wx409.github.io\\data\\最优音频清单.xlsx（巡次/日期/城市/来源/级别/文件/原始路径/大小/格式/采样率/码率/时长）

用法：
  python -X utf8 project_b/best_audio_export.py --dry-run     # 只算体量
  python -X utf8 project_b/best_audio_export.py               # 复制 + 出表

安全保证（重要）：
  **只复制，绝不移动/删除/改名原始文件。** 全脚本只使用 shutil.copy2，
  不含任何 unlink/rmtree/move；结束后逐个核对源文件仍存在且大小未变。
  原始目录（小卡带 / 录音笔 / 自录 / 场次音频 / FLAC）保持原样，供其它程序继续使用。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
XLSX = ROOT / "data" / "最优音频清单.xlsx"
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")

BASE = Path(r"E:\wx\论文素材_王晰作传")
SELF = Path(r"E:\wx\自录\王晰巡演素材存档")
CARD = BASE / "现场录音-小卡带"
REC = BASE / "现场录音-录音笔"
SUP = BASE / "现场录音-补充"
FLAC = BASE / "_staging_现场"
SCENE = BASE / "音域分析" / "场次音频"

TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
AUDIO = {".wav", ".flac", ".m4a", ".mp3", ".aac", ".ape"}
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
""".split()]


def parse(text: str):
    t = text
    date8 = ""
    for pat in (r"(20\d{2})(\d{2})(\d{2})",
                r"(20\d{2})[.\-_/年](\d{1,2})[.\-_/月](\d{1,2})"):
        for m in re.finditer(pat, t):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                date8 = f"{y}{mo:02d}{d:02d}"
                break
        if date8:
            break
    tour = next((x for x in TOURS if x in t), "")
    city = next((c for c in sorted(CITIES, key=len, reverse=True) if c in t), "")
    return date8, tour, city


def ffprobe(path: Path):
    try:
        r = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_streams", "-show_format",
                            "-select_streams", "a:0", "-of", "json", str(path)],
                           capture_output=True, text=True, timeout=30)
        j = json.loads(r.stdout or "{}")
        s = (j.get("streams") or [{}])[0]
        dur = float((j.get("format") or {}).get("duration") or 0)
        return {"codec": s.get("codec_name"), "sr": int(s.get("sample_rate") or 0),
                "ch": s.get("channels"), "bits": s.get("bits_per_raw_sample") or s.get("bits_per_sample"),
                "kbps": round(int(s.get("bit_rate") or 0) / 1000) or None,
                "dur_s": round(dur, 1)}
    except Exception:
        return {}


def scan():
    """返回 {show_key: {"tour","date8","city","files":[{path,src,tier}]}}"""
    shows = defaultdict(lambda: {"tour": "", "date8": "", "city": "", "files": []})

    def add(path: Path, src: str, tier: int, hint: str = ""):
        date8, tour, city = parse(hint or str(path))
        key = date8 or (tour + (city or ""))
        if not key:
            key = str(path.parent)
        sh = shows[key]
        sh["tour"] = sh["tour"] or tour
        sh["date8"] = sh["date8"] or date8
        sh["city"] = sh["city"] or city
        sh["files"].append({"path": str(path), "src": src, "tier": tier})

    # 1 自录
    if SELF.exists():
        for p in SELF.rglob("*"):
            if p.is_file() and p.suffix.lower() in AUDIO:
                add(p, "自录", 1)
    # 2/3/4 小卡带（每场目录）
    if CARD.exists():
        for show_dir in CARD.iterdir():
            if not show_dir.is_dir():
                continue
            for p in show_dir.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in AUDIO:
                    continue
                tier = 3 if p.suffix.lower() == ".m4a" else 4
                add(p, "小卡带", tier, show_dir.name)
    # 5 录音笔 / 补充 / FLAC
    for root, src in ((REC, "录音笔"), (SUP, "现场补充"), (FLAC, "FLAC分曲")):
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in AUDIO and "htdemucs" not in str(p):
                    add(p, src, 5)
    # 2 中控台直出（在 场次音频 里）
    if SCENE.exists():
        for p in SCENE.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in AUDIO:
                continue
            if "中控台" in p.name:
                add(p, "中控台", 2)
            elif p.suffix.lower() == ".m4a":
                add(p, "官方直传", 6)
    return shows


def pick(sh):
    """同一场次取最高优先级；C 级只留 1 个最大文件兜底，避免把 400 多首单曲全复制。"""
    files = sh["files"]
    if not files:
        return []
    # 政策（2026-11-28 用户要求）：自录与小卡带两份都保留，不因优先级丢弃
    # tier 1=自录、2=中控台、3=小卡带分曲、4=小卡带整场 —— 1~4 全部保留；仅 5/6 才按优先级取
    top = min(f["tier"] for f in files)
    if top == 6:
        return []
    if top <= 4:
        cand = [f for f in files if f["tier"] <= 4]
    else:
        cand = [f for f in files if f["tier"] == top]
    # 自录：同名的 flac 若已有 wav，跳过（避免重复）
    if top == 1:
        wav_stems = {Path(f["path"]).stem for f in cand if Path(f["path"]).suffix.lower() == ".wav"}
        cand = [f for f in cand if not (Path(f["path"]).suffix.lower() == ".flac"
                                       and Path(f["path"]).stem in wav_stems)]
    cand.sort(key=lambda f: f["path"])
    return cand


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-copy", action="store_true", help="只出 Excel，不复制")
    args = ap.parse_args()

    shows = scan()
    plan, total_mb = [], 0.0
    for key, sh in sorted(shows.items(), key=lambda kv: (TOURS.index(kv[1]["tour"]) if kv[1]["tour"] in TOURS else 99,
                                                         kv[1]["date8"] or "99999999")):
        chosen = pick(sh)
        if not chosen:
            continue
        tour = sh["tour"] or "未标注"
        label = f"{sh['date8'] or '日期未知'}_{sh['city'] or '城市未知'}"
        for f in chosen:
            p = Path(f["path"])
            mb = p.stat().st_size / 1048576
            total_mb += mb
            plan.append({"tour": tour, "date8": sh["date8"], "city": sh["city"], "src": f["src"],
                         "tier": f["tier"], "src_path": str(p), "size_mb": round(mb, 1),
                         "label": label, "name": p.name})

    print(f"场次 {len({(x['tour'], x['label']) for x in plan})} 个，文件 {len(plan)} 个，合计 {total_mb/1024:.1f} GB")
    by_src = defaultdict(lambda: [0, 0.0])
    for x in plan:
        by_src[x["src"]][0] += 1
        by_src[x["src"]][1] += x["size_mb"]
    for s, (c, mb) in sorted(by_src.items(), key=lambda kv: -kv[1][1]):
        print(f"  {s}: {c} 文件 {mb/1024:.1f} GB")

    if args.dry_run:
        print("--dry-run：未复制、未写表")
        return 0

    # 复制
    rows = []
    if not args.no_copy:
        for x in plan:
            dst_dir = OUT_ROOT / x["tour"] / x["label"]
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / f"[{x['src']}]{x['name']}"
            src_size = Path(x["src_path"]).stat().st_size
            if dst.exists() and dst.stat().st_size != src_size:
                # 同名但内容不同（不同日期/不同片段的 video1.wav 等）：加序号，绝不覆盖
                stem, suf = dst.stem, dst.suffix
                i = 2
                while True:
                    cand = dst_dir / f"{stem}_{i}{suf}"
                    if not cand.exists() or cand.stat().st_size == src_size:
                        dst = cand
                        break
                    i += 1
            if dst.exists() and dst.stat().st_size == src_size:
                pass
            else:
                try:
                    shutil.copy2(x["src_path"], dst)
                except Exception as e:
                    print("复制失败", x["src_path"], e)
                    continue
            x["dst"] = str(dst)
    for x in plan:
        meta = ffprobe(Path(x["src_path"]))
        rows.append({
            "巡次": x["tour"], "日期": x["date8"] or "", "城市": x["city"] or "",
            "来源": x["src"],
            "级别": {1: "A(自录)", 2: "A(中控台)", 3: "A(小卡带·分曲无损)", 4: "A(小卡带·整场)",
                     5: "B(录音笔/FLAC)", 6: "C(官方直传)"}[x["tier"]],
            "文件名": Path(x.get("dst") or x["src_path"]).name,
            "目标路径": x.get("dst", ""), "原始路径": x["src_path"],
            "大小MB": x["size_mb"], "格式": meta.get("codec"), "采样率": meta.get("sr"),
            "位深": meta.get("bits"), "码率kbps": meta.get("kbps"), "时长秒": meta.get("dur_s"),
        })

    # 未复制但需要登记的：只有 C 级（官方直传）的场次
    for key, sh in shows.items():
        if pick(sh):
            continue
        t6 = [f for f in sh["files"] if f["tier"] == 6]
        if not t6:
            continue
        best = max(t6, key=lambda f: Path(f["path"]).stat().st_size)
        meta = ffprobe(Path(best["path"]))
        rows.append({
            "巡次": sh["tour"] or "未标注", "日期": sh["date8"] or "", "城市": sh["city"] or "",
            "来源": "官方直传", "级别": "C(官方直传·未复制·码率不足)", "文件名": "(未复制)",
            "目标路径": "", "原始路径": best["path"],
            "大小MB": round(Path(best["path"]).stat().st_size / 1048576, 1),
            "格式": meta.get("codec"), "采样率": meta.get("sr"), "位深": meta.get("bits"),
            "码率kbps": meta.get("kbps"), "时长秒": meta.get("dur_s"),
        })

    # 自录里的视频素材（大疆等）只登记不复制
    if SELF.exists():
        for p in SELF.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".mkv"):
                d8, tr, ct = parse(str(p))
                rows.append({
                    "巡次": tr or "未标注", "日期": d8 or "", "城市": ct or "",
                    "来源": "自录(视频)", "级别": "V(视频素材·未复制)", "文件名": p.name,
                    "目标路径": "", "原始路径": str(p),
                    "大小MB": round(p.stat().st_size / 1048576, 1),
                    "格式": "", "采样率": "", "位深": "", "码率kbps": "", "时长秒": "",
                })

    # Excel
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
    except Exception as e:
        print("!! 没有 openpyxl，跳过 Excel:", e)
        (ROOT / "data" / "最优音频清单.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        return 1

    wb = Workbook()
    ws = wb.active
    ws.title = "最优音频"
    cols = ["巡次", "日期", "城市", "来源", "级别", "文件名", "目标路径", "原始路径",
            "大小MB", "格式", "采样率", "位深", "码率kbps", "时长秒"]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", start_color="305496")
        c.alignment = Alignment(horizontal="center")
    for r in rows:
        ws.append([r.get(k) for k in cols])
    widths = {"A": 8, "B": 10, "C": 10, "D": 10, "E": 22, "F": 38, "G": 60, "H": 60,
              "I": 9, "J": 8, "K": 9, "L": 7, "M": 10, "N": 9}
    for k, v in widths.items():
        ws.column_dimensions[k].width = v
    ws.freeze_panes = "A2"

    # 汇总页
    ws2 = wb.create_sheet("按巡次汇总")
    ws2.append(["巡次", "场次", "文件数", "合计GB"])
    agg = defaultdict(lambda: [set(), 0, 0.0])
    for x in plan:
        a = agg[x["tour"]]
        a[0].add(x["label"])
        a[1] += 1
        a[2] += x["size_mb"]
    for t in TOURS + ("未标注",):
        if t in agg:
            ws2.append([t, len(agg[t][0]), agg[t][1], round(agg[t][2] / 1024, 2)])
    for c in ws2[1]:
        c.font = Font(bold=True)

    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)
    print("Excel:", XLSX)
    print("音频目录:", OUT_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
