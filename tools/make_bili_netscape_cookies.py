# -*- coding: utf-8 -*-
"""把 E:\\wx\\index_records\\bilibili_cookies.txt（单行 "k=v; k=v" 形式）转成
Netscape 格式 cookies 文件，供 yt-dlp 使用（本机用，写入 B 站 cookies 目录，不进 git）。

用法：python -X utf8 tools/make_bili_netscape_cookies.py
输出：E:\\wx\\index_records\\bilibili_cookies_netscape.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(r"E:\wx\index_records\bilibili_cookies.txt")
DST = Path(r"E:\wx\index_records\bilibili_cookies_netscape.txt")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = SRC.read_text(encoding="utf-8", errors="ignore").strip()
    if raw.startswith("# Netscape") or "\t" in raw.splitlines()[0]:
        DST.write_text(raw if raw.endswith("\n") else raw + "\n", encoding="utf-8")
        print("[=] 已是 Netscape 格式，直接复制 →", DST)
        return 0
    lines = ["# Netscape HTTP Cookie File", "# 由 tools/make_bili_netscape_cookies.py 生成（本机用，勿入 git）"]
    n = 0
    for part in raw.replace("\n", ";").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k:
            continue
        # domain  flag  path  secure  expiry  name  value
        lines.append("\t".join([".bilibili.com", "TRUE", "/", "TRUE", "0", k, v]))
        n += 1
    DST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] 转换 %d 条 cookie → %s" % (n, DST))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
