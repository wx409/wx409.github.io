#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_danmaku_fan.py —— fo 王晰的高播放舞台直拍：搜→按播放排序→取前 20→拉弹幕"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
import zlib
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
from collect_show_feedback import bili_search  # noqa
from banned_words import is_banned

OUTDIR = Path(r"E:\wx\私有工具\bili_danmaku_fan")
PUB = ROOT / "data" / "bili_danmaku_fan.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"
COOKIE = Path(r"E:\wx\index_records\bilibili_cookies.txt")
KWS = ["王晰 直拍", "王晰 现场", "王晰 舞台", "王晰 演唱会", "王晰 多听有益"]


def get(url, referer="https://www.bilibili.com/"):
    ck = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer, "Cookie": ck})
    return urllib.request.urlopen(req, timeout=20).read()


def main():
    seen, vids = set(), []
    for kw in KWS:
        for v in bili_search(kw, pages=2, order="click"):
            bv = v.get("bvid")
            if not bv or bv in seen:
                continue
            seen.add(bv)
            if v.get("self_archive"):
                continue
            author = (v.get("author") or "")
            title = (v.get("title") or "") + " " + (v.get("desc") or "")
            if is_banned(title):
                continue
            if author == "王晰Elvis" or "王晰档案站" in author:
                continue
            if "王晰" not in title:
                continue
            vids.append(v)
    vids.sort(key=lambda x: -(x.get("play") or 0))
    vids = vids[:20]
    print("候选", len(vids))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for v in vids:
        bv = v["bvid"]
        try:
            j = json.loads(get("https://api.bilibili.com/x/web-interface/view?bvid=" + bv).decode("utf-8", "replace"))
            data = j.get("data") or {}
            cid = data.get("cid") or (((data.get("pages") or [{}])[0]).get("cid"))
        except Exception as e:
            print(bv, "view ERR", str(e)[:50])
            continue
        if not cid:
            continue
        xml = b""
        for u in ("https://api.bilibili.com/x/v1/dm/list.so?oid=%s" % cid,
                  "https://comment.bilibili.com/%s.xml" % cid):
            try:
                xml = get(u, "https://www.bilibili.com/video/" + bv)
                if xml:
                    break
            except Exception:
                pass
        if not xml.lstrip().startswith(b"<?xml"):
            try:
                xml = zlib.decompress(xml, -15)
            except Exception:
                pass
        texts = [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r"<d [^>]*>(.*?)</d>", xml.decode("utf-8", "replace"), re.S)]
        texts = [t for t in texts if t and not is_banned(t)]
        rows.append({"bvid": bv, "title": v.get("title"), "author": v.get("author"),
                     "play": v.get("play"), "count": len(texts), "danmaku": texts})
        (OUTDIR / (bv + ".json")).write_text(json.dumps(rows[-1], ensure_ascii=False, indent=1), encoding="utf-8")
        print(bv, v.get("play"), len(texts), (v.get("title") or "")[:36])

    import jieba
    stop = set("的了是我你他她它在有就和都也不很还这那啊吧吗呀哦嗯哈一个什么怎么就是真的可以没有我们你们他们")
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
           "videos": [{"bvid": r["bvid"], "title": r["title"], "author": r["author"],
                       "play": r["play"], "count": r["count"]} for r in rows],
           "top_words": [{"w": w, "n": n} for w, n in words.most_common(50)],
           "emotion": dict(emo)}
    PUB.write_text(json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    print("汇总", len(rows), "个视频 /", sum(r["count"] for r in rows), "条弹幕 →", PUB)


if __name__ == "__main__":
    raise SystemExit(main())
