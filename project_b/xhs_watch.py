#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xhs_watch.py —— 小红书关键词笔记“互动增速”监控（不依赖热搜 API）

每天搜索王晰关键词 → 记录笔记点赞/评论/收藏 → 与上次快照比较 → 输出增速榜。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
CRAWLER = Path(r"E:\wx\私有工具\xhs_proxy\xhs_crawler.py")
ARCHIVE = Path(r"E:\wx\私有工具\xhs_archive")
STATE = ROOT / "temp" / "xhs_watch_state.json"
OUT = ROOT / "data" / "xhs_watch.json"
KWS = ["王晰", "王晰 现场", "王晰 新歌", "王晰 巡演"]


def to_int(v):
    s = str(v or "0").strip().replace(",", "")
    try:
        if "万" in s:
            return int(float(s.replace("万", "")) * 10000)
        if "k" in s.lower():
            return int(float(s.lower().replace("k", "")) * 1000)
        return int(float(s))
    except Exception:
        return 0


def main():
    subprocess.run([sys.executable, "-X", "utf8", str(CRAWLER),
                    "--keywords", ",".join(KWS), "--pages", "1"], timeout=600)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    now = datetime.now()
    rows = []
    for m in ARCHIVE.rglob("meta.json"):
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
        except Exception:
            continue
        txt = " ".join([str(d.get("detail_desc") or ""), str(d.get("desc") or ""), str(d.get("title") or "")])
        if "王晰" not in txt:
            continue
        ds = str(d.get("date") or "")[:10]
        if ds < (now.date().replace(day=1)).isoformat():
            continue
        nid = str(d.get("note_id") or "").split("#")[0]
        if len(nid) < 24:
            continue
        st = d.get("stats") or {}
        likes, comments = to_int(st.get("likes")), to_int(st.get("comments"))
        prev = state.get(nid)
        growth = None
        if prev:
            hours = max(0.5, (now - datetime.fromisoformat(prev["t"])).total_seconds() / 3600)
            growth = round(((likes + comments) - (prev["likes"] + prev["comments"])) / hours, 1)
        state[nid] = {"likes": likes, "comments": comments, "t": now.isoformat(timespec="seconds"),
                      "date": ds, "desc": txt[:60]}
        rows.append({"id": nid, "desc": txt[:60], "date": ds, "likes": likes, "comments": comments,
                     "growth_per_hour": growth,
                     "url": "https://www.xiaohongshu.com/explore/%s?xsec_token=%s&xsec_source=pc_search" % (nid, d.get("xsec_token") or "")})
    uniq = {}
    for r in rows:
        k = r["id"]
        if k not in uniq or (r["likes"] + r["comments"]) > (uniq[k]["likes"] + uniq[k]["comments"]):
            uniq[k] = r
    rows = list(uniq.values())
    rows.sort(key=lambda x: (-(x["growth_per_hour"] or -1), -(x["likes"] + x["comments"])))
    OUT.write_text(json.dumps({"generated_at": now.strftime("%Y-%m-%d %H:%M"), "notes": rows[:30]}, ensure_ascii=False, indent=1), encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    hot = [r for r in rows if r["growth_per_hour"] and r["growth_per_hour"] >= 30][:3]
    if hot:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify
        body = "".join("<p><b>%s</b>（+%s/小时）<br>%s<br><a href='%s'>笔记</a></p>" %
                       (r["desc"][:30], r["growth_per_hour"], r["desc"][:80], r["url"]) for r in hot)
        notify.record("小红书增速：%d 条笔记在涨" % len(hot), body, category="小红书监控", source="xhs_watch")
    print("笔记", len(rows), "增速>=30", len(hot), "→", OUT)


if __name__ == "__main__":
    main()
