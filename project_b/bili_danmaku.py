#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_danmaku.py —— 拉 B站弹幕并做词频/情绪初筛

输入：E:\\wx\\论文素材_王晰作传\\B站\\官方空间\\bilibili_summary.json
输出：E:\\wx\\私有工具\\bili_danmaku\\<bvid>.json
      D:\\wx409.github.io\\data\\bili_danmaku.json（公开聚合，无昵称）
用法：python -X utf8 project_b\\bili_danmaku.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SRC = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间\bilibili_summary.json")
OUTDIR = Path(r"E:\wx\私有工具\bili_danmaku")
PUB = ROOT / "data" / "bili_danmaku.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"
COOKIE = Path(r"E:\wx\index_records\bilibili_cookies.txt")


def get(url):
    ck = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/", "Cookie": ck})
    return urllib.request.urlopen(req, timeout=20).read()


def main():
    items = json.loads(SRC.read_text(encoding="utf-8")).get("items") or []
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for it in items:
        bv = it["bvid"]
        try:
            j = json.loads(get("https://api.bilibili.com/x/web-interface/view?bvid=" + bv).decode("utf-8", "replace"))
            data = j.get("data") or {}
            cid = data.get("cid") or (((data.get("pages") or [{}])[0]).get("cid"))
        except Exception as e:
            print(bv, "view ERR", str(e)[:60])
            continue
        if not cid:
            print(bv, "no cid")
            continue
        xml = b""
        for u in ("https://api.bilibili.com/x/v1/dm/list.so?oid=%s" % cid,
                  "https://comment.bilibili.com/%s.xml" % cid):
            try:
                xml = get(u)
                if b"<d " in xml:
                    break
            except Exception:
                pass
        if not xml.lstrip().startswith(b"<?xml") and not xml.lstrip().startswith(b"<i>"):
            try:
                import zlib
                xml = zlib.decompress(xml, -15)
            except Exception:
                pass
        texts = [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r"<d [^>]*>(.*?)</d>", xml.decode("utf-8", "replace"), re.S)]
        texts = [t for t in texts if t]
        rows.append({"bvid": bv, "title": it.get("title"), "owner": it.get("owner"),
                     "duration": it.get("duration"), "count": len(texts), "danmaku": texts})
        (OUTDIR / (bv + ".json")).write_text(json.dumps(rows[-1], ensure_ascii=False, indent=1), encoding="utf-8")
        print(bv, len(texts), "条弹幕")
    # 公开聚合：词频 + 情绪
    import jieba
    stop = set("的了是我你他她它在有就和都也不很还这那啊吧吗呀哦嗯哈一个")
    words = Counter()
    emo = Counter({"笑": 0, "哭": 0, "夸": 0, "惊": 0})
    for r in rows:
        for t in r["danmaku"]:
            for w in jieba.lcut(t):
                if len(w) >= 2 and w not in stop:
                    words[w] += 1
            if re.search(r"哈哈|笑死|哈哈哈", t): emo["笑"] += 1
            if re.search(r"哭|泪|破防", t): emo["哭"] += 1
            if re.search(r"好听|绝|稳|帅|牛|爱", t): emo["夸"] += 1
            if re.search(r"卧槽|我去|震惊|竟然", t): emo["惊"] += 1
    pub = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "videos": [{"bvid": r["bvid"], "title": r["title"], "owner": r["owner"], "count": r["count"]} for r in rows],
           "top_words": [{"w": w, "n": n} for w, n in words.most_common(50)],
           "emotion": dict(emo)}
    PUB.write_text(json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    print("汇总", len(rows), "个视频 →", PUB)


if __name__ == "__main__":
    raise SystemExit(main())
