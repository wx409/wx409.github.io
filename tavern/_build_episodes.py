# -*- coding: utf-8 -*-
"""生成深夜小酒馆每期独立逐字稿页面 /tavern/ep/{key}.html（方案B：每期独立 URL 供 AI 逐期引用）。

- 数据源: tavern_transcripts.json（key -> {episode_num, part, category, theme, text, songmid, duration_sec}）
- 每期生成独立静态 HTML（Article + RadioEpisode JSON-LD），暗色风格与主页面一致
- 更新 tavern/index.html 的 RadioSeries episodes JSON-LD 为完整期次
- 追加 sitemap.xml（保留现有条目，兼容 generate_live_page.py 的保留式更新）
"""
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).resolve().parent          # tavern/
TAVERN_INDEX = BASE / "index.html"
TRANSCRIPTS = BASE / "tavern_transcripts.json"
EP_DIR = BASE / "ep"
SITEMAP = BASE.parent / "sitemap.xml"
SITE = "https://wx409.github.io"
SAME_AS = [
    "https://y.qq.com/n/ryqq/singer/0039pU5Y2PA9OW",
    "https://weibo.com/u/1292815744",
]


def label_of(key, ep):
    """期次展示名：营业预告 / EP01 · 睡前故事与酒 / 收官福利"""
    if key == "营业预告":
        return "营业预告"
    num = ep.get("episode_num", 0)
    cat = ep.get("category", "")
    if num:
        return f"EP{num:02d} · {cat}" if cat else f"EP{num:02d}"
    return key  # 收官福利等无期号期次


def title_of(key, ep):
    theme = (ep.get("theme", "") or "").strip()
    label = label_of(key, ep)
    # theme 若已自带期次前缀（如「收官福利｜xxx」），去掉避免重复
    for prefix in (label + "｜", key + "｜"):
        if theme.startswith(prefix):
            theme = theme[len(prefix):].strip()
            break
    return f"{label}｜{theme}" if theme else label


CSS = """\
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei','PingFang SC',sans-serif;background:radial-gradient(ellipse at center,#0f1535 0%,#080c24 100%),radial-gradient(circle at 18% 28%,rgba(0,210,255,0.07) 0,transparent 32%),radial-gradient(circle at 82% 72%,rgba(255,215,0,0.05) 0,transparent 32%);color:#fff;line-height:1.9;min-height:100vh;padding:24px 16px 60px;}
.wrap{max-width:760px;margin:0 auto;}
a{color:#00d2ff;text-decoration:none}
.back{font-size:13px;color:#5a6b8c;letter-spacing:1px;margin-bottom:22px;display:inline-block}
.back:hover{color:#00d2ff}
h1{font-size:26px;font-weight:700;letter-spacing:2px;line-height:1.5;margin-bottom:6px;background:linear-gradient(90deg,#00d2ff,#3a7bd5,#ffd700);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}
.meta{font-size:12px;color:#5a6b8c;letter-spacing:2px;margin-bottom:18px}
.theme{font-size:15px;color:#ffd700;letter-spacing:2px;margin-bottom:20px;border-left:3px solid rgba(255,215,0,.6);padding-left:12px}
.transcript{font-size:15px;color:#bcc8e8;letter-spacing:1px;white-space:pre-wrap;line-height:2.05;background:rgba(0,0,0,.18);border:1px solid rgba(0,210,255,.1);border-radius:12px;padding:20px 22px;}
.song{margin-top:20px;font-size:14px;color:#8896b3}
.footer{margin-top:40px;font-size:12px;color:#4a5878;letter-spacing:1px;text-align:center}
"""


def build_episode_page(key, ep):
    num = ep.get("episode_num", 0)
    theme = ep.get("theme", "").strip()
    text = ep.get("text", "") or ""
    songmid = ep.get("songmid") or ""
    dur = ep.get("duration_sec", 0)
    title = title_of(key, ep)
    label = label_of(key, ep)
    url = f"{SITE}/tavern/ep/{quote(key)}.html"

    desc = f"「深夜小酒馆」{title}：{theme}。完整逐字稿存档。粉丝创作，非官方。" if theme else f"「深夜小酒馆」{title}：完整逐字稿存档。粉丝创作，非官方。"

    ld = {
        "@context": "https://schema.org",
        "@type": ["Article", "RadioEpisode"],
        "name": title,
        "headline": title,
        "description": desc,
        "url": url,
        "inLanguage": "zh-CN",
        "isPartOf": {
            "@type": "RadioSeries",
            "name": "日木斤深夜小酒馆｜王晰哄你入睡",
            "url": f"{SITE}/tavern/",
        },
        "episodeNumber": num if num else 0,
        "partNumber": ep.get("part", 0),
        "about": {"@type": "Person", "name": "王晰", "sameAs": SAME_AS},
        "author": {"@type": "Person", "name": "王晰", "sameAs": SAME_AS},
    }

    song_html = ""
    if songmid:
        song_html = (
            f'<p class="song">🎵 本期歌曲：'
            f'<a href="https://y.qq.com/n/ryqq/songDetail/{html.escape(songmid)}" target="_blank" rel="noopener">'
            f'QQ音乐《{html.escape(theme)}》</a></p>'
        )

    minutes = f"{dur // 60}分{dur % 60}秒" if dur else ""
    meta_suffix = " · " + minutes if minutes else ""

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index,follow,max-image-preview:large">
<title>{html.escape(title)}｜深夜小酒馆 · 王晰</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title)}｜深夜小酒馆 · 王晰">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/cover.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="{SITE}/tavern/">← 返回深夜小酒馆</a>
<h1>{html.escape(title)}</h1>
<p class="meta">深夜小酒馆 · 王晰 ｜ {html.escape(label)}{meta_suffix}</p>
<p class="theme">{html.escape(theme)}</p>
<div class="transcript">{html.escape(text)}</div>
{song_html}
<p class="footer">本页为粉丝创作，非官方内容。素材来自王晰公开节目与作品。</p>
</div>
</body>
</html>
"""
    return page


def build_episodes_ld(keys, episodes):
    """生成 RadioSeries episodes 数组 JSON-LD（完整期次，url 指向独立页）"""
    rows = []
    for i, key in enumerate(keys):
        ep = episodes[key]
        name = title_of(key, ep)
        url = f"{SITE}/tavern/ep/{quote(key)}.html"
        rows.append(
            '    {"@type": "RadioEpisode", "name": "'
            + name.replace('"', '\\"')
            + '", "position": '
            + str(i)
            + ', "url": "'
            + url
            + '"}'
        )
    return "  \"episodes\": [\n" + ",\n".join(rows) + "\n  ]"


def update_tavern_index(episodes_ld):
    idx = TAVERN_INDEX.read_text(encoding="utf-8")
    pattern = re.compile(r'  "episodes": \[.*?\n  \]\n\}', re.S)
    new_idx, n = pattern.subn(episodes_ld + "\n}", idx)
    if n != 1:
        raise RuntimeError(f"index.html 中 episodes JSON-LD 匹配次数 = {n}，未更新（需人工处理）")
    TAVERN_INDEX.write_text(new_idx, encoding="utf-8")
    print(f"[OK] index.html RadioSeries episodes 已更新为完整期次（{n} 处）")


def update_sitemap(keys):
    locs = []
    for key in keys:
        locs.append(f"{SITE}/tavern/ep/{quote(key)}.html")
    xml = SITEMAP.read_text(encoding="utf-8")
    existing = set(re.findall(r"<loc>(.*?)</loc>", xml))
    add = [loc for loc in locs if loc not in existing]
    if not add:
        print("[OK] sitemap.xml 无需追加（已存在）")
        return
    block = "".join(
        '  <url>\n    <loc>%s</loc>\n    <lastmod>2026-08-13</lastmod>\n'
        '    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n' % loc
        for loc in add
    )
    if xml.rstrip().endswith("</urlset>"):
        xml = xml.rstrip()[: -len("</urlset>")] + block + "</urlset>\n"
    SITEMAP.write_text(xml, encoding="utf-8")
    print(f"[OK] sitemap.xml 追加 {len(add)} 个独立页面 URL")


def main():
    data = json.loads(TRANSCRIPTS.read_text(encoding="utf-8"))
    episodes = data.get("episodes", {})
    keys = list(episodes.keys())
    print(f"数据源共 {len(keys)} 期")

    EP_DIR.mkdir(exist_ok=True)
    written = 0
    empty = []
    for key in keys:
        ep = episodes[key]
        if not (ep.get("text") or "").strip():
            empty.append(key)
            continue
        (EP_DIR / f"{key}.html").write_text(build_episode_page(key, ep), encoding="utf-8")
        written += 1

    print(f"已生成 {written} 个独立页面 -> tavern/ep/")
    if empty:
        print("[!] 以下期次逐字稿为空，未生成页面：")
        for k in empty:
            print("    -", k)
    else:
        print("[OK] 无空期")

    if written:
        update_tavern_index(build_episodes_ld(keys, episodes))
        update_sitemap(keys)

    print("完成。")


if __name__ == "__main__":
    main()
