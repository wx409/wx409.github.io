#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ingest_filters.py —— 入库统一拒绝规则（混剪 / 合集 / 多人合唱等）

为什么单独成模块：抓取入口有好几个（bili_best_fetch / bili_multip_fetch /
bili_show_fill / bili_supplement / bili_song_fill / bili_upgrade），
规则必须**一处定义、处处生效**，否则总有一条路把混剪放进来。

用户明确（2026-11-29）：**混剪不要**——无法确认它用的音源是哪一场，
对声学实测和"成长线"都是污染。
"""
from __future__ import annotations

import re

# 硬拒绝：出现在标题里就不入库
HARD = (
    "混剪", "剪辑", "多机位", "合集", "合辑", "群像",
    "reaction", "盘点", "专访", "访谈", "花絮", "预告", "片段合集",
    "同唱一首", "群星", "合唱版", "多人合唱", "饭制MV", "MV混剪",
    # 电视节目/综艺（不是巡演场次，混进来会污染场次统计）
    "声入人心", "我是歌手", "金钟奖", "春晚", "跨年晚会", "元宵", "中秋晚会",
    "综艺", "练习室", "彩排", "彩排版", "录音棚",
    # 注意：串烧**不拒绝**——它是巡演编排的一部分（用户 2026-11-29 明确）
)

# 软拒绝：出现这些词要额外判据（这里直接拦，宁缺毋滥）
SOFT = ("cover", "翻唱", "片段", "cut", "CUT")


TOUR_MARKERS = ("巡演", "巡回音乐会", "个人巡回", "个人音乐会", "音乐会", "站")


def excluded(title: str) -> str:
    """返回拒绝理由；空字符串表示可以入库。

    例外：标题里带「巡演/巡回音乐会/个人音乐会」等巡演标记时，
    即使同时出现「声入人心」这类频道前缀，也按**巡演实录**放行
    （例如 UP 主频道叫「声入人心」但上传的是 2024 杭州巡演全场）。
    """
    t = str(title or "")
    low = t.lower()
    hit = ""
    for w in HARD:
        if w.lower() in low:
            hit = w
            break
    if not hit:
        return ""
    if any(m in t for m in TOUR_MARKERS) and hit in ("声入人心", "综艺", "练习室"):
        return ""
    return f"混剪/非原始音源（{hit}）"


def excluded_soft(title: str) -> str:
    t = str(title or "")
    for w in SOFT:
        if w in t:
            return f"可能非本场原始音源（{w}）"
    return ""
