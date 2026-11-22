#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_danmaku_words.py —— 弹幕高频词清洗（合并变体/去口水词/去合作方名）"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
from banned_words import is_banned  # noqa

OUT = ROOT / "data" / "danmaku_words.json"
ROOTS = [
    Path(r"E:\wx\私有工具\bili_danmaku"),
    Path(r"E:\wx\私有工具\bili_danmaku_fan"),
    Path(r"E:\wx\私有工具\bili_danmaku_dense"),
]
STOP = set("""的 了 我 你 他 她 它 是 在 有 就 也 都 不 很 还 这 那 啊 吧 吗 呀 哦 嗯 哈 一个
这个 那个 什么 怎么 就是 真的 可以 这么 感觉 还是 不是 好好 老师 爸爸 大龙 尚雯婕 深深
一下 一点 已经 现在 时候 自己 我们 你们 他们 因为 所以 但是 如果 然后 还有 没有 知道
嘎子 蔡蔡 周深 首歌 这首 觉得 这里 开始 为什么 激动 这是 好像 出来 大家 男人 佳哥 鹤鹤 看到 知道 节目 川子 黄子 一样 警告 这样 表情 感觉""".split())
MERGE = {
    "好听": "好听", "开口": "开口跪", "开口跪": "开口跪",
    "前方": "前方高能", "高能": "前方高能",
    "低音": "低音", "音色": "音色", "声音": "声音",
    "声入": "声入人心", "人心": "声入人心",
    "晰哥": "王晰", "晰晰": "王晰", "王晰": "王晰",
    "呜呜": "哭", "泪": "哭", "破防": "哭",
}


def norm(t):
    t = re.sub(r"哈{2,}", "笑", t)
    t = re.sub(r"啊{2,}", "激动", t)
    t = re.sub(r"呜{2,}", "哭", t)
    t = re.sub(r"[^\u4e00-\u9fa5A-Za-z]", " ", t)
    return t


def main():
    import jieba
    c = Counter()
    for root in ROOTS:
        if not root.exists():
            continue
        for f in root.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for t in d.get("danmaku") or []:
                if not t or is_banned(t):
                    continue
                for w in jieba.lcut(norm(t)):
                    w = w.strip()
                    if len(w) < 2 or w in STOP:
                        continue
                    w = MERGE.get(w, w)
                    if w in ("笑", "激动", "哭"):
                        c[w] += 1
                    elif w not in STOP:
                        c[w] += 1
    top = [{"w": w, "n": n} for w, n in c.most_common(40)]
    OUT.write_text(json.dumps({"generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "top_words": top}, ensure_ascii=False, indent=1), encoding="utf-8")
    print([(x["w"], x["n"]) for x in top[:20]])
    print("→", OUT)


if __name__ == "__main__":
    main()
