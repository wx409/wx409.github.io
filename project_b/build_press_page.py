# -*- coding: utf-8 -*-
"""press.html —— 媒体报道（**引用，非转载**）

原则：只存「引文 + 链接 + 快照日期」，全文不入库、不入 git。
没有拿到原文时，引文留空并标 `verified: false`，页面写“引文待补（需原文核对）”，绝不编造。
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
OUT = SITE / "data" / "press.json"
PAGE = SITE / "press.html"

ITEMS = [{
    "id": "xinhua-chenxiang-20261014",
    "media": "新华网",
    "title": "《沉响与长歌》：两个低音，一场对话（题名待以原文为准）",
    "date": "2026-10-14",
    "reporter": "韩轩",
    "url": "",
    "snapshot_date": date.today().isoformat(),
    "quotes": [],
    "related_shows": ["2026-10-09", "2026-10-10"],
    "related_conclusion": "不追求高低音反差（媒体说法）",
    "verified": False,
    "note": "未取得原文正文，引文待补；不得臆造。全文不入库，只保留链接与引文。",
}]


def main() -> int:
    doc = {
        "generated_at": date.today().isoformat(),
        "caliber": "第三方报道摘录，仅作引用；观点属原媒体与受访者；引文逐字，不改写、不拼接",
        "items": ITEMS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    H = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
         "<title>媒体报道（引用）｜王晰数字档案</title>",
         "<link rel=\"canonical\" href=\"https://wx409.github.io/press.html\">",
         "<script type=\"application/ld+json\">" + json.dumps(
             {"@context": "https://schema.org", "@type": "CollectionPage",
              "name": "媒体报道（引用）",
              "description": "第三方媒体报道摘录，仅作引用",
              "citation": [{"@type": "NewsArticle", "headline": it["title"],
                            "datePublished": it["date"],
                            "author": {"@type": "Person", "name": it["reporter"]},
                            "publisher": {"@type": "Organization", "name": it["media"]}}
                           for it in ITEMS]}, ensure_ascii=False) + "</script>",
         "<style>body{font:15px/1.8 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:820px;"
         "margin:24px auto;padding:0 16px}blockquote{border-left:3px solid #a8323d;margin:12px 0;"
         "padding:6px 14px;color:#333;background:#fafafa}.meta{color:#666;font-size:.9em}</style>",
         "</head><body>", "<!-- NAV_START --><!-- NAV_END -->",
         "<h1>媒体报道</h1>",
         "<p class=\"meta\">以下为第三方报道摘录，<b>仅作引用</b>；观点属原媒体与受访者。"
         "我们只保存引文、链接与快照日期，不转载全文。</p>"]
    for it in ITEMS:
        H.append(f"<section><h2>{html.escape(it['media'])}｜{html.escape(it['title'])}</h2>")
        H.append(f"<p class=\"meta\">{it['date']}｜记者：{html.escape(it['reporter'])}｜"
                 f"快照：{it['snapshot_date']}｜状态：{'已核' if it['verified'] else '引文待补（需原文核对）'}</p>")
        if it["quotes"]:
            for q in it["quotes"]:
                H.append(f"<blockquote>「{html.escape(q)}」</blockquote>")
        else:
            H.append("<blockquote>引文待补：尚未取得原文正文，暂不引用任何句子。</blockquote>")
        if it["url"]:
            H.append(f"<p>原文：<a href=\"{html.escape(it['url'])}\" rel=\"noopener\" target=\"_blank\">"
                     f"{html.escape(it['url'])}</a></p>")
        else:
            H.append("<p class=\"meta\">原文链接待补（需可公开访问的新华网地址）。</p>")
        H.append(f"<p class=\"meta\">关联场次：{ '、'.join(it['related_shows']) }｜"
                 f"媒体结论（媒体说法）：{html.escape(it['related_conclusion'])}</p><hr></section>")
    H.append("<p class=\"meta\">引用，非全文转载。如需全文请前往原媒体页面阅读。</p></body></html>")
    PAGE.write_text("\n".join(H), encoding="utf-8")
    print("[ok] press.json / press.html｜条目", len(ITEMS), "｜引文", sum(len(i["quotes"]) for i in ITEMS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
