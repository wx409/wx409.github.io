"""无头浏览器抓取（解决 JS 渲染 / 反爬）：公众号、头条、知乎等

用法：
  python -X utf8 project_b/fetch_headless.py --url "<URL>"
  python -X utf8 project_b/fetch_headless.py --from-file data/js_pages.txt
输出：E:\\wx\\私有\\王晰全文库\\采访目录\\网页\\<slug>.txt（同 fetch_web_interviews 的格式）
"""
import argparse
import os
import re
import time

from playwright.sync_api import sync_playwright

OUT = r"E:\wx\私有\王晰全文库\采访目录\网页"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 正文容器候选（按优先级）
SELECTORS = [
    "#js_content",            # 微信公众号
    "article",
    "div.article-content",
    "div.article",
    "div#article",
    "div.content",
    "div.rich_media_content",
    "div.post-content",
    "div.main-content",
    "div.text",
    "body",
]


def slug(u):
    return re.sub(r"[^0-9A-Za-z]+", "_", u.split("//", 1)[-1])[:70]


def grab(url):
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, locale="zh-CN",
                            viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        pg.set_default_timeout(30000)
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            pass
        pg.wait_for_timeout(3500)
        # 公众号需滚动触发加载
        try:
            pg.mouse.wheel(0, 2000)
            pg.wait_for_timeout(1200)
        except Exception:
            pass
        title = pg.title() or ""
        best = ""
        for sel in SELECTORS:
            try:
                els = pg.query_selector_all(sel)
            except Exception:
                continue
            for el in els[:3]:
                try:
                    txt = el.inner_text()
                except Exception:
                    continue
                if len(txt) > len(best):
                    best = txt
            if len(best) > 800:
                break
        b.close()
    best = re.sub(r"\n{3,}", "\n\n", best).strip()
    return title.strip(), best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--from-file")
    ap.add_argument("--min-chars", type=int, default=600)
    a = ap.parse_args()

    urls = [a.url] if a.url else []
    if a.from_file:
        urls += [l.strip() for l in open(a.from_file, encoding="utf-8") if l.strip() and not l.startswith("#")]

    os.makedirs(OUT, exist_ok=True)
    ok = fail = 0
    for u in urls:
        p = os.path.join(OUT, slug(u) + ".txt")
        if os.path.exists(p) and os.path.getsize(p) > 600:
            print("  跳过（已存在）", u[:60])
            continue
        try:
            title, body = grab(u)
        except Exception as e:
            print("  ✗", u[:60], type(e).__name__)
            fail += 1
            continue
        if len(body) < a.min_chars:
            print("  ✗ 正文太短(%d) %s" % (len(body), u[:60]))
            fail += 1
            continue
        with open(p, "w", encoding="utf-8") as f:
            f.write("标题：%s\n链接：%s\n抓取：%s（无头浏览器）\n\n%s\n"
                    % (title, u, time.strftime("%Y-%m-%d %H:%M"), body))
        print("  ✓ %d 字 %s" % (len(body), (title or u)[:50]))
        ok += 1
        time.sleep(1.0)
    print("成功 %d｜失败 %d" % (ok, fail))


if __name__ == "__main__":
    main()
