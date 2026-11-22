#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_content_calendar.py —— 每周内容日历 + 同担草稿（模板化，零 token）"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
MOMENTS = ROOT / "data" / "moments.json"
OUT = ROOT / "data" / "content_calendar.json"
DRAFTS = Path(r"E:\wx\私有工具\trend_drafts\weekly")


def main():
    m = json.loads(MOMENTS.read_text(encoding="utf-8"))
    q = (m.get("quotes") or [{}])[0]
    s = (m.get("screams") or [{}])[0]
    mem = (m.get("memes") or [{}])[0]
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    slots = [
        {"day": "周一", "date": monday.isoformat(), "type": "数据故事",
         "title": "26 首歌里，只有它唱完指数涨了 +54.2%",
         "body": "用《多听有益》做一条 30 秒：低音现场 + 字幕“26 首歌里唯一上涨”。配 story_duoting.png。",
         "link": "https://wx409.github.io/docs/交叉分析_曲目×指数×场次_2026-11-22.md"},
        {"day": "周三", "date": (monday + timedelta(days=2)).isoformat(), "type": "金句卡",
         "title": q.get("quote", ""),
         "body": "发 quote 卡：%s（%s）。配 /assets/share/quotes/q01.png，回链 moments.html。" % (q.get("quote", ""), q.get("time", "")),
         "link": q.get("url", "https://wx409.github.io/moments.html")},
        {"day": "周五", "date": (monday + timedelta(days=4)).isoformat(), "type": "现场尖叫",
         "title": s.get("title", ""),
         "body": "剪 15 秒：从弹幕峰值那一秒开始（%s 秒），保留观众尖叫/弹幕，回链原视频。" % (s.get("peak_t", "")),
         "link": "https://www.bilibili.com/video/%s" % s.get("bvid", "")},
        {"day": "周日", "date": (monday + timedelta(days=6)).isoformat(), "type": "一周合集",
         "title": "本周王晰：一条数据、一句话、一个现场",
         "body": "把本周三条合成图文；结尾放“本周路人梗”：%s" % (mem.get("top") or [""])[0],
         "link": "https://wx409.github.io/moments.html"},
    ]
    doc = {"week_start": monday.isoformat(), "generated_at": date.today().isoformat(), "slots": slots}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    DRAFTS.mkdir(parents=True, exist_ok=True)
    lines = ["# 本周内容日历（%s）" % monday.isoformat(), ""]
    for x in slots:
        lines += ["## %s %s｜%s" % (x["day"], x["date"], x["type"]), "", "**标题**：%s" % x["title"],
                  "", x["body"], "", "链接：%s" % x["link"], ""]
    (DRAFTS / (monday.isoformat() + ".md")).write_text("\n".join(lines), encoding="utf-8")
    print("→", OUT, "|", DRAFTS / (monday.isoformat() + ".md"))


if __name__ == "__main__":
    main()
