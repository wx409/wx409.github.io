#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_danmaku_timeline.py —— 弹幕时间轴：找出“哪一秒观众炸了”"""
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
from banned_words import is_banned  # noqa

OUT = ROOT / "data" / "danmaku_timeline.json"
FAN = ROOT / "data" / "bili_danmaku_fan.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"
COOKIE = Path(r"E:\wx\index_records\bilibili_cookies.txt")


def get(url, ref="https://www.bilibili.com/"):
    ck = COOKIE.read_text(encoding="utf-8", errors="ignore").strip() if COOKIE.exists() else ""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": ref, "Cookie": ck})
    return urllib.request.urlopen(req, timeout=20).read()


def main():
    vids = (json.loads(FAN.read_text(encoding="utf-8")).get("videos") or [])
    rows = []
    for v in vids:
        bv = v["bvid"]
        try:
            j = json.loads(get("https://api.bilibili.com/x/web-interface/view?bvid=" + bv).decode("utf-8", "replace"))
            cid = (j.get("data") or {}).get("cid")
            if not cid:
                continue
            xml = get("https://api.bilibili.com/x/v1/dm/list.so?oid=%s" % cid, "https://www.bilibili.com/video/" + bv)
            if not xml.lstrip().startswith(b"<?xml"):
                try:
                    xml = zlib.decompress(xml, -15)
                except Exception:
                    pass
            items = []
            for m in re.finditer(r'<d p="([^"]+)">(.*?)</d>', xml.decode("utf-8", "replace"), re.S):
                try:
                    t = float(m.group(1).split(",")[0])
                except Exception:
                    continue
                txt = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if txt and not is_banned(txt):
                    items.append((t, txt))
            bins = Counter(int(t // 5) * 5 for t, _ in items)
            peaks = []
            for t, n in bins.most_common(3):
                samples = [x for tt, x in items if t <= tt < t + 5 and 4 <= len(x) <= 30][:3]
                peaks.append({"t": t, "count": n, "samples": samples})
            rows.append({"bvid": bv, "title": v.get("title"), "author": v.get("author"),
                         "count": len(items), "peaks": peaks})
            print(bv, len(items), peaks[0] if peaks else None)
        except Exception as e:
            print(bv, "ERR", str(e)[:60])
    OUT.write_text(json.dumps({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "videos": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT)


if __name__ == "__main__":
    main()
