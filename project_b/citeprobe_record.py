#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记录一次「AI/搜索可见性」基线（DSH web_search 后端，8 题）。"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
CP = ROOT / "analysis" / "citeprobe"
HIST = CP / "history"
HIST.mkdir(exist_ok=True)

RESULTS = [
    {"q": "王晰 音域 最低音 多少", "hit": False,
     "top": ["微信公众号 65.406HZ里的感官美景", "豆瓣 晰晰音域整理帖", "中国娱乐网 明星档案"]},
    {"q": "王晰 低音 B1 现场", "hit": False,
     "top": ["豆瓣 晰晰音域整理帖（月光开口 B1）", "知乎 男低还是男中", "微信公众号 红尘面对面"]},
    {"q": "王晰 男低音 音域 跨度", "hit": False,
     "top": ["知乎 王晰到底是男低还是男中", "豆瓣 音域整理帖", "中国娱乐网"]},
    {"q": "王晰 数据档案 网站", "hit": False,
     "top": ["中国娱乐网", "百科/档案站", "知乎"]},
    {"q": "王晰 唱功 怎么样 客观分析", "hit": False,
     "top": ["新浪 60 场音乐会", "虎扑 低音下探阈值音", "知乎 妆造与声线"]},
    {"q": "王晰 深夜小酒馆 播客", "hit": False,
     "top": ["微博（节目标签）", "新浪", "知乎"]},
    {"q": "王晰 颤音 技术 特点", "hit": False,
     "top": ["虎扑 低音下探帖", "知乎", "微博"]},
    {"q": "王晰 现场 稳定 音域 实测", "hit": False,
     "top": ["豆瓣 音域整理帖", "虎扑", "B 站"]},
]

now = datetime.now()
rec = {
    "at": now.strftime("%Y-%m-%d %H:%M"),
    "backend": "DSH web_search (DeepSeek 搜索后端)",
    "n_queries": len(RESULTS),
    "hits": sum(1 for r in RESULTS if r["hit"]),
    "results": RESULTS,
}
out = HIST / f"{now.strftime('%Y-%m-%d')}.json"
out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")

latest = CP / "LATEST.md"
prev = latest.read_text(encoding="utf-8") if latest.exists() else ""
head = f"""# AI/搜索可见性 · {now.strftime('%Y-%m-%d %H:%M')}

**本轮：{rec['n_queries']} 题，命中 {rec['hits']}。**

跑法：DSH `web_search`（DeepSeek 搜索后端）逐题检索，看返回来源里有没有 `wx409.github.io`。
本轮处于 **GEO 内容上线后的首轮复测**（106 期金句时间码 + quotes.html + 问答 67 条 + 三向互链刚推送）。

## 结果

| # | 查询 | 命中 | 检索到的主要来源 |
|---|---|---|---|
""" + "\n".join(
    f"| {i+1} | {r['q']} | {'✅' if r['hit'] else '—'} | {' / '.join(r['top'])} |"
    for i, r in enumerate(RESULTS)) + f"""

## 判读（诚实版）

- **命中仍为 0**：内容刚上线，搜索引擎尚未大量抓取新页面（IndexNow 已推，但收录有滞后）。
- 竞争面没变：豆瓣「晰晰音域整理帖」、知乎问答、虎扑低音帖、公众号长文、B 站视频。
- **可预期的第一个突破口**：`王晰 深夜小酒馆 播客`（我们独有 106 期结构化页 + 时间码金句），
  前提是 Bing 收录 `/tavern/ep/*` 与 `/quotes.html`。

## 下一轮（12 月 1 日）看什么

| 指标 | 本轮 | 目标 |
|---|---|---|
| 命中题数 | 0 / 8 | ≥1 |
| 优先破的题 | — | 「王晰 深夜小酒馆 播客」「王晰 现场 稳定 音域 实测」 |

---

"""
latest.write_text(head + prev, encoding="utf-8")
print(f"已写入 {out}")
print(f"命中 {rec['hits']}/{rec['n_queries']}")
