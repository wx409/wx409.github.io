#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录音室作品目录口径（单一事实源 = data/albums.json）。

为什么需要这个模块：
  《回望》（2021-12-23）是 **3 首数字 EP，未出实体**，其余 7 张为录音室专辑。
  站内旧文案一律写「8 张专辑」，属不准确表述（专辑/EP 混计）。
  按项目纪律「不写死数字」，页面上的作品数一律从本模块派生，禁止手写。

用法：
    from album_catalog import phrase, stats
    stats()   -> {'works': 8, 'albums': 7, 'eps': 1, 'ep_names': ['回望'], 'songs': 72}
    phrase()  -> '七张专辑与一张数字 EP（7 张专辑 + 1 张 EP《回望》）'
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "albums.json"

_CN = {0: "零", 1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
       6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}


def _doc() -> dict:
    return json.loads(SRC.read_text(encoding="utf-8"))


def stats() -> dict:
    albums = _doc().get("albums") or []
    # 单曲（single）不计入「录音室作品」计数，避免把 2026-10 的《火光》算成第九张作品
    albums = [a for a in albums if str(a.get("kind", "")).lower() != "single"]
    eps = [a for a in albums if str(a.get("kind", "")).lower() == "ep"]
    return {
        "works": len(albums),
        "albums": len(albums) - len(eps),
        "eps": len(eps),
        "ep_names": [a.get("name", "") for a in eps],
        "songs": sum(len(a.get("songs") or []) for a in albums),
    }


def cn(n: int) -> str:
    return _CN.get(n, str(n))


def phrase(with_parenthetical: bool = True) -> str:
    """'七张专辑与一张数字 EP（7 张专辑 + 1 张 EP《回望》）' —— 全部由 albums.json 派生。"""
    s = stats()
    head = f"{cn(s['works'])}张录音室作品"
    if not with_parenthetical or s["eps"] == 0:
        return head
    ep = "、".join(f"《{n}》" for n in s["ep_names"] if n)
    tail = f"{s['albums']} 张专辑 + {s['eps']} 张 EP"
    return f"{head}（{tail}{('·' + ep) if ep else ''}）"


if __name__ == "__main__":
    print(json.dumps(stats(), ensure_ascii=False))
    print(phrase())
