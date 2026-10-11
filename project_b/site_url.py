# -*- coding: utf-8 -*-
"""站点单一域名源（2026-10-11 立）：换域只改这里一处。

**边界**：本文件是唯一允许出现域名字面量的生成器文件；
守卫 `audit_site_url.py` 只扫生成器源码（生成页天然含 canonical/og:url 域名，不算硬编码）。

用法：
    from site_url import SITE_URL, url, canonical, og_url
    url("/voice.html")        -> "https://wx409.github.io/voice.html"
    canonical("/voice.html")  -> <link rel="canonical" ...> 片段
"""
from __future__ import annotations

SITE_URL = "https://wx409.github.io"


def url(path: str) -> str:
    """根相对路径 → 绝对 URL（path 以 / 开头）。"""
    pth = path if path.startswith("/") else "/" + path
    return SITE_URL + pth


def canonical(path: str) -> str:
    return f'<link rel="canonical" href="{url(path)}">'


def og_url(path: str) -> str:
    return f'<meta property="og:url" content="{url(path)}">'
