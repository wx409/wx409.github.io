#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_today.py —— 每日小作文：今天 + 最近 7 天，本地留存可作灵感库"""
from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SRC = ROOT / "data" / "bili_daily.json"
MEAS = ROOT / "data" / "bili_live_measurements_2026.json"
ALBUMS = ROOT / "data" / "archive_vocal_albums.json"
ARCHIVE = Path(r"E:\wx\私有工具\每日小作文")
HIST = ROOT / "data" / "today_history.json"
OUT = ROOT / "today.html"
JSONOUT = ROOT / "data" / "today.json"


def esc(s):
    return html.escape(str(s or ""))


def clean_title(t):
    t = str(t or "").rsplit(".mp4", 1)[0]
    t = t.split("_", 1)[-1].strip()
    return t.replace("王晰", "").strip() or t


def studio_of(title):
    try:
        songs = json.loads(ALBUMS.read_text(encoding="utf-8")).get("songs") or []
    except Exception:
        return None
    for x in songs:
        if x.get("title") and x["title"] in title:
            return x
    return None


def make_entry(d, fresh):
    day = d.get("date") or date.today().isoformat()
    items = d.get("items") or []
    measured = [x for x in items if x.get("measured")]
    measured.sort(key=lambda x: (x["measured"].get("low", {}).get("hz") or 999))
    try:
        ordinal = date.fromisoformat(day).toordinal()
    except Exception:
        ordinal = date.today().toordinal()
    if not items:
        songs = []
        try:
            songs = json.loads(ALBUMS.read_text(encoding="utf-8")).get("songs") or []
        except Exception:
            pass
        if songs:
            s = songs[ordinal % len(songs)]
            essay = [
                "今天没有新的 B站视频，翻回《%s》听了一遍。" % s.get("title"),
                "最低稳定音 %s（%sHz），单曲跨度 %s 个八度，音符内稳定性 %s 音分。" % (
                    s.get("low"), s.get("low_hz"), s.get("span_octaves"), s.get("stability_cents")),
                "这不是新发现，是旧证据重听；但每天重听一次，才知道哪些数字是真的，哪些只是当天的情绪。",
                "今天先记到这里。",
            ]
        else:
            essay = ["今天没有新的 B站视频。"]
        headline = "今天没有新的 B站视频。"
        tags = ["#王晰", "#旧档案重听"]
    else:
        live = [x for x in measured if ("直拍" in x["title"] or "点歌" in x["title"])]
        focus = min(live or measured, key=lambda x: x["measured"]["low"].get("hz") or 999) if measured else None
        openers = [
            "今天把 B站官方空间新补的 %d 条视频过了一遍，挑出 %d 条能做声学测量的。",
            "今天新收了 %d 条 B站视频，先把能测的 %d 条听完了。",
            "今天补档 %d 条，最后留下 %d 条值得做一次声学测量的。",
        ]
        essay = [openers[ordinal % len(openers)] % (len(items), len(measured))]
        if focus:
            m = focus["measured"]
            low = m.get("low") or {}
            title = clean_title(focus["title"])
            studio = studio_of(title)
            raw = None
            try:
                old = json.loads(MEAS.read_text(encoding="utf-8")).get("tracks") or []
                raw = next((x.get("f0_min_hz") for x in old if x.get("bvid") == focus.get("bvid")), None)
            except Exception:
                pass
            line = "最想先说 %s：稳定最低音落在 %s（%sHz），跨度 %s 个八度，稳定性 %s 音分。" % (
                title, low.get("note"), low.get("hz"), m.get("span"), m.get("stability"))
            if raw and low.get("hz") and raw < low.get("hz") - 5:
                line += "原始 F0 其实摸到过 %sHz，但没通过稳定音门槛——所以今天没有“新低音纪录”，只有一条“现场稳、但别拿一帧说事”的证据。" % raw
            essay.append(line)
            if studio and studio.get("low_hz"):
                essay.append("对照录音室《%s》的 %s（%sHz），这次现场稳定音更高；不是他唱不低，是完整乐队直拍本来就不适合刷最低音。" % (
                    studio.get("title"), studio.get("low"), studio.get("low_hz")))
        if len(essay) == 1:
            essay.append("今天这几条里没有特别适合单独讲的声音，先把它们留在档案里，等下次现场再对照。")
        essay.append("今天先记到这里。")
        headline = "今天补到 %d 条 B站视频，%d 条做了声学测量。" % (len(items), len(measured))
        tags = ["#王晰", "#男低音", "#今日档案"]
    return {"date": day, "fresh": fresh, "headline": headline,
            "essay": essay, "tags": tags,
            "measurements": [{"title": clean_title(x["title"]), "bvid": x.get("bvid"),
                              "low": x["measured"].get("low"), "span": x["measured"].get("span"),
                              "stability": x["measured"].get("stability")} for x in measured],
            "source": "bili_daily.json", "generated_at": d.get("generated_at") or ""}


def save_local(entry):
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / (entry["date"] + ".json")).write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# %s 今天，听王晰听到什么" % entry["date"], "", "> " + entry["headline"], ""]
    lines += [p + "\n" for p in entry.get("essay") or []]
    lines += ["## 声学测量", ""]
    for m in entry.get("measurements") or []:
        low = m.get("low") or {}
        lines.append("- 《%s》 %s · 稳定最低 %s %sHz · 跨度 %s 八度 · 稳定性 %s 音分" % (
            m["title"], m["bvid"], low.get("note"), low.get("hz"), m.get("span"), m.get("stability")))
    lines += ["", "完整数据：https://wx409.github.io/today.html", ""]
    (ARCHIVE / (entry["date"] + ".md")).write_text("\n".join(lines), encoding="utf-8")


def load_history():
    items = []
    if ARCHIVE.exists():
        for f in sorted(ARCHIVE.glob("*.json"), reverse=True)[:30]:
            try:
                items.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
    return items


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    fresh = d.get("date") == today
    entry = make_entry(d, fresh)
    save_local(entry)
    uniq = {}
    for x in load_history():
        uniq[x["date"]] = x
    history = sorted(uniq.values(), key=lambda x: x["date"], reverse=True)
    HIST.write_text(json.dumps(history[:7], ensure_ascii=False, indent=1), encoding="utf-8")

    shown = entry if fresh else (history[0] if history else None)
    status = "今日已更新" if fresh else "今日自动化未完成；下面是最近一篇 %s" % ((shown or {}).get("date", ""))
    cards = "".join('<div class="card"><div class="t">%s</div><div class="meta">%s · 稳定最低 %s %sHz · 跨度 %s 八度 · 稳定性 %s 音分</div></div>' % (
        esc(m["title"]), esc(m.get("bvid")), esc((m.get("low") or {}).get("note")), esc((m.get("low") or {}).get("hz")),
        esc(m.get("span")), esc(m.get("stability"))) for m in ((shown or {}).get("measurements") or []))

    hist_html = ""
    for h in history[:7]:
        if shown and h["date"] == shown["date"]:
            continue
        hist_html += '<details class="hist"><summary><b>%s</b> ｜ %s</summary><div class="essay small">%s</div>%s</details>' % (
            esc(h["date"]), esc(h["headline"]),
            "".join("<p>%s</p>" % esc(p) for p in (h.get("essay") or [])),
            "".join('<div class="meta">《%s》 %s %sHz · 跨度 %s</div>' % (
                esc(m["title"]), esc((m.get("low") or {}).get("note")), esc((m.get("low") or {}).get("hz")), esc(m.get("span")))
                for m in (h.get("measurements") or [])[:2]))

    page = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>今天，听王晰听到什么｜王晰数字档案</title>
<meta name="description" content="每天一段：今天新入库的 B站视频、声学初测与一句人话；保留最近 7 天，供阅读与二创参考。">
<meta name="robots" content="index, follow"><meta name="llms" content="1"><link rel="canonical" href="https://wx409.github.io/today.html">
<meta property="og:type" content="website"><meta property="og:title" content="今天，听王晰听到什么">
<meta property="og:image" content="https://wx409.github.io/assets/share/og_moments.png">
<style>body{margin:0;background:#faf9f7;color:#1f2328;font:17px/1.9 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:760px;margin:0 auto;padding:30px 22px 70px}h1{font-size:29px;line-height:1.35;margin:6px 0 4px}
.meta{color:#8a8175;font-size:13px}.essay{margin:20px 0 16px;font-size:17px;line-height:2}.essay p{margin:0 0 14px}
.tags{color:#a8323d;font-size:13px;margin:2px 0 22px}h2{font-size:19px;margin:28px 0 8px;border-left:4px solid #a8323d;padding-left:10px}
.card{background:#fff;border:1px solid #e6e2dc;border-radius:10px;padding:12px 14px;margin:8px 0}.t{font-weight:600}
.sub{color:#777;font-size:13.5px}a{color:#a8323d;text-decoration:none}
.hist{background:#fff;border:1px solid #e6e2dc;border-radius:10px;padding:10px 14px;margin:8px 0}.hist summary{cursor:pointer;font-size:14px}
.small{font-size:14px;line-height:1.85;margin-top:8px}.small p{margin:0 0 8px}</style></head><body><main>
<h1>今天，听王晰听到什么</h1>
<p class="meta">%s ｜ %s</p>
<div class="essay">%s</div>
<p class="tags">%s</p>
<h2>今天的测量</h2>%s
<h2>最近 7 天</h2>%s
<p class="sub">稳定最低音按 ≥0.15s、HNR≥5dB、极值音本身≥0.2s 过滤；原始 F0 更低不等于“能唱到”。完整乐队直拍受编曲/混音影响，不用于刷最低音纪录。</p>
<p class="sub">本地灵感库：<code>E:\\wx\\私有工具\\每日小作文\\YYYY-MM-DD.md</code>（每日一段 + 测量摘要，供发布参考）</p>
<p class="sub">完整数据：<a href="/dashboard/">数据大屏</a> · <a href="/voice.html">B1 是什么概念</a> · <a href="/vocal.html">音域实测</a></p>
</main></body></html>""" % (
        esc((shown or {}).get("date", today)), esc(status),
        "".join("<p>%s</p>" % esc(p) for p in ((shown or {}).get("essay") or [])),
        " ".join((shown or {}).get("tags") or []), cards or "<p class='sub'>今天没有可测量的歌曲视频。</p>",
        hist_html or "<p class='sub'>还没有更早的留存。</p>")

    OUT.write_text(page, encoding="utf-8")
    summary = {"date": today, "fresh": fresh, "latest_date": (shown or {}).get("date", ""),
               "headline": (shown or {}).get("headline", ""),
               "new_count": len(d.get("items") or []),
               "measured_count": len(entry.get("measurements") or []),
               "updated_at": d.get("generated_at") or "", "history_days": len(history[:7])}
    JSONOUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("today", today, "fresh", fresh, "| history", len(history[:7]))


if __name__ == "__main__":
    main()
