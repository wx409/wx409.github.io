#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_rules.py —— 什么素材不能进「今日」和「声学测量」的判定规则（唯一出处）

为什么要它：
  「同唱一首｜《我真的受伤了》王菀之 张学友 张杰 … 王晰 周深 …」这类群星合唱，
  测出来的「稳定最低音 B1 62.0Hz、跨度 4.03 八度」不是王晰的，是多人的最低音混在一起。
  这类素材必须整条挡在门外，而不是靠事后人工删。

三类规则：
  A 硬排除（关键词）    同唱一首/群星/合唱/串烧/合辑/联动/盘点/专访/访谈/花絮/预告/reaction
  B 多人识别（歌手名）  标题里除王晰外出现 ≥3 位歌手名 → 判为群星/拼接
  C 测量合理性        跨度 >3.6 八度 或 稳定性 >25 音分 → 不采信为「他的音域」
  另外读 data/live_exclusions.json 的 match 字段作为人工黑名单（优先级最高）。

用法：
  from bili_rules import exclude_reason, measurement_ok
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA = Path(r"D:\wx409.github.io\data")
EXCLUSIONS = DATA / "live_exclusions.json"

# A 硬排除：标题里出现即整条不要
HARD_EXCLUDE = (
    "同唱一首", "群星", "合唱", "串烧", "合辑", "联动", "连线", "多人",
    "专访", "访谈", "花絮", "幕后", "预告", "盘点", "reaction", "Reaction",
    "集锦", "合集", "盘点向", "百位", "十位",
)

# B 多人识别用的歌手名（出现在标题里就算一位；王晰本身不算）
ARTISTS = (
    "王菀之", "张学友", "张杰", "厉娜", "陈楚生", "周深", "邓紫棋", "李宇春",
    "俞灏明", "王栎鑫", "王心凌", "胡彦斌", "简美妍", "莫文蔚", "言承旭",
    "张靓颖", "于文文", "周传雄", "张凌赫", "方大同", "李佳薇", "傲日其愣",
    "张碧晨", "郁可唯", "韩红", "孙楠", "汪峰", "毛不易", "周华健", "李健",
    "林俊杰", "陈奕迅", "那英", "谭维维", "张韶涵", "杨宗纬", "萧敬腾",
    "尚雯婕", "萨顶顶", "腾格尔", "龚琳娜", "平安", "阿云嘎", "郑云龙",
)

MULTI_ARTIST_THRESHOLD = 3      # 除王晰外 ≥3 位 → 判群星
SPAN_MAX_OK = 3.6               # 八度：男低音单人极少超过 3.6
STABILITY_MAX_OK = 25.0         # 音分：越大越可能是拼接/多来源


_cache = {"bvs": None}


def manual_bvs():
    """人工黑名单：live_exclusions.json 里 in_publish=false 或任何列出的 match。"""
    if _cache["bvs"] is not None:
        return _cache["bvs"]
    s = set()
    try:
        j = json.loads(EXCLUSIONS.read_text(encoding="utf-8"))
        for it in j.get("items") or []:
            m = (it.get("match") or "").strip()
            if m.startswith("BV"):
                s.add(m)
            elif it.get("bvid"):
                s.add(it["bvid"])
    except Exception:
        pass
    _cache["bvs"] = s
    return s


def count_other_artists(title: str) -> int:
    t = re.sub(r"王晰|Elvis\s*Wang", "", title or "", flags=re.I)
    return sum(1 for a in ARTISTS if a and a in t)


def exclude_reason(title: str = "", bvid: str = "") -> str:
    """返回排除原因；空字符串表示可以进入。"""
    if bvid and bvid in manual_bvs():
        return "人工黑名单(live_exclusions)"
    t = title or ""
    for k in HARD_EXCLUDE:
        if k in t:
            return f"关键词排除：{k}"
    n = count_other_artists(t)
    if n >= MULTI_ARTIST_THRESHOLD:
        return f"多人素材：标题含 {n} 位其他歌手"
    return ""


def measurement_ok(span=None, stability=None) -> tuple:
    """测量是否可采信。返回 (ok, 原因)。"""
    try:
        if span is not None and float(span) > SPAN_MAX_OK:
            return False, f"跨度 {span} 八度 > {SPAN_MAX_OK}，疑多人/拼接"
        if stability is not None and float(stability) > STABILITY_MAX_OK:
            return False, f"稳定性 {stability} 音分 > {STABILITY_MAX_OK}，疑多来源拼接"
    except Exception:
        pass
    return True, ""
