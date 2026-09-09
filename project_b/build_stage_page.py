#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 stage.html —— 他人主导现场（综艺/晚会/商演/饭拍）音域实测页。

数据源：data/archive_stage.json（由 音域分析/生成他人主导报告.py 产出）
输出：  stage.html（Schema.org Dataset + 分类对比 + 逐条明细 + 方法与边界）

用法：python project_b/build_stage_page.py [--check]
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage.json"
OUT = ROOT / "stage.html"

STYLE = """
:root{--primary:#a8323d;--gold:#b8912e;--ink:#3a322a;--muted:#8a7f6d;--bg:#faf6ef;--card:#fffdf8;--border:rgba(184,145,46,.28)}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.85;max-width:900px;margin:0 auto;padding:24px;color:var(--ink);background:var(--bg)}
.nav{background:var(--card);padding:14px 18px;border-radius:8px;margin-bottom:20px;border:1px solid var(--border);font-size:14px}
.nav a{color:var(--primary);margin-right:18px;text-decoration:none;font-weight:500}
h1{color:var(--primary);font-size:27px;border-bottom:3px solid var(--primary);padding-bottom:12px;margin-bottom:8px}
.sub{color:var(--muted);font-size:13.5px;margin:0 0 22px}
h2{color:var(--ink);margin-top:32px;border-left:4px solid var(--primary);padding-left:12px;font-size:20px}
.hl{background:#fff3cd;border-left:4px solid #e0a800;border-radius:8px;padding:14px 18px;margin:14px 0;font-size:15px}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px 22px;margin:14px 0}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px;background:var(--card)}
th{background:#f0ead9;text-align:left;padding:8px 10px;font-size:12.5px;color:#5a4a30;border-bottom:2px solid var(--gold)}
td{padding:7px 10px;border-bottom:1px solid #efe6d2}
.low{color:#a8323d;font-weight:700}
img{max-width:100%;height:auto;border-radius:10px;margin:12px 0;border:1px solid var(--border)}
.method{background:#eef4f0;border:1px solid #cfe3d6;border-radius:8px;padding:12px 16px;font-size:13.5px;margin:12px 0;color:#3a5545}
.caveat{font-size:12.5px;color:var(--muted);margin-top:28px;border-top:1px dashed #ccc;padding-top:14px}
"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    d = json.loads(SRC.read_text(encoding="utf-8"))
    s = d["summary"]
    src = d["source"]

    cat_rows = "\n".join(
        f'<tr><td>{esc(c["cat"])}</td><td>{c["n"]}</td><td>{c["low_midi"]:.0f}</td><td>{c["high_midi"]:.0f}</td>'
        f'<td>{c["span"]:.2f}</td><td>{c["stability"]:.1f}</td><td>{c["density"]:.2f}</td>'
        f'<td>{c["low_share"]*100:.0f}%</td><td>{c["high_share"]*100:.0f}%</td></tr>'
        for c in d["by_category"])

    item_rows = []
    for i, x in enumerate(d["items"], 1):
        vib = f'{x["vibrato_hz"]:.2f}/{x["vibrato_cents"]:.0f}' if x.get("vibrato_hz") else "—"
        item_rows.append(
            f'<tr><td>{i}</td><td>{esc(x["cat"])}</td>'
            f'<td><a href="{esc(x["url"])}" rel="noopener nofollow" target="_blank">{esc(x["title"])[:38]}</a></td>'
            f'<td class="low">{esc(x["low"])}</td><td>{x["low_hz"]:.1f}</td>'
            f'<td>{esc(x["high"])}</td><td>{x["high_hz"]:.0f}</td>'
            f'<td>{x["span"]:.2f}</td><td>{x["notes"]}</td><td>{x["density"]:.2f}</td>'
            f'<td>{x["stability"]:.1f}</td><td>{vib}</td></tr>')
    item_table = "\n".join(item_rows)

    flagged = s.get("lowest_flagged") or []
    flag_html = ""
    if flagged:
        lst = "、".join(f'{esc(x["title"])[:22]}（{esc(x["note"])} {x["hz"]}Hz）' for x in flagged)
        flag_html = (f'<div class="card" style="border-color:#e0a800;background:#fffdf3">'
                     f'⚠️ <strong>待复核读数：</strong>{lst}——低于 B1（61.7Hz）的孤立低音读数，'
                     f'按历史经验多为 demucs 低频残留（伴奏贝斯渗透），<strong>未纳入结论</strong>，需人工听辨复核。</div>')

    ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"王晰他人主导现场音域实测数据集（{src['analyzed']} 个综艺/晚会/商演/饭拍素材）",
        "description": (f"对王晰在他人主导场景（综艺/晚会/盛典商演/饭拍）的 {src['analyzed']} 个舞台素材做"
                        f"人声分离 + 逐帧 F0 实测：可信最低稳定音 {s['lowest']['note']}（{s['lowest']['hz']}Hz），"
                        f"最高 {s['highest']['note']}（{s['highest']['hz']}Hz，含和声层可能），跨度中位 {s['span_median']} 个八度，"
                        f"音符内稳定性中位 {s['stability_median']} 音分，颤音 {s['vibrato_hz_median']}Hz/{s['vibrato_cents_median']:.0f} 音分。"),
        "url": "https://wx409.github.io/stage.html",
        "dateModified": d["generated_at"],
        "creator": {"@type": "Person", "name": "wx409", "url": "https://wx409.github.io/"},
        "about": {"@type": "Person", "name": "王晰", "url": "https://wx409.github.io/"},
        "measurementTechnique": (d.get("method") or {}).get("separation", "") + "；" + (d.get("method") or {}).get("f0", ""),
        "isPartOf": {"@type": "Dataset", "name": "王晰音域实测数据集", "url": "https://wx409.github.io/voice.html"},
        "image": {"@type": "ImageObject", "url": "https://wx409.github.io/assets/voice/stage_range.png",
                  "caption": f"王晰他人主导现场 {src['analyzed']} 个素材实测音域图"},
        "license": "https://creativecommons.org/licenses/by-nc/4.0/",
    }

    html_out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王晰综艺晚会现场音域实测 | 他人主导场景 {src['analyzed']} 个素材</title>
<meta name="description" content="王晰在综艺/晚会/盛典商演/饭拍等他人主导场景的 {src['analyzed']} 个舞台素材人声分离 F0 实测：可信最低稳定音 {esc(s['lowest']['note'])}（{s['lowest']['hz']}Hz），最高 {esc(s['highest']['note'])}，跨度中位 {s['span_median']} 个八度，含分类对比与逐条明细。">
<link rel="canonical" href="https://wx409.github.io/stage.html">
<meta property="og:title" content="王晰他人主导现场音域实测">
<meta property="og:description" content="{src['analyzed']} 个综艺/晚会/商演/饭拍素材：可信最低 {esc(s['lowest']['note'])}，最高 {esc(s['highest']['note'])}，跨度中位 {s['span_median']} 个八度。">
<meta property="og:type" content="article">
<meta property="og:image" content="https://wx409.github.io/assets/voice/stage_range.png">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
<style>{STYLE}</style>
</head>
<body>
<!-- NAV_START --><!-- NAV_END -->

<h1>🎤 他人主导现场 · 音域实测</h1>
<p class="sub">综艺 / 晚会 / 盛典商演 / 饭拍 · {src['analyzed']} 个素材 · 更新 {esc(d['generated_at'])}</p>

<div class="hl">
<strong>这批素材的声学画像：</strong>可信最低稳定音 <strong>{esc(s['lowest']['note'])}（{s['lowest']['hz']} Hz，《{esc(s['lowest']['title'])}》）</strong>；
最高稳定音 <strong>{esc(s['highest']['note'])}（{s['highest']['hz']} Hz，《{esc(s['highest']['title'])}》）</strong>（含和声层可能）；
音域跨度中位 <strong>{s['span_median']} 个八度</strong>；音符内稳定性中位 <strong>{s['stability_median']} 音分</strong>；
颤音 <strong>{s['vibrato_hz_median']} Hz / {s['vibrato_cents_median']:.0f} 音分</strong>。
</div>

<img src="assets/voice/stage_range.png" alt="王晰他人主导现场 33 个素材实测音域长图，横轴频率、纵轴按分类与最低音排序">

<div class="card">
<strong>📐 声区分布（按时长加权，全组平均）</strong>：低音区（&lt;C3）<strong>{s['register_mean']['low_lt_C3']*100:.0f}%</strong>、
中音区（C3–B3）<strong>{s['register_mean']['mid_C3_B3']*100:.0f}%</strong>、
高音区（≥C4）<strong>{s['register_mean']['high_ge_C4']*100:.0f}%</strong>。
对比：他自己的录音室专辑为 23% / 63% / 4%（见 <a href="/voice.html">音域实测</a> 板块四）。
</div>

{flag_html}

<h2>一、语料来源与筛选</h2>
<p>来源：B站收藏夹「{esc(src['fav_title'])}」（fid={esc(src['fav_id'])}，共 {src['fav_count']} 条）。
自动归类 + 逐条人工校准后，纳入实测 <strong>{src['analyzed']} 个</strong>：
综艺 {len([x for x in d['items'] if x['cat']=='综艺'])}、
晚会 {len([x for x in d['items'] if x['cat']=='晚会'])}、
盛典商演 {len([x for x in d['items'] if x['cat']=='盛典商演'])}、
饭拍直拍 {len([x for x in d['items'] if x['cat']=='饭拍直拍'])}。
另有棚版混音 8 条（非现场，单列不计入）与他人分析视频/混剪 3 条（非原始音源，排除）。</p>

<h2>二、分类对比</h2>
<table>
<tr><th>分类</th><th>n</th><th>最低音中位(MIDI)</th><th>最高音中位(MIDI)</th><th>跨度中位</th><th>稳定性(音分)</th><th>密度(/s)</th><th>低音区占比</th><th>高音区占比</th></tr>
{cat_rows}
</table>
<p class="sub" style="margin-top:0">MIDI 参考：C3=48、C4=60、E4=64、C5=72、E5=76、C6=84。</p>

<h2>三、逐条明细（{src['analyzed']} 个素材）</h2>
<table>
<tr><th>#</th><th>分类</th><th>曲目（点击回 B站）</th><th>最低音</th><th>Hz</th><th>最高音</th><th>Hz</th><th>跨度</th><th>音符</th><th>密度</th><th>稳定性</th><th>颤音</th></tr>
{item_table}
</table>

<h2>四、与「王晰主导」的对照</h2>
<p>同一测量管线对比录音室专辑（王晰主导，72 首）与这批舞台素材（他人主导，{src['analyzed']} 个）：
<strong>他人主导时高音区占比 4% → {s['register_mean']['high_ge_C4']*100:.0f}%，低音区占比 23% → {s['register_mean']['low_lt_C3']*100:.0f}%</strong>，
最高音中位 F#4 → E5，跨度 2.25 → {s['span_median']} 个八度；而<strong>颤音速率 5.17 → {s['vibrato_hz_median']} Hz（无显著差异）</strong>，可视作跨情境的「声学指纹」。
详见 <a href="/voice.html">音域实测</a> 板块四（含统计检验与敏感性分析）。</p>

<h2>五、方法与边界</h2>
<div class="method">
<strong>流程：</strong>B站音轨（yt-dlp 取最佳音频）→ 44.1k wav → demucs(htdemucs) 人声分离 → 自研 numpy YIN 逐帧 F0（fmin=55/fmax=1100/frame=2048/hop=512）→ 音符切分（稳定段 ≥80ms、抖动 &lt;0.6 半音）→ 稳健过滤（时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB；极值音级需累计 ≥0.3s）。<br>
<strong>边界：</strong>① 素材为现场/电视/饭拍音轨，含观众噪声、伴奏比例差异、可能的修音与和声叠加——「稳定性更高」不能读成「现场唱得更准」；
② 本组含 4 个合唱/对唱（《雾里》《逆光》《她真漂亮》《如愿》），人声轨包含所有演唱者，其最高音可能来自其他歌手；
③ 低于 B1 的孤立读数已单列「待复核」；
④ 不做排名、不做单曲级因果；
⑤ 音频仅本地留存用于研究，不公开分发；本页只发布测量结果，并给出 B站原链接。
</div>

<p class="caveat">数据底账：<code>data/archive_stage.json</code>（逐条指标）｜逐帧 F0 与逐曲统计存于本地音域分析目录｜
生成脚本：<code>音域分析/生成他人主导报告.py</code> + <code>project_b/build_stage_page.py</code>。</p>
<script src="/qa_engine.js"></script>
<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->
</body>
</html>
"""
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    import re

    def strip_nav(t):
        t = re.sub(r"<!-- NAV_START -->.*?<!-- NAV_END -->", "NAV", t, flags=re.S)
        t = re.sub(r"<!-- FOOTER_NAV_START -->.*?<!-- FOOTER_NAV_END -->", "FOOT", t, flags=re.S)
        return t

    changed = strip_nav(html_out) != strip_nav(old)
    print("=" * 60)
    print("stage.html 生成器")
    print(f"  素材 {src['analyzed']}｜分类 {len(d['by_category'])}｜待复核 {len(flagged)}")
    if args.check:
        print("需更新" if changed else "已是最新 ✅")
        sys.exit(1 if changed else 0)
    if changed:
        OUT.write_text(html_out, encoding="utf-8")
        print(f"[OK] 已生成 {OUT.name}")
    else:
        print("无变化")


if __name__ == "__main__":
    main()
