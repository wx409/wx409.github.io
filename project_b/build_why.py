#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_why.py —— 深度长文：为什么王晰被低估（事实/解释/判断三层）"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT = ROOT / "why.html"


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s or ""))


def main():
    av = load("data/archive_vocal_albums.json")["summary"]
    vocal = load("data/archive_vocal.json").get("conclusion") or {}
    cal = {x["id"]: x["value"] for x in load("data/calibers.json")["calibers"]}
    songs = load("data/song_show_index.json").get("songs") or []
    dy = next((x for x in songs if x.get("song") == "多听有益"), {})
    low = av.get("lowest") or {}
    b1s = "、".join((vocal.get("b1_songs") or [])[:4])
    shows_all = cal.get("shows_all", 64)
    shows_tour = cal.get("shows_tour", 59)
    cities = cal.get("cities", 22)
    median = av.get("span_median_octaves")
    maxspan = av.get("span_max_octaves")
    stab = av.get("stability_cents_median")
    dy_lift = dy.get("avg_lift_pct")
    dy_n = dy.get("shows")

    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>为什么王晰被低估：一把用错的尺子｜王晰数字档案</title>
<meta name="description" content="王晰被低估，不是因为他不够好，而是因为评价他的尺子错了：B1 61.5Hz 的低频体感在手机外放上不可见；主流流行旋律不为男低音写作；他的核心资产是现场、耳机与体验，而非短视频传唱。本文把事实、解释与判断分开写。">
<meta name="robots" content="index, follow"><link rel="canonical" href="https://wx409.github.io/why.html">
<style>
body{{margin:0;background:#faf9f7;color:#1f2328;font:17px/1.85 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
main{{max-width:860px;margin:0 auto;padding:34px 22px 70px}}
h1{{font-size:34px;line-height:1.3;margin:0 0 10px}}
.stand{{font-size:19px;color:#444;border-left:4px solid #a8323d;padding-left:14px;margin:18px 0 26px}}
h2{{font-size:23px;margin:38px 0 10px;border-bottom:1px solid #e6e2dc;padding-bottom:6px}}
h3{{font-size:18px;margin:22px 0 6px}}
p{{margin:10px 0}}
.fact{{background:#fff;border:1px solid #e6e2dc;border-radius:12px;padding:14px 18px;margin:14px 0}}
.fact b{{color:#a8323d}}
.tag{{display:inline-block;font-size:12px;padding:1px 8px;border-radius:20px;background:#f3efe9;color:#6b5320;margin-right:6px}}
.warn{{background:#fffdf8;border:1px solid rgba(184,145,46,.35);border-radius:10px;padding:12px 16px;color:#6b5320;font-size:15px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e6e2dc;border-radius:10px;overflow:hidden;margin:12px 0}}
th,td{{padding:8px 12px;border-bottom:1px solid #e6e2dc;font-size:15px;text-align:left}}th{{background:#f3efe9}}
a{{color:#a8323d;text-decoration:none}}
.small{{color:#777;font-size:14px}}
</style></head><body><main>
<h1>为什么王晰被低估：一把用错的尺子</h1>
<p class="stand">他不是“不够好”，他是“好”的方式，刚好不是这个市场最容易被看见的方式。</p>

<p>先把结论放在前面：<b>王晰的问题，主要不是音域，也不是唱功，而是“产品形态”和“评价体系”错配。</b>他的核心资产是低频体感、现场声压、低音里的清晰度；市场的主要终端是手机外放、短视频、流媒体播放量。这三把尺子，都不测他最强的东西。</p>

<div class="warn">下面把“事实”“解释”“判断”分开写。事实可查；解释是我的分析；判断是观点，不是数据。</div>

<h2>一、事实：他到底做到了什么</h2>
<div class="fact">
<p><span class="tag">事实</span><b>最低稳定音 B1（{low.get('hz')}Hz）</b>，出自《{esc(low.get('song'))}》；72 首录音室曲目全量实测。</p>
<p><span class="tag">事实</span><b>低音主区 {esc(vocal.get('main_range'))}</b>，整体低于男低音参考音 E2（82.4Hz）。</p>
<p><span class="tag">事实</span><b>单曲跨度中位 {median} 个八度</b>，最大 {maxspan} 个八度；<b>音符内稳定性中位 {stab} 音分</b>。</p>
<p><span class="tag">事实</span><b>全站 {shows_all} 场 = 六轮巡演 {shows_tour} 场 + 签唱会 5 场</b>，覆盖 {cities} 城。</p>
<p><span class="tag">事实</span>现有对照样本里，<b>专辑层与“他人主导舞台”的最低稳定音差异不显著（p=0.197）</b>。注意：这不是“现场 vs 录音室”的检验，样本也有限，只能说明“未发现显著差异”。</p>
</div>
<p class="small">出处：<a href="/vocal.html">音域实测</a>、<a href="/voice.html">B1 是什么概念</a>、<a href="/research.html">研究索引</a>。</p>

<h2>二、解释：为什么这些事实没有变成市场</h2>

<h3>1）手机外放，放不出他的核心卖点</h3>
<p>B1 是 {low.get('hz')}Hz。手机扬声器、笔记本、大多数蓝牙小音箱的低频截止通常在 150–300Hz 以上；{low.get('hz')}Hz 的基频，在手机上基本放不出来，你听到的是泛音和房间反射。</p>
<p>所以：他在现场、耳机、好音响里是“低音炮”；在手机外放和短视频里，这个优势被物理屏蔽了。<b>不是他的声音普通，是他的产品形态需要环境。</b></p>

<h3>2）主流流行旋律，不为这个声部写作</h3>
<p>这不是“没人喜欢低音”，而是供给问题：主流流行歌的旋律重心偏中高音区，低音声部在流行工业里不是主赛道。结果是，他拿到的原料大多是“降调翻唱”或“用低音当点缀”，而不是“为这个声部量身写的主打歌”。</p>
<p>这能解释一个表面矛盾：<b>他翻唱常常比原创更出圈</b>。不是团队不努力，是“歌本身有没有为这个声音留位置”。</p>

<h3>3）他的稀缺不是“低”，是“低 + 清 + 稳”</h3>
<p>很多男低音低得下去，但会糊、会闷、听不清字。频率越低，共鸣腔的共振峰间距越窄，元音区分越难——这是声乐里公认的硬难题。王晰同时拿着“低”和“清楚”两个互相打架的属性，这才是他真正难被复制的地方。</p>

<h3>4）现场与录音室：不是“完全一样”，是“没有显著落差”</h3>
<p>现有对照里，他的专辑层与“他人主导舞台”的最低稳定音差异不显著（p=0.197）。这不能被写成“他现场和录音室完全一样”，更不能写成“证明了一套抗干扰技术体系”。准确说法是：<b>在现有样本里，没有发现显著的能力落差。</b></p>

<h2>三、判断：他更适合什么赛道</h2>
<p><span class="tag">判断</span>如果继续用“流行男歌手 / 短视频爆款”的尺子量他，结论永远是“可惜”。但他真正值钱的场景，可能是另一组：</p>
<table>
<tr><th>场景</th><th>为什么适合</th></tr>
<tr><td>剧场 / 音乐剧</td><td>低频需要空间和声压；他的声音在剧场里不是“点缀”，是“建筑”</td></tr>
<tr><td>耳机 / 音响向录音</td><td>{low.get('hz')}Hz 的基频，只有好设备能放出来</td></tr>
<tr><td>朗读 / 有声 / 哄睡</td><td>低而清楚的声音，是这类内容最稀缺的原料</td></tr>
<tr><td>爵士 / Bossa / 慢歌现场</td><td>不靠高音刺激，靠音色、气息、空间</td></tr>
<tr><td>纪录片 / 旁白</td><td>低音 + 咬字清楚，天然适合叙述</td></tr>
</table>
<p>这些场景的共同点是：<b>消费者为“体验”付费，不为“旋律传唱度”付费。</b>在这些场景里，低频不是劣势，是门票本身。</p>

<h3>关于“贵”</h3>
<p><span class="tag">判断</span>他像一件“奢侈乐器”：造价高、维护贵、不可复制，但市场一直用“普通歌手”的单价在采购。问题不在他“不够努力”，在他被放错了货架。</p>

<h2>四、边界：哪些话不能说</h2>
<div class="fact">
<p><b>❌ “64 场巡演”</b>：全站 {shows_all} 场 = 巡演 {shows_tour} + 签唱会 5。写“64 场演出”可以，写“64 场巡演”是错的。</p>
<p><b>❌ “3.5 个八度是常态”</b>：单曲跨度中位 {median} 个八度；最大 {maxspan} 是极值，不是大多数歌的样子。</p>
<p><b>❌ “p=0.197 证明现场和录音室一样”</b>：它检验的是专辑层 vs 他人主导舞台，且是“未发现显著差异”，不是“证明无差异”。</p>
<p><b>❌ “男低音的歌男高音唱不了”</b>：唱得了旋律，唱不出那个物理质感。准确说法是“可唱，但不可替代”。</p>
<p><b>❌ “61.5Hz 先被身体听到”</b>：需要足够声压；手机外放上你连基频都听不到。体感是有条件的。</p>
</div>

<h2>五、如果你只做三件事</h2>
<ol>
<li><b>戴耳机听一首</b>：先听《多听有益》或《静止了的夜晚》，把音量开到你能承受的七成。</li>
<li><b>看一场现场</b>：不是看直拍，是去剧场/音乐会，感受低频在空间里的样子。</li>
<li><b>用事实卡传播</b>：B1 {low.get('hz')}Hz；单曲中位 {median} 个八度；{shows_all} 场演出（巡演 {shows_tour} + 签唱会 5）。别用 3.5 当常态，别把“稳”当卖点。</li>
</ol>

<h2>六、一个可验证的例外</h2>
<p>25 场有指数窗口的演出、26 首常唱曲目里，<b>《多听有益》是唯一唱完指数明显上涨的歌</b>：{dy_n} 场平均 <b>+{dy_lift}%</b>。不是因为它“最高级”，而是因为歌名、低音下探、可剪辑性，第一次形成了“人歌合一”的闭环。</p>
<p class="small">口径与明细：<a href="/docs/交叉分析_曲目×指数×场次_2026-11-22.md">曲目×指数×场次交叉分析</a>。</p>

<h2>收尾</h2>
<p>王晰不是“唱歌很低的男歌手”。他是一件以人形存在的低音乐器，恰好还会说话、会温柔、会在凌晨哄你睡觉。</p>
<p>市场迄今做过的最荒谬的事，是拿着手机外放，去鉴定一把低音提琴的好坏。</p>
<p><b>不是尺子上的数字错了，是尺子选错了。</b></p>
<p class="small">本文事实来自站内实测与口径表；解释与判断为作者观点。最后更新：2026-11-22。</p>
</main></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print("写入", OUT, "| B1", low.get("hz"), "| shows", shows_all, "/", shows_tour)


if __name__ == "__main__":
    main()
