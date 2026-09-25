# -*- coding: utf-8 -*-
"""王晰知识库构建器：统一 实体/事实/关系 三层数据（第一性原理，幂等可复用）

输入（只读，均来自站点数据层）：
  data/timeline.json  data/setlists.json  data/cities.json  data/albums.json
  data/songs_meta.json  entity_index.json  data/live_repos.json  data/quotes.json
  data/tour/*.json  tavern/tavern_transcripts.json
输出：
  data/kb/entities.json / facts.json / relations.json / kb_digest.md / manifest.json
用法：
  python project_b/build_kb_graph.py           # 全量重建（幂等）+ 问答库扩充
  python project_b/build_kb_graph.py --no-qa   # 跳过 qa_bank 扩充
设计：docs/知识库设计_第一性原理.md
"""
import argparse, io, json, re, sys
from datetime import datetime
from pathlib import Path
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from song_names import canon  # noqa: E402

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
OUT = DATA / "kb"
CITY_PY = {"重庆": "chongqing", "北京": "beijing", "上海": "shanghai", "广州": "guangzhou",
           "深圳": "shenzhen", "南京": "nanjing", "杭州": "hangzhou", "武汉": "wuhan",
           "长沙": "changsha", "成都": "chengdu", "南昌": "nanchang", "三亚": "sanya",
           "郑州": "zhengzhou", "昆明": "kunming", "南宁": "nanning", "延边": "yanbian",
           "澳门": "macao", "苏州": "suzhou", "乌鲁木齐": "wulumuqi", "伊宁": "yining",
           "舟山": "zhoushan", "庐山": "lushan", "莫斯科": "moscow", "河南": "henan"}
ALIASES = {"person:wangxi": ["王晰Elvis", "低音炮", "Low C", "晰哥", "王晰老师", "王晰"],
           "person:studio": ["晰息相关Elvis", "王晰工作室"]}

# 来源登记表（2026-09-13 第八阶段）：facts.json 每条事实的 source 字段在此登记
# 对应的公开 URL 与来源类型，使单条事实可被外部读者/爬虫直接追溯。
SITE = "https://wx409.github.io"
SOURCE_REGISTRY = {
    "timeline.json": (SITE + "/history.html", "站内数据·生涯时间轴"),
    "songs_meta.json": (SITE + "/works.html", "站内数据·作品元数据"),
    "live_repos.json": (SITE + "/live.html", "站内数据·现场repo"),
    "albums.json": (SITE + "/data/albums.json", "站内数据·专辑发行核验"),
    "quotes.json": (SITE + "/history.html", "站内数据·语录档案"),
    "analyze_audience_comments": (SITE + "/live-reviews.html", "站内数据·观众评论分析"),
}


def load(p, fb=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return fb


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[写] %s" % name)


def show_id(date, city):
    return "show:%s-%s" % (date, CITY_PY.get(city, city))


class KB:
    def __init__(self):
        self.entities, self.facts, self.relations = {}, [], []
        self.fact_n = 0

    def ent(self, eid, etype, name, attrs=None):
        if eid not in self.entities:
            self.entities[eid] = {"type": etype, "name": name,
                                  "aliases": ALIASES.get(eid, []), "attrs": attrs or {}}
        return eid

    def fact(self, subject, prop, value, valid_from="", valid_to="", source="", conf=0.7):
        self.fact_n += 1
        # 2026-09-13 瘦身 2.0 第八阶段：每条原子事实补 source_url + source_type，
        # 使 facts.json 单条即可追溯（此前只有 source 文件名，外部读者无法定位）。
        s_url, s_type = SOURCE_REGISTRY.get(source, ("", "站内数据"))
        self.facts.append({"id": "f%04d" % self.fact_n, "subject": subject, "property": prop,
                           "value": value, "valid_from": valid_from, "valid_to": valid_to,
                           "source": source, "source_url": s_url, "source_type": s_type,
                           "confidence": round(conf, 2)})

    def rel(self, src, rtype, tgt, context="", ref=""):
        self.relations.append({"source": src, "type": rtype, "target": tgt,
                               "context": context, "source_ref": ref})


def build():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    OUT.mkdir(parents=True, exist_ok=True)
    kb = KB()

    # ---- 王晰本体 ----
    kb.ent("person:wangxi", "person", "王晰")
    kb.ent("person:studio", "person", "王晰Elvis-晰息相关")
    kb.fact("person:wangxi", "birth", "1985-04-09 出生于辽宁省营口市", "1985-04-09", "", "timeline.json", 0.95)

    # ---- 0) qa_factoids.json：由「问答短答」迁入的结构化事实（2026-09-14）----
    # 迁移理由：常识性短答（出生地/奖项/何时加入某团/专辑有哪些）不需要问答形式，
    # AI 直接取结构化事实更可靠。注入后，expand_qa 会把这些问句从自动生成集中移除。
    factoid_qs = []
    for fo in (load(DATA / "qa_factoids.json", {}) or {}).get("factoids", []):
        kb.facts.append({
            "id": "f%04d" % (kb.fact_n + 1), "subject": fo["subject"], "property": fo["property"],
            "value": fo["value"], "valid_from": fo.get("valid_from", ""),
            "valid_to": fo.get("valid_to", ""), "source": fo.get("source_file", ""),
            "source_url": fo.get("source_url", ""), "source_type": fo.get("source_type", ""),
            "confidence": fo.get("confidence", 0.9),
        })
        kb.fact_n += 1
        if fo.get("replaces_question"):
            factoid_qs.append(fo["replaces_question"])
    if factoid_qs:
        print("[facts] 由问答迁入结构化事实 %d 条" % len(factoid_qs))

    # ---- 1) timeline.json → 生涯事实 + event 实体 ----
    tl = load(DATA / "timeline.json", [])
    for i, e in enumerate(tl):
        eid = "event:t%03d" % i
        kb.ent(eid, "event", e.get("title", ""), {"date": e.get("date"), "type": e.get("type")})
        conf = 0.95 if e.get("source") in ("公开资料", "官方") or e.get("stage") else 0.8
        kb.fact("person:wangxi", "career_%s" % e.get("type", "event"), e.get("title", ""),
                e.get("date", ""), "", "timeline.json", conf)
        kb.rel("person:wangxi", "has_event", eid, e.get("type", ""), "timeline.json")

    # ---- 2) setlists.json → show 实体 + song→show 关系 ----
    sl = load(DATA / "setlists.json", {}) .get("setlists", {})
    for date, s in sl.items():
        city = s.get("city") or s.get("scene", "")
        sid = show_id(date, city)
        kb.ent(sid, "show", "%s %s %s" % (date, city, s.get("theme", "")),
               {"venue": s.get("venue"), "tour": s.get("tour"), "theme": s.get("theme")})
        if s.get("venue"):
            kb.ent("venue:%s" % s["venue"], "venue", s["venue"])
            kb.rel(sid, "held_at", "venue:%s" % s["venue"], date, "setlists.json")
        if city:
            kb.ent("city:%s" % city, "city", city)
            kb.rel(sid, "in_city", "city:%s" % city, date, "setlists.json")
        if s.get("tour"):
            kb.ent("tour:%s" % s["tour"], "tour", s["tour"])
            kb.rel(sid, "part_of", "tour:%s" % s["tour"], s.get("theme", ""), "setlists.json")
        for song in s.get("songs", []):
            t = song.get("title", "")
            if not t:
                continue
            kb.ent("song:%s" % canon(t), "song", t)
            kb.rel("song:%s" % canon(t), "performed_in", sid, "第%s首" % song.get("order", "?"), "setlists.json")

    # ---- 3) cities.json → 22城 show 事实（补 tour_num/live_url） ----
    cs = load(DATA / "cities.json", {}).get("cities", {})
    for city, c in cs.items():
        kb.ent("city:%s" % city, "city", city, {"coord": c.get("coord")})
        for sh in c.get("shows", []):
            sid = show_id(sh.get("date", ""), city)
            kb.ent(sid, "show", "%s %s %s" % (sh.get("date"), city, sh.get("theme", "")),
                   {"venue": sh.get("venue"), "tour": sh.get("tour"), "tour_num": sh.get("tour_num"),
                    "theme": sh.get("theme"), "cancelled": sh.get("cancelled")})
            if sh.get("venue"):
                kb.ent("venue:%s" % sh["venue"], "venue", sh["venue"])
                kb.rel(sid, "held_at", "venue:%s" % sh["venue"], sh.get("date"), "cities.json")
            if sh.get("tour"):
                kb.ent("tour:%s" % sh["tour"], "tour", sh["tour"])
                kb.rel(sid, "part_of", "tour:%s" % sh["tour"], sh.get("theme", ""), "cities.json")
            if sh.get("cancelled"):
                kb.fact("person:wangxi", "show_cancelled", "%s %s 取消" % (sh["date"], city),
                        sh.get("date"), "", "cities.json", 0.9)

    # ---- 4) albums.json → 专辑实体 ----
    for a in load(DATA / "albums.json", {}).get("albums", []):
        name = a.get("name") or a.get("title") or ""
        if not name:
            continue
        kb.ent("album:%s" % name, "album", name)
        kb.fact("person:wangxi", "released_album", name, a.get("release") or a.get("date") or "",
                "", "albums.json", 0.9)
        kb.rel("person:wangxi", "released", "album:%s" % name, "", "albums.json")

    # ---- 5) songs_meta.json → 歌曲实体 + 统计事实 ----
    for name, m in load(DATA / "songs_meta.json", {}).get("songs", {}).items():
        kb.ent("song:%s" % canon(name), "song", name, {"album": m.get("album")})
        if m.get("show_count"):
            kb.fact("song:%s" % canon(name), "performed_count", m["show_count"], "", "", "songs_meta.json", 0.8)
        if m.get("cities"):
            kb.fact("song:%s" % canon(name), "performed_cities", "、".join(m["cities"]), "", "", "songs_meta.json", 0.8)
        if m.get("album"):
            kb.rel("song:%s" % canon(name), "belongs_to_album", "album:%s" % m["album"], "", "songs_meta.json")

    # ---- 6) live_repos.json → 媒体/报道实体 + 关系 ----
    repos = load(DATA / "live_repos.json", {}).get("repos", {})
    for date, lst in repos.items():
        for i, r in enumerate(lst):
            mid = "media:%s-%02d" % (date, i)
            conf = {"official": 0.95, "verified": 0.9, "single": 0.7}.get(r.get("level"), 0.7)
            kb.ent(mid, "media", r.get("title", ""), {"platform": r.get("platform"), "level": r.get("level")})
            kb.fact("person:wangxi", "media_coverage", r.get("title", ""), date, "",
                    "live_repos.json", conf)
            sid = show_id(date, "广州" if "广州" in (r.get("platform") or "") else "".join(
                [c for c in "北京上海广州深圳南京杭州武汉长沙成都南昌三亚郑州昆明南宁延边澳门苏州乌鲁木齐伊宁舟山庐山莫斯科" if c in (r.get("title") or "")]))
            if sid in kb.entities:
                kb.rel(mid, "covers", sid, r.get("platform", ""), "live_repos.json")

    # ---- 7) quotes.json + tour/*.json → 金句实体 + 关系 ----
    for q in load(DATA / "quotes.json", {}).get("quotes", []):
        date = q.get("date", "")
        city = q.get("city", "")
        qid = "quote:%s-%s" % (date, q.get("source_transcript_id", "?"))
        kb.ent(qid, "quote", q.get("text", "")[:40], {"scene": q.get("scene"), "verified": q.get("verified")})
        if q.get("verified"):
            kb.fact("person:wangxi", "quoted", q.get("text", ""), date, "", "quotes.json", 0.9)
        sid = show_id(date, city)
        if sid in kb.entities:
            kb.rel(qid, "said_at", sid, q.get("scene", ""), "quotes.json")
        elif city:
            kb.ent(sid, "show", "%s %s" % (date, city))
            kb.rel(qid, "said_at", sid, q.get("scene", ""), "quotes.json")

    # ---- 8) tavern_transcripts.json → 小酒馆期次 ----
    tt = load(ROOT / "tavern" / "tavern_transcripts.json", {})
    for k, ep in (tt.get("episodes") or {}).items():
        eid = "tavern:%s" % k
        kb.ent(eid, "tavern", ep.get("theme") or ep.get("category") or k,
               {"part": ep.get("part"), "episode_num": ep.get("episode_num")})
        kb.rel("person:wangxi", "hosts", eid, ep.get("category", ""), "tavern_transcripts.json")

    # ---- 9) 观众评论分析维度（analyze_audience_comments.py 产出，论文/分析/档案维度）----
    import glob as _glob
    an_dir = ROOT / "temp" / "audience_analysis"
    n_an = 0
    for ap in sorted(_glob.glob(str(an_dir / "*.json"))):
        try:
            an = json.loads(Path(ap).read_text(encoding="utf-8"))
        except Exception:
            continue
        date, city = an.get("date", ""), an.get("city", "")
        if not date:
            continue
        sid = show_id(date, city)
        kb.ent(sid, "show", "%s %s" % (date, city))
        st = an.get("stats") or {}
        total = st.get("total") or 0
        if total:
            kb.fact(sid, "audience_comments_total", total, date, "", "analyze_audience_comments", 0.8)
        dims = st.get("dimensions") or {}
        if dims:
            kb.fact(sid, "audience_dim_top", "、".join("%s(%d)" % (k, v) for k, v in sorted(dims.items(), key=lambda x: -x[1])[:3]),
                    date, "", "analyze_audience_comments", 0.8)
            kb.fact(sid, "audience_dim_dist", "；".join("%s %d" % (k, v) for k, v in sorted(dims.items(), key=lambda x: -x[1])),
                    date, "", "analyze_audience_comments", 0.8)
        song_top = st.get("song_top") or []
        if song_top:
            kb.fact(sid, "audience_song_top", "、".join("%s(%d次)" % (s[0], s[1]) for s in song_top[:5]),
                    date, "", "analyze_audience_comments", 0.8)
        pf = st.get("platforms") or {}
        if pf:
            kb.fact(sid, "audience_platforms", "；".join("%s %d" % (k, v) for k, v in pf.items()),
                    date, "", "analyze_audience_comments", 0.8)
        n_an += 1
    if n_an:
        print("[评论维度] %d 个场次分析结果入 KB（评论数/评价维度/歌曲提及/平台分布）" % n_an)

    # ---- 组织归属（从 timeline 事件推导 valid_from/valid_to） ----
    org_rules = [("海政文工团", "2011", "2018"), ("乐华娱乐", "2019-04-09", "2024"),
                 ("中国东方演艺集团", "2025", "")]
    for org, vf, vt in org_rules:
        kb.ent("org:%s" % org, "org", org)
        kb.fact("person:wangxi", "member_of", org, vf, vt, "timeline.json", 0.95)
        kb.rel("person:wangxi", "belongs_to", "org:%s" % org, "%s→%s" % (vf, vt or "至今"), "timeline.json")

    save("entities.json", {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                           "entity_count": len(kb.entities), "entities": kb.entities})
    save("facts.json", kb.facts)
    save("relations.json", kb.relations)
    save("manifest.json", {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                           "facts": len(kb.facts), "relations": len(kb.relations),
                           "entities_by_type": {t: sum(1 for e in kb.entities.values() if e["type"] == t)
                                                for t in sorted(set(e["type"] for e in kb.entities.values()))},
                           "sources": ["timeline.json", "setlists.json", "cities.json", "albums.json",
                                       "songs_meta.json", "entity_index.json", "live_repos.json",
                                       "quotes.json", "tour/*.json", "tavern_transcripts.json"]})
    build_digest(kb)
    print("[KB] 实体 %d / 事实 %d / 关系 %d" % (len(kb.entities), len(kb.facts), len(kb.relations)))
    return kb


def build_digest(kb):
    """面向 LLM/GEO 的纯文本摘要：生涯事实按时间排序 + 关键统计"""
    L = ["# 王晰知识库摘要（自动生成）", "",
         "> 华语流行男低音歌手王晰（1985-04-09，辽宁营口）· 数字档案 · 生成 %s" % datetime.now().strftime("%Y-%m-%d"), "",
         "## 生涯里程碑（按时间）"]
    events = sorted([f for f in kb.facts if f["subject"] == "person:wangxi" and f["property"].startswith("career_")],
                    key=lambda f: f["valid_from"])
    for f in events:
        L.append("- %s：%s" % (f["valid_from"] or "?", f["value"]))
    L += ["", "## 机构归属时间线"]
    for f in kb.facts:
        if f["property"] == "member_of":
            L.append("- %s（%s→%s）" % (f["value"], f["valid_from"], f["valid_to"] or "至今"))
    songs = [e for e in kb.entities.values() if e["type"] == "song"]
    shows = [e for e in kb.entities.values() if e["type"] == "show"]
    albums = [e for e in kb.entities.values() if e["type"] == "album"]
    taverns = [e for e in kb.entities.values() if e["type"] == "tavern"]
    L += ["", "## 体量", "- 歌曲 %d 首；专辑 %d 张；演出场次 %d 场；小酒馆 %d 期" %
          (len(songs), len(albums), len(shows), len(taverns))]
    vq = [f for f in kb.facts if f["property"] == "quoted"]
    if vq:
        L += ["", "## 已核实金句精选"]
        for f in vq[:12]:
            L.append("- %s（%s）" % (f["value"], f["valid_from"]))
    L += ["", "## 数据资产", "- 平台指数日频 143.5万行；微博语料 1522+1059 条；巡演歌单单一事实源；详见 E:\\wx 索引"]
    (OUT / "kb_digest.md").write_text("\n".join(L), encoding="utf-8")
    print("[写] kb_digest.md（%d 行）" % len(L))


def expand_qa(kb):
    """从事实层规则生成问答（零 LLM），并入 qa_bank.json（幂等，按 question 去重）"""
    qa = load(DATA / "qa_bank.json", {"items": []})
    # 幂等自愈：清除上一轮自动生成条目后重建（人工条目保留）
    items = [i for i in qa.get("items", []) if i.get("category") != "知识库自动生成"]
    # 2026-09-14：人工条目答案里若残留 markdown 星号，在 HTML 里会原样显示
    # （如「王晰**未开过个人演唱会**」）——统一在此净化，避免逐条手改。
    for _it in items:
        if isinstance(_it.get("answer"), str) and "**" in _it["answer"]:
            _it["answer"] = _it["answer"].replace("**", "")
    seen = {i.get("question") for i in items}
    new = []
    facts = kb.facts
    born = next((f for f in facts if f["property"] == "birth"), None)
    if born:
        new.append(("王晰出生于哪里？", "%s（%s）" % (born["value"], born["source"])))
    for f in facts:
        if f["property"] == "career_award":
            new.append(("王晰获得过哪些奖项？", f["value"]))
        if f["property"] == "member_of":
            new.append(("王晰何时加入%s？" % f["value"],
                        "%s（%s→%s，%s）" % (f["value"], f["valid_from"], f["valid_to"] or "至今", f["source"])))
    albums = sorted({f["value"] for f in facts if f["property"] == "released_album"})
    if albums:
        new.append(("王晰的专辑有哪些？", "；".join(albums)))
    # 2026-09-14（方案 A 全做）：不再生成 289 条「某歌在哪些演出唱过」问答。
    # 理由（第一性原理）：场次列表天然是**表**（行=歌，列=日期/城市/巡次），
    # 套上「问+答」不增加信息，只增加模板风险，且 78/289 答案不足 20 字。
    # 原数据一条不丢，改由 data/songs_shows_index.json + /songs-shows.html 承载
    # （生成器 project_b/build_songs_shows.py，数据源同为 data/setlists.json）。
    rel = kb.relations
    ents = kb.entities
    _ = (rel, ents)   # 保留引用，供后续其他规则使用
    shows_by_tour = {}
    for e in kb.entities.values():
        if e["type"] == "show" and e["attrs"].get("tour"):
            shows_by_tour.setdefault(e["attrs"]["tour"], []).append(e["name"])
    # 2026-09-14：只对真正的巡次（一巡…六巡）生成「有哪些场次」问答。
    # 「签唱会」「其他」不是巡次，硬套「X王晰巡演有哪些场次？」模板会产生
    # 「签唱会王晰巡演有哪些场次？」这类错误问题；它们的场次改由
    # songs_shows（歌曲×场次索引表）与 tour 分组表承载。
    for tour, lst in sorted(shows_by_tour.items()):
        if not re.match(r"^(一巡|二巡|三巡|四巡|五巡|六巡)$", str(tour)):
            continue
        new.append(("%s王晰巡演有哪些场次？" % tour, "；".join(sorted(lst))))
    added = 0
    # 已被 data/qa_factoids.json 迁为结构化事实的问句，不再作为「问答」生成
    migrated = {fo.get("replaces_question") for fo in
                (load(DATA / "qa_factoids.json", {}) or {}).get("factoids", [])
                if fo.get("replaces_question")}
    for q, a in new:
        if q in seen or q in migrated:
            continue
        # 答案里残留的 markdown 星号在 HTML 里会原样显示（如「王晰**未开过个人演唱会**」）
        a = str(a).replace("**", "")
        items.append({"question": q, "answer": a,
                      "category": "知识库自动生成", "source": "data/kb/facts.json",
                      "generated_at": datetime.now().strftime("%Y-%m-%d")})
        seen.add(q)
        added += 1
    qa["items"] = items
    qa["meta"]["count"] = len(items)
    (DATA / "qa_bank.json").write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[QA] 新增 %d 条（累计 %d 条）-> data/qa_bank.json" % (added, len(items)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-qa", action="store_true")
    a = ap.parse_args()
    kb = build()
    if not a.no_qa:
        expand_qa(kb)
