# -*- coding: utf-8 -*-
"""watch_web.py —— 王晰全渠道动态聚合监测（Bing 索引，尽力而为）

说明：
- 微博/小红书/抖音/百度均无公开可稳定抓取的 API，本脚本通过 Bing（已实测可程序化访问）
  的多组关键词检索这些平台的公开索引 + 内容类型，间接实现"全渠道聚合"。
- 逐条正文匹配"王晰"，命中才采集；与上次结果 diff，只报新增。
- 结果汇总成"每日 1 条"经 notify.py（Server酱）推微信，避免刷爆免费版每日 5 条额度。
- 只读脚本：不改数据、不入库，输出 data/pending_web.json 供人工核对。

用法：
  python project_b/watch_web.py              # 只检索 + 写 pending_web.json
  python project_b/watch_web.py --notify     # 检索 + 有新增时汇总推送微信
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pending_web.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"}

# 关键词组：用 site: 定点提高召回（实测 Bing 对"王晰"人名裸搜几乎全被分词拆散，
# 只有带 site: 或强锚点词时才稳定命中）。覆盖：垂直站 + 内容类型。
QUERIES = [
    'site:wx409.github.io 王晰 新歌',
    'site:wx409.github.io 王晰 巡演',
    'site:music.163.com 王晰',
    'site:y.qq.com 王晰',
    'site:baike.baidu.com 王晰 专辑',
    'site:weibo.com 王晰 新歌',
    'site:xiaohongshu.com 王晰',
    '王晰 个人巡回音乐会 2026',
    '王晰 新专辑 发行',
    '王晰 演唱会 官宣 开票',
]
HIT = re.compile(r"王晰")


def bing(q):
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(q)
    try:
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        # Bing 结果：<h2><a href="...">标题</a></h2>，加正文摘要 <p>
        return re.findall(r'<li class="b_algo".*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>', d, re.S)
    except Exception as e:
        return []


def strip(t):
    return re.sub(r"<[^>]+>", "", t or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notify", action="store_true", help="有新增时汇总推送微信")
    args = ap.parse_args()

    # 读旧结果用于 diff
    old = {}
    if OUT.exists():
        try:
            old = {r["url"]: r for r in json.loads(OUT.read_text(encoding="utf-8")).get("results", [])}
        except Exception:
            old = {}

    found = {}
    for q in QUERIES:
        for url, title, snippet in bing(q):
            t = strip(title)
            s = strip(snippet)
            if not HIT.search(t + " " + s):
                continue
            # 去重（同 url 只留第一条）
            if url not in found:
                found[url] = {"title": t[:100], "url": url, "snippet": s[:200], "query": q}
        time.sleep(0.8)

    # 排序：按标题，稳定输出
    results = list(found.values())
    results.sort(key=lambda x: x["title"])

    out = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rule": "Bing 索引聚合（微博/小红书/抖音/百度无公开 API，经 Bing 间接覆盖）。只读候选，需人工确认后入库。",
        "count": len(results),
        "results": results,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    new = [r for r in results if r["url"] not in old]
    print("[OK] 全渠道聚合 %d 条，其中本次新增 %d 条 -> data/pending_web.json" % (len(results), len(new)))
    for r in new[:15]:
        print("  +", r["title"][:50], "|", r["query"])

    if args.notify and new:
        try:
            sys.path.insert(0, str(ROOT / "project_b"))
            import notify
            lines = "\n".join("- %s\n  %s" % (r["title"], r["url"]) for r in new[:10])
            notify.send(
                "📣 王晰动态聚合 %d 条新增（需你确认）" % len(new),
                "全渠道(Bing索引)本日新增：\n" + lines
                + ("\n…等共 %d 条" % len(new) if len(new) > 10 else "")
                + "\n\n详情见 data/pending_web.json；确认后入库。",
            )
        except Exception as e:
            print("[notify] 失败:", e)


if __name__ == "__main__":
    main()
