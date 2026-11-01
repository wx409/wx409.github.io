"""把通知里出现的媒体网页抓下来 → 抽正文 → 切句入池

用法：
  python -X utf8 project_b/fetch_web_interviews.py --from-notifications
  python -X utf8 project_b/fetch_web_interviews.py --url "https://www.sohu.com/a/950494911_121124743"
  python -X utf8 project_b/fetch_web_interviews.py --dry        # 只列出候选

流程：抓取 → bs4 去噪 → 取正文最长块 → 落盘 采访目录/网页/<slug>.txt → 切句入池（quality=mid）
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

NOTIF = r"D:\wx409.github.io\data\notifications.json"
OUT = r"E:\wx\私有\王晰全文库\采访目录\网页"
SKIP = ("wx409.github.io", "weibo.com", "weibo.cn", "douyin.com", "qq.com", "y.qq.com",
        "bilibili.com", "kugou", "music.163", "tieba.baidu")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def candidates():
    d = json.load(open(NOTIF, encoding="utf-8"))
    items = d if isinstance(d, list) else (d.get("items") or d.get("notifications") or [])
    urls = []
    for it in items:
        urls += re.findall(r"https?://[^\s\"\\)]+", json.dumps(it, ensure_ascii=False))
    out = []
    for u in dict.fromkeys(urls):
        if any(s in u for s in SKIP):
            continue
        if not re.search(r"(sohu|sina|163|zhihu|baike|ifeng|qq|toutiao|thepaper|guancha|wemp|mp\.weixin)", u):
            continue
        out.append(u)
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    raw = urllib.request.urlopen(req, timeout=25).read()
    m = re.search(rb"charset=[\"']?([\w-]+)", raw[:2000])
    enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        html = raw.decode(enc, "ignore")
    except LookupError:
        html = raw.decode("utf-8", "ignore")
    return html


def extract(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        t.decompose()
    title = (soup.title.string or "").strip() if soup.title else ""
    # 候选容器：文章/正文类 class 优先
    best, best_len = "", 0
    for sel in ["article", "div.article", "div#article", "div.content", "div#content",
                "div.article-content", "div.post-content", "div.main-content", "div.text"]:
        for node in soup.select(sel):
            txt = node.get_text("\n", strip=True)
            if len(txt) > best_len:
                best, best_len = txt, len(txt)
    if best_len < 400:
        body = soup.body or soup
        paras = [p.get_text(" ", strip=True) for p in body.find_all(["p", "div"])]
        paras = [p for p in paras if len(p) >= 25]
        best = "\n".join(paras)
    best = re.sub(r"\n{3,}", "\n\n", best)
    return title, best.strip()


def slug(u):
    return re.sub(r"[^0-9A-Za-z]+", "_", u.split("//", 1)[-1])[:70]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--from-notifications", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--min-chars", type=int, default=800)
    a = ap.parse_args()

    urls = [a.url] if a.url else (candidates() if a.from_notifications else [])
    print("候选网页", len(urls))
    if a.dry:
        for u in urls:
            print("  ", u)
        return 0

    os.makedirs(OUT, exist_ok=True)
    ok = fail = skip = 0
    for u in urls:
        p = os.path.join(OUT, slug(u) + ".txt")
        if os.path.exists(p) and os.path.getsize(p) > 500:
            skip += 1
            continue
        try:
            html = fetch(u)
            title, body = extract(html)
        except Exception as e:
            print("  ✗", u[:70], type(e).__name__)
            fail += 1
            continue
        if len(body) < a.min_chars:
            print("  ✗ 正文太短(%d)" % len(body), u[:70])
            fail += 1
            continue
        with open(p, "w", encoding="utf-8") as f:
            f.write("标题：%s\n链接：%s\n抓取：%s\n\n%s\n"
                    % (title, u, time.strftime("%Y-%m-%d %H:%M"), body))
        print("  ✓", len(body), "字", u[:70])
        ok += 1
        time.sleep(1.0)

    print("成功 %d｜跳过 %d｜失败 %d｜目录 %s" % (ok, skip, fail, OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
