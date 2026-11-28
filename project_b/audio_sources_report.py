#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audio_sources_report.py —— 一到六巡「高质量音频」位置清单

只为回答一个问题：哪一场、有什么高质量录音、文件在哪。
扫描四个来源，按「场次」归并，产出 JSON + Markdown。

来源与质量分级：
  A 小卡带（SD 卡录音机）   E:\\wx\\论文素材_王晰作传\\现场录音-小卡带      ← 自录，最高
  A 中控台直出              工作室官微（见来源台账 source_verdict）
  B 录音笔直出（B站UP上传）  E:\\wx\\论文素材_王晰作传\\现场录音-录音笔
  B 现场补充（wav）         E:\\wx\\论文素材_王晰作传\\现场录音-补充
  B FLAC 分曲               E:\\wx\\论文素材_王晰作传\\_staging_现场\\*
  C 官方直传（m4a 320k）    场次音频\\来源台账.json（官方直传）

用法：python -X utf8 project_b/audio_sources_report.py
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
BASE = Path(r"E:\wx\论文素材_王晰作传")
SRC = {
    "小卡带": BASE / "现场录音-小卡带",
    "录音笔": BASE / "现场录音-录音笔",
    "现场补充": BASE / "现场录音-补充",
    "FLAC分曲": BASE / "_staging_现场",
    "场次音频": BASE / "音域分析" / "场次音频",
}
TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
AUDIO_EXT = {".wav", ".flac", ".m4a", ".mp3", ".aac", ".ape", ".wv"}
def tier_of(src_name: str) -> str:
    if "小卡带" in src_name or "中控台" in src_name:
        return "A"
    if "录音笔" in src_name or "补充" in src_name or "_staging" in src_name:
        return "B"
    return "C"


def parse_show(text: str):
    """从路径里提取 (date8, tour, city)。"""
    t = text
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", t)
    if not m:
        m = re.search(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})", t)
    date8 = ""
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            date8 = f"{y}{mo}{d}"
    tour = next((x for x in TOURS if x in t), "")
    # 城市：从常见分隔符里取
    city = ""
    for sep in ("·", "｜", "|", "_"):
        if sep in t:
            parts = [p for p in t.split(sep) if p]
            for p in reversed(parts):
                p = p.strip()
                if 2 <= len(p) <= 5 and not any(c.isdigit() for c in p) and p not in TOURS:
                    city = p
                    break
        if city:
            break
    return date8, tour, city


def walk_audio(root: Path, top_only=False):
    if not root.exists():
        return
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in AUDIO_EXT:
            continue
        if "htdemucs" in str(p) or "input_ascii" in p.name:
            continue          # 人声分离中间产物，不算原始素材
        rel = str(p.relative_to(root))
        if "小卡带" in root.name and ("\\" in rel):
            head = rel.split("\\")[0]          # 形如 "20190908 一巡·…·深圳"
            date8, tour, city = parse_show(head)
            if not city:
                seg = [x.strip() for x in head.split("·") if x.strip()]
                city = re.sub(r"[（(].*?[)）]", "", seg[-1]) if seg else ""
        else:
            date8, tour, city = parse_show(p.parent.name + "/" + p.name)
        yield {
            "src": root.name, "file": str(p), "rel": rel,
            "name": p.name, "size_mb": round(p.stat().st_size / 1048576, 1),
            "ext": p.suffix.lower(), "date8": date8, "tour": tour, "city": city,
        }


def probe(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "a:0",
                            "-of", "json", str(path)], capture_output=True, text=True, timeout=20)
        s = (json.loads(r.stdout or "{}").get("streams") or [{}])[0]
        return {"codec": s.get("codec_name"), "sr": s.get("sample_rate"),
                "ch": s.get("channels"), "bits": s.get("bits_per_raw_sample") or s.get("bits_per_sample"),
                "kbps": (int(s.get("bit_rate") or 0) // 1000) or None}
    except Exception:
        return {}


def main():
    shows = defaultdict(lambda: {"tour": "", "city": "", "date8": "", "files": []})
    total = 0
    for name, root in SRC.items():
        n = 0
        for item in walk_audio(root):
            key = item["date8"] or item["rel"].split("\\")[0]
            sh = shows[key]
            sh["tour"] = sh["tour"] or item["tour"]
            sh["city"] = sh["city"] or item["city"]
            sh["date8"] = sh["date8"] or item["date8"]
            item["tier"] = tier_of(item["src"])
            sh["files"].append(item)
            n += 1
            total += 1
        print(f"{name}: {n} 个音频文件")

    # 按巡次排序
    order = {t: i for i, t in enumerate(TOURS)}
    items = sorted(shows.values(), key=lambda s: (order.get(s["tour"], 99), s["date8"] or "9999"))

    out = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "note": "A=自录/中控台直出，B=录音笔/FLAC分曲，C=官方直传m4a；htdemucs 人声分离中间文件已排除",
           "total_files": total, "shows": []}
    for s in items:
        files = sorted(s["files"], key=lambda x: ({"A": 0, "B": 1, "C": 2}[x["tier"]], -x["size_mb"]))
        out["shows"].append({"tour": s["tour"] or "未标注", "city": s["city"], "date8": s["date8"],
                             "bytes_mb": round(sum(f["size_mb"] for f in files), 1),
                             "files": files})

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "audio_sources_1to6.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # Markdown
    lines = ["# 一到六巡 · 高质量音频位置清单", "",
             f"> 生成：{out['generated_at']}　共 {total} 个音频文件",
             "> 分级：**A** 自录小卡带 / 中控台直出　**B** 录音笔直出 / FLAC 分曲　**C** 官方直传 m4a",
             "> 已排除 htdemucs 人声分离的中间文件（那是派生产物，不是原始录音）", ""]
    cur = None
    for s in out["shows"]:
        tour = s["tour"]
        if tour != cur:
            lines += ["", f"## {tour}", ""]
            cur = tour
        head = f"### {s['date8'] or '日期未知'} {s['city'] or ''}　（{len(s['files'])} 个文件 / {s['bytes_mb']} MB）"
        lines.append(head)
        lines.append("")
        lines.append("| 级别 | 来源 | 文件 | 大小 |")
        lines.append("|---|---|---|---|")
        for f in s["files"][:12]:
            lines.append(f"| {f['tier']} | {f['src']} | `{f['file']}` | {f['size_mb']} MB |")
        if len(s["files"]) > 12:
            lines.append(f"| … | | 还有 {len(s['files']) - 12} 个文件，见 JSON | |")
        lines.append("")
    (DATA / "audio_sources_1to6.md").write_text("\n".join(lines), encoding="utf-8")

    # 控制台汇总
    by_tour = defaultdict(lambda: [0, 0.0])
    for s in out["shows"]:
        by_tour[s["tour"]][0] += 1
        by_tour[s["tour"]][1] += s["bytes_mb"]
    print("\n按巡次：")
    for t in TOURS + ("未标注",):
        if t in by_tour:
            c, mb = by_tour[t]
            print(f"  {t}: {c} 场，{mb/1024:.1f} GB")
    print("\n输出:", DATA / "audio_sources_1to6.md")


if __name__ == "__main__":
    main()
