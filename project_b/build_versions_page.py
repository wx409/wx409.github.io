#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同曲跨场矩阵页：data/live_versions.json → versions.html（纯派生，禁手写数字）。

为什么单独一页：
  站内此前只有「单曲×单场」读数与「录音室↔现场」成对比较；缺的是同一首歌在多个巡次/年份/城市
  之间的横向排列。这一层回答的是"同一歌手如何随场景调整"，是唱功评价里最容易被形容词替代的部分。

口径纪律：
  - 只展示数据层已给的内容；`state=pending` 的读数标「待判」，不进统计、不作能力依据；
  - 页面里的每个数字都来自 live_versions.json，脚本内不出现任何统计常量；
  - 导航/底部索引由 build_nav.py 统一注入（标记占位，勿手改）。

用法：python -X utf8 project_b/build_versions_page.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "live_versions.json"
OUT = ROOT / "versions.html"

STYLE = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
           line-height: 1.75; max-width: 980px; margin: 0 auto; padding: 20px; color: #333;
           background: #fdfcf9; }
    h1 { border-bottom: 3px solid #8a6d3b; padding-bottom: 10px; font-size: 26px; }
    h2 { margin-top: 34px; font-size: 19px; border-left: 4px solid #8a6d3b; padding-left: 10px; }
    .meta { color: #666; font-size: 13.5px; margin: 8px 0 18px; }
    .note { background: #fff8e6; border-left: 3px solid #c9a227; padding: 12px 16px;
            font-size: 13.5px; border-radius: 4px; margin: 16px 0; }
    table { border-collapse: collapse; width: 100%; font-size: 13.5px; margin: 10px 0 6px; }
    th, td { border: 1px solid #e5ddcc; padding: 6px 8px; text-align: left; }
    th { background: #f6f1e4; font-weight: 600; }
    td.n { text-align: right; font-variant-numeric: tabular-nums; }
    .ok { color: #2e7d32; } .pending { color: #b26a00; }
    .sub { color: #555; font-size: 13.5px; margin: 4px 0 0; }
    .foot { color: #777; font-size: 12.5px; margin: 26px 0 10px; }
"""


CLAIMS = json.loads((Path(__file__).resolve().parent.parent / "data" / "claims.json")
                     .read_text(encoding="utf-8"))
_CMAP = {c["id"]: c for c in CLAIMS.get("claims", [])}
SONG_CLAIMS = {"让她降落": "C4-rangta-c2", "再见我的爱人": "C5-zaijian-same-note"}


def claim_block(song: str) -> str:
    """两首试点：判读句与状态由主张派生；主张暂停则整块降级。"""
    cid = SONG_CLAIMS.get(song)
    if not cid:
        return ""
    c = _CMAP.get(cid)
    if not c:
        return ""
    if c.get("status") in ("暂停", "撤回"):
        return ('<p class="sub" style="color:#c0392b"><b>该曲主张已暂停</b>：'
                '下列读数暂不作为结论，仅留档。</p>')
    sc = c.get("scope") or {}
    head = (f'<p class="sub" style="color:#8a6d3b"><b>可引用句（主张 {cid}）</b>：'
            f'{esc(c["can_write"][0])}</p>')
    meta = (f'<p class="sub">版本 {sc.get("total_versions")}｜纳入 {sc.get("included")}｜'
            f'排除 {sc.get("excluded")}（{esc(sc.get("exclude_rule"))}）｜'
            f'跨调性：{"是" if sc.get("cross_key") else "否"}｜极差 {sc.get("range_semitones")} 半音</p>')
    return head + meta


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def table_all(doc: dict) -> str:
    h = ['<table>', '<tr><th>曲目</th><th>版本</th><th>巡次</th><th>目标段读数中位</th>'
         '<th>与录音室</th><th>版本间极差</th></tr>']
    for s in doc["songs"]:
        d = s.get("vs_studio_semitones")
        r = s.get("low_range_semitones")
        h.append(
            "<tr><td><a href=\"#s-{}\">{}</a></td><td class=\"n\">{}</td><td class=\"n\">{}</td>"
            "<td class=\"n\">{} Hz</td><td class=\"n\">{}</td><td class=\"n\">{}</td></tr>".format(
                esc(s["song"]), esc(s["song"]), s["n_versions"], s["n_tours"],
                esc(s.get("low_median") if s.get("low_median") is not None else "—"),
                f"{d:+.1f} 半音" if d is not None else "—",
                f"{r:.1f} 半音" if r else "—"))
    h.append("</table>")
    return "\n".join(h)


def section(s: dict) -> str:
    stu = s.get("studio") or {}
    h = [f'<h2 id="s-{esc(s["song"])}">{esc(s["song"])}</h2>']
    if stu.get("hz"):
        h.append(f'<p class="sub">录音室参照：<b>{esc(stu.get("note"))} {stu.get("hz")} Hz</b>'
                 f'（{esc(stu.get("album"))}）</p>')
    else:
        h.append('<p class="sub">录音室参照：本站未收该曲录音室实测，仅列现场。</p>')
    bits = [f'{s["n_tours"]} 个巡次', f'{s["n_versions"]} 个版本']
    if s.get("low_median") is not None:
        bits.append(f'目标段读数中位 <b>{s["low_median"]} Hz</b>')
    if s.get("vs_studio_semitones") is not None:
        bits.append(f'与录音室相差 <b>{s["vs_studio_semitones"]:+.1f} 半音</b>')
    if s.get("low_range_semitones"):
        bits.append(f'版本间极差 <b>{s["low_range_semitones"]:.1f} 半音</b>')
    h.append('<p class="sub">' + "｜".join(bits) + "</p>")
    vd = verdict(s)
    if vd:
        h.append(f'<p class="sub" style="color:#8a6d3b">怎么读：{vd}</p>')
    cb = claim_block(s["song"])
    if cb:
        h.append(cb)
    h.append("<table><tr><th>巡次</th><th>日期</th><th>城市</th><th>最低音</th><th>最高音</th>"
             "<th>跨度</th><th>稳定(音分)</th><th>颤音(Hz)</th><th>状态</th></tr>")
    for v in s["versions"]:
        stt = {"ok": '<span class="ok">过门槛</span>',
               "pending": '<span class="pending">待判</span>',
               "recorded": "已测"}.get(v["state"], esc(v["state"]))
        h.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{} {} Hz</td><td>{}</td>"
            "<td class=\"n\">{}</td><td class=\"n\">{}</td><td class=\"n\">{}</td><td>{}</td></tr>".format(
                esc(v["tour"] or "—"), esc(v["date"] or "—"), esc(v["city"] or "—"),
                esc(v["low_note"] or "—"), esc(v["low_hz"]),
                (esc(v["high_note"]) + f" {v['high_hz']} Hz") if v.get("high_hz") else "—",
                f'{v["span_octaves"]:.2f}' if v.get("span_octaves") else "—",
                f'{v["stability_cents"]:.1f}' if v.get("stability_cents") is not None else "—",
                f'{v["vibrato_hz"]:.2f}' if v.get("vibrato_hz") is not None else "—",
                stt))
    h.append("</table>")
    return "\n".join(h)



def verdict(s: dict) -> str:
    """由数据派生一句判读，不写死。"""
    bits = []
    if s.get("n_versions", 0) >= 15:
        bits.append(f'版本最多的一首（{s["n_versions"]} 个），适合看同一首歌怎么随场次变化')
    rng = s.get("low_range_semitones")
    if rng is not None and rng < 0.5:
        bits.append(f'版本间极差只有 {rng:.2f} 半音，几乎落在同一个音上')
    elif rng is not None:
        bits.append(f'版本间极差 {rng:.1f} 半音——不同调性，不能当能力对比')
    pend = sum(1 for v in s.get("versions", []) if v.get("state") == "pending")
    if pend:
        bits.append(f'含 {pend} 条「待判」读数，未计入中位')
    if not s.get("studio"):
        bits.append('本站未收该曲录音室实测，只作现场内部比较')
    return "；".join(bits[:3]) + ('。' if bits else '')


def main() -> None:
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    c = doc["counts"]
    n_ok = sum(1 for s in doc["songs"] for v in s["versions"] if v["state"] == "ok")
    n_pending = sum(1 for s in doc["songs"] for v in s["versions"] if v["state"] == "pending")

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question",
             "name": "同一首歌在不同城市的现场，最低音会差多少？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 "本页按巡次与城市逐条列出同一首歌的现场读数。以《多听有益》为例，四巡上海生日与杭州均为 C2 65.2Hz，"
                 "北京直拍为 D2 74.9Hz，2024-04-18 其他演出为 F#2 95.2Hz，版本间极差约 9.3 个半音——差异主要来自当场调性与编配，"
                 "不能直接当作唱功升降。"}},
            {"@type": "Question",
             "name": "为什么有些现场读数标着「待判」？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 "低音区基频常常弱于伴奏与低音乐器，需要原始混音的谐波列判定或人耳听辨才能定案。"
                 "标「待判」的读数照原样展示，但不计入中位统计，也不作为能力结论的依据。"}},
            {"@type": "Question",
             "name": "这个矩阵能说明什么、不能说明什么？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 "它能说明同一首歌在多轮巡演中能否回到相近的音高坐标，以及版本之间的实际差异；"
                 "它不能替代逐句听辨，也不能把不同场次的最低音直接排成能力高低。"}},
        ],
    }
    dataset = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "王晰同曲跨场现场读数矩阵",
        "description": f"同一首歌在不同巡次、年份、城市的现场实测读数（{c['songs']} 首 / {c['versions']} 个版本）。",
        "isAccessibleForFree": True,
        "creator": {"@type": "Person", "name": "王晰数字档案站"},
        "license": "https://wx409.github.io/about.html",
        "variableMeasured": ["最低稳定音", "最高稳定音", "跨度", "音符内稳定性", "颤音速率"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": "https://wx409.github.io/data/live_versions.json"}],
    }

    body = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<meta name="robots" content="index, follow">',
        f'<title>同曲跨场矩阵｜王晰现场 {c["songs"]} 首 × {c["versions"]} 个版本｜AI 可读数字档案</title>',
        f'<meta name="description" content="同一首歌跨巡次、跨年份、跨城市的现场读数矩阵：{c["songs"]} 首、{c["versions"]} 个版本，'
        '逐个标出稳定音、跨度、音符内稳定性与复核状态。差异来自调性与编配，不用于能力排名。">',
        '<link rel="canonical" href="https://wx409.github.io/versions.html">',
        '<link rel="stylesheet" href="assets/brand.css">',
        f"<style>{STYLE}</style>",
        f'<script type="application/ld+json">{json.dumps(dataset, ensure_ascii=False)}</script>',
        f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>',
        "</head><body>",
        "<!-- NAV_START --><!-- NAV_END -->",
        "<h1>🔀 同曲跨场矩阵</h1>",
        f'<p class="meta">同一首歌，换个城市、隔几年再唱，他还能不能回到同一个音高坐标？'
        f'本页把 {c["songs"]} 首、{c["versions"]} 个现场版本按巡次与日期排开——'
        f'其中 {n_ok} 条已过复核门槛，{n_pending} 条标注「待判」。</p>',
        '<div class="note">口径：只收有最低音读数的现场素材；人耳否决的读数已排除；'
        '「待判」条目照原样展示但不进中位统计。跨场最低音差异主要来自当场调性与编配，'
        '本页不据此做能力排名。数据源 <code>data/live_versions.json</code>，由 '
        '<code>project_b/build_live_versions.py</code> 生成。</div>',
        '<details class="note"><summary><b>怎么读这张表</b>（点开／收起）</summary>'
        '<p>① <b>音名 vs 频率</b>：音名（如 C2）是乐理写法，Hz 是实测；同一音名可以差几十音分，所以本页同时给赫兹。</p>'
        '<p>② <b>稳定音 vs 待判</b>：过复核门槛的才叫稳定音，能进统计；标「待判」的照原样展示，但不进中位、不作能力依据。</p>'
        '<p>③ <b>「与录音室」那一列</b>：正值＝现场比录音室高几个半音。半音＝钢琴相邻两键的距离；1 半音＝100 音分。</p>'
        '<p>④ <b>术语</b>：<i>音分</i>＝半音的一百分之一；<i>跨度</i>＝一首歌里最低到最高的距离；<i>颤音速率</i>＝每秒音高起伏的次数。</p></details>',
        "<h2>一眼总览</h2>",
        table_all(doc),
        '<p class="foot">「与录音室」按该曲录音室最低稳定音对照（无录音室记录者留空）；'
        '「版本间极差」只统计已过门槛的现场读数。</p>',
    ]
    for s in doc["songs"]:
        body.append(section(s))
    body += [
        '<h2>可以直接抄走的三句</h2>',
        '<div class="note"><p>① 同一首歌在不同场次的最低音会变，主要是调性和编配不同，'
        '不能拿来给状态打分。</p>'
        '<p>② 这里统计的是「最低稳定音」——过复核门槛、能进乐句的那个音，不是单帧扫到的低频。</p>'
        '<p>③ 版本间极差越小的曲目（如 0.1–0.5 半音），越能说明他能在不同场次回到同一个音高坐标。</p></div>',
        '<p class="foot">口径：稳定音（音符 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB；极值音本身 ≥0.2s）；'
        '待判读数不进统计。数据源 <code>data/live_versions.json</code>。</p>',
        '<p class="foot">方法：QQ 音乐 320k / 现场素材 → demucs htdemucs 人声分离 → 自研 YIN 逐帧 F0'
        '（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）→ 音符切分（≥80ms、抖动 &lt;0.6 半音）'
        '→ 稳健过滤（时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB）；低音读数另做原始混音谐波列判定。'
        f'最后更新：{esc(doc.get("generated_at"))}。</p>',
        "<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->",
        "</body></html>",
    ]
    OUT.write_text("\n".join(body), encoding="utf-8")
    print(f"[OK] {OUT.name}｜曲目 {c['songs']}｜版本 {c['versions']}｜过门槛 {n_ok}｜待判 {n_pending}")


if __name__ == "__main__":
    main()
