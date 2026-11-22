# -*- coding: utf-8 -*-
"""build_voices_page.py —— 听众之声（评论语料聚合页）

数据：data/voices.json（由 project_b/comment_insights.py 从私有评论库派生）
输出：voices.html
原则：只发布聚合 + ≤60 字匿名短引用；不含昵称、不含本地路径、不搬整串评论。
"""
from __future__ import annotations
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "voices.json"
OUT = ROOT / "voices.html"

CSS = """
:root{--red:#a8323d;--ink:#1f2328;--mute:#666;--bg:#faf9f7;--line:#e6e2dc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:960px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:30px;margin:8px 0 4px}
.sub{color:var(--mute);margin:0 0 22px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:18px 0 26px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card b{display:block;font-size:26px;color:var(--red)}
.card span{color:var(--mute);font-size:13px}
h2{font-size:20px;margin:34px 0 12px;border-left:4px solid var(--red);padding-left:10px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:8px 12px;border-bottom:1px solid var(--line);text-align:left;font-size:14px}
th{background:#f3efe9;color:#444}
.bar{height:8px;background:var(--red);border-radius:4px;display:inline-block;vertical-align:middle}
.quotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.q{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.q p{margin:0 0 8px}
.q .meta{color:var(--mute);font-size:12px}
.note{background:#fff8e6;border:1px solid #f0d9a8;border-radius:10px;padding:12px 16px;font-size:14px;color:#6b5320}
a{color:var(--red)}
footer{margin-top:40px;color:var(--mute);font-size:13px}
"""

def esc(s) -> str:
    return html.escape(str(s), quote=True)

def main() -> int:
    if not SRC.exists():
        print("[SKIP] 缺少 data/voices.json（先跑 comment_insights.py）——不改动 voices.html")
        return 0
    d = json.loads(SRC.read_text(encoding="utf-8"))
    n, posts = d["n_comments"], d["n_posts"]
    years = d.get("by_year") or []
    ymax = max([x["n"] for x in years] or [1])
    kw = d.get("keywords") or []
    kmax = max([x["count"] for x in kw] or [1])
    quotes = d.get("quotes") or []
    top_posts = d.get("top_posts") or []
    y0, y1 = (years[0]["y"], years[-1]["y"]) if years else ("—", "—")
    title = "听众之声｜王晰微博评论语料（%s 条）" % format(n, ",")

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "王晰微博评论语料聚合",
        "description": "对王晰相关微博评论的聚合统计与匿名短引用：%d 条评论、%d 条帖子，覆盖 %s–%s。"
                       "不含昵称与原文全量，仅发布聚合与 ≤60 字匿名引用。" % (n, posts, y0, y1),
        "url": "https://wx409.github.io/voices.html",
        "license": "https://creativecommons.org/licenses/by-nc/4.0/",
        "creator": {"@type": "Organization", "name": "AI 可读数字档案｜GEO 资料站"},
        "temporalCoverage": "%s/%s" % (y0, y1),
        "size": "%d comments" % n,
        "variableMeasured": ["评论数", "年份分布", "关键词频次", "高赞引用"],
        "isBasedOn": "微博公开评论（匿名化处理）",
    }

    parts = []
    parts.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append("<title>%s</title>" % esc(title))
    parts.append('<meta name="description" content="%s">' % esc(
        "王晰微博评论语料聚合：%d 条评论、%d 条帖子，%s–%s。只发布匿名聚合与短引用。"
        % (n, posts, y0, y1)))
    parts.append('<meta name="robots" content="index, follow">')
    parts.append('<link rel="canonical" href="https://wx409.github.io/voices.html">')
    parts.append('<script type="application/ld+json">%s</script>' % json.dumps(jsonld, ensure_ascii=False))
    parts.append("<style>%s</style>\n</head>\n<body>\n<main>" % CSS)

    parts.append("<h1>听众之声</h1>")
    parts.append('<p class="sub">另见 <a href="/danmaku.html">B站弹幕里的王晰（观众即时反应）</a></p>')
    parts.append('<p class="sub">%d 条微博评论的聚合视图 · %d 条帖子 · %s–%s · 只发布匿名统计与 ≤60 字短引用</p>'
                 % (n, posts, y0, y1))

    parts.append('<div class="cards">')
    parts.append('<div class="card"><b>%s</b><span>评论（已去空/去超短）</span></div>' % format(n, ","))
    parts.append('<div class="card"><b>%s</b><span>近 7 天新增</span></div>' % format(d.get("n_last7") or 0, ","))
    parts.append('<div class="card"><b>%d</b><span>帖子</span></div>' % posts)
    parts.append('<div class="card"><b>%s–%s</b><span>时间跨度</span></div>' % (y0, y1))
    parts.append('<div class="card"><b>%d</b><span>年份数</span></div>' % len(years))
    parts.append("</div>")

    parts.append("<h2>年份分布</h2><table><tr><th>年份</th><th>评论数</th><th></th></tr>")
    for x in years:
        w = max(2, int(x["n"] / ymax * 260))
        parts.append("<tr><td>%s</td><td>%s</td><td><span class='bar' style='width:%dpx'></span></td></tr>"
                     % (esc(x["y"]), format(x["n"], ","), w))
    parts.append("</table>")

    parts.append("<h2>他们在说什么</h2><table><tr><th>词</th><th>出现次数</th><th>占全部评论</th><th></th></tr>")
    for x in kw[:14]:
        w = max(2, int(x["count"] / kmax * 260))
        parts.append("<tr><td>%s</td><td>%s</td><td>%.2f%%</td><td><span class='bar' style='width:%dpx'></span></td></tr>"
                     % (esc(x["word"]), format(x["count"], ","), x["pct"], w))
    parts.append("</table>")
    parts.append('<p class="sub" style="margin-top:8px">注：关键词为包含式匹配，含复读与转评（//@）。</p>')

    parts.append("<h2>高赞原话（匿名）</h2><div class='quotes'>")
    for q in quotes:
        parts.append("<div class='q'><p>%s</p><div class='meta'>赞 %s · %s</div></div>"
                     % (esc(q["text"]), format(q["likes"], ","), esc(q.get("date") or "")))
    parts.append("</div>")

    s = d.get("search") or {}
    if s.get("n"):
        parts.append("<h2>王晰广场短帖（受众自述）</h2>")
        parts.append('<p class="sub">微博搜索「王晰」广场里的公开短帖，共 %s 条；'
                     "与评论区分开统计——这是受众自己发的，不是回复。</p>" % format(s["n"], ","))
        if s.get("by_year"):
            parts.append("<table><tr><th>年份</th><th>短帖数</th></tr>")
            for x in s["by_year"]:
                parts.append("<tr><td>%s</td><td>%s</td></tr>" % (esc(x["y"]), format(x["n"], ",")))
            parts.append("</table>")
        if s.get("samples"):
            parts.append("<div class='quotes'>")
            for q in s["samples"]:
                parts.append("<div class='q'><p>%s</p><div class='meta'>%s</div></div>"
                             % (esc(q["text"]), esc(q.get("date") or "")))
            parts.append("</div>")

    parts.append("<h2>讨论最多的帖子</h2><table><tr><th>帖子</th><th>评论文本数</th><th>最高赞</th></tr>")
    for p in top_posts:
        label = "微博 " + str(p.get("post_mid") or "")
        link = p.get("post") or "#"
        parts.append("<tr><td><a href='%s' rel='nofollow noopener' target='_blank'>%s</a></td><td>%s</td><td>%s</td></tr>"
                     % (esc(link), esc(label), format(p["comments"], ","), format(p["top_like"], ",")))
    parts.append("</table>")

    recent = d.get("recent") or []
    if recent:
        parts.append("<h2>最近 30 天随机短评</h2>")
        parts.append("<p class='sub'>从近 30 天评论中随机抽取（不是按赞），用于观察最新语气；每条 ≤60 字、匿名。</p>")
        parts.append('<div class="quotes">')
        for q in recent:
            parts.append('<div class="q">“%s”<div class="src">%s</div></div>' % (esc(q["text"]), esc(q.get("date") or "")))
        parts.append("</div>")

    try:
        th = json.loads((ROOT / "data" / "comment_themes.json").read_text(encoding="utf-8"))
        parts.append("<h2>评论主题分布</h2>")
        parts.append("<p class='sub'>按关键词规则给 12.8 万条评论打主题标签（可多标签）；每条只取 ≤60 字匿名短引用。</p>")
        parts.append("<table><tr><th>主题</th><th>评论数</th><th>代表性短引用（按赞）</th></tr>")
        for t in th.get("themes") or []:
            qs = "；".join("“%s”" % esc(q["text"]) for q in (t.get("quotes") or [])[:2])
            parts.append("<tr><td>%s</td><td class='n'>%s</td><td>%s</td></tr>"
                         % (esc(t["name"]), format(t["n"], ","), qs))
        parts.append("</table>")

        try:
            tc = json.loads((ROOT / "data" / "comment_topics.json").read_text(encoding="utf-8"))
            parts.append("<h2>自动主题图谱（bge 向量 + 聚类）</h2>")
            parts.append("<p class='sub'>对清洗后的评论做语义聚类，得到 24 个主题；词为 TF-IDF 高权重词，样本为匿名短句。</p>")
            parts.append("<table><tr><th>主题词</th><th>条数</th><th>样本</th></tr>")
            for t in (tc.get("topics") or [])[:24]:
                sample = "；".join("“%s”" % esc(x[:40]) for x in (t.get("samples") or [])[:1])
                parts.append("<tr><td>%s</td><td class='n'>%s</td><td>%s</td></tr>"
                             % (esc("、".join(t.get("words") or [])[:8]), format(t.get("count") or 0, ","), sample))
            parts.append("</table>")
        except Exception:
            pass

        parts.append("<h2>场次相关评论（日期 ±10 天 + 城市/剧名命中）</h2>")
        parts.append("<table><tr><th>场次</th><th>评论数</th><th>短引用</th></tr>")
        for s in th.get("by_show") or []:
            qs = "；".join("“%s”" % esc(q["text"]) for q in (s.get("quotes") or [])[:1])
            parts.append("<tr><td>%s</td><td class='n'>%s</td><td>%s</td></tr>"
                         % (esc(s["show"]), format(s["n"], ","), qs))
        parts.append("</table>")
    except Exception:
        pass

    parts.append('<div class="note" style="margin-top:26px"><b>口径与局限</b><br>%s<br>'
                 "· 只采公开评论；uid 已哈希、不含昵称；用户删评后本地同步删除。<br>"
                 "· 公开层只发布聚合与 ≤60 字匿名短引用，不搬整串评论、不二次分发原文。</div>"
                 % esc(d.get("coverage_note", "")))

    parts.append("<footer>数据来源：微博公开评论（本地私有库，不入 git）｜生成：%s｜"
                 "方法：每帖最多 6 页采样 + 去空/去超短 + 关键词与赞数聚合</footer>"
                 % esc(d.get("generated_at", "")))

    parts.append("</main>\n</body>\n</html>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print("写入", OUT, "| 字节", OUT.stat().st_size)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
