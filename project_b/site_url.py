# -*- coding: utf-8 -*-
"""站点单一域名源（2026-10-11 立）：换域只改这里一处。

用法：
    from site_url import SITE_URL, url
    url("/voice.html")  ->  "https://wx409.github.io/voice.html"
说明：**只集中常量，不改现有 canonical 值**；新增生成器一律从这里取域名。
"""
from __future__ import annotations

SITE_URL = "https://wx409.github.io"


def url(path: str) -> str:
    """根相对路径 → 绝对 URL（path 以 / 开头）。"""
    p = path if path.startswith("/") else "/" + path
    return SITE_URL + p
