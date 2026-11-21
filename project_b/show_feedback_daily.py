#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""show_feedback_daily.py —— 演出次日自动链路（B站补收 + 专场页 + 反馈入库 + live-reviews 索引）

触发标志：data/activity_master.json 里出现「日期 + 城市 + 标题」的演出行。
用法：
  python -X utf8 project_b\\show_feedback_daily.py --dry
  python -X utf8 project_b\\show_feedback_daily.py            # 处理昨天
  python -X utf8 project_b\\show_feedback_daily.py --date 2026-11-20
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
ACT = ROOT / "data" / "activity_master.json"
LIVE = ROOT / "live"
REVIEWS = ROOT / "live-reviews.html"
START, END = "<!-- AUTO-SHOWS:START -->", "<!-- AUTO-SHOWS:END -->"


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def slug(s):
    return re.sub(r"[^\w\u4e00-\u9fa5\-]+", "-", s).strip("-")[:40]


def shows_on(d):
    rows = json.loads(ACT.read_text(encoding="utf-8")).get("rows") or []
    return [x for x in rows if str(x.get("date")) == d and x.get("city")]


def page_for(show):
    title = show.get("title") or ""
    toks = [show["city"], show["date"][:4]] + re.findall(r"[\u4e00-\u9fa5]{4}", title)[:1]
    for p in LIVE.glob("*.html"):
        if all(t in p.name for t in toks if t):
            return p
    return LIVE / ("%s-%s-%s.html" % (show["date"], show["city"], slug(title or "演出")))


def ensure_page(show):
    p = page_for(show)
    if p.exists():
        return p
    LIVE.mkdir(exist_ok=True)
    title = show.get("title") or "演出"
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · %s站（%s）· 观众反馈｜王晰档案</title>
<meta name="description" content="%s（%s，%s）观众反馈自动汇总：微博、小红书、B站等平台短评，匿名展示、可回溯原帖。">
<meta name="robots" content="index, follow">
<style>body{margin:0;background:#faf9f7;color:#1f2328;font:16px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:960px;margin:0 auto;padding:28px 20px 60px}h1{font-size:28px;margin:8px 0 4px}.sub{color:#666;margin:0 0 18px}
.notice{background:#fff8e6;border:1px solid #f0d9a8;border-radius:10px;padding:12px 16px;font-size:14px;color:#6b5320}</style>
</head><body><main>
<h1>%s · %s站</h1>
<p class="sub">%s｜%s｜%s</p>
<div class="notice">演出进行中/待更新：观众反馈将在演出后自动汇总（微博 / 小红书 / B站 / 网页），短句匿名展示、保留原帖链接。</div>
<p class="sub">最后更新：%s</p>
</main></body></html>
""" % (title, show["city"], show["date"], title, show["city"], show["date"],
       title, show["city"], title, show["date"], show["city"], date.today().isoformat())
    p.write_text(html, encoding="utf-8")
    log("新建专场页 %s" % p.name)
    return p


def update_reviews():
    rows = json.loads(ACT.read_text(encoding="utf-8")).get("rows") or []
    today = date.today()
    picked = []
    for x in rows:
        try:
            d = datetime.strptime(str(x.get("date")), "%Y-%m-%d").date()
        except Exception:
            continue
        if not x.get("city") or d < today - timedelta(days=7) or d > today + timedelta(days=7):
            continue
        picked.append((d, x))
    picked.sort(key=lambda t: t[0], reverse=True)
    items = []
    for d, x in picked[:10]:
        p = page_for(x)
        label = "%s · %s站" % (x.get("title") or "演出", x.get("city"))
        if p.exists():
            items.append('<li>%s（%s）— <a href="/live/%s">观众反馈与现场实录 →</a></li>' % (label, d, p.name))
        else:
            items.append("<li>%s（%s）</li>" % (label, d))
    block = START + "\n<section id=\"auto-shows\" style=\"margin:24px 0;padding:14px 18px;background:#fff;border:1px solid #e6e2dc;border-radius:10px;\">\n<h2 style=\"margin:0 0 6px;font-size:20px;\">近期演出与观众反馈（自动索引）</h2>\n<ul>" + "".join(items) + "</ul>\n</section>\n" + END
    s = REVIEWS.read_text(encoding="utf-8")
    if START in s and END in s:
        s = re.sub(re.escape(START) + r".*?" + re.escape(END), block, s, flags=re.S)
    else:
        i = s.find("</main>")
        if i < 0:
            i = s.find("</body>")
        s = s[:i] + block + s[i:]
    REVIEWS.write_text(s, encoding="utf-8")
    log("live-reviews 自动索引已更新（%d 条）" % len(items))


def run(args):
    r = subprocess.run([sys.executable, "-X", "utf8"] + args, cwd=str(ROOT))
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--days", type=int, default=3, help="回看天数（B站上传有延迟，默认近 3 天都重试）")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--skip-bili", action="store_true")
    a = ap.parse_args()
    base = date.fromisoformat(a.date) if a.date else (date.today() - timedelta(days=1))
    dates = [(base - timedelta(days=i)).isoformat() for i in range(max(1, a.days))]
    any_show = False
    for target in dates:
        shows = shows_on(target)
        if not shows:
            continue
        any_show = True
        for show in shows:
            p = ensure_page(show)
            title = show.get("title") or ""
            log("%s %s → %s" % (target, show["city"], p.name))
            if a.dry:
                continue
            if not a.skip_bili:
                run([r"project_b\collect_show_feedback.py", "--date", target, "--city", show["city"],
                     "--title", title, "--bili-only", "--bili-pages", "3", "--bili-order", "pubdate"])
            run([r"project_b\feedback_week.py", "--date", target, "--city", show["city"], "--no-collect"])
    if not any_show:
        log("近 %d 天无演出，跳过" % a.days)
    if not a.dry:
        update_reviews()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
