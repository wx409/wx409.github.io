# -*- coding: utf-8 -*-
"""watch_tours.py —— 演出/巡演候选监测（只读，人工确认后并入长表）

数据源：公开票务/资讯搜索关键词（大麦/秀动/保利票务/新闻）。
输出 data/pending_events.json（候选清单），**绝不自动入库**——演出信息必须人工确认（纪律：诚实披露）。

注意：网页爬取可能失败或被反爬；失败时输出空清单并注明，不阻塞流水线。
"""
import json
import re
import time
import urllib.parse
import urllib.request

ROOT = r"D:\wx409.github.io"
OUT = ROOT + r"\data\pending_events.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
# 候选关键词（可扩展）
QUERIES = [
    "王晰 巡回音乐会 开票",
    "王晰 演唱会 官宣",
    "王晰 个人巡回 2026",
]


def fetch_text(url):
    try:
        req = urllib.request.Request(url, headers=UA, timeout=15)
        return urllib.request.urlopen(req).read().decode("utf-8", "ignore")
    except Exception:
        return ""


def main():
    candidates = []
    for q in QUERIES:
        # 用搜索引擎 HTML 摘要接口不可靠，这里改为 QQ/票务平台内搜索（可替换为实际票务 API）
        # 示例：秀动/大麦无公开 JSON API，先记录关键词占位，预留对接点
        candidates.append({
            "query": q, "status": "需人工检索",
            "note": "票务平台无公开 API，此条目为提醒：请人工在大麦/秀动/保利票务搜索确认是否有新场次",
        })
        time.sleep(0.5)

    out = {
        "generated_at": "",
        "rule": "只读候选清单；确认后并入巡演歌单长表 xlsx 或 cities.json，再跑 deploy_all",
        "candidates": candidates,
    }
    import datetime
    out["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[OK] 候选清单 -> data/pending_events.json（请人工确认）")


if __name__ == "__main__":
    main()
