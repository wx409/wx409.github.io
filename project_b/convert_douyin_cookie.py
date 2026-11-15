#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把浏览器复制的 Cookie 行转成 yt-dlp 认的 Netscape cookies.txt。

输入：E:\\wx\\index_records\\douyin_cookie_raw.txt（一行 `k=v; k=v`，或已是 Netscape 格式）
输出：E:\\wx\\论文素材_王晰作传\\抖音\\douyin_cookies.txt
"""
from __future__ import annotations

import time
from pathlib import Path

RAW = Path(r"E:\wx\index_records\douyin_cookie_raw.txt")
OUT = Path(r"E:\wx\论文素材_王晰作传\抖音\douyin_cookies.txt")


def main() -> int:
    txt = RAW.read_text(encoding="utf-8", errors="ignore").strip()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    if "\t" in txt:  # 已是 Netscape
        OUT.write_text(txt, encoding="utf-8")
        print("已是 Netscape 格式，直接复制:", OUT)
        return 0

    line = txt.splitlines()[0].strip()
    if line.lower().startswith("cookie:"):
        line = line[7:].strip()
    pairs = [p.strip() for p in line.split(";") if "=" in p]
    exp = int(time.time()) + 30 * 86400
    out = ["# Netscape HTTP Cookie File", "# 由 douyin_cookie_raw.txt 转换", ""]
    for p in pairs:
        name, _, val = p.partition("=")
        name, val = name.strip(), val.strip()
        if not name or not val:
            continue
        out.append("\t".join([".douyin.com", "TRUE", "/", "TRUE", str(exp), name, val]))
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"转换 {len(pairs)} 条 cookie → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
