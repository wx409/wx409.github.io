# -*- coding: utf-8 -*-
"""build_dongyan_page.py —— 东演专区页 → dongyan.html

定位：把「王晰 × 中国东方演艺集团」的合作项目收在一页（当前：歌舞剧《草原之夜》、演唱会《沉响与长歌》）。
数据来源：
  · data/dongyan_projects.json —— 定性内容（角色、说明、主创、出处；人工维护）
  · data/activity_master.json  —— 场次/日期/城市/曲目（派生，**页面里的数字全部从这里算**，禁写死）
  · data/event_lifecycle.json  —— 官宣/开演里程碑与指数窗口（有则展示）
用法：python -X utf8 project_b\\build_dongyan_page.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT = ROOT / "dongyan.html"
URL = "https://wx409.github.io/dongyan.html"
TODAY = date.today().isoformat()
CSS = ("body{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;max-width:960px;margin:0 auto;"
       "padding:24px 18px 60px;line-height:1.75;color:#222}h1{font-size:1.7rem;margin:.2em 0 .6em}"
       "h2{font-size:1.25rem;margin:2em 0 .5em;padding-bottom:.25em;border-bottom:2px solid #a8323d}"
       "h3{font-size:1.05rem;margin:1.4em 0 .4em}.lead{color:#555}table{border-collapse:collapse;width:100%;"
       "margin:.6em 0;font-size:.94rem}th,td{border:1px solid #e2e2e2;padding:6px 9px;text-align:left;vertical-align:top}"
       "th{background:#faf7f7}.badge{display:inline-block;background:#a8323d;color:#fff;border-radius:4px;"
       "padding:1px 8px;font-size:.8rem;margin-left:8px;vertical-align:middle}.role{background:#f3f3f3;color:#444}"
       ".meta{color:#666;font-size:.9rem}.box{background:#fafafa;border-left:4px solid #a8323d;padding:10px 14px;"
       "margin:1em 0}ul{padding-left:1.3em}.tag{display:inline-block;background:#f1f1f1;border-radius:10px;"
       "padding:1px 9px;margin:2px 4px 2px 0;font-size:.86rem}.pending{color:#8a6d3b;background:#fcf8e3;"
       "border-left:4px solid #faebcc;padding:8px 12px;font-size:.9rem}")


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


proj = load(D / "dongyan_projects.json", {})
am = load(D / "activity_master.json", {})
lc = load(D / "event_lifecycle.json", {})
rows = am.get("rows", [])
events = lc.get("events", [])


def shows_for(match: str) -> list[dict]:
    out = [r for r in rows if isinstance(r, dict) and match in (r.get("title") or "")]
    out.sort(key=lambda r: r.get("date") or "")
    return out


def songs_for(match: str) -> list[str]:
    seen, out = set(), []
    for r in shows_for(match):
        for s in r.get("songs") or []:
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def nights_for(match: str) -> list[dict]:
    """按夜歌单（data/show_setlists/*.json）：只取 show.name 含该项目关键字的文件。
    **全部数字由文件派生，不写死**；供「按夜场次与歌单差异」小节使用。"""
    out = []
    d = ROOT / "data" / "show_setlists"
    if not d.exists():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = str((j.get("show") or {}).get("name", ""))
        if match and match not in name:
            continue
        dl = j.get("delta_vs_first_show") or {}
        added = [x.get("song") for x in (dl.get("added_compared_to_first_show")
                                         or dl.get("added_confirmed") or []) if x.get("song")]
        ps = dl.get("point_song_segment") or {}
        out.append({"date": (j.get("show") or {}).get("date"),
                    "segments": j.get("segments"), "songs": len(j.get("songs") or []),
                    "added": added,
                    "point_song": (ps.get("second_show_2026-10-10")
                                   or (j.get("delta_vs_first_show") or {}).get("point_song")
                                   or []),
                    "no_removed": bool(dl.get("no_song_removed")),
                    "file": f.name})
    return out


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


parts: list[str] = []
jsonld_events = []
for p in proj.get("projects", []):
    sh = shows_for(p["match"])
    sg = songs_for(p["match"])
    cities = []
    for r in sh:
        c = (r.get("city") or "").strip()
        if c and c not in cities:
            cities.append(c)
    span = ""
    if sh:
        span = sh[0]["date"] if len(sh) == 1 else "%s ~ %s" % (sh[0]["date"], sh[-1]["date"])
    parts.append('<h2>%s<span class="badge">%s</span></h2>' % (esc(p["title"]), esc(p.get("kind", ""))))
    # ★ 2026-10-14：曲目口径改为**两栏并列**（节目编号 23｜实际歌曲 N，换算式同列），
    #   数字从 data/show_setlists/*.json 现算，禁手写。
    conv = ""
    try:
        import json as _json
        _rows = []
        for f in sorted((ROOT / "data" / "show_setlists").glob("*.json")):
            j = _json.loads(f.read_text(encoding="utf-8"))
            if "沉响" not in str((j.get("show") or {}).get("name", "")):
                continue
            _rows.append({
                "date": (j.get("show") or {}).get("date", f.stem),
                "primary": j.get("songs_count_primary") or j.get("segments_no"),
                "total": j.get("songs_count_total"),
                "with_encore": j.get("songs_count_total_with_encore"),
                "conversion": j.get("songs_count_conversion", ""),
            })
        _rows.sort(key=lambda x: x["date"])
        if _rows:
            bits = []
            for r in _rows:
                n = r["with_encore"] or r["total"]
                bits.append(f"{r['date']}：节目编号 <b>{r['primary']}</b>｜实际歌曲 <b>{n}</b> 首")
            conv = ("；".join(bits)
                    + "。换算式：" + (_rows[-1].get("conversion") or "")
                    + "（旧文「19 段 / 26 曲」为早期口径，今以本行为准）")
    except Exception as e:
        conv = f"（口径读取失败：{e}）"
    parts.append('<table><tr><th>王晰的角色</th><td><span class="badge role">%s</span></td></tr>'
                 '<tr><th>主要场馆</th><td>%s</td></tr>'
                 '<tr><th>场次</th><td>共 <b>%d</b> 场%s%s</td></tr>'
                 '<tr><th>曲目</th><td>%s</td></tr></table>'
                 % (esc(p.get("role", "")), esc(p.get("venue", "")), len(sh),
                    "（%s）" % esc(span) if span else "",
                    "，覆盖 %s" % "、".join(cities) if cities else "",
                    conv or ("共 <b>%d</b> 首（按长表去重）" % len(sg))))
    parts.append('<p class="lead">%s</p>' % esc(p.get("summary", "")))
    if p.get("facts"):
        parts.append("<h3>可引用要点</h3><ul>%s</ul>"
                     % "".join("<li>%s</li>" % esc(f) for f in p["facts"]))
    if p.get("credits"):
        parts.append("<h3>关键主创（已核实）</h3><table><tr><th>职务</th><th>姓名</th><th>最亮眼履历</th><th>出处</th></tr>%s</table>"
                     % "".join("<tr><td>%s</td><td><b>%s</b></td><td>%s</td><td class=meta>%s</td></tr>"
                               % (esc(c["role"]), esc(c["name"]), esc(c["highlight"]), esc(c["source"]))
                               for c in p["credits"]))
    if sg:
        parts.append("<h3>曲目（首场全场）</h3><p>%s</p>" % "".join('<span class="tag">%s</span>' % esc(s) for s in sg))
    nts = nights_for(p.get("match", ""))
    if nts:
        rows = []
        for n in nts:
            extra = []
            if n.get("added"):
                extra.append("新增：" + "、".join(esc(x) for x in n["added"]))
            if n.get("point_song"):
                extra.append("点歌段：" + "、".join(esc(x) for x in n["point_song"]))
            if n.get("no_removed"):
                extra.append("无曲目被顶掉")
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class=meta>%s</td></tr>"
                        % (esc(n.get("date")), esc(n.get("segments") or "—"),
                           esc(n.get("songs")), "；".join(extra) or esc(n.get("file"))))
        parts.append("<h3>按夜场次与歌单差异</h3>"
                     "<table><tr><th>日期</th><th>段数</th><th>曲目数</th><th>与首场差异</th></tr>%s</table>"
                     "<p class=meta>数据源：<code>data/show_setlists/*.json</code>（按夜独立歌单）｜"
                     "★ 本页场次属「院团合作场次（东演）」，与个人巡演 59 场<b>分列</b>，不得混加</p>"
                     % "".join(rows))
    if sh:
        parts.append("<h3>场次表</h3><table><tr><th>日期</th><th>城市</th><th>曲目数</th><th>出处</th></tr>%s</table>"
                     % "".join("<tr><td>%s</td><td>%s</td><td>%d</td><td class=meta>%s</td></tr>"
                               % (esc(r.get("date")), esc(r.get("city")), len(r.get("songs") or []), esc(r.get("status") or r.get("source") or ""))
                               for r in sh))
        jsonld_events.append({"@type": "Event", "name": p["title"],
                              "startDate": sh[0]["date"], "endDate": sh[-1]["date"],
                              "location": {"@type": "Place", "name": p.get("venue", ""), "address": "、".join(cities)},
                              "performer": {"@type": "Person", "name": "王晰"}})
    ev = next((e for e in events if p["match"] in (e.get("title") or "")), None)
    if ev and ev.get("milestones"):
        ms = ev["milestones"]
        parts.append('<h3>数据窗口（里程碑前后指数）</h3><table><tr><th>里程碑</th><th>日期</th><th>窗口统计</th></tr>%s</table>'
                     % "".join("<tr><td>%s</td><td>%s</td><td class=meta>%s</td></tr>"
                               % (esc(m.get("kind")), esc(m.get("date")),
                                  esc(json.dumps(m.get("stats"), ensure_ascii=False)[:300]) if m.get("stats") else "待数据")
                               for m in ms))
    if p.get("pending"):
        parts.append('<div class="pending">%s</div>' % esc(p["pending"]))
    parts.append('<p class="meta">出处：%s</p>' % esc("；".join(p.get("sources", []))))

jsonld = {
    "@context": "https://schema.org", "@type": "CollectionPage",
    "name": "东演合作专区 · AI 可读数字档案｜GEO 资料站", "url": URL,
    "description": "王晰与中国东方演艺集团合作项目档案：歌舞剧《草原之夜——来自可克达拉的歌谣》、演唱会《沉响与长歌》，含场次、曲目、关键主创与出处。",
    "isPartOf": {"@type": "WebSite", "name": "AI 可读数字档案｜GEO 资料站", "url": "https://wx409.github.io/"},
    "about": {"@type": "PerformingGroup", "name": proj.get("org", {}).get("name", "中国东方演艺集团")},
    "hasPart": jsonld_events,
    "dateModified": TODAY,
}

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>东演合作专区 · AI 可读数字档案｜GEO 资料站</title>
<meta name="description" content="王晰 × 中国东方演艺集团合作项目档案：歌舞剧《草原之夜》、演唱会《沉响与长歌》——场次、曲目、关键主创与逐条出处。">
<meta name="robots" content="index, follow">
<link rel="canonical" href="%(url)s">
<script type="application/ld+json">%(jsonld)s</script>
<style>%(css)s</style>
</head>
<body>
<!-- NAV_START --><!-- NAV_END -->
<main>
<h1>东演合作专区<span class="badge">%(_org)s</span></h1>
<p class="lead">%(orgnote)s</p>
%(body)s
<div class="box"><b>口径提醒</b>：本页收录的是王晰与院团合作的<b>单场 / 驻演项目</b>，<b>不计入</b>站点巡演口径「全站 64 场 = 巡演 59 + 签唱会 5」；巡演场次见 <a href="live/">演出详情目录</a> 与 <a href="map/">巡演地图</a>。</div>
<p class="meta">页面生成：%(today)s ｜ 数字全部由 <code>data/activity_master.json</code> 派生（不写死）｜ 定性内容维护于 <code>data/dongyan_projects.json</code></p>
</main>
<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->
</body>
</html>
""" % {
    "url": URL, "css": CSS, "today": TODAY,
    "jsonld": json.dumps(jsonld, ensure_ascii=False, indent=1),
    "_org": esc(proj.get("org", {}).get("name", "")),
    "orgnote": esc(proj.get("org", {}).get("note", "")),
    "body": "\n".join(parts),
}

OUT.write_text(html, encoding="utf-8")
print("[OK] %s（%d 项目｜%d 字节）" % (OUT.name, len(proj.get("projects", [])), len(html.encode("utf-8"))))
