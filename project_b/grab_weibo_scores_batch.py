#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量抓取「柯烬」扒谱合集（微博）里的谱面图片，存本地（不上网）。

流程：
  1) 取合集长微博（mid 5079953865179303）→ 解析「曲名 + 网页链接」对；
  2) 逐条走本地 weibo_proxy（自带签名与 wb.txt cookie）取详情；
  3) 下载图片到 E:\\wx\\论文素材_王晰作传\\曲谱_网友扒谱\\<曲名>\\；
  4) 写索引 index.json（曲名/微博URL/图片文件名/抓取时间）。

用法：python -X utf8 project_b\\grab_weibo_scores_batch.py [--limit 3] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"E:\wx\私有工具\weibo_proxy")
import weibo_proxy as wp  # noqa: E402

MID = "5079953865179303"
OUTROOT = Path(r"E:\wx\论文素材_王晰作传\曲谱_网友扒谱")
INDEX = OUTROOT / "index.json"


def parse_pairs(html: str):
    """从长微博 HTML 里抽出 (曲名, 微博链接)。曲名取链接前最近的《…》或中文短语。"""
    pairs = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html):
        url, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        if "weibo.com/7087121910/" not in url:
            continue
        before = re.sub(r"<[^>]+>", "", html[: m.start()])
        cand = re.findall(r"《([^》]{1,20})》", before[-120:])
        name = cand[-1] if cand else re.sub(r"\s+", "", label)[:16]
        if not name:
            name = before.strip()[-12:]
        pairs.append((name.strip(), url.strip()))
    # 去重（同一链接只留第一次）
    seen, out = set(), []
    for n, u in pairs:
        key = u.split("?")[0].rstrip("/").split("/")[-1]
        if key in seen:
            continue
        seen.add(key)
        out.append((n, u))
    return out


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name)[:40] or "未命名"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    coll = wp._fetch_detail(MID)
    if not coll:
        print("合集获取失败")
        return 2
    pairs = parse_pairs(coll.get("text") or "")
    print(f"解析到 {len(pairs)} 条谱子链接")
    if a.dry_run:
        for n, u in pairs[:15]:
            print("  ", n, "→", u)
        return 0
    if a.limit:
        pairs = pairs[: a.limit]

    OUTROOT.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"items": []}
    done = {(i["url"]) for i in index["items"]}

    ok = 0
    for name, url in pairs:
        if url in done:
            continue
        key = url.rstrip("/").split("/")[-1]
        try:
            m = wp._fetch_detail(key)
        except Exception as e:
            print("  [fail]", name, str(e)[:60])
            continue
        if not m:
            print("  [fail]", name, "无详情")
            continue
        pics = wp._extract_pics(m) if hasattr(wp, "_extract_pics") else []
        d = OUTROOT / safe(name)
        d.mkdir(parents=True, exist_ok=True)
        files = []
        for i, u in enumerate(pics, 1):
            dest = d / ("%02d.jpg" % i)
            try:
                wp._download(u, dest)
                files.append(dest.name)
            except Exception as e:
                print("    [img fail]", i, str(e)[:50])
        index["items"].append({
            "song": name, "url": url, "mid": key,
            "dir": str(d.relative_to(OUTROOT)),
            "files": files, "n": len(files),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        ok += 1
        print(f"  [{ok}] {name}: {len(files)} 张")

    index["source"] = "微博 @7087121910（授权转载，仅本地留存，不上网）"
    index["collection"] = f"https://weibo.com/7087121910/{MID}"
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"完成 {ok} 条｜索引 → {INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
