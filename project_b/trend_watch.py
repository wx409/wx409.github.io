#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""trend_watch.py —— 王晰热点雷达（零 token，纯规则）

每 10 分钟扫微博/抖音/B站热榜，命中「王晰」或桥接词（音乐剧/男低音/OST/央视/新疆/苏州…）时：
  1) 写站点通知（notifications.html）
  2) 写 data/trend_alerts.json（公开，只含热词/排名/桥接事实，不含原文）
  3) 本地日志 temp/trend_watch.log

用法：
  python -X utf8 project_b\\trend_watch.py --dry
  python -X utf8 project_b\\trend_watch.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
import notify  # noqa: E402

STATE = ROOT / "temp" / "trend_watch_state.json"
OUT = ROOT / "data" / "trend_alerts.json"
LOG = ROOT / "temp" / "trend_watch.log"

BRIDGE = {
    "音乐剧": "《草原之夜——来自可克达拉的歌谣》2026-11-20/21 苏州湾大剧院，王晰饰垦荒者；《沉响与长歌》2026-10-09/10 北京天桥。",
    "舞台剧": "同上：王晰参演歌舞剧《草原之夜》。",
    "男低音": "王晰：72 首录音室曲目实测最低稳定音 B1 61.5Hz（《静止了的夜晚》）。",
    "低音炮": "同上：B1 61.5Hz 为稳定音口径，非单帧读数。",
    "低音": "同上：男低音声部，姚峰称「流行圈内恐怕就是孤本」。",
    "美声": "王晰出身声乐科班，青歌赛/金钟奖双冠。",
    "歌剧": "王晰参演歌舞剧《草原之夜》，并跨界音乐剧舞台。",
    "OST": "王晰 OST 列表：《小丈夫》《最远的心跳》《梦回长安》《绝不放手》等。",
    "影视原声": "同上：王晰演唱多部剧集 OST。",
    "央视": "王晰多次登央视舞台；2026-11-16 CMG媒体之夜与李佳薇合唱亚太歌曲串烧。",
    "春晚": "王晰多次参与央视/卫视晚会。",
    "中秋": "王晰多次参与中秋/晚会类节目。",
    "晚会": "王晰晚会记录见时间轴；2026-11-16 CMG媒体之夜深圳。",
    "声入人心": "王晰是 2018《声入人心》成员。",
    "新疆": "《草原之夜》故事发生地可克达拉在新疆伊犁。",
    "伊犁": "同上：可克达拉属新疆伊犁。",
    "可克达拉": "《草原之夜——来自可克达拉的歌谣》剧目原型地。",
    "苏州": "2026-11-20/21 苏州湾大剧院《草原之夜》。",
    "剧院": "王晰六轮巡演覆盖 22 城剧院/音乐厅。",
    "乐华": "王晰为乐华娱乐旗下歌手。",
    "蓝色大提琴": "王晰代表作《蓝色大提琴》。",
    "草原之夜": "2026-11-20/21 苏州站；王晰饰垦荒者。",
    "音域": "72 首录音室实测：跨度中位 2.23 八度。",
    "声乐": "王晰声乐科班出身；青歌赛/金钟奖双冠。",
    "音乐现场": "王晰现场层：巡演 59 场 + 签唱会 5 场；现场稳定音与录音室差异不显著（p=0.197）。",
    "音乐Live": "同上：王晰现场层实测覆盖 888 条素材。",
    "演唱会": "王晰六轮巡演 59 场 / 22 城；《沉响与长歌》2026-10-09/10 北京。",
    "音乐节": "王晰有音乐节/拼盘演出记录，详见时间轴与 live 页。",
    "巡演": "王晰六轮巡演 59 场 / 22 城。",
    "现场": "王晰现场层：888 条素材、现场稳定音中位 2.69 八度。",
    "Live": "同上：现场层与录音室同管线、同口径对照。",
    "舞台": "王晰舞台记录：巡演、晚会、音乐剧《草原之夜》。",
}

# 宽泛词：单独命中不提醒，必须叠加「王晰/歌曲/音乐语境」
BROAD = {"音乐现场", "音乐Live", "演唱会", "音乐节", "巡演", "现场", "Live", "舞台"}
_CTX = ("音乐", "唱", "歌", "舞台", "翻唱", "原唱", "版本", "现场", "Live")


def load_songs():
    names = set()
    try:
        for x in json.loads((ROOT / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))["songs"]:
            if x.get("title"):
                names.add(x["title"])
    except Exception:
        pass
    try:
        for k in json.loads((ROOT / "data" / "songs_meta.json").read_text(encoding="utf-8"))["songs"]:
            if k:
                names.add(k)
    except Exception:
        pass
    try:
        sl = json.loads((ROOT / "data" / "setlists.json").read_text(encoding="utf-8")).get("setlists")
        seq = sl.values() if isinstance(sl, dict) else (sl or [])
        for show in seq:
            for s in (show.get("songs") or []) if isinstance(show, dict) else []:
                if isinstance(s, str) and s:
                    names.add(s)
    except Exception:
        pass
    return sorted({n for n in names if len(n) >= 2}, key=len, reverse=True)


SONGS = load_songs()

VIDEO_INDEX = Path(r"E:\wx\私有工具\video_index.json")
_VC = None


def video_counts():
    global _VC
    if _VC is None:
        try:
            d = json.loads(VIDEO_INDEX.read_text(encoding="utf-8"))
            _VC = {k: len(v) for k, v in (d.get("by_song") or {}).items()}
        except Exception:
            _VC = {}
    return _VC

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
WB = Path(r"E:\wx\index_records\wb.txt")
DY = Path(r"E:\wx\index_records\douyin_cookie_raw.txt")


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_json(url, cookie="", referer=""):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer, "Cookie": cookie})
    return json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "replace"))


def fetch_weibo():
    ck = WB.read_text(encoding="utf-8", errors="ignore").strip() if WB.exists() else ""
    j = get_json("https://weibo.com/ajax/side/hotSearch", ck, "https://weibo.com/")
    out = []
    for i, x in enumerate(((j.get("data") or {}).get("realtime") or [])[:50]):
        w = x.get("word") or ""
        if w:
            out.append({"source": "微博", "word": w, "rank": i + 1,
                        "url": "https://s.weibo.com/weibo?q=%s" % __import__("urllib.parse", fromlist=["quote"]).quote(w)})
    return out


def fetch_douyin():
    ck = DY.read_text(encoding="utf-8", errors="ignore").strip() if DY.exists() else ""
    j = get_json("https://www.douyin.com/aweme/v1/web/hot/search/list/", ck, "https://www.douyin.com/")
    out = []
    for x in ((j.get("data") or {}).get("word_list") or [])[:50]:
        w = x.get("word") or ""
        if w:
            out.append({"source": "抖音", "word": w, "rank": int(x.get("position") or 0),
                        "url": "https://www.douyin.com/search/%s" % __import__("urllib.parse", fromlist=["quote"]).quote(w)})
    return out


def fetch_bili():
    j = get_json("https://api.bilibili.com/x/web-interface/search/square?limit=30")
    out = []
    for i, x in enumerate(((j.get("data") or {}).get("trending") or {}).get("list") or []):
        w = x.get("keyword") or ""
        if w:
            out.append({"source": "B站", "word": w, "rank": i + 1,
                        "url": "https://search.bilibili.com/all?keyword=%s" % __import__("urllib.parse", fromlist=["quote"]).quote(w)})
    return out


def match(topics):
    hits = []
    for t in topics:
        w = t["word"]
        direct = "王晰" in w
        specific = [k for k in BRIDGE if k not in BROAD and k in w]
        broad = [k for k in BROAD if k.lower() in w.lower()]
        songs = []
        for s in SONGS:
            if s in w and (len(s) >= 4 or direct or any(c in w for c in _CTX)):
                songs.append(s)
            if len(songs) >= 2:
                break
        if not (direct or specific or songs or broad):
            continue
        # 宽泛词单独命中不提醒：必须叠加王晰/具体桥接/歌曲
        if broad and not (direct or specific or songs):
            continue
        facts = ["王晰本人相关"] if direct else []
        for b in specific:
            if BRIDGE[b] not in facts:
                facts.append(BRIDGE[b])
        for s in songs:
            n = video_counts().get(s, 0)
            facts.append("王晰演唱/原唱《%s》；本地视频库 %d 条。" % (s, n) if n
                         else "王晰演唱/原唱《%s》；站内可查歌曲页与现场记录。" % s)
        if not facts:
            facts.append("王晰现场/巡演记录见站内 live 页。")
        hits.append({**t, "bridges": specific + broad, "songs": songs, "facts": facts[:3]})
    return hits


DRAFTS = Path(r"E:\wx\私有工具\trend_drafts")


def _slug(s):
    return re.sub(r"[^\w\u4e00-\u9fa5\-]+", "-", str(s)).strip("-")[:40]


def write_drafts(hits):
    """命中热点后写 3 个角度草稿（模板化、零 token），供人审。"""
    try:
        DRAFTS.mkdir(parents=True, exist_ok=True)
        for h in hits[:3]:
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            fn = DRAFTS / ("%s_%s.md" % (ts, _slug(h["word"])))
            if fn.exists():
                continue
            facts = "\n".join("- " + f for f in h.get("facts") or [])
            songs = "、".join(h.get("songs") or []) or "—"
            body = """---
date: {ts}
hot: {hot}
source: {src} 第{rank}
bridges: {br}
songs: {songs}
status: draft
---
# 热点草稿：{hot}

## 角度 1｜数据派
**标题**：从「{hot}」说起：王晰的低音到底低到哪
**开头 100 字**：热榜上出现「{hot}」，很多人第一反应是“男低音是不是噱头”。王晰的录音室实测给出的是可复核的数字：最低稳定音 B1 61.5Hz、低音主区 B1–D2，全部低于男低音下限 E2。
**证据**：
{facts}

## 角度 2｜故事派
**标题**：他为什么把「{hot}」唱成这样
**开头 100 字**：同一副嗓子，在录音室是精密仪器，在舞台上是有体温的叙事。王晰的现场层与录音室同管线对照，最低稳定音差异不显著（p=0.197）——他不是“录音棚歌手”。
**证据**：
{facts}

## 角度 3｜对比派
**标题**：「{hot}」里的男低音，和录音室里的王晰
**开头 100 字**：把热榜里的片段和王晰的 72 首录音室全量放在一起看，差异不在“能不能唱低”，而在“低下去之后还能不能稳住”。跨度中位 2.23 个八度、音符内稳定性中位 7 音分，是这条对比线的硬指标。
**证据**：
{facts}

## 本地素材
- 相关歌曲：{songs}
- 本地视频：{vc} 条（索引 `E:\\wx\\私有工具\\video_index.json`）
- 原热点：{url}

## 风险与口径
- 热点与王晰必须有可验证桥接，无桥接不发；
- 音域只用「最低稳定音」，不写单帧/瞬时读数；
- 不蹭灾难/社会新闻；评论限量、人审后发。
""".format(ts=datetime.now().strftime("%Y-%m-%d %H:%M"), hot=h["word"], src=h["source"],
           rank=h["rank"], br="、".join(h.get("bridges") or []) or "—",
           songs=songs, facts=facts,
           vc=sum(video_counts().get(s, 0) for s in (h.get("songs") or [])),
           url=h.get("url") or "")
            fn.write_text(body, encoding="utf-8")
            log("草稿 %s" % fn.name)
    except Exception as e:
        log("[warn] 草稿写入失败：%s" % str(e)[:80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    topics, fail = [], 0
    for fn in (fetch_weibo, fetch_douyin, fetch_bili):
        try:
            topics += fn()
        except Exception as e:
            fail += 1
            log("[warn] %s 失败：%s" % (fn.__name__, str(e)[:80]))
    state["fail"] = fail
    if fail >= 3:
        state["cooldown_until"] = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        log("三源全失败，冷却 30 分钟")
        return 0
    if state.get("cooldown_until") and datetime.now() < datetime.strptime(state["cooldown_until"], "%Y-%m-%d %H:%M:%S"):
        log("冷却中，跳过")
        return 0

    hits = match(topics)
    last = state.setdefault("last", {})
    new_hits = []
    now = datetime.now()
    for h in hits:
        key = h["source"] + "|" + h["word"]
        prev = last.get(key) or {}
        improved = prev.get("rank") and h["rank"] and prev["rank"] - h["rank"] >= 5
        fresh = not prev or (now - datetime.fromisoformat(prev["seen"])).total_seconds() > 6 * 3600
        last[key] = {"rank": h["rank"], "seen": now.isoformat(timespec="seconds")}
        if fresh or improved:
            new_hits.append(h)
    state["ran_at"] = now.isoformat(timespec="seconds")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    # 公开快照
    OUT.write_text(json.dumps({"generated_at": now.strftime("%Y-%m-%d %H:%M"),
                               "hits": new_hits[:20]}, ensure_ascii=False, indent=1), encoding="utf-8")

    if not new_hits:
        log("热点 %d 条，命中 0（或均在去重窗口内）" % len(topics))
        return 0
    log("命中 %d 条：%s" % (len(new_hits), "；".join("%s/%s" % (h["source"], h["word"]) for h in new_hits[:5])))
    if a.dry:
        return 0
    lines = []
    for h in new_hits[:5]:
        lines.append("<p><b>%s · 第%s</b>：%s<br><span style='color:#666'>%s</span><br><a href='%s'>查看热点</a></p>"
                     % (h["source"], h["rank"], h["word"], "；".join(h["facts"]), h["url"]))
    notify.record("热点雷达：命中 %d 条（王晰相关）" % len(new_hits),
                  "".join(lines) + "<p style='color:#888'>规则：热词含「王晰」或桥接词（音乐剧/男低音/OST/央视/新疆/苏州…）；只提醒，不自动发。</p>",
                  category="热点雷达", source="trend_watch")
    write_drafts(new_hits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
