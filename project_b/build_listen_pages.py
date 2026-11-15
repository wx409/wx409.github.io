#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「免登录收听页」listen/<歌曲>.html：内嵌 B站官方/公开视频 + 站内音域数据。

用途：NFC 贴片/二维码指向 https://wx409.github.io/listen/<歌曲>.html → 直接能听，不要登录。
合规：只嵌入 B站 公开视频（官方播放器），不分发音频文件。
用法：python -X utf8 project_b/build_listen_pages.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT = ROOT / "listen"
SITE = "https://wx409.github.io"
VOCAL = ROOT / "data" / "archive_vocal_albums.json"

# 歌曲 → B站 视频（bvid, 上传者类型, 备注）
SONGS = [
    {"song": "多听有益", "bvid": "BV1zG411f72T", "kind": "官方发布",
     "note": "王晰官方账号发布，免登录可看。"},
    {"song": "微醺23点08分", "bvid": "BV1C8411U7MR", "kind": "官方发布",
     "note": "王晰官方账号发布，免登录可看。"},
    {"song": "在路上", "bvid": "BV15ppdzsE8R", "kind": "粉丝上传 · 大俄电视直播版",
     "note": "粉丝上传的电视直播版，音质较干净；另附现场版链接。"},
]
ALT = {"在路上": ("BV1ACJyzhE4f", "现场 Live 版（粉丝上传）")}


def vocal_row(song: str):
    try:
        d = json.loads(VOCAL.read_text(encoding="utf-8"))
        rows = [r for r in (d.get("songs") or []) if song in str(r.get("title", ""))]
        return rows[0] if rows else None
    except Exception:
        return None


CSS = """body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;line-height:1.8;
max-width:900px;margin:0 auto;padding:20px;color:#20303f;background:#fbfcfe}
h1{font-size:24px;border-bottom:3px solid #3aa0d8;padding-bottom:10px}
.tag{display:inline-block;background:#eaf3fb;color:#2d6f96;border-radius:12px;padding:2px 10px;
font-size:12px;margin-right:8px}
.player{position:relative;width:100%;aspect-ratio:16/9;margin:16px 0;background:#000;border-radius:10px;overflow:hidden}
.player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}
th,td{border-bottom:1px solid #e4eef6;padding:7px 9px;text-align:left}
a{color:#1c7bb8}
.note{background:#eef7fd;border:1px solid #cfe8f7;border-radius:8px;padding:11px 14px;font-size:13px;color:#3b556b}
.nfc{background:#f5f2ff;border:1px solid #ddd4ff;border-radius:8px;padding:11px 14px;font-size:13px}
"""


def page(s):
    song = s["song"]
    v = vocal_row(song)
    bv = s["bvid"]
    url = f"{SITE}/listen/{song}.html"
    alt_html = ""
    if song in ALT:
        ab, an = ALT[song]
        alt_html = f'<p>另一个版本：<a href="https://www.bilibili.com/video/{ab}" target="_blank" rel="noopener">{html.escape(an)}</a></p>'

    if v:
        vocal_html = f"""<h2>站内实测</h2>
<table>
<tr><th>最低稳定音</th><td>{html.escape(str(v.get('low')))} · {v.get('low_hz')} Hz</td></tr>
<tr><th>最高稳定音</th><td>{html.escape(str(v.get('high')))} · {v.get('high_hz')} Hz</td></tr>
<tr><th>单曲跨度</th><td><b>{v.get('span_octaves')} 个八度</b></td></tr>
<tr><th>专辑</th><td>{html.escape(str(v.get('album')))}</td></tr>
</table>
<p class="note">口径：最低稳定音需音符 ≥0.15s、HNR≥5dB，并经谐波列复核；详见
<a href="/vocal.html">音域实测</a>。</p>"""
    else:
        vocal_html = '<p class="note">这首歌暂未进站内录音室实测（待补）。</p>'

    ld = {
        "@context": "https://schema.org",
        "@type": ["WebPage", "MusicRecording"],
        "name": f"王晰《{song}》",
        "url": url,
        "inLanguage": "zh-CN",
        "about": {"@type": "Person", "name": "王晰"},
        "video": {"@type": "VideoObject", "name": f"《{song}》", "embedUrl": f"https://player.bilibili.com/player.html?bvid={bv}"},
    }

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index,follow">
<title>王晰《{html.escape(song)}》免登录收听｜{html.escape(s['kind'])}</title>
<meta name="description" content="王晰《{html.escape(song)}》：免登录直接播放（B站公开视频），并附站内音域实测与出处。">
<link rel="canonical" href="{url}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
<h1>王晰《{html.escape(song)}》</h1>
<p><span class="tag">{html.escape(s['kind'])}</span><span class="tag">免登录播放</span></p>
<div class="player"><iframe src="https://player.bilibili.com/player.html?bvid={bv}&page=1&high_quality=1&danmaku=0&autoplay=0"
 allowfullscreen scrolling="no" frameborder="0"></iframe></div>
<p class="note">{html.escape(s['note'])} 若嵌入被拦，请
<a href="https://www.bilibili.com/video/{bv}" target="_blank" rel="noopener">直接在 B站 打开</a>。</p>
{alt_html}
{vocal_html}
<p class="nfc">📱 这张 NFC 卡片贴到手机，会打开本页。内容随时更新，链接不变。</p>
<p><a href="/">← 返回王晰数字档案</a> · <a href="/quotes.html">可引用金句</a> · <a href="/vocal.html">音域实测</a></p>
</body>
</html>
"""


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index,follow">
<title>王晰 · 免登录收听（NFC 卡片目的地）</title>
<meta name="description" content="贴卡即听：王晰歌曲免登录播放页汇总（B站公开视频 + 站内音域实测）。">
<link rel="canonical" href="{site}/listen/index.html">
<style>body{{font-family:-apple-system,'PingFang SC',sans-serif;max-width:760px;margin:0 auto;padding:24px;
line-height:1.9;color:#20303f;background:#fbfcfe}}h1{{border-bottom:3px solid #3aa0d8;padding-bottom:10px}}
li{{margin:8px 0}}a{{color:#1c7bb8}}.n{{background:#eef7fd;border:1px solid #cfe8f7;border-radius:8px;padding:12px;font-size:13px}}</style>
</head><body>
<h1>王晰 · 免登录收听</h1>
<p class="n">这些页面内嵌 B站 公开视频，<b>不用登录、不用会员</b>。NFC 卡片贴手机即打开本页。</p>
<ul>
{items}
</ul>
<p><a href="/">返回数字档案</a> · <a href="/vocal.html">音域实测</a> · <a href="/quotes.html">可引金句</a></p>
</body></html>"""


def build_index():
    items = "\n".join(
        f'<li><a href="/listen/{s["song"]}.html">《{s["song"]}》</a> · {s["kind"]}</li>' for s in SONGS)
    html_txt = INDEX_HTML.format(site=SITE, items=items)
    (OUT / "index.html").write_text(html_txt, encoding="utf-8")
    print("生成: listen/index.html")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    build_index()
    for s in SONGS:
        p = OUT / f"{s['song']}.html"
        p.write_text(page(s), encoding="utf-8")
        print("生成:", p.name)
    print("共", len(SONGS), "页 →", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
