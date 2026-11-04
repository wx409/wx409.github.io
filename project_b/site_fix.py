# -*- coding: utf-8 -*-
"""站点收录 + 元信息修复（唯一出口，可重复跑）。

  python -X utf8 project_b/site_fix.py --check   # 只读校验，有缺 exit 1（挂部署链）
  python -X utf8 project_b/site_fix.py           # 补 sitemap 缺页 + 补 meta
"""
import html
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://wx409.github.io/"
SM = ROOT / "sitemap.xml"
SKIP = {"404.html", "weibo-oauth-callback.html", "social_wall.html"}  # 后两个是嵌入片段，无 <head>
DIRS = ("tavern", "live", "map", "data", "culture", "dashboard", "debate")


def pages():
    ps = [p for p in ROOT.glob("*.html")
          if p.name not in SKIP and not p.name.startswith(("_", "live_template"))]
    for d in DIRS:
        ps += [p for p in (ROOT / d).rglob("*.html")
               if not p.name.startswith("_") and "rendered" not in p.parts]  # rendered = 卡片片段
    return sorted(ps)


def url(p):
    return SITE + quote(p.relative_to(ROOT).as_posix())


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def head(t):
    i = t.find("</head>")
    return t[:i] if i > 0 else t[:4000], i


def pick_desc(h, body):
    for pat in (r'property="og:description"\s+content="([^"]*)"',
                r'name="twitter:description"\s+content="([^"]*)"'):
        m = re.search(pat, h)
        if m and m.group(1).strip():
            return html.unescape(m.group(1)).strip()
    m = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
    if m:
        s = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip()
        if len(s) > 60:
            return s[:116] + "…"
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return html.unescape(m.group(1)).strip() if m else "王晰 · AI 可读数字档案"


def fix_meta(p, t):
    h, i = head(t)
    if i < 0:
        return t
    add = ""
    if 'name="viewport"' not in h:
        add += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    if 'name="description"' not in h:
        add += '<meta name="description" content="%s">\n' % html.escape(pick_desc(h, t[i:]), True)
    if 'rel="canonical"' not in h:
        add += '<link rel="canonical" href="%s">\n' % url(p)
    return t[:i] + add + t[i:]


def lack(t):
    h, _ = head(t)
    return [k for k, s in (("viewport", 'name="viewport"'),
                           ("description", 'name="description"'),
                           ("canonical", 'rel="canonical"')) if s not in h]


def main():
    check = "--check" in sys.argv
    ps, bad_meta = pages(), []
    for p in ps:
        try:
            m = lack(read(p))
        except UnicodeDecodeError:
            print("跳过(非UTF8):", p)
            continue
        if m:
            bad_meta.append((p, m))
    sm = read(SM)
    locs = set(re.findall(r"<loc>(.*?)</loc>", sm))
    missing = [p for p in ps if url(p) not in locs]

    print("页面 %d | sitemap 缺 %d | 元信息缺 %d" % (len(ps), len(missing), len(bad_meta)))
    for p in missing[:10]:
        print("  缺收录:", url(p))
    if check:
        return 1 if (missing or bad_meta) else 0

    if missing:
        add = "".join(
            "  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq></url>\n"
            % (url(p), date.fromtimestamp(p.stat().st_mtime).isoformat())
            for p in missing)
        sm = sm.replace("</urlset>", add + "</urlset>")

    # 清掉不属于站点页面的条目（嵌入片段）
    frag = re.compile(r"[ \t]*<url><loc>%s(?:social_wall\.html|data/share/rendered/[^<]*)</loc>.*?</url>\n?"
                      % re.escape(SITE))
    sm = frag.sub("", sm)
    write(SM, sm)

    n = 0
    for p, _ in bad_meta:
        try:
            t = read(p)
        except UnicodeDecodeError:
            continue
        t2 = fix_meta(p, t)
        if t2 != t:
            write(p, t2)
            n += 1
    print("已补收录 %d 条 | 已补元信息 %d 页" % (len(missing), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
