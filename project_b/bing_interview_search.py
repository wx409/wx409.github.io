"""用 Bing 搜索找「王晰 采访/访谈」→ 收集候选 URL

用法：
  python -X utf8 project_b/bing_interview_search.py --q "王晰 专访 实录"
  python -X utf8 project_b/bing_interview_search.py            # 用默认多组查询
  python -X utf8 project_b/bing_interview_search.py --save     # 结果写入 data/bing_interview_urls.json
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
OUT = r"D:\wx409.github.io\data\bing_interview_urls.json"

QUERIES = [
    "王晰 专访 全文",
    "王晰 访谈 实录",
    "王晰 采访 “记者” 对话",
    "王晰 专访 搜狐",
    "王晰 访谈 网易 娱乐",
    "王晰 专访 新浪",
    "王晰 对话 音乐 低音",
]

BLOCK = ("zhihu.com", "baike.baidu", "wikipedia", "bilibili.com", "weibo.", "douyin",
         "y.qq.com", "music.163", "kugou", "xiaohongshu", "tieba.baidu", "zhuanlan")


def bing(q, pages=2):
    out = []
    for p in range(pages):
        first = p * 10 + 1
        url = "https://www.bing.com/search?q=%s&first=%d&setlang=zh-CN&cc=CN" % (
            urllib.parse.quote(q), first)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}), timeout=25).read()
            html = raw.decode("utf-8", "ignore")
        except Exception as e:
            print("   ! Bing 请求失败", type(e).__name__)
            break
        # 结果链接：<h2><a href="...">
        for m in re.finditer(r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S):
            link, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
            out.append({"url": link, "title": title.strip()[:90], "q": q})
        time.sleep(1.2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", action="append")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    qs = a.q or QUERIES
    found, seen = [], set()
    for q in qs:
        print("查询:", q)
        for r in bing(q):
            u = r["url"]
            if any(b in u for b in BLOCK):
                continue
            if u in seen:
                continue
            seen.add(u)
            found.append(r)
            print("   +", r["title"][:50], "|", u[:70])

    print("\n可用候选 %d 条" % len(found))
    if a.save:
        json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("→", OUT)


if __name__ == "__main__":
    main()
