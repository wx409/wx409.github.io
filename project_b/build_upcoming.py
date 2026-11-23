#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_upcoming.py —— 已官宣、未发生的场次（主页宣传用）"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
ACT = ROOT / "data" / "activity_master.json"
OUT = ROOT / "data" / "upcoming.json"


def link_for(title: str) -> str:
    if "长城长" in title:
        return "/dongyan.html"
    if "草原之夜" in title:
        return "/live-reviews.html"
    return "/live.html"


def main():
    rows = json.loads(ACT.read_text(encoding="utf-8")).get("rows") or []
    today = date.today().isoformat()
    seen, items = set(), []
    for r in rows:
        ds = str(r.get("date") or "")[:10]
        if not ds or ds < today or r.get("cancelled"):
            continue
        title = str(r.get("title") or "").strip()
        city = str(r.get("city") or "").strip()
        key = (ds, title, city)
        if not title or key in seen:
            continue
        seen.add(key)
        items.append({"date": ds, "city": city, "title": title,
                      "kind": r.get("kind") or "", "link": link_for(title)})
    items.sort(key=lambda x: x["date"])
    OUT.write_text(json.dumps({"generated_at": date.today().isoformat(), "items": items[:8]},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("未发生场次", len(items), "→", OUT)


if __name__ == "__main__":
    main()
