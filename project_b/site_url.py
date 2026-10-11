# -*- coding: utf-8 -*-
"""站点单一域名源 + 历史域名别名表（2026-10-11 立）。

**运维口径**：**换域 = ① 在 SITE_ALIASES 里填入旧域名 ② 改 SITE_URL 一处 ③ 跑一次部署**。
生成产物里的旧域名由 `project_b/apply_site_url.py`（生成后单点收口，输出中性）统一，
**无需改 99 个生成器**。

**边界**：本文件是唯一允许出现域名字面量的生成器文件；守卫 `audit_site_url.py` 只扫生成器源码
（生成页天然含 canonical/og:url 域名，那是产物不是硬编码，**禁止改成全站扫描**）。

用法：
    from site_url import SITE_URL, SITE_ALIASES, url, canonical, og_url
"""
from __future__ import annotations

SITE_URL = "https://wx409.github.io"

# 本站历史域名（换域时把旧域名填进来；默认空 = 无历史域名，收口步骤必然零改动）
SITE_ALIASES: list[str] = []


def url(path: str) -> str:
    """根相对路径 → 绝对 URL（path 以 / 开头）。"""
    pth = path if path.startswith("/") else "/" + path
    return SITE_URL + pth


def canonical(path: str) -> str:
    return f'<link rel="canonical" href="{url(path)}">'


def og_url(path: str) -> str:
    return f'<meta property="og:url" content="{url(path)}">'
