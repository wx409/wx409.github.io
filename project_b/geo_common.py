#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B项目 GEO 公共路径与清洗规则（独立版，不依赖星厂 config）"""

from pathlib import Path

BASE = Path("/mnt/d/wx409.github.io/project_b")
RAW_GEO = BASE / "01_原始数据" / "geo"
CLEAN_GEO = BASE / "02_清洗数据" / "geo"
OUTPUT_GEO = BASE / "03_周报输出" / "geo"
WEBSITE_DIR = Path("/mnt/d/wx409.github.io")

for d in (RAW_GEO, CLEAN_GEO, OUTPUT_GEO):
    d.mkdir(parents=True, exist_ok=True)


def geo_sanitize_label(text, default="听众分享"):
    if not text:
        return default
    t = str(text).strip()
    return default if t.startswith("@") else t


def geo_sanitize_summary(text):
    if not text:
        return ""
    t = str(text).strip()
    return "" if t.startswith("@") else t
