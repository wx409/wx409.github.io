#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""keep_dual_sources.py —— 「自录有的、小卡带也有的，两份都保留」

之前 best_audio_export 按优先级只取最高一级（自录 > 小卡带），
导致两边都有的场次（2023-11-12 北京首场、2023-12-31 上海跨年）只剩自录。

本脚本：把小卡带那一份**补回** 最优音频 目录（前缀 [小卡带]），并登记 Excel（S 级）。
不删除任何文件；已存在的同名同尺寸文件跳过。
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
XLSX = ROOT / "data" / "最优音频清单.xlsx"
OUT = Path(r"E:\wx\王晰巡演_最优音频")
CARD = Path(r"E:\wx\论文素材_王晰作传\现场录音-小卡带")
ALIAS = {"一巡": ("Cherish", "珍晰", "一巡"), "二巡": ("二巡",), "三巡": ("图景", "三巡"),
         "四巡": ("肆益", "四巡"), "五巡": ("吾", "五巡"), "六巡": ("沉响与长歌", "六巡")}
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
""".split()]
AUDIO = {".wav", ".flac", ".m4a", ".mp3", ".aac"}


def parse(name: str):
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    d8 = m.group(0) if m else ""
    tour = next((t for t, ws in ALIAS.items() if any(w in name for w in ws)), "")
    city = next((c for c in sorted(CITIES, key=len, reverse=True) if c in name), "")
    return d8, tour, city


def main():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}
    existing = {str(r[idx["目标路径"]] or "") for r in ws.iter_rows(min_row=2, values_only=True)}

    copied = 0
    for show_dir in sorted(p for p in CARD.iterdir() if p.is_dir()):
        d8, tour, city = parse(show_dir.name)
        if not tour or not d8:
            continue
        dst_dir = OUT / tour / f"{d8}_{city or '城市未知'}"
        for src in show_dir.rglob("*"):
            if not src.is_file() or src.suffix.lower() not in AUDIO:
                continue
            if "htdemucs" in str(src):
                continue
            dst = dst_dir / f"[小卡带]{src.stem}{src.suffix}"
            if dst.exists() and dst.stat().st_size == src.stat().st_size:
                continue
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
            if str(dst) in existing:
                continue
            row = {
                "巡次": tour, "日期": d8, "城市": city, "来源": "小卡带",
                "级别": "S(真无损·小卡带)", "文件名": dst.name, "目标路径": str(dst),
                "原始路径": str(src), "大小MB": round(dst.stat().st_size / 1048576, 1),
                "格式": dst.suffix.lstrip(".").lower(), "采样率": "", "位深": "",
                "码率kbps": "", "时长秒": "", "BV": "",
            }
            ws.append([row.get(c) for c in cols])
            existing.add(str(dst))
    wb.save(XLSX)
    print(f"补回小卡带 {copied} 个文件；Excel 已同步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
