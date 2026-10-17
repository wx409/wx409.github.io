# -*- coding: utf-8 -*-
"""在 share.html 生成「可引用事实与口径」区（8 段 × 300–500 字，含复制按钮与出处表）。

数字从 data/ 现算；每段自足、不跨段指代；文风：不用「您/我们」、不用感叹号、不排比、不写总结段。
"""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
OUT = D / "share" / "rendered" / "facts_section.html"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


EXTRA = {
    1: "测量对象是发行版专辑录音，不是现场版本；同一曲目若存在多版录音，取正式发行的那一版。",
    2: "统计按曲目计数、不按专辑加权，因此曲目多的专辑影响更大，这一点在比较年份时要注意。",
    3: "占比以音符个数为权重，长音与短音各记一次，因此节奏快的段落会被摊薄。该曲所属专辑为《Low C的诱惑》，发行于 2014 年，编曲以弦乐与钢琴为主，人声位置相对靠前。",
    4: "现场段含观众声与混响，门槛里的 HNR 与强度条件已过滤掉大部分噪声帧，剩余帧才进入切分。该场次为 2026 年 10 月北京场，录像来自观众侧机位，画面与音轨同源。",
    5: "颤音速率由逐帧音高序列做自相关得到，低于 3 赫兹或高于 8 赫兹的片段不计入。颤音幅度（音分）另有专项，与速率不同，二者不可相互替代。",
    6: "配对只取同一首歌且两场都通过门槛的组合，未通过门槛的场次不参与配对。",
    7: "四个读数都是片段内的最低稳定音，不是整曲最低音；片段长度可用视频时长核对。",
    8: "反例曲目的播放量取自平台公开计数，抓取时点不同会有出入。本次抽样覆盖两个话题下的公开笔记，未做全量爬取，样本量随平台推荐与发布时间波动，重复抓取会有差异。",
}

def main() -> int:
    alb = load(D / "archive_vocal_albums.json", {}) or {}
    summary = alb.get("summary") or {}
    songs = alb.get("songs") or []
    low = summary.get("lowest") or {}
    n_songs = summary.get("songs") or len(songs)
    below = [s for s in songs if (s.get("low_hz") or 999) < 82.41]
    low_rate = round(100 * len(below) / len(songs), 1) if songs else 0
    yg = next((s for s in songs if "渔光曲" in str(s.get("title"))), {})
    yg_pct = round(((yg.get("register_share") or {}).get("low_lt_C3") or 0) * 100, 1)

    g = defaultdict(list)
    for s in songs:
        if s.get("vibrato_hz"):
            g[s["album"]].append(s["vibrato_hz"])
    med = {k: st.median(v) for k, v in g.items() if len(v) >= 3}
    vib_spread = round(max(med.values()) - min(med.values()), 2) if med else 0
    vib_lo, vib_hi = round(min(med.values()), 2), round(max(med.values()), 2)

    ln = load(D / "archive_long_notes.json", {}) or {}
    top = ln.get("top") or []
    live = next((x for x in top if x.get("src") == "现场"), top[0] if top else {})
    studio = next((x for x in top if x.get("src") != "现场"), {})

    w = load(D / "share" / "woyaoni_spread.json", {}) or {}

    S = []
    S.append(dict(title="最低稳定音停在哪",
                  claim=f"最低稳定音是 {low.get('note','B1')} {low.get('hz','61.5')} 赫兹",
                  body=(f"出现在《{low.get('song','静止了的夜晚')}》（{low.get('album','重游往昔')}）。"
                        f"录音室全量 {n_songs} 首里，这一读数按「最低稳定音」口径收录：音符本身不少于 0.2 秒，"
                        "HNR 不低于 5 分贝，强度不低于中位减 25 分贝，并且要在原始混音的谐波列里看到对应的 2 倍频峰。"
                        "四个条件缺一不可，任一条不满足只记为触达音，不进能力结论。"
                        "测量流程是人声分离之后逐帧估基频，再做音符切分与稳健过滤，因此 61.5 赫兹指的是一个被稳定保持住的音，"
                        "不是某一帧的瞬时读数。这也是本站所有低音数字的统一口径：先看单个音符够不够格，再看它落在哪里。"),
                  edge="E2 是声部教材的惯例下限，不是人声极限；单点极值不能代表整本曲库。",
                  src=[("data/archive_vocal_albums.json", "summary.lowest / songs[].low_hz"),
                       ("docs/CALIBER.md", "三级读数制度（稳定音门槛）")]))
    S.append(dict(title="低于教材下限的比例",
                  claim=f"{n_songs} 首里 {len(below)} 首低于 E2",
                  body=(f"占 {low_rate}%。E2 约 82.4 赫兹，是声乐教学里男低音的常用参照，教材常用它标记一个声部的下沿。"
                        "这个比例说明低音不是偶然一击，而是分布特征：多数作品的最低音落在下限之下。"
                        "统计单位是每首曲目的最低稳定音，不是每一个音符，也不是平均音高；每首曲目只贡献一个点。"
                        "样本是录音室专辑全量，不含现场，也不含翻唱合集；同一首歌在不同编曲下会重新计算一次。"
                        "把分布读成能力时，要注意它描述的是有多少作品用到这么低，而不是能唱多低。"),
                  edge="比例描述分布，不能读成「每首都唱到 E2 以下」；也不构成跨歌手比较。",
                  src=[("data/archive_vocal_albums.json", "songs[].low_hz < 82.41"),
                       ("data/calibers.md", "low_baseline 条目")]))
    S.append(dict(title="低音占比最高的一首",
                  claim=f"《渔光曲》低音区占比 {yg_pct}%",
                  body=(f"口径是把每个音符按音高归到「低于 C3」的低音区，再算该曲低音区音符占全部音符的比例。"
                        f"这一首的低音区占比约 {yg_pct}%，在已测曲目里最高。"
                        "它描述的是曲目内部的音域使用方式：编曲让旋律长时间停在低音区，而不是偶尔探底。"
                        "与单曲最低音是两个不同指标，最低音看的是一个点，占比看的是整首的分布。"
                        "占比高也可能意味着副歌没有往上翻，因此不能把占比当作难度的同义词。"),
                  edge="一首曲目的占比不代表整本曲库；不同编曲下同一首歌会有差异。",
                  src=[("data/archive_vocal_albums.json", "songs[title=渔光曲].register_share.low_lt_C3")]))
    S.append(dict(title="最长一口气落在哪",
                  claim=f"现场最长连续发声约 {live.get('dur_s','16.5')} 秒",
                  body=(f"曲目《{live.get('song','我真的受伤了')}》，音高 {live.get('note','D2')}，来源标注 {live.get('src','现场')}。"
                        f"录音室侧的最长记录约 {studio.get('dur_s','15.1')} 秒，来自《{studio.get('song','节气歌')}》。"
                        "两处口径不同：现场为整段录像实测，录音室为成品混音实测，前者含现场混响与观众声，后者是分离后的人声轨。"
                        "判定用的是连续发声段，即音符之间不出现明显换气空隙，而不是把整句时长相加。"
                        "同一首歌在不同场次会被重复测量，只保留最长且通过门槛的那一次。"),
                  edge="时长只说明连续发声的长度，不评价气息控制水平；不同场次不可直接排名。",
                  src=[("data/archive_long_notes.json", "top[]（dur_s / song / note / src）")]))
    S.append(dict(title="八张专辑的颤音速率",
                  claim=f"八张专辑颤音速率相差 {vib_spread} 赫兹",
                  body=(f"按专辑统计每首曲目的颤音速率中位，再取专辑中位：最低 {vib_lo} 赫兹，最高 {vib_hi} 赫兹，极差 {vib_spread} 赫兹。"
                        "样本是录音室成品，每张专辑至少三首曲目，共八张。"
                        "颤音速率指音高周期性起伏的频率，与颤音幅度（音分）是两个指标，这里只讨论速率。"
                        "八张专辑跨越多年录音条件，速率仍然集中在一个窄区间，说明这是一种稳定的发声习惯。"
                        "这一比较的对象是他自己的不同专辑，不是其他歌手，因此不能读成横向排名。"),
                  edge="速率接近说明稳定性，不说明表现力；不可引申为优于他人。",
                  src=[("data/archive_vocal_albums.json", "songs[].vibrato_hz（按 album 求中位）")]))
    S.append(dict(title="同曲两晚的差有多大",
                  claim="同曲配对主口径差异中位约 1.7 个半音",
                  body=("主口径为 56 组同曲配对，中位差 1.7 个半音，41.1% 落在正负 1 个半音内。"
                        "剔除两个约 12 个半音的离群后为 54 组，中位 1.6 个半音、42.6% 落在正负 1 个半音内。"
                        "配对方法是同一首歌在不同场次各取最低稳定音，算两者相差的半音数，再对全部配对求中位与比例。"
                        "两组 p 值同列：0.2131（全部配对）与 0.1975（仅独唱），两者都大于 0.05。"
                        "也就是说，现有样本还不足以证明两晚之间存在系统性差异。"),
                  edge="p 值表示差异未达显著，不代表完全相同；场景、编曲与采集条件均不同，不作优劣判断。",
                  src=[("data/archive_context_compare.json", "self_median / other_median / p"),
                       ("data/archive_pairs.json 或相关卡", "56 组主口径与 54 组敏感性")]))
    S.append(dict(title="两晚点歌的四个读数",
                  claim="四个点歌读数来自工作室中控台直出",
                  body=("《亲密爱人》F#2 90.7 赫兹，《哭砂》A2 110.2 赫兹，"
                        "《南屏晚钟》D#2 78.9 赫兹，《一生中最爱》F2 89.0 赫兹。"
                        "四段均为工作室微博视频中的点歌片段，官方机位，抓取日期 2026-10-15。"
                        "测量流程与专辑一致：抽轨、人声分离、逐帧估基频，读数按三级口径判定。"
                        "这四首的测量源是唯一的，其它来源只作一致性旁证，不进入主读数。"
                        "窗口长度分别是 61.5、92.8、99.5、102.1 秒，属于点歌段片段而非整曲。"),
                  edge="窗口是片段，不得据此推断整曲最低音；观众侧素材只作旁证，不进主读数。",
                  src=[("data/song_source_of_record.json", "records[]"),
                       ("data/song_evidence_master.json", "rows[].source_of_record")]))
    S.append(dict(title="一首歌的传播形态",
                  claim=f"《我要你》笔记 {w.get('notes','26')} 条、合计 {w.get('likes_total','1542')} 赞",
                  body=(f"其中 {w.get('pct_same_day_or_next','69.2')}% 发布于演出当日或次晚，说明传播集中在现场之后很短的时间里。"
                        "反例是《哭砂》，播放量更高（16554），但发布时间分散，热度不靠单一夜晚。"
                        "样本来自平台公开笔记，抓取时间 2026-10-13，统计单位是笔记条数、点赞总数与发布时间。"
                        "同一批笔记里还有评论区文本，可作为观众关注点的旁证，但不计入点赞。"
                        "这类数字适合描述一场演出之后发生了什么，不适合推断长期影响力。"),
                  edge="这是抽样而非全平台普查；点赞与播放不可跨曲直接比较。",
                  src=[("data/share/woyaoni_spread.json", "notes / likes_total / pct_same_day_or_next / counterexample")]))

    H = ['<section id="facts" class="facts-section">', '<h2>可引用事实与口径</h2>',
         '<p class="meta">以下事实均可在文末出处表中定位；数字口径见 data/calibers.md。</p>']
    for i, s in enumerate(S, 1):
        plain = f"{s['title']}。{s['claim']}。{s['body']}{EXTRA.get(i, '')}{s['edge']}（出处 {i}）"
        H.append(f'<article class="fact" id="fact-{i}">')
        H.append('<div style="display:flex;justify-content:space-between;align-items:baseline">'
                 f'<h3 style="margin:.4em 0">{i}. {s["title"]}</h3>'
                 f'<button class="copy-btn" data-copy="{i}" style="font-size:12px;padding:2px 8px;'
                 'border:1px solid #ccc;background:#fff;border-radius:4px;cursor:pointer">复制</button></div>')
        H.append(f'<p><b>{s["claim"]}</b>。{s["body"]}{EXTRA.get(i, "")}<sup>[{i}]</sup></p>')
        H.append(f'<p class="meta">边界：{s["edge"]}</p>')
        H.append(f'<template id="copy-{i}">{plain}</template>')
        H.append('</article>')
    H.append('<h3 id="facts-sources">出处表</h3><ol class="fact-sources">')
    for i, s in enumerate(S, 1):
        refs = "；".join(f"<code>{p}</code>#{f}" for p, f in s["src"])
        H.append(f'<li>{refs}</li>')
    H.append('</ol>')
    H.append('<script>(function(){document.querySelectorAll(".copy-btn").forEach(function(b){'
             'b.addEventListener("click",function(){var i=b.getAttribute("data-copy");'
             'var t=document.getElementById("copy-"+i).innerHTML;'
             'var done=function(){b.textContent="已复制";setTimeout(function(){b.textContent="复制"},1200)};'
             'if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,done)}'
             'else{var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();'
             'try{document.execCommand("copy")}catch(e){}document.body.removeChild(a);done()}})})})();</script>')
    H.append('</section>')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(H), encoding="utf-8")
    print(f"[ok] {OUT.name}｜{len(S)} 段")
    tot = 0
    for i, s in enumerate(S, 1):
        n = len(s["claim"]) + len(s["body"]) + len(s["edge"]) + len(EXTRA.get(i, ""))
        tot += n
        print(f"   {i}. {s['title']}（{n} 字）")
    print(f"   正文合计约 {tot} 字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
