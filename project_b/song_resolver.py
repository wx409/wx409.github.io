# -*- coding: utf-8 -*-
"""曲名解析器（共享件）——不要再造轮子。

归一化与别名都复用仓库既有实现/数据：
  · 归一化：NFKC + 去空白 + 去书名号（与 project_b/build_entity_index.py 的 norm 一致）
  · 别名表：复用 tools/append_point_songs_to_longtable.py 的 ALIAS_TO_CANONICAL，再补本站已知别名

名称库分三级（按权威度从高到低，命中即返回，并记录来源）：
  L1 巡演歌单     data/setlists.json（64 场，「A+B」串烧会拆分）
  L2 演出活动表   E:\wx\index_records\王晰演出活动.xlsx 的「演唱曲目」列（音乐剧/晚会/综艺等）
  L3 全量曲库     data/songs_meta.json + data/song_archive.json（587 首，含单曲/OST/Live）

用法：
  from song_resolver import resolve, acoustic_for, catalog
  resolve("如果云知道")        → {'canonical': '云一定知道', 'norm': ..., 'source': 'catalog'}
  acoustic_for("多听有益")      → 最低稳定音读数（来自 data/vocal_measurements.json）
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EVENTS_XLSX = Path(r"E:\wx\index_records\王晰演出活动.xlsx")
SONG_INFO_XLSX = Path(r"E:\wx\index_records\王晰歌曲信息汇总.xlsx")   # OST&单曲 / 专辑 两表（含网易云独有曲目）

# 复用既有别名表（tools/append_point_songs_to_longtable.py）
try:
    sys.path.insert(0, str(ROOT / "tools"))
    from append_point_songs_to_longtable import ALIAS_TO_CANONICAL as _TOOLS_ALIAS  # type: ignore
except Exception:
    _TOOLS_ALIAS = {}

ALIAS = {**{k: v for k, v in _TOOLS_ALIAS.items()}, **{
    "如果云知道": "云一定知道",        # 歌迷文章把两首并写
    "thesoundofsilence": "Sound of Silence",
    "soundofsilence": "Sound of Silence",
}}


def norm(name: str) -> str:
    """NFKC + 去空白 + 去书名号（与 build_entity_index.norm 同规则）。"""
    if name is None:
        return ""
    s = str(name).strip().replace("《", "").replace("》", "")
    try:
        s = unicodedata.normalize("NFKC", s)
    except Exception:
        pass
    return re.sub(r"\s+", "", s)


def _alias(name: str) -> str:
    """别名查表：原样 + 归一化(去空白小写) 两种键都试。"""
    raw = str(name or "").strip()
    if raw in ALIAS:
        return ALIAS[raw]
    k = norm(raw).lower()
    for a, c in ALIAS.items():
        if norm(a).lower() == k:
            return c
    return raw


def split_titles(raw: str) -> list[str]:
    """拆分「A+B」「A、B」「A，B」「A/B」这类合写曲名。"""
    if not raw:
        return []
    parts = re.split(r"[+＋、,，;；/／·•]|和|与|&", str(raw))
    return [p.strip() for p in parts if p and p.strip()]


_CACHE: dict[str, dict] = {}


def catalog() -> dict[str, dict]:
    """构建三级名称库：norm(曲名) → {canonical, source, kind}"""
    if _CACHE:
        return _CACHE
    def put(name: str, source: str, kind: str = "song"):
        n = norm(_alias(name))
        if n and n not in _CACHE:
            _CACHE[n] = {"canonical": str(name).strip(), "source": source, "kind": kind}

    # L1 巡演歌单
    sl = (json.loads((DATA / "setlists.json").read_text(encoding="utf-8")).get("setlists") or {})
    for v in sl.values():
        for s in v.get("songs") or []:
            for t in split_titles(str(s.get("title") or "")) or [str(s.get("title") or "")]:
                put(t, "setlist")
    # L2 演出活动表
    try:
        import pandas as pd
        df = pd.read_excel(EVENTS_XLSX, sheet_name=0)
        for raw in df.get("演唱曲目", []):
            for t in split_titles(str(raw or "")):
                put(t, "event")
    except Exception as e:
        print(f"[WARN] 活动表读取失败（{type(e).__name__}）：{e}", file=sys.stderr)
    # L3 全量曲库
    try:
        sm = json.loads((DATA / "songs_meta.json").read_text(encoding="utf-8")).get("songs") or {}
        for k, v in sm.items():
            put(v.get("name") or k, "catalog")
    except Exception:
        pass
    try:
        sa = json.loads((DATA / "song_archive.json").read_text(encoding="utf-8")).get("songs")
        items = sa.values() if isinstance(sa, dict) else (sa or [])
        for v in items:
            if isinstance(v, dict):
                put(v.get("name") or v.get("title"), "catalog")
    except Exception:
        pass
    # L4 歌曲信息汇总.xlsx（OST&单曲 / 专辑 两个工作表；网易云独有音源的曲目在此）
    try:
        import pandas as pd
        xl = pd.ExcelFile(SONG_INFO_XLSX)
        for sh in xl.sheet_names:
            df = pd.read_excel(SONG_INFO_XLSX, sheet_name=sh, header=0)
            for col in ("歌名", "歌曲名称"):
                if col in df.columns:
                    for raw in df[col]:
                        put(raw, "songinfo")
    except Exception as e:
        print(f"[WARN] 歌曲信息汇总.xlsx 读取失败（{type(e).__name__}）", file=sys.stderr)
    # L5 网易云目录（王晰 solo 条目；网易云独有音源）
    try:
        nc = json.loads((DATA / "netease_catalog.json").read_text(encoding="utf-8")).get("songs") or {}
        for k, v in (nc.items() if isinstance(nc, dict) else []):
            if "王晰" in str(v.get("artists") or ""):
                put(v.get("name") or k, "netease")
    except Exception:
        pass
    return _CACHE


def resolve(name: str, kind_hint: str = "") -> dict:
    """把任意来源的曲名解析到规范名。命中来源优先级：setlist > event > catalog。"""
    raw = str(name or "").strip()
    if kind_hint in ("album", "series") or re.search(r"专辑|系列", raw):
        return {"canonical": raw, "norm": norm(raw), "source": "none",
                "kind": "album" if "专辑" in raw else "series"}
    cat = catalog()
    n = norm(_alias(raw))
    hit = cat.get(n)
    if hit:
        return {**hit, "norm": n}
    # 前缀/包含兜底（仅 ≥3 字，避免 2 字误配），命中多条时取来源权威度高者
    if len(n) >= 3:
        cands = [(k, v) for k, v in cat.items() if len(k) >= 3 and (k.startswith(n) or n.startswith(k))]
        if cands:
            rank = {"setlist": 0, "event": 1, "catalog": 2}
            k, v = sorted(cands, key=lambda kv: rank.get(kv[1]["source"], 9))[0]
            return {**v, "norm": k, "matched": "近似"}
    return {"canonical": raw, "norm": n, "source": "none", "kind": "song"}


_MEAS: dict[str, dict] = {}


def acoustic_for(name: str) -> dict | None:
    """查声学实测的最低稳定音（口径纪律：排除「触达音」等不作能力依据的读数）。"""
    if not _MEAS:
        try:
            rows = json.loads((DATA / "vocal_measurements.json").read_text(encoding="utf-8")).get("rows") or []
        except Exception:
            rows = []
        for r in rows:
            m = r.get("metrics") or {}
            if not m.get("low_hz"):
                continue
            if "触达" in str(r.get("version") or ""):        # 触达音单独存在，不作能力依据
                continue
            _MEAS.setdefault(norm(r.get("song")), []).append(r)
    n = norm(name)
    rows = _MEAS.get(n)
    if not rows and len(n) >= 3:
        for k, v in _MEAS.items():
            if len(k) >= 3 and (k.startswith(n) or n.startswith(k)):
                rows = v
                break
    if not rows:
        return None
    best = min(rows, key=lambda x: x["metrics"]["low_hz"])
    return {"song": best.get("song"), "layer": best.get("layer"),
            "low_note": best["metrics"]["low_note"], "low_hz": best["metrics"]["low_hz"],
            "versions": len(rows)}


if __name__ == "__main__":
    cat = catalog()
    from collections import Counter
    print(f"名称库 {len(cat)} 条｜来源分布 {Counter(v['source'] for v in cat.values())}")
    for t in ["花儿为什么这样红", "如果云知道", "The sound of silence", "渡荆门送别", "夜", "你不要担心", "向着太阳"]:
        r = resolve(t)
        a = acoustic_for(r["norm"])
        print(f"  {t:<20} → {r['source']:<8} 规范名={r['canonical'][:18]:<20} 声学={a['low_note'] + ' ' + str(a['low_hz']) + 'Hz' if a else '—'}")
