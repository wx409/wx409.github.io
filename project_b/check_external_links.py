# -*- coding: utf-8 -*-
"""
王晰数字档案站 · 外链死链检测（微博"半年可见"专项）
========================================================
用途：定期检测 live_repos.json 中的外链是否存活，重点排查微博"半年可见"导致的失效。

为什么需要：
    王晰微博开了"半年可见"，已有的微博链接在半年后会变成死链/仅自己可见。
    需要定期检测，把失效链接标记出来，供替换为百家号或快照。

用法：
    python project_b/check_external_links.py            # 检测全部外链
    python project_b/check_external_links.py --weibo    # 只检测微博链接（快速）

输出：
    temp/dead_links_report.json    # 完整检测结果
    temp/dead_links_report.txt     # 可读报告

注意：本脚本只做检测，不修改任何数据文件；结果供人工决策。
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
LIVE_REPOS = ROOT / "data" / "live_repos.json"
REPORT_JSON = ROOT / "temp" / "dead_links_report.json"
REPORT_TXT = ROOT / "temp" / "dead_links_report.txt"

# 微博死链的判定特征（半年可见/登录墙/已删除）
WEIBO_DEAD_MARKS = ["登录", "passport.weibo.com", "仅自己可见", "此微博已被删除",
                    "抱歉，此微博", "仅展示最近", "内容已删除", "已被作者删除"]


def collect_links(weibo_only=False):
    repos = json.loads(LIVE_REPOS.read_text(encoding="utf-8")).get("repos", {})
    out = []
    seen = set()
    for date, items in repos.items():
        for it in items:
            url = (it.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            if weibo_only and "weibo.com" not in url and "m.weibo.cn" not in url:
                continue
            out.append((date, it.get("platform", ""), url, it.get("title", "")[:50]))
    return out


def check_one(entry):
    date, platform, url, title = entry
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, method="HEAD", headers=ua)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return (url, "ok", date, platform, title)
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):
            try:
                req2 = urllib.request.Request(url, method="GET", headers=ua)
                with urllib.request.urlopen(req2, timeout=15) as resp:
                    body = resp.read(4096).decode("utf-8", errors="ignore")
                    if any(m in body for m in WEIBO_DEAD_MARKS):
                        return (url, "失效(登录墙/删除)", date, platform, title)
                    return (url, "ok", date, platform, title)
            except Exception:
                return (url, f"HTTP {e.code}", date, platform, title)
        return (url, f"HTTP {e.code}", date, platform, title)
    except Exception as e:
        return (url, f"网络错误({str(e)[:50]})", date, platform, title)


def main():
    ap = argparse.ArgumentParser(description="外链死链检测")
    ap.add_argument("--weibo", action="store_true", help="只检测微博链接")
    a = ap.parse_args()

    links = collect_links(weibo_only=a.weibo)
    print(f"待检测外链: {len(links)} 条" + ("（仅微博）" if a.weibo else ""))

    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(check_one, l) for l in links]
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if i % 20 == 0:
                print(f"  进度 {i}/{len(links)}")

    dead = [r for r in results if r[1] != "ok"]
    report = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(results), "dead": len(dead), "weibo_only": a.weibo,
        "dead_links": [{"url": r[0], "status": r[1], "date": r[2], "platform": r[3], "title": r[4]} for r in dead],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [f"外链死链检测报告（{report['checked_at']}）",
             f"总 {report['total']} · 存活 {report['total']-report['dead']} · 失效 {report['dead']}", "=" * 60]
    for r in dead:
        lines.append(f"[失效][{r[2]}] {r[3]} | {r[4][:30]}")
        lines.append(f"  {r[0]}")
        lines.append(f"  状态: {r[1]}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n检测完成: 存活 {report['total']-report['dead']} / 失效 {report['dead']}")
    print(f"报告: {REPORT_JSON}")
    if dead:
        print("\n疑似失效:")
        for r in dead[:25]:
            print(f"  [{r[2]}] {r[1]}: {r[0][:70]}")


if __name__ == "__main__":
    main()
