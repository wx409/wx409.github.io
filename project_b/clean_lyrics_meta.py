# -*- coding: utf-8 -*-
"""清理 songs_meta.json 已抓取歌词中的 LRC 元信息行（[ti:][ar:][al:][by:][offset:] 等）"""
import json
import re

META = r"D:\wx409.github.io\data\songs_meta.json"
META_LINE = re.compile(r"^\[(ti|ar|al|by|offset|length|re|ve|co|la|total|language)\s*:", re.I)
# 版权/制作信息行（QQ LRC 常见）：词/曲/编曲/原唱/制作人/Written by 等
INFO_LINE = re.compile(
    r"^(词|曲|作词|作曲|编曲|制作人|原唱|翻唱|演唱|录音|混音|母带|吉他|贝斯|鼓|键盘|弦乐|和声|监制|出品|制作|发行|长笛|单簧管|双簧管|大提琴|小提琴|中提琴|钢琴|萨克斯|小号|圆号|长号|大号|竖琴|手风琴|口琴|打击乐|管乐|配唱|和音|伴唱|合唱|企划|统筹|文案|摄影|设计|导演|录音室|录音师|混音师|母带师|制作总监|制作统筹|制作团队|母带处理|音乐总监|声乐指导|和声编写|弦乐编写|钢琴编写|Written by|Composed by|Arranged by|Produced by|Lyrics by|Music by|OP|SP)[:：]", re.I)
# 通用信息行：短标签 + 冒号（"录音室：xxx"、"王晰："声部标注、"合："等）
GENERIC_INFO = re.compile(r"^[\u4e00-\u9fa5A-Za-z·/]{1,10}[:：]")
# 特别企划/版权声明行
SPECIAL_LINE = re.compile(r"^(TME特别企划|本作品声明|出品方|企划方|文案策划)")
# 标题行：LRC 第一行常为 "歌名 - 歌手"（如 "哭砂 - 王晰"、"Autumn Leaves (Live) - 王晰 (Elvis Wang)"）
TITLE_LINE = re.compile(r"^.{1,45} - 王晰.{0,20}$")

meta = json.load(open(META, encoding="utf-8"))
cleaned_songs = 0
removed = 0
for k, v in meta["songs"].items():
    if not v.get("lyrics"):
        continue
    before = len(v["lyrics"])
    keep = []
    for i, f in enumerate(v["lyrics"]):
        t = (f.get("text") or "").strip()
        if META_LINE.match(t) or INFO_LINE.match(t) or SPECIAL_LINE.match(t):
            continue
        if i == 0 and TITLE_LINE.match(t):
            continue  # 仅移除第一行的 "歌名 - 王晰" 标题
        if GENERIC_INFO.match(t) and len(t) < 60:
            continue  # 短标签：信息/声部标注行（如 "录音室：xxx"、"王晰："）
        keep.append(f)
    v["lyrics"] = keep
    after = len(keep)
    if after != before:
        cleaned_songs += 1
        removed += before - after

json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("清理 %d 首歌, 移除 %d 行元信息" % (cleaned_songs, removed))
print("有歌词总数:", sum(1 for v in meta["songs"].values() if v.get("lyrics")))
