#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bing Webmaster Tools API 探测：收录/流量/查询词/抓取。

用法：python -X utf8 project_b/bing_wmt.py [--json out.json]
Key 从 D:\\DSH\\.dsh\\secrets\\bing_api_key.txt 读取（第一行 key，第二行站点 URL）。
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

KEY_FILE = Path(r"D:\DSH\.dsh\secrets\bing_api_key.txt")
BASE = "https://ssl.bing.com/webmaster/api.svc/json/"


def load():
    lines = [l.strip() for l in KEY_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    key = lines[0]
    site = lines[1] if len(lines) > 1 else "https://wx409.github.io/"
    return key, site


def call(method, key, **params):
    q = {"apikey": key}
    q.update(params)
    url = BASE + method + "?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read().decode("utf-8", "ignore")
        return json.loads(raw)
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:120]}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="结果另存 JSON")
    a = ap.parse_args()
    key, site = load()
    out = {}

    user = call("GetUser", key)
    out["user"] = {"ok": "_error" not in user, "name": (user.get("d") or {}).get("UserName") if "_error" not in user else user["_error"]}

    sites = call("GetSites", key)
    d = sites.get("d") or [] if "_error" not in sites else []
    out["sites"] = [s.get("Url") for s in d] if d else sites.get("_error")

    traffic = call("GetRankAndTrafficStats", key, siteUrl=site)
    td = traffic.get("d") or [] if "_error" not in traffic else []
    out["traffic_days"] = len(td)
    if td:
        last = sorted(td, key=lambda x: x.get("Date", ""))[-1]
        out["traffic_last"] = last
        out["clicks_sum"] = sum(int(x.get("Clicks") or 0) for x in td)
        out["impressions_sum"] = sum(int(x.get("Impressions") or 0) for x in td)
    else:
        out["traffic_error"] = traffic.get("_error")

    qs = call("GetQueryStats", key, siteUrl=site)
    qd = qs.get("d") or [] if "_error" not in qs else []
    out["queries"] = len(qd)
    if qd:
        top = sorted(qd, key=lambda x: -(int(x.get("Impressions") or 0)))[:10]
        out["top_queries"] = [{"q": t.get("Query"), "imp": t.get("Impressions"), "clicks": t.get("Clicks")} for t in top]
    else:
        out["queries_error"] = qs.get("_error")

    crawl = call("GetCrawlStats", key, siteUrl=site)
    cd = crawl.get("d") or [] if "_error" not in crawl else []
    out["crawl_days"] = len(cd)
    if cd:
        last = sorted(cd, key=lambda x: x.get("Date", ""))[-1]
        out["crawl_last"] = last
    else:
        out["crawl_error"] = crawl.get("_error")

    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("已写出:", a.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
