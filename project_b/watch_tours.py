# -*- coding: utf-8 -*-
"""watch_tours.py —— 演出/巡演候选监测（尽力而为 + 人工确认）

数据源：Bing 网页搜索（精确词查询，多次尝试）。
输出 data/pending_events.json 候选清单。
**绝不自动入库**：票务无公开 API、搜索易反爬/分词干扰，演出信息必须人工确认
（纪律：不伪造；确认后一条命令入库：python project_b/confirm_event.py ...）
"""
import json
import re
import time
import urllib.parse
import urllib.request

ROOT = r"D:\wx409.github.io"
OUT = ROOT + r"\data\pending_events.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"}

QUERIES = [
    '"王晰" 演唱会 官宣 开票',
    '"王晰" 巡回音乐会 新场次',
    '"王晰" 个人巡回 2026 售票',
]
HIT = re.compile(r"王晰")
KEEP = re.compile(r"演唱会|音乐会|巡演|巡回|开票|官宣|演出|剧场|剧院|票务", re.I)


def bing(q):
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(q)
    try:
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore")
        return re.findall(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', d, re.S)
    except Exception:
        return []


def main():
    candidates = []
    seen = set()
    for q in QUERIES:
        for url, title in bing(q):
            t = re.sub(r"<[^>]+>", "", title).strip()
            if not HIT.search(t) or not KEEP.search(t):
                continue
            if t in seen:
                continue
            seen.add(t)
            candidates.append({"title": t[:80], "url": url, "query": q,
                               "confirm_hint": "确认后执行: python project_b/confirm_event.py --date YYYY-MM-DD --city XX --venue XX --tour X巡"})
        time.sleep(1.0)

    out = {
        "generated_at": "",
        "rule": "只读候选清单（Bing 网页检索，尽力而为）。票务无公开 API，演出信息必须人工确认后经 confirm_event.py 入库。",
        "candidates": candidates,
    }
    import datetime
    out["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[OK] 候选 %d 条 -> data/pending_events.json（请人工确认）" % len(candidates))
    for c in candidates[:10]:
        print("  -", c["title"])

    # 有候选 → 明显通知（微信/邮件），提醒人工确认
    if candidates:
        try:
            sys.path.insert(0, ROOT + r"\project_b")
            import notify
            lines = "\n".join("- %s\n  %s" % (c["title"], c["url"]) for c in candidates[:8])
            notify.send("🎤 发现巡演候选 %d 条，需你确认" % len(candidates),
                        "候选清单（data/pending_events.json）：\n" + lines
                        + "\n\n确认后入库命令示例：\n"
                        + "python project_b/confirm_event.py --date YYYY-MM-DD --city XX --venue XX --tour X巡")
        except Exception as e:
            print("[notify] 失败:", e)


if __name__ == "__main__":
    main()
