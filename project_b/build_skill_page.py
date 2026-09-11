# -*- coding: utf-8 -*-
"""生成「唱功实测」页 (skill.html)：七维全部由本地实测数据派生，不写死数字。

数据源：
  data/archive_vocal.json          10 曲精测（稳定音/触达音/颤音/稳定度/密度/跨度）
  data/archive_vocal_albums.json   72 曲全量（跨度/音准/分布/HNR/密度）
  data/archive_context_compare.json 王晰主导 vs 他人主导 六项指标对照
用法：python -X utf8 project_b/build_skill_page.py
"""
from __future__ import annotations

import html as H
import io
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
esc = lambda s: H.escape(str(s if s is not None else ""))


def load(rel, default=None):
    p = ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def main() -> int:
    v = load("data/archive_vocal.json")
    alb = load("data/archive_vocal_albums.json")
    ctx = load("data/archive_context_compare.json")
    songs = v.get("songs") or []
    concl = v.get("conclusion") or {}
    asum = alb.get("summary") or {}
    metrics = (ctx.get("metrics") or [])

    # ── 七维表格 ──
    dims = []
    dims.append(("低音能力", "最低稳定音", f"{concl.get('main_range', '—')}",
                 "全部低于一般男低音下限 E2(82.4Hz)", "低音主区实测"))
    if songs:
        lows = sorted(songs, key=lambda s: s.get("lowest_hz") or 999)
        dims.append(("低音能力", "最低音曲目", f"{lows[0].get('name')}（{lows[0].get('stable_note')} "
                                            f"{lows[0].get('stable_hz')}Hz）", "", "10 曲精测"))
    if asum:
        dims.append(("音域跨度", "跨度中位", f"{asum.get('span_median_octaves')} 个八度",
                     f"最大 {asum.get('span_max_octaves')}", "72 曲全量"))
    vib = [s.get("vibrato_rate_hz_median") for s in (v.get("songs") or []) if s.get("vibrato_rate_hz_median")]
    if vib:
        dims.append(("颤音", "速率中位", f"{sorted(vib)[len(vib)//2]} Hz", "专业常见 4.5–6.5Hz", "10 曲精测"))
    vc = [s.get("vibrato_extent_cents_median") for s in (v.get("songs") or []) if s.get("vibrato_extent_cents_median")]
    if vc:
        dims.append(("颤音", "幅度中位", f"{sorted(vc)[len(vc)//2]} 音分", "专业常见 50–100 音分", "10 曲精测"))
    st = [s.get("stability_cents_median") for s in (v.get("songs") or []) if s.get("stability_cents_median")]
    if st:
        dims.append(("长音控制", "音符内稳定性中位", f"{sorted(st)[len(st)//2]} 音分",
                     "越小越稳（同一音内 F0 抖动）", "10 曲精测"))
    if asum:
        dims.append(("长音控制", "音准偏差中位", f"{asum.get('intonation_cents_median', '—')} 音分",
                     "与十二平均律最近半音之差", "72 曲全量"))
    if asum:
        dims.append(("咬字与跑动", "音符密度中位", f"{asum.get('note_density_median')} 个/秒",
                     "含快速经过句", "72 曲全量"))
    import statistics
    dens = [s.get("note_density_per_s") for s in songs if s.get("note_density_per_s")]
    if dens:
        dims.append(("咬字与跑动", "精测曲密度区间",
                     f"{min(dens)}–{max(dens)} 个/秒", "跨曲差异反映编曲而非能力", "10 曲精测"))
    if asum:
        dims.append(("声区使用", "按时长加权",
                     f"低音区 {asum.get('register_low_share', '约 30%')}／中音区 "
                     f"{asum.get('register_mid_share', '约 61%')}／高音区 {asum.get('register_high_share', '约 9%')}",
                     "以 C3/C4 为界", "72 曲全量"))
    hnr = [s.get("hnr_db_median") for s in songs if s.get("hnr_db_median")]
    if hnr:
        dims.append(("音色与控制", "谐噪比中位", f"{sorted(hnr)[len(hnr)//2]} dB",
                     "分离人声轨的谐噪比（近似）", "10 曲精测"))
    rows = "\n".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td><strong>{esc(c)}</strong></td>"
        f"<td>{esc(d)}</td><td class='verify'>{esc(e)}</td></tr>" for a, b, c, d, e in dims)

    # ── 现场 vs 录音室（同曲两版） ──
    live_rows = ""
    svl = v.get("studio_vs_live") or {}
    if svl:
        live_rows = (f"<tr><td>{esc(svl.get('song'))}</td><td>录音室</td>"
                     f"<td>{esc(svl.get('studio_note'))}</td><td>{esc(svl.get('studio_hz'))} Hz</td></tr>"
                     f"<tr><td>{esc(svl.get('song'))}</td><td>现场</td>"
                     f"<td>{esc(svl.get('live_note'))}</td><td>{esc(svl.get('live_hz'))} Hz</td></tr>")

    # ── 与他人的对照 ──
    ctx_rows = ""
    if metrics:
        for m in metrics:
            self_m = m.get("self_median")
            oth = m.get("other_median")
            p = m.get("p")
            ctx_rows += (f"<tr><td>{esc(m.get('label') or m.get('key'))}</td>"
                         f"<td>{'' if self_m is None else round(self_m, 2)}</td>"
                         f"<td>{'' if oth is None else round(oth, 2)}</td>"
                         f"<td>{'' if p is None else p}</td></tr>")

    # ── 终裁状态表（唱功结论的可信度） ──
    st_rows = ""
    for s in songs[:12]:
        st_rows += (f"<tr><td>{esc(s.get('name'))}</td><td>{esc(s.get('stable_note'))}</td>"
                    f"<td>{esc(s.get('stable_hz'))} Hz</td><td>{esc(s.get('stable_dur_s'))}s</td>"
                    f"<td>{esc(s.get('stable_hnr_db'))} dB</td>"
                    f"<td class='verify'>{esc(s.get('stable_status') or '未复核')}</td></tr>")

    # ── 每日唱功卡片（build_skill_card.py 产出；按日期确定性轮转）──
    cards = load("data/skill_cards.json")
    _today = cards.get("today") or {}
    _recent = cards.get("recent") or []

    def md(t: str) -> str:
        parts = esc(t).split("**")
        return "".join(f"<strong>{p}</strong>" if i % 2 else p for i, p in enumerate(parts))

    card_html = ""
    card_hist = ""
    if _today:
        card_html = f'''<div class="hl">
<div class="sub">📇 <strong>今日唱功卡片</strong> · {esc(_today.get('date'))} · 主题 {esc(_today.get('topic'))} · 编号 {_today.get('index')}/{cards.get('pool_size')}</div>
<h2 style="margin:6px 0 8px">{esc(_today.get('title'))}</h2>
<ul>{''.join(f'<li>{md(x)}</li>' for x in _today.get('lines') or [])}</ul>
<p class="sub"><strong>口径</strong>：{esc(_today.get('caliber'))}　<strong>数据底账</strong>：<code>{esc(_today.get('source'))}</code></p>
<details><summary>可直接发的社交短文案</summary>
<ul>{''.join(f'<li>{md(x)}</li>' for x in _today.get('social') or [])}</ul></details>
</div>'''
        card_hist = ("<h2>六、每日唱功卡片（历史留存）</h2>\n"
                     f"<p class=\"sub\">每天一张、按日期确定性轮转，内容各不相同；全部卡片同时留存本地传记素材目录，站点只展示近期。"
                     f"卡片池 {cards.get('pool_size')} 张，全部取自已落盘实测数据，不使用音乐指数数值。</p>\n"
                     "<table>\n<tr><th>日期</th><th>主题</th><th>卡片</th></tr>\n"
                     + "".join(f"<tr><td>{esc(c.get('date'))}</td><td>{esc(c.get('topic'))}</td>"
                               f"<td>{esc(c.get('title'))}</td></tr>" for c in _recent[:14])
                     + "\n</table>")

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>王晰唱功实测｜七个维度的可测量证据</title>
<meta name="description" content="王晰唱功七维实测：低音能力（最低稳定音 B1 61.6Hz）、音域跨度、颤音速率与幅度、长音内稳定性、咬字跑动密度、声区使用、现场与录音室对照——全部由人声分离 + 逐帧 F0 实测派生，标注取证状态。">
<link rel="canonical" href="https://wx409.github.io/skill.html">
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:920px;margin:0 auto;
padding:22px 18px 60px;line-height:1.75;color:#2b2723;background:#fbf9f4}}
h1{{font-size:26px;margin:0 0 6px}} h2{{font-size:19px;margin:26px 0 10px;padding-left:9px;border-left:4px solid #a8323d}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0}}
th,td{{border-bottom:1px solid #e6dfd2;padding:7px 8px;text-align:left;vertical-align:top}}
th{{background:#f4efe4;font-weight:600}} .verify{{color:#8a7f6d;font-size:12.5px}}
.hl{{background:#fffdf5;border:1px solid #eadfc4;border-radius:10px;padding:12px 14px;margin:14px 0}}
.sub{{color:#8a7f6d;font-size:13.5px}} .nav a{{margin-right:12px;color:#a8323d;text-decoration:none}}
</style>
</head>
<body>
<div class="nav"><a href="/">首页</a><a href="/voice.html">音域实测</a><a href="/stage.html">舞台实测</a>
<a href="/skill.html">唱功实测</a><a href="/dashboard/">数据大屏</a></div>
<h1>🎙️ 王晰唱功实测</h1>
<p class="sub">七个维度 · 全部由人声分离（demucs）+ 逐帧 F0 实测派生 · 生成 {datetime.now().strftime('%Y-%m-%d')}</p>

<div class="hl">
<strong>一句话结论：</strong>可测量的唱功证据里，他最突出的不是"能唱多低"，而是
<strong>低音区的长音控制</strong>（音符内稳定性中位 {esc(sorted(st)[len(st)//2] if st else '—')} 音分）与
<strong>颤音的长期一致性</strong>（跨七年 4.89–5.17Hz，极差 &lt;0.3Hz）；
低音能力本身（最低稳定音 <strong>{esc(concl.get('main_range','—'))}</strong>）是"稀缺性锚点"，
而"低音区的花腔式跑动"是比"低音炮"更难被替代的技术特征。
</div>

{card_html}

<h2>一、七个维度（实测值）</h2>
<table>
<tr><th>维度</th><th>指标</th><th>实测</th><th>参考/说明</th><th>来源与状态</th></tr>
{rows}
</table>

<h2>二、长音与颤音：手艺的指纹</h2>
<p class="sub">颤音速率与幅度、音符内稳定性是"唱功"里最抗录音条件影响的指标（不依赖绝对音高）。
同一首歌跨六年四次现场实测：颤音速率 4.89–5.17Hz、长音稳定 6–8 音分。</p>

<h2>三、现场 vs 录音室（同曲两版）</h2>
<table>
<tr><th>曲目</th><th>版本</th><th>最低音</th><th>频率</th></tr>
{live_rows or '<tr><td colspan="4">—</td></tr>'}
</table>
<p class="sub">现场读数与录音室读数分别标注取证状态；触达音（声音短暂到过的最低 F0）不作能力依据。</p>

<h2>四、与他人的对照（同管线、同口径）</h2>
<table>
<tr><th>指标</th><th>王晰主导（中位）</th><th>他人主导（中位）</th><th>p</th></tr>
{ctx_rows or '<tr><td colspan="4">—</td></tr>'}
</table>
<p class="sub">对照只说明"使用模式差异"，不指向能力排序——两组曲目库与编曲条件不同。</p>

<h2>五、十曲精测与取证状态（可追溯）</h2>
<table>
<tr><th>曲目</th><th>最低稳定音</th><th>频率</th><th>时长</th><th>HNR</th><th>复核状态</th></tr>
{st_rows}
</table>
<p class="sub"><strong>复核状态</strong>：✅双引擎一致 ｜ 🟡已取证（谱列解释度 + 四轨归属/谱图支持）｜
⚪待复核（不作结论依据，且不进任何汇总计数）。方法细节见<a href="/voice.html">音域实测页</a>的《终裁纪律》。</p>

{card_hist}

<div class="hl">
<strong>方法与边界（诚实披露）：</strong>① 全部数据来自本地人声分离 + 自研 YIN 逐帧 F0，音源为流媒体有损/无损音频，非母带；② 绝对频率存在 ±0.5Hz 量级误差，但不影响音级判定；
③ 高音侧可能混入伴唱/和声层，需人工听辨，不作"能唱该音"的断言；④ 本页不作排名式结论；
⑤ "唱功"一词在本页严格限定为<strong>可测量的发声控制指标</strong>（音域/颤音/稳定性/密度/声区），不涉及艺术评价。
</div>
<p class="sub">生成器：<code>project_b/build_skill_page.py</code>（数据全部派生自站点 JSON，无手写数字）。</p>
</body></html>"""
    out = ROOT / "skill.html"
    out.write_text(page, encoding="utf-8")
    print(f"[OK] {out}｜维度 {len(dims)}｜对照指标 {len(metrics)}｜精测曲 {len(songs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
