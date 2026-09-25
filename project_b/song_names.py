# -*- coding: utf-8 -*-
"""曲名归一化模块（基础数据层单一事实源）——解决统计遗漏。

问题（2026-09-25 实测）
----------------------
指数池与站点数据里，同一首歌存在多种写法，直接统计会**漏算**：
  · `Bésame Mucho` / `Bésame Mucho (Live)`（27 首存在 (Live) 拆分）
  · `Besame Mucho` / `BesameMucho` / `Bésame Mucho` / `BésameMucho`（songs_meta 里 4 种）
  · 现场层文件名 `12Bésame Mucho`、`Besamemucho` 等
策略：**规范化键（norm）+ 别名表（data/song_aliases.json）→ 规范名（canonical）**
用法：
    from song_names import canon, norm
    canon("Bésame Mucho (Live)")   # → "Bésame Mucho"
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
ALIAS_FILE = SITE / "data" / "song_aliases.json"

# 去重规则：这些后缀/前缀不构成不同曲目
_STRIP_SUFFIX = re.compile(
    r"(?i)\s*[（(\[【]?\s*(live|现场|演唱会版|live\s*版|remix|ver\.?|version|伴奏|纯享|片段|demo)\s*[)）\]】]?\s*$")
_LEAD_NUM = re.compile(r"^\d{1,3}(?=[^\d])")          # 现场层文件名前缀 "12Bésame Mucho"
_EXT = re.compile(r"\.(wav|mp3|flac|m4a|csv|json|txt)$", re.I)


def norm(s: str) -> str:
    """规范化键：去重音、去括号后缀、去标点空格、小写。用于**匹配**，不用于展示。"""
    s = _EXT.sub("", str(s or "").strip())
    s = _LEAD_NUM.sub("", s)
    s = _STRIP_SUFFIX.sub("", s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"(?i)\b(live|remix|ver|version|feat)\b", "", s)
    s = re.sub(r"[\s·、,，.。!！?？\"'“”‘’\-—_/\\|｜（）()\[\]【】]+", "", s)
    return s.lower()


@lru_cache(maxsize=1)
def _aliases() -> dict:
    """{norm(别名): 规范名} + {规范名: 规范名}"""
    try:
        d = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    m = {}
    for canon_name, alist in (d.get("aliases") or {}).items():
        m[norm(canon_name)] = canon_name
        for a in alist:
            m[norm(a)] = canon_name
    return m


def canon(s: str) -> str:
    """返回规范名；不在别名表且无后缀则原样返回（保持展示友好）。"""
    raw = str(s or "").strip()
    a = _aliases()
    n = norm(raw)
    if n in a:
        return a[n]
    # 未登记：若原文只有 (Live) 这类后缀差异，剥掉后缀返回
    stripped = _STRIP_SUFFIX.sub("", raw).strip()
    if stripped != raw and norm(stripped) not in a:
        return stripped
    return raw


def _display_score(s: str) -> float:
    """规范名优选：偏好展示友好形式（含空格、保留重音、首字母大写）。"""
    sc = 0.0
    if _STRIP_SUFFIX.search(str(s).strip()):
        sc -= 3.0                      # 带 (Live)/现场/伴奏 后缀者不作规范名
    if " " in str(s).strip():
        sc += 2.0                      # 有空格 → 更像正式曲名（"Bésame Mucho"）
    if str(s)[:1].isupper() or ord(str(s)[:1] or "a") > 127:
        sc += 0.5
    sc += min(len(str(s)), 40) / 100   # 同分时长者略优
    return sc


def canon_list(names) -> dict:
    """把名字列表合并为 {规范名: [原始名...]}，用于审计与合并统计。"""
    out: dict[str, list[str]] = {}
    for n in names:
        out.setdefault(norm(n), []).append(n)      # 先按 norm 分组，避免 canon 回环
    res: dict[str, list[str]] = {}
    for _, variants in out.items():
        best = sorted(variants, key=lambda x: -_display_score(x))[0]
        res[best] = variants
    return res


if __name__ == "__main__":
    for t in ("Bésame Mucho (Live)", "BesameMucho", "12Bésame Mucho", "Bésame Mucho.wav",
              "一生守候 (Live)", "Sound of Silence", "在路上"):
        print(f"  {t!r:32} → {canon(t)!r}   (norm={norm(t)!r})")
