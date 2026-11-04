#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IndexNow 批量提交（Bing / Yandex / Seznam / Naver）。

与 deploy_all.py 里逐条 GET 的老实现相比，本脚本走官方推荐的 **POST 批量接口**：
    POST https://api.indexnow.org/indexnow
    {"host": "...", "key": "...", "keyLocation": "https://.../<key>.txt", "urlList": [...]}
协议单次最多 10,000 条 URL，本机 sitemap 约 250 条 → 一次请求搞定。

用法（工作目录 = D:\\wx409.github.io）：
    python -X utf8 project_b\\indexnow_submit.py --dry-run   # 只看会提交哪些
    python -X utf8 project_b\\indexnow_submit.py             # 真提交
    python -X utf8 project_b\\indexnow_submit.py --only tavern/ep
    python -X utf8 project_b\\indexnow_submit.py --file urls.txt

退出码：0 = 全部 URL 被接收；1 = 有 URL 未提交（网络/HTTP 异常）。
注意：IndexNow **只覆盖 Bing/Yandex/Seznam/Naver，不覆盖 Google**。
Google 没有公开的 sitemap 提交接口（2023 年已下线 ping 端点），只能走 Search Console。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SITEMAP = ROOT / "sitemap.xml"
KEY_FILE = ROOT / "e3f1a2b4c5d6e7f8a9b0c1d2e3f4a5b6.txt"
HOST = "wx409.github.io"
SITE = f"https://{HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_PER_REQUEST = 10000  # 协议上限


def sitemap_urls() -> list[str]:
    xml = SITEMAP.read_text(encoding="utf-8")
    urls = [u.strip() for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)]
    return sorted(dict.fromkeys(urls))


def post_batch(urls: list[str], key: str, key_location: str, retries: int = 3) -> tuple[bool, str]:
    body = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls,
    }).encode("utf-8")
    last = ""
    for attempt in range(retries):
        req = urllib.request.Request(
            ENDPOINT, data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                code = resp.status
                if code in (200, 202):
                    return True, f"HTTP {code}"
                last = f"HTTP {code}"
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            last = f"HTTP {e.code} {detail}"
            if e.code in (400, 403, 422):  # 参数/密钥问题，重试无意义
                return False, last
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 + attempt * 3 + random.random() * 2)
    return False, last


def main() -> int:
    ap = argparse.ArgumentParser(description="IndexNow 批量提交（读 sitemap 单一事实源）")
    ap.add_argument("--dry-run", action="store_true", help="只打印目标，不提交")
    ap.add_argument("--only", default="", help="只提交 URL 含该子串的条目，如 tavern/ep")
    ap.add_argument("--file", default="", help="改用指定 URL 清单（每行一个）")
    args = ap.parse_args()

    urls = ([ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if args.file else sitemap_urls())
    if args.only:
        urls = [u for u in urls if args.only in u]
    if not urls:
        print("没有可提交的 URL")
        return 1

    if not KEY_FILE.exists():
        print(f"[IndexNow] key 文件缺失：{KEY_FILE.name}")
        return 1
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    key_location = f"{SITE}/{KEY_FILE.name}"

    print(f"[IndexNow] 目标 {len(urls)} 条（来源：{'sitemap.xml' if not args.file else args.file}"
          f"{'，过滤 ' + args.only if args.only else ''}）")
    if args.dry_run:
        for u in urls[:10]:
            print("   ", u)
        if len(urls) > 10:
            print(f"    … 其余 {len(urls) - 10} 条")
        print("[IndexNow] dry-run，未提交")
        return 0

    failed: list[str] = []
    for i in range(0, len(urls), MAX_PER_REQUEST):
        chunk = urls[i:i + MAX_PER_REQUEST]
        ok, msg = post_batch(chunk, key, key_location)
        print(f"[IndexNow] 批次 {i // MAX_PER_REQUEST + 1}：{len(chunk)} 条 -> {'已接收' if ok else '失败'}（{msg}）")
        if not ok:
            failed.extend(chunk)

    print(f"[IndexNow] 完成：成功 {len(urls) - len(failed)}/{len(urls)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
