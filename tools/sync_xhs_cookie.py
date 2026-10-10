# -*- coding: utf-8 -*-
"""同步小红书 Cookie：从 E:\\wx\\index_records\\xhs.txt 分发到抓取工具实际读取的位置。

惯例与 `tools/sync_weibo_cookie.py` 一致：源是人工粘贴的 Cookie 原文（可能带 `Cookie:` 前缀）。

源：
  E:\\wx\\index_records\\xhs.txt                    # 你手工粘贴的最新 Cookie 原文

目标（按各工具**实际读取路径**逐一核对后确定，2026-10-10）：
  1. E:\\wx\\私有工具\\xhs_proxy\\xhs_cookie.json           # xhs_crawler.py 直接读（{"cookie":..,"saved_at":..}）
  2. E:\\wx\\私有工具\\realtime_cookies\\xiaohongshu_cookie.json  # 本地实时备份（{"cookie":..}）

说明：`fetch_xhs_links.py` / `fetch_xhs_user.py` **本身已优先读 xhs.txt**（fxl.load_cookie），
所以不需要额外分发；本脚本只补齐 xhs_crawler.py 这一处，并留一份实时备份。

用法：
  python -X utf8 tools\\sync_xhs_cookie.py
  python -X utf8 tools\\sync_xhs_cookie.py --check    # 只做连通性自检（1 个请求），不改文件
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = Path(r"E:\wx\index_records\xhs.txt")
CRAWLER_DST = Path(r"E:\wx\私有工具\xhs_proxy\xhs_cookie.json")
REALTIME_DST = Path(r"E:\wx\私有工具\realtime_cookies\xiaohongshu_cookie.json")
# 小红书 Cookie 常见字段（用于粗校验，避免把微博 Cookie 误贴进来）
XHS_KEYS = ("a1=", "web_session", "webId", "gid=")


def clean_cookie(raw: str) -> str:
    c = raw.strip()
    if c.lower().startswith("cookie:"):
        c = c[len("cookie:"):].strip()
    return c


def load_cookie() -> str:
    if SRC.exists():
        return clean_cookie(SRC.read_text(encoding="utf-8", errors="ignore"))
    try:
        return json.loads(CRAWLER_DST.read_text(encoding="utf-8")).get("cookie", "")
    except Exception:
        return ""


def probe(cookie: str) -> str:
    """连通性自检：1 个搜索请求，三态判定 有效 / 失效 / 被风控。"""
    sys.path.insert(0, r"E:\wx\私有工具\xhs_proxy")
    sys.path.insert(0, r"E:\wx\私有工具\Spider_XHS-master")   # 与 xhs_crawler.py 相同的依赖根
    try:
        from xhs_utils.xhs_pc import XHSPcAuth          # noqa
        from apis.xhs_pc_apis import XHS_Apis           # noqa
    except Exception as e:
        return f"无法加载小红书工具链：{e!r}"
    try:
        auth = XHSPcAuth.from_cookie(cookie)
        api = XHS_Apis(auth).bootstrap()          # 与 xhs_crawler.py 相同的调用方式
        results = []
        for kw in ("沉响与长歌", "王晰"):
            try:
                ok, msg, res = api.search_note(kw, page=1, sort_type_choice=2)
            except Exception as e:
                ok, msg, res = False, repr(e), None
            n = 0
            if isinstance(res, dict):
                # 实测结构：res["data"]["items"]（与 xhs_crawler.py 一致）
                n = len((res.get("data") or {}).get("items") or [])
            elif isinstance(res, list):
                n = len(res)
            results.append((kw, ok, str(msg)[:80], n))
            print(f"  自检[{kw}]：ok={ok} n={n} msg={str(msg)[:120]}")
            time.sleep(1)
        if any(ok and n > 0 for _, ok, _, n in results):
            return "有效"
        if all(ok and "成功" in m for _, ok, m, _ in results):
            # API 全部成功应答但都没结果：Cookie 有效，只是词没命中
            return "有效（两词均无结果，属正常）"
        joined = " ".join(m for _, _, m, _ in results)
        if any(k in joined for k in ("登录", "expired", "未登录", "-100")):
            return "失效"
        if any(k in joined for k in ("风控", "频繁", "461", "471", "300012", "300013")):
            return "被风控"
        return "失效或未知"
    except Exception as e:
        s = repr(e)
        if any(k in s for k in ("461", "471", "风控", "300012")):
            return "被风控"
        return f"失效（异常：{s[:120]}）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只做连通性自检，不写文件")
    a = ap.parse_args()

    if not SRC.exists():
        print(f"[X] 找不到源文件: {SRC}")
        return 1
    cookie = clean_cookie(SRC.read_text(encoding="utf-8", errors="ignore"))
    if not cookie or "=" not in cookie:
        print("[X] xhs.txt 为空或不像 Cookie")
        return 1
    if not any(k in cookie for k in XHS_KEYS):
        print(f"[!] 警告：xhs.txt 未包含常见小红书字段 {XHS_KEYS}，请确认没有误贴微博 Cookie")

    print(f"源：{SRC}（{len(cookie)} 字符）")
    if a.check:
        state = probe(cookie)
        print(f"[自检] 三态判定：{state}")
        return 0 if state == "有效" else 2

    state = probe(cookie)
    print(f"[自检] 三态判定：{state}")
    if state != "有效":
        print("[X] Cookie 非「有效」，**不覆盖现有 cookie 文件**（避免把还能用的旧值弄坏）。"
              "如确认要强制写入，请手动备份后操作。")
        return 2

    CRAWLER_DST.parent.mkdir(parents=True, exist_ok=True)
    REALTIME_DST.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    CRAWLER_DST.write_text(json.dumps({"cookie": cookie, "saved_at": now},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {CRAWLER_DST}（xhs_crawler.py 读取）")
    REALTIME_DST.write_text(json.dumps({"cookie": cookie, "saved_at": now},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {REALTIME_DST}（本地实时备份）")
    print("提示：fetch_xhs_links.py / fetch_xhs_user.py 已自带优先读 xhs.txt，无需分发。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
