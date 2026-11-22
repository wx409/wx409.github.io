# -*- coding: utf-8 -*-
"""banned_words.py —— 弹幕/评论采集的禁用词（周深及其变体、CP 梗）"""

BANNED = [
    "周深", "深深", "深呼吸", "深呼晰", "小深", "吸深", "盘深",
    "深崽", "深宝宝", "深呼晰CP", "Zhou Shen", "Charlie Zhou",
]


def is_banned(text: str) -> bool:
    t = str(text or "")
    return any(w and w in t for w in BANNED)


def clean_lines(lines):
    return [x for x in lines if x and not is_banned(x)]
