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
        self.facts.append({"id": "f%04d" % self.fact_n, "subject": subject, "property": prop,
                           "value": value, "valid_from": valid_from, "valid_to": valid_to,
                           "source": source, "confidence": round(conf, 2)})

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
            kb.ent("song:%s" % t, "song", t)
            kb.rel("song:%s" % t, "performed_in", sid, "第%s首" % song.get("order", "?"), "setlists.json")

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
        kb.ent("song:%s" % name, "song", name, {"album": m.get("album")})
        if m.get("show_count"):
            kb.fact("song:%s" % name, "performed_count", m["show_count"], "", "", "songs_meta.json", 0.8)
        if m.get("cities"):
            kb.fact("song:%s" % name, "performed_cities", "、".join(m["cities"]), "", "", "songs_meta.json", 0.8)
        if m.get("album"):
            kb.rel("song:%s" % name, "belongs_to_album", "album:%s" % m["album"], "", "songs_meta.json")

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
    rel = kb.relations
    ents = kb.entities
    for e in ents.values():
        if e["type"] == "song":
            shows = [ents.get(r["target"], {}).get("name", r["target"])
                     for r in rel if r["source"] == "song:%s" % e["name"] and r["type"] == "performed_in"]
            if shows:
                new.append(("王晰的歌曲《%s》在哪些演出唱过？" % e["name"], "；".join(sorted(set(shows))[:8])))
    shows_by_tour = {}
    for e in kb.entities.values():
        if e["type"] == "show" and e["attrs"].get("tour"):
            shows_by_tour.setdefault(e["attrs"]["tour"], []).append(e["name"])
    for tour, lst in shows_by_tour.items():
        new.append(("%s王晰巡演有哪些场次？" % tour, "；".join(sorted(lst))))
    added = 0
    for q, a in new:
        if q in seen:
            continue
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
