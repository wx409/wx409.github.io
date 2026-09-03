# -*- coding: utf-8 -*-
"""同步微博 Cookie：从 E:\\wx\\index_records\\wb.txt 分发到 3 个抓取工具使用的文件。

源：
  E:\\wx\\index_records\\wb.txt           # 你手工粘贴的最新 Cookie 原文

目标：
  1. E:\\wx\\私有工具\\weibo_cookies.txt           # collect_show_feedback / pipeline_weibo_update 读取
  2. E:\\wx\\私有工具\\weibo_proxy\\weibo_cookie.json   # weibo_proxy.py / weibo_proxy_studio.py 读取
  3. E:\\wx\\私有工具\\realtime_cookies\\weibo_cookie.json  # 本地实时备份

用法：
  python -X utf8 tools\\sync_weibo_cookie.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(r"E:\wx\index_records\wb.txt")
RAW_DST = Path(r"E:\wx\私有工具\weibo_cookies.txt")
PROXY_DST = Path(r"E:\wx\私有工具\weibo_proxy\weibo_cookie.json")
REALTIME_DST = Path(r"E:\wx\私有工具\realtime_cookies\weibo_cookie.json")


def clean_cookie(raw: str) -> str:
    """去掉首尾空白、可能的 'Cookie:' 前缀，确保只保留 Cookie 内容本身。"""
    c = raw.strip()
    if c.lower().startswith("cookie:"):
        c = c[len("cookie:"):].strip()
    return c


def main() -> int:
    if not SRC.exists():
        print(f"[X] 找不到源文件: {SRC}")
        return 1

    raw = SRC.read_text(encoding="utf-8", errors="ignore")
    cookie = clean_cookie(raw)

    if not cookie:
        print("[X] wb.txt 内容为空")
        return 1

    # 简单校验：应包含常见微博 Cookie 字段
    if "=" not in cookie:
        print("[X] wb.txt 内容不像 Cookie，请检查是否复制完整")
        return 1

    RAW_DST.parent.mkdir(parents=True, exist_ok=True)
    PROXY_DST.parent.mkdir(parents=True, exist_ok=True)
    REALTIME_DST.parent.mkdir(parents=True, exist_ok=True)

    # 1) 纯文本 Cookie：供 collect_show_feedback / pipeline_weibo_update
    RAW_DST.write_text(cookie, encoding="utf-8")
    print(f"[OK] {RAW_DST}")

    # 2) 自动拼 JSON：供 weibo_proxy.py / weibo_proxy_studio.py
    payload = {"cookie": cookie}
    json_text = json.dumps(payload, ensure_ascii=False)

    PROXY_DST.write_text(json_text, encoding="utf-8")
    print(f"[OK] {PROXY_DST}")

    # 3) realtime_cookies 备份
    REALTIME_DST.write_text(json_text, encoding="utf-8")
    print(f"[OK] {REALTIME_DST}")

    print("\n完成：已把 wb.txt 的 Cookie 同步到 3 个抓取工具文件。")
    print("提示：若仍报 HTTP 432，请先换 IP/冷却，再重新抓取 Cookie 覆盖 wb.txt 后重跑本脚本。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
