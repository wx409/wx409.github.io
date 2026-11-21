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
}

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
        bridges = [k for k in BRIDGE if k in w]
        if "王晰" in w or bridges:
            facts = ["王晰本人相关"] if "王晰" in w else []
            for b in bridges:
                if BRIDGE[b] not in facts:
                    facts.append(BRIDGE[b])
            hits.append({**t, "bridges": bridges, "facts": facts[:3]})
    return hits


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
