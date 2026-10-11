# -*- coding: utf-8 -*-
"""④ 三视图（按歌／按事件／按问题）：**只加新页、不动任何已有 URL**；守卫注释补边界。"""
import io, json, sys
from datetime import date
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
TODAY = date.today().isoformat()


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def esc(s):
    return (str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def shell(title, desc, canon, inner, extra_jsonld=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}｜AI 可读数字档案｜GEO 资料站</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="https://wx409.github.io/{canon}">
{extra_jsonld}
<style>
body{{max-width:900px;margin:0 auto;padding:18px;font:15px/1.75 -apple-system,"Microsoft YaHei",sans-serif;color:#2b2320;background:#faf6ef}}
h2{{margin:26px 0 8px;border-bottom:2px solid #e6d9c4;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}} td,th{{border:1px solid #e6d9c4;padding:5px 7px;text-align:left}}
.meta{{color:#8a7f6d;font-size:12.5px}} a{{color:#8a5a2b}}
</style></head><body>
<!-- NAV_START --><!-- NAV_END -->
<h1>{esc(title)}</h1>
<p class="meta">生成 {TODAY}｜<b>经验性认知（非官方）</b>｜本页是**新增索引视图**，不改动任何已有页面 URL</p>
{inner}
</body></html>
"""


def main():
    made = []
    blocks = [load(f) for f in sorted((D / "show_blocks").glob("*.json"))]
    ssi = load(D / "songs_shows_index.json")
    qa = load(D / "qa_bank.json").get("items", [])
    setlists = {p.stem: load(p) for p in sorted((D / "show_setlists").glob("*.json"))}

    # ① 按歌：歌名 → 场次（长表曲目×场次）+ 该场反馈锚点
    rows = []
    fb_by_show = {}
    for b in blocks:
        key = (b.get("show") or {}).get("date")
        fb = b.get("feedback") or {}
        fb_by_show[key] = fb
    for s in ssi.get("songs", [])[:60]:
        shows = s.get("shows") or []
        anchor = ""
        for k, fb in fb_by_show.items():
            for m in (fb.get("song_mentions") or []):
                if m and m[0] == s.get("title"):
                    anchor += f'<a href="live-reviews.html">看现场反馈</a> ' if False else ""
        _ex = "；".join("%s %s" % (x.get("date"), x.get("city")) for x in shows[:3])
        _tr = "、".join(sorted({x.get("tour") for x in shows if x.get("tour")}))
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class=meta>%s…</td></tr>"
                    % (esc(s.get("title")), s.get("count"), esc(_tr), esc(_ex)))
    (SITE / "index-by-song.html").write_text(shell(
        "按歌索引入口", "王晰曲目 × 场次 × 巡次索引视图（按歌查场次，不改动已有页面 URL）",
        "index-by-song.html",
        "<h2>按歌查场次</h2>"
        f"<p class=meta>数据源：<code>data/songs_shows_index.json</code>（本页只做视图，统计口径不变）</p>"
        f"<table><tr><th>曲目</th><th>场次提及</th><th>巡次</th><th>示例场次</th></tr>{''.join(rows)}</table>"
        "<p class=meta>相关：<a href='songs.html'>曲目档案</a>｜<a href='live-reviews.html'>现场反馈汇总</a></p>"),
        encoding="utf-8")
    made.append("index-by-song.html")

    # ② 按事件：事件 → 记录（预留给山河令这类案例位）
    ev_rows = "".join(
        f"<tr><td>{esc((b.get('show') or {}).get('date'))}</td><td>{esc((b.get('show') or {}).get('name'))}</td>"
        f"<td>{esc((b.get('show') or {}).get('kind') or '演唱会')}</td>"
        f"<td>{esc(str((b.get('feedback') or {}).get('total', '—')))}</td>"
        f"<td class=meta>{esc(((b.get('feedback') or {}).get('platform_composition_note') or '')[:60])}</td></tr>"
        for b in blocks)
    (SITE / "index-by-event.html").write_text(shell(
        "按事件索引入口", "王晰演出/项目事件索引视图（含预留案例位；不改动已有页面 URL）",
        "index-by-event.html",
        "<h2>按事件查记录</h2>"
        "<p class=meta>已登记事件（数据源 <code>data/show_blocks/*.json</code>）：</p>"
        f"<table><tr><th>日期</th><th>事件</th><th>性质</th><th>反馈条数</th><th>平台构成注记</th></tr>{ev_rows}</table>"
        "<h2>预留案例位</h2>"
        "<p class=meta>本区为**待补案例位**（如外部作品引发的路人讨论类事件）：需素材到位后按信源分级+匿名化+含负面/中性条目验收项处理。"
        "**当前无素材，标注待补，不编造。**</p>"
        "<p class=meta>相关：<a href='dongyan.html'>东演合作专区</a>｜<a href='history.html'>生涯</a></p>"),
        encoding="utf-8")
    made.append("index-by-event.html")

    # ③ 按问题：问题 → 答案锚点（与 qa.html 互链）
    q_rows = "".join(
        f"<tr><td>{i+1}</td><td>{esc(x.get('q') or x.get('question'))}</td>"
        f"<td><a href='qa.html'>qa.html</a></td></tr>" for i, x in enumerate(qa))
    (SITE / "index-by-question.html").write_text(shell(
        "按问题索引入口", "王晰档案站问答索引视图（与 qa.html 互链；不改动已有页面 URL）",
        "index-by-question.html",
        "<h2>按问题查答案</h2>"
        f"<p class=meta>共 {len(qa)} 条实质问答（数据源 <code>data/qa_bank.json</code>）；"
        "答案正文在 <a href='qa.html'>qa.html</a>，本页只是索引视图。</p>"
        f"<table><tr><th>#</th><th>问题</th><th>答案</th></tr>{q_rows}</table>"
        "<p class=meta>互链：<a href='qa.html'>qa.html</a>（问答库）｜<a href='search.html'>search.html</a>（查询工具）</p>"),
        encoding="utf-8")
    made.append("index-by-question.html")
    print("[④] 三视图已生成：", "、".join(made))

    # 挂档案区（底部全站索引）：登记进 build_nav 的完整档案页清单
    P = SITE / "project_b" / "build_nav.py"
    t = io.open(P, encoding="utf-8").read()
    if "index-by-song.html" not in t:
        import re
        m = re.search(r'(ARCHIVE\w*\s*=\s*\[)([^\]]*)(\])', t, re.S)
        if m:
            t = t[:m.end(2)] + '\n    "index-by-song.html", "index-by-event.html", "index-by-question.html",' + t[m.end(2):]
            io.open(P, "w", encoding="utf-8").write(t)
            print("[④] 已登记进 build_nav（档案区/底部索引）")
        else:
            print("[④] 未找到档案页清单锚点 → 需手工登记")
    else:
        print("[④] 已登记")

    # 守卫注释补边界说明
    P2 = SITE / "project_b" / "audit_site_url.py"
    t2 = io.open(P2, encoding="utf-8").read()
    if "边界" not in t2:
        t2 = t2.replace('"""换域回归守卫',
                        '"""换域回归守卫（**边界**：只扫生成器源码 project_b/*.py 与 tools/*.py——'
                        '生成页天然含 canonical/og:url 域名，那是产物不是硬编码，**禁止改成全站扫描**）', 1)
        io.open(P2, "w", encoding="utf-8").write(t2)
        print("[1] 守卫已写明边界（禁改全站扫描）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
