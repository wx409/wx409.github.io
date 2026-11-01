"""每日自动：搜索「王晰 采访/访谈」→ 抓正文 → 抽本人原话入池 → 重建

用法：
  python -X utf8 project_b/interview_web_daily.py            # 正常跑（每天限量）
  python -X utf8 project_b/interview_web_daily.py --max 6    # 本轮最多抓几篇
  python -X utf8 project_b/interview_web_daily.py --dry      # 只看候选

搜索：360（so.com，纯 HTTP 可用）为主；Bing 结果不稳定已弃用。
抓取：先走轻量 HTTP，正文过短再切无头浏览器（Playwright）。
状态：data/web_interview_seen.json（已处理 URL），避免重复。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

PROJ = r"D:\wx409.github.io"
sys.path.insert(0, os.path.join(PROJ, "project_b"))

STATE = os.path.join(PROJ, "data", "web_interview_seen.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

QUERIES = [
    "site:sohu.com 王晰 专访", "site:sina.com.cn 王晰 访谈", "site:163.com 王晰 专访",
    "site:chinanews.com 王晰", "site:whb.cn 王晰", "site:ifeng.com 王晰 专访",
    "site:thepaper.cn 王晰", "site:people.com.cn 王晰 专访", "site:qq.com 王晰 专访",
    "王晰 专访 实录", "王晰 访谈 记者", "王晰 采访 低音", "王晰 对话 音乐",
    "王晰 专访 2019", "王晰 专访 2020", "王晰 专访 2021", "王晰 专访 2022",
    "王晰 专访 2023", "王晰 专访 2024", "王晰 专访 2025", "王晰 访谈 综艺",
    "王晰 采访 专辑", "王晰 专访 巡演", "王晰 访谈 声入人心",
]

GOOD_DOMAIN = ("sohu.com", "sina.com", "sina.cn", "163.com", "ifeng.com", "chinanews.com",
               "cnr.cn", "whb.cn", "zhoudaosh.com", "voc.com.cn", "thepaper.cn",
               "toutiao.com", "mp.weixin.qq.com", "qq.com", "people.com.cn", "xinhuanet",
               "cri.cn", "ynet.com", "eastday.com", "bjnews.com.cn", "chinanews.com.cn")
BAD = ("zhihu.com", "baidu.com", "baike", "wikipedia", "bilibili.com", "weibo.",
       "douyin.com", "y.qq.com", "music.163", "kugou", "xiaohongshu", "tieba", "so.com")


def load_seen():
    if os.path.exists(STATE):
        try:
            return set(json.load(open(STATE, encoding="utf-8")))
        except Exception:
            pass
    return set()


def save_seen(s):
    json.dump(sorted(s), open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def search(q, pages=1):
    out = []
    for p in range(pages):
        url = "https://www.so.com/s?q=%s&pn=%d" % (urllib.parse.quote(q), p + 1)
        try:
            h = urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}), timeout=25
            ).read().decode("utf-8", "ignore")
        except Exception:
            continue
        for u, t in re.findall(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
            title = re.sub(r"<[^>]+>", "", t).strip()
            out.append((u.replace("&amp;", "&"), title))
        time.sleep(1.2)
    return out


def resolve(u):
    """360 的跳转链接 → 真实 URL（页面里通常带 URL=... 或 location.replace）"""
    if "so.com/link" not in u:
        return u
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            u, headers={"User-Agent": UA}), timeout=20)
        body = r.read(6000).decode("utf-8", "ignore")
        m = (re.search(r'URL=([^"\'&]+)', body)
             or re.search(r'window\.location\.replace\("([^"]+)"', body)
             or re.search(r'location\.href\s*=\s*"([^"]+)"', body))
        if m:
            return m.group(1).replace("&amp;", "&")
        final = r.geturl()
        return "" if "so.com" in final else final
    except Exception:
        return ""


def pick(cands, seen, maxn):
    picked = []
    for u, t in cands:
        if u in seen:
            continue
        real = resolve(u)
        if not real or real in seen:
            continue
        if any(b in real for b in BAD):
            continue
        if not any(g in real for g in GOOD_DOMAIN):
            continue
        picked.append((real, t))
        seen.add(real)
        if len(picked) >= maxn:
            break
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=6)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    # 每天轮换 3 组关键词，避免同一批结果
    day = int(time.strftime("%j"))
    qs = [QUERIES[(day + i) % len(QUERIES)] for i in range(3)]
    print("今日关键词:", " / ".join(qs))

    seen = load_seen()
    cands = []
    for q in qs:
        got = search(q, pages=2)
        print("  %s → %d 条" % (q, len(got)))
        cands += got

    picked = pick(cands, seen, a.max)
    print("新候选 %d 篇" % len(picked))
    for u, t in picked:
        print("   +", t[:44], "|", u[:70])

    if a.dry or not picked:
        save_seen(seen)
        return 0

    # 抓取：先轻量，失败再无头
    ok = []
    for u, t in picked:
        rc = subprocess.call([sys.executable, "-X", "utf8",
                              os.path.join(PROJ, "project_b", "fetch_web_interviews.py"),
                              "--url", u])
        if rc == 0:
            ok.append(u)
    if not ok:
        print("轻量抓取全失败，改用无头浏览器")
        for u, t in picked:
            subprocess.call([sys.executable, "-X", "utf8",
                             os.path.join(PROJ, "project_b", "fetch_headless.py"), "--url", u])

    # 抽句入池
    subprocess.call([sys.executable, "-X", "utf8",
                     os.path.join(PROJ, "project_b", "import_page_interviews.py")])

    save_seen(seen)

    # 重建
    for s in ("build_phrase_index.py", "build_phrases_page.py", "build_qa_page.py",
              "inject_phrase_recall.py", "build_nav.py"):
        subprocess.call([sys.executable, "-X", "utf8", os.path.join(PROJ, "project_b", s)])

    try:
        import notify
        notify.record("网页访谈自动采集", "本轮新抓 %d 篇，已抽句入池（见 phrases.html）" % len(picked))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
