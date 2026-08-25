# -*- coding: utf-8 -*-
"""观众匿名编号模块：把小红书 @昵称 映射为稳定的「观众A/B/C」编号。

- 数据源保留原始昵称（temp/_xhs_classified.json 为内部数据），仅在渲染层匿名化；
- 编号按昵称出现频次降序、同频按昵称字典序分配，确定性可复现；
- render_xhs_songs.py / render_gz_quotes.py 共用，保证同一观众在两处编号一致。
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLS = ROOT / "temp" / "_xhs_classified.json"


def nick_of(text):
    """从 '@昵称：正文' 提取昵称；非该格式返回 None。"""
    m = re.match(r"^@([^：:]+)[：:]\s*", str(text or ""))
    return m.group(1).strip() if m else None


def strip_nick(text):
    """去掉 '@昵称：' 前缀，返回正文（用于展示）。"""
    return re.sub(r"^@([^：:]+)[：:]\s*", "", str(text or "")).strip()


def build_audience_map():
    """昵称 -> 编号（观众A/B/C…）。数据缺失时返回空映射。"""
    if not CLS.exists():
        return {}
    data = json.loads(CLS.read_text(encoding="utf-8"))

    def _iter_items():
        for _g in data.get("song_groups", {}).values():  # song_groups 值是数组，需再展开一层
            yield from _g
        yield from data.get("general", [])
        yield from data.get("short", [])

    nicks = []
    for item in _iter_items():
        if isinstance(item, dict):
            item = item.get("text", "")
        n = nick_of(item)
        if n:
            nicks.append(n)
    cnt = Counter(nicks)
    order = sorted(cnt.keys(), key=lambda n: (-cnt[n], n))
    m = {}
    for i, n in enumerate(order):
        if i < 26:
            code = chr(ord("A") + i)
        else:
            code = chr(ord("A") + (i % 26)) + str(i // 26 + 1)
        m[n] = code
    return m


def anonymize(raw_author, aud_map=None):
    """'小红书 @DanyLesinad氷' -> '小红书观众 C'；昵称不在映射中回退 '小红书观众'。"""
    if aud_map is None:
        aud_map = build_audience_map()
    m = re.search(r"@([^：:]+)", str(raw_author or ""))
    if m and m.group(1).strip() in aud_map:
        return f"小红书观众 {aud_map[m.group(1).strip()]}"
    return "小红书观众"
