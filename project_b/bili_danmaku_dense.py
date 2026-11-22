#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_danmaku_dense.py —— 按弹幕数（而非播放）选 Top20 王晰视频并拉弹幕"""
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
from banned_words import is_banned  # noqa

OUTDIR = Path(r"E:\wx\私有工具\bili_danmaku_dense")
PUB = ROOT / "data" / "bili_danmaku_dense.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"
COOKIE = Path(r"E:\wx\index_records\bilibili_cookies.txt")
KWS = ["王晰 现场", "王晰 直拍", "王晰 舞台", "王晰 演唱会", "王晰 声入人心"]


def get(url, ref="https://www.bilibili.com/"):
    ck = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": ref, "Cookie": ck})
    return urllib.request.urlopen(req, timeout=20).read()


def main():
    seen, cand = set(), {}
    for kw in KWS:
        for v in bili_search(kw, pages=2, order="click"):
            bv = v.get("bvid")
            if not bv or bv in seen:
                continue
            seen.add(bv)
            if v.get("self_archive") or is_banned((v.get("title") or "") + (v.get("desc") or "")):
                continue
            cand[bv] = v
    print("候选", len(cand))
    rows = []
    for bv, v in cand.items():
        try:
            j = json.loads(get("https://api.bilibili.com/x/web-interface/view?bvid=" + bv).decode("utf-8", "replace"))
            d = j.get("data") or {}
            st = d.get("stat") or {}
            dm = int(st.get("danmaku") or 0)
            cid = d.get("cid") or (((d.get("pages") or [{}])[0]).get("cid"))
        except Exception:
            continue
        rows.append((dm, bv, cid, v.get("title"), v.get("author"), v.get("play")))
    rows.sort(reverse=True)
    top = rows[:20]
    print("按弹幕 Top", [(x[0], x[3][:24]) for x in top[:5]])
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = []
    for dm, bv, cid, title, author, play in top:
        if not cid:
            continue
        xml = b""
        try:
            xml = get("https://api.bilibili.com/x/v1/dm/list.so?oid=%s" % cid, "https://www.bilibili.com/video/" + bv)
        except Exception:
            pass
        if xml and not xml.lstrip().startswith(b"<?xml"):
            try:
                xml = zlib.decompress(xml, -15)
            except Exception:
                pass
        texts = [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r"<d [^>]*>(.*?)</d>", xml.decode("utf-8", "replace"), re.S)]
        texts = [t for t in texts if t and not is_banned(t)]
        out.append({"bvid": bv, "title": title, "author": author, "play": play, "danmaku_count": dm, "count": len(texts)})
        (OUTDIR / (bv + ".json")).write_text(json.dumps({**out[-1], "danmaku": texts}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(bv, dm, len(texts))
    PUB.write_text(json.dumps({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "videos": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", PUB)


if __name__ == "__main__":
    raise SystemExit(main())
