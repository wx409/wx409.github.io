"""抓取公开采访全文 → 本地目录 + 切句入池（只打印统计，不打印正文）"""
import json, os, re, ssl, urllib.request
from collections import Counter

ROOT = r"D:\wx409.github.io"
OUT = r"E:\wx\私有\王晰全文库\采访目录"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
os.makedirs(OUT, exist_ok=True)

URLS = [
    ("对话男低音王晰：不求万人合唱，只希望在夜深人静的时候明媚忧伤", "周到", "2018-11-19",
     "http://static.zhoudaosh.com/files/cnews/2018/20181119/12EF00478DAB7BC7D70B93A07126EB8F79A09BDE59390E461556710198E7DD5A/1.html"),
    ("王晰：夜深人静时愿你想起我的歌", "搜狐", "", "https://www.sohu.com/a/276878181_119778"),
    ("王晰做客《背后》讲述成名路：用音乐创造属于自己的安全区", "新黄河", "2025", "https://www.jinantimes.com.cn/news-265-5099232.html"),
    ("王晰忆往昔：感谢“快男”没让我一夜爆红", "中国新闻网", "2016-02-20", "http://www.chinanews.com.cn/m/yl/2016/02-20/7765820.shtml"),
    ("王晰做客《背后》：用音乐创造“安全区”", "河南广电·大象", "2025-06-29", "http://news.hnr.cn/djn/article/1/1939267934256844802"),
    ("星月对话｜王晰：就要跟音乐谈恋爱，你爱她，她就会爱你", "微信公众号", "", "https://mp.weixin.qq.com/s?__biz=MzA3MDgzMzEwNQ==&mid=2652058593&idx=1&sn=44e246d0a38478c653b993e5f8ff1e67"),
]

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def get(url):
    req = urllib.request.Request(url, headers=H)
    raw = urllib.request.urlopen(req, timeout=30, context=ctx).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")

def text_of(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
    h = re.sub(r"[ \t]+", " ", h)
    lines = [l.strip() for l in h.splitlines() if len(l.strip()) >= 8]
    return "\n".join(lines)

catalog, bodies = [], []
for title, media, date, url in URLS:
    try:
        html = get(url)
        body = text_of(html)
        if len(body) < 800:
            catalog.append({"题目": title, "来源": media, "日期": date, "url": url,
                            "全文路径": "", "字数": len(body), "备注": "抓取过短，需人工补"})
            continue
        fn = re.sub(r"[\\/:*?\"<>|\s]+", "_", title)[:60] + ".txt"
        path = os.path.join(OUT, fn)
        with open(path, "w", encoding="utf-8") as f:
            f.write("题目：%s\n来源：%s\n日期：%s\nURL：%s\n\n%s\n" % (title, media, date, url, body))
        catalog.append({"题目": title, "来源": media, "日期": date, "url": url,
                        "全文路径": fn, "字数": len(body), "备注": ""})
        bodies.append((title, media, body))
    except Exception as e:
        catalog.append({"题目": title, "来源": media, "日期": date, "url": url,
                        "全文路径": "", "字数": 0, "备注": "抓取失败：%s" % type(e).__name__})

json.dump({"updated": "2026-10-31", "count": len(catalog),
           "fields": ["题目", "来源", "日期", "url", "全文路径", "字数", "备注", "采访者"],
           "note": "全文落本地私有库（不入 git、不上站）；入池只取引号内原话。",
           "items": catalog},
          open(os.path.join(OUT, "采访目录.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("目录条目", len(catalog), "| 成功全文", len(bodies))
for c in catalog:
    print("  ", c["题目"][:26], "|", c["来源"], "|", c["字数"], "字", "|", c["备注"][:16])

# 切句入池：只取引号内他本人的话
bank = json.load(open(BANK, encoding="utf-8"))
exist = {it["text"] for it in bank["items"]}
QUOTE = re.compile(r"[“\"]([^”\"]{10,70})[”\"]")
added = []
for title, media, body in bodies:
    for q in QUOTE.findall(body):
        q = q.strip().strip("，。、；：")
        if not (10 <= len(q) <= 70) or q in exist:
            continue
        if re.search(r"记者|报道|编辑|来源|转载|版权", q):
            continue
        exist.add(q)
        added.append({"text": q, "type": "interview", "source": "网页采访｜%s（%s）" % (title[:24], media),
                      "curated": False, "rights": "free", "mood": "quote_web", "verified": True})

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("网页引语入池", len(added), "| 现共", bank["count"], bank["by_type"])
