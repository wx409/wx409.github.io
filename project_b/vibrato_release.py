# -*- coding: utf-8 -*-
"""颤音极差的唯一读取口：页面与生成器不得自行 max-min。"""
from __future__ import annotations

import json
from pathlib import Path

_D = Path(__file__).resolve().parent.parent / "data" / "derived" / "vibrato_spread.json"


def load() -> dict:
    return json.loads(_D.read_text(encoding="utf-8"))


def release() -> tuple[float, str, str]:
    """当前发布值（完整基准）、快照日期、快照 id。"""
    d = load()
    r = d.get("release") or {}
    return float(r.get("value_hz", 0.27)), str(r.get("snapshot_date", "")), str(r.get("snapshot_id", ""))


def candidate() -> tuple[float, str, bool]:
    """候选值、状态、是否可发布。"""
    d = load()
    c = d.get("candidate") or {}
    return float(c.get("value_hz", d.get("value_hz", 0.39))), str(c.get("status", "")), bool(c.get("publishable"))
