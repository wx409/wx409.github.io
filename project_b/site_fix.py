# -*- coding: utf-8 -*-
"""站点收录 + 元信息修复（唯一出口，可重复跑）。

  python -X utf8 project_b/site_fix.py --check   # 只读校验，有缺 exit 1（挂部署链）
  python -X utf8 project_b/site_fix.py           # 补 sitemap 缺页 + 补 meta
"""
import html
import json
import re
import xml.etree.ElementTree as ET
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://wx409.github.io/"
SM = ROOT / "sitemap.xml"
SKIP = {"404.html", "weibo-oauth-callback.html", "social_wall.html"}  # 后两个是嵌入片段，无 <head>
DIRS = ("tavern", "live", "map", "data", "culture", "dashboard", "debate",
        "stories", "share")  # 2026-11-04 归档：场次故事 / 分享卡
ROBOTS_RE = re.compile(r'<meta[^>]*name=["\']robots["\'][^>]*>', re.I)


def is_noindex(p):
    """页面自己声明了 noindex → 不得进 sitemap（自相矛盾会被搜索引擎判软 404）。"""
    try:
        h, _ = head(read(p))
    except (UnicodeDecodeError, OSError):
        return False
    m = ROBOTS_RE.search(h)
    return bool(m and "noindex" in m.group(0).lower())


def candidates():
    ps = [p for p in ROOT.glob("*.html")
          if p.name not in SKIP and not p.name.startswith(("_", "live_template"))]
    for d in DIRS:
        ps += [p for p in (ROOT / d).rglob("*.html")
               if not p.name.startswith("_") and "rendered" not in p.parts]  # rendered = 卡片片段
    return sorted(ps)


def pages():
    return [p for p in candidates() if not is_noindex(p)]


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


BLOCK_SKIP = re.compile(r"<(nav|header|footer|script|style)\b.*?</\1>", re.I | re.S)


def _text(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([，。；：、！？）」』])", r"\1", s)   # 标签拆分留下的空格
    s = re.sub(r"([（「『])\s+", r"\1", s)
    return s.replace("**", "")


def _jsonld_desc(h):
    m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', h)
    if not m:
        return ""
    try:
        return json.loads('"%s"' % m.group(1))
    except Exception:
        return ""


def desc_candidates(h, body, title):
    """按可信度给出 description 候选；绝不返回 title 本身。"""
    out = []
    for pat in (r'property="og:description"\s+content="([^"]*)"',
                r'name="twitter:description"\s+content="([^"]*)"'):
        m = re.search(pat, h)
        if m:
            out.append(html.unescape(m.group(1)).strip())
    jd = _jsonld_desc(h)
    if jd:
        out.append(jd)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    h1t = _text(h1.group(1)) if h1 else ""
    after = BLOCK_SKIP.sub(" ", body[h1.end():] if h1 else body)  # 去掉导航/页眉/页脚/脚本
    paras = [p for p in (_text(x) for x in re.findall(r"<p[^>]*>(.*?)</p>", after, re.S))
             if len(p) >= 20]
    for p in paras[:2]:
        segs = p.split("｜")
        if segs and re.fullmatch(r"\d{4}-\d{2}-\d{2}", segs[0].strip()):
            segs = segs[1:]  # 首段常以「日期｜场地｜…」开头，日期已在标题里
        p = "｜".join(segs)
        out.append((h1t + "：" + p) if h1t and not p.startswith(h1t[:12]) else p)
    res, seen = [], set()
    for c in out:
        c = _text(c)
        if len(c) < 20 or c == title or c in seen or c == h1t:
            continue
        if c.startswith("|") or c.count("|") >= 3:
            continue  # 表格行，不当摘要
        if c.count("｜") >= 2 or "数据截至" in c:
            continue  # 「日期｜场馆｜数据截至」这类元信息行，不作为摘要
        if re.match(r"(生成|数据更新)\s*20\d{2}", c) or "经验性认知（非官方）" in c:
            continue  # 过程稿标记
        seen.add(c)
        res.append(c[:118] + ("…" if len(c) > 118 else ""))
    return res


def pick_desc(h, body, title):
    for c in desc_candidates(h, body, title):
        return c
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    base = _text(h1.group(1)) if h1 else title
    return (base + "｜王晰数字档案：可查、可问、可引用的男低音实测数据记录")[:118]


def desc_issue(h):
    """现有 description 的问题类型：缺 / 与标题相同 / 过短。"""
    m = re.search(r'<meta name="description" content="([^"]*)"', h)
    ti = re.search(r"<title>(.*?)</title>", h, re.S)
    title = html.unescape(ti.group(1)).strip() if ti else ""
    if not m:
        return "缺"
    d = html.unescape(m.group(1)).strip()
    if title and d == title:
        return "与标题相同"
    if len(d) < 20:
        return "过短"
    if "数据截至" in d:
        return "元信息行"  # 「日期｜场馆｜数据截至」不是摘要
    return ""


def fix_meta(p, t):
    h, i = head(t)
    if i < 0:
        return t
    add, repl = "", ""
    if 'name="viewport"' not in h:
        add += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    if lack_desc(h):
        ti = re.search(r"<title>(.*?)</title>", h, re.S)
        title = html.unescape(ti.group(1)).strip() if ti else ""
        d = html.escape(pick_desc(h, t[i:], title), True)
        if 'name="description"' in h:
            repl = re.sub(r'<meta name="description" content="[^"]*">',
                          '<meta name="description" content="%s">' % d, h, count=1)
        else:
            add += '<meta name="description" content="%s">\n' % d
    if 'rel="canonical"' not in h:
        add += '<link rel="canonical" href="%s">\n' % url(p)
    if repl:
        return repl + t[i:]
    return t[:i] + add + t[i:]


def lack_desc(h):
    return desc_issue(h) != ""


def lack(t):
    h, _ = head(t)
    return [k for k, s in (("viewport", 'name="viewport"' not in h),
                           ("description", lack_desc(h)),
                           ("canonical", 'rel="canonical"' not in h)) if s]



def stale_entries(locs):
    """sitemap 里不该有的条目：noindex 页 / 文件已不存在的 .html。"""
    bad = []
    for u in locs:
        rel = u[len(SITE):] if u.startswith(SITE) else None
        if rel is None:
            continue
        rel = unquote(rel)  # sitemap 里 CJK 路径是 percent-encoded
        if not rel.endswith(".html"):
            continue
        p = ROOT / rel
        if not p.exists():
            bad.append((u, "文件不存在"))
        elif is_noindex(p):
            bad.append((u, "页面声明 noindex"))
    return bad


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
    xml_bad = ""
    try:
        ET.fromstring(sm)  # 结构自检：宁可 gate 报错，也不许把坏 XML 推上线
    except ET.ParseError as e:
        xml_bad = str(e)
    locs = set(re.findall(r"<loc>(.*?)</loc>", sm))
    missing = [p for p in ps if url(p) not in locs]
    stale = stale_entries(locs)

    print("页面 %d | sitemap 缺 %d | sitemap 多余 %d | 元信息缺 %d"
          % (len(ps), len(missing), len(stale), len(bad_meta)))
    for p in missing[:10]:
        print("  缺收录:", url(p))
    if xml_bad:
        print("  sitemap XML 结构错误:", xml_bad)
    for u, why in stale[:10]:
        print("  多余收录(%s):" % why, u)
    if check:
        return 1 if (missing or stale or bad_meta or xml_bad) else 0

    if "--preview" in sys.argv:
        for p, m in bad_meta:
            if "description" not in " ".join(m):
                continue
            t = read(p)
            h, i = head(t)
            ti = re.search(r"<title>(.*?)</title>", h, re.S)
            title = html.unescape(ti.group(1)).strip() if ti else ""
            old = re.search(r'<meta name="description" content="([^"]*)"', h)
            print("·", p.as_posix())
            print("   旧:", html.unescape(old.group(1)) if old else "（无）")
            print("   新:", pick_desc(h, t[i:], title))
        print("共 %d 页待改 description（preview，未写盘）"
              % sum(1 for _, m in bad_meta if "description" in " ".join(m)))
        return 0

    if missing:
        add = "".join(
            "  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq></url>\n"
            % (url(p), date.fromtimestamp(p.stat().st_mtime).isoformat())
            for p in missing)
        sm = sm.replace("</urlset>", add + "</urlset>")

    # 清掉不属于站点页面的条目（嵌入片段 / noindex 页 / 已删除文件）
    # 按整个 <url> 块删除：只删 <loc> 行会留下无 loc 的残块，XML 直接坏掉。
    drop = {u for u, _ in stale}
    drop.add(SITE + "social_wall.html")

    def _strip(m):
        blk = m.group(0)
        mm = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", blk)
        if mm and (mm.group(1) in drop or "data/share/rendered/" in mm.group(1)):
            return ""
        return blk

    sm = re.sub(r"[ \t]*<url>.*?</url>\r?\n?", _strip, sm, flags=re.S)
    ET.fromstring(sm)  # 写盘前再验一次结构
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
