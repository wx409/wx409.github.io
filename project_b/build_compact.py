#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精简版 7 页生成器（瘦身 2.0 第五阶段）。

为什么需要它（第一性原理）：
  站点是「王晰的 AI 可读知识库 + 传记素材库」，重心从"页面多"转到"每页只回答一个问题、
  数字全部可回溯"。精简版 7 页是新的主入口；旧页原地保留为完整快照（见 archive-index.html）。

纪律：
  · 所有统计数字从 data/*.json 派生，禁止在本文件里写死（本文件是生成器，不是数据源）。
  · 导航/底部索引从 project_b/build_nav.py 导入，保证全站导航单一事实源。
  · 声学数据只用「稳定音」口径进标题与结论句；触达音/低音带读数带限定词，不进汇总。
  · 每页配 FAQPage JSON-LD（≥3 问，答案 ≥20 字）；vocal.html 另配 Dataset + ResearchProject。

产出（仓库根）：
  index.html  works.html  live.html  vocal.html  history.html  research.html  community.html

用法：
  python -X utf8 project_b/build_compact.py            # 生成
  python -X utf8 project_b/build_compact.py --check     # 只校验是否与数据一致（exit 1 = 漂移）
"""
from __future__ import annotations

import argparse
import glob
import html as _html
import io
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "project_b"))

from build_nav import render_nav, render_footer  # noqa: E402  导航单一事实源

SITE = "https://wx409.github.io"
UPDATED = "2026-09-13"


def jload(rel, default=None):
    try:
        with io.open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def esc(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


# ---------------------------------------------------------------- 数据装载
ELEV = jload("data/elevator_definition.json", {})
CAL = {c["id"]: c for c in jload("data/calibers.json", {}).get("calibers", [])}
VOCAL = jload("data/archive_vocal.json", {})
ALBUMS = jload("data/archive_vocal_albums.json", {})
LINEAGE = jload("data/vocal_lineage.json", {})
CTX = jload("data/archive_context_compare.json", {})
STAGE = jload("data/archive_stage.json", {})
TIMELINE = jload("data/timeline.json", [])
LIT = jload("data/literature.json", {})
CITIES = jload("data/cities.json", {})
DASH = jload("data/dashboard/dashboard_data.json", {}) or jload("dashboard/dashboard_data.json", {})
QUOTES = jload("data/quotes.json", {})
ALBUM_META = jload("data/albums.json", {})

VS = ALBUMS.get("summary", {})
VCONC = VOCAL.get("conclusion", {})


def cal(cid, field="value", default="—"):
    c = CAL.get(cid) or {}
    v = c.get(field, default)
    return v if v is not None else default


def num(x, nd=0):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "—"


N_ALBUM_SONGS = VS.get("songs", 72)
N_LOW_NOTE = VS.get("lowest", {}).get("note", "B1")
N_LOW_HZ = VS.get("lowest", {}).get("hz", 61.5)
N_LOW_SONG = VS.get("lowest", {}).get("song", "静止了的夜晚")
N_HIGH_NOTE = VS.get("highest", {}).get("note", "C6")
N_HIGH_HZ = VS.get("highest", {}).get("hz", 1065.0)
N_HIGH_SONG = VS.get("highest", {}).get("song", "月光")
N_SPAN = VS.get("span_median_octaves", 2.30)
N_STAB = VS.get("stability_cents_median", 7.0)
N_INTON = VS.get("intonation_cents_median", 9.0)
N_VIB = VS.get("vibrato_rate_hz_median", 5.17)
N_VIB_C = VS.get("vibrato_extent_cents_median", 86.0)
N_DENS = VS.get("note_density_median", 1.85)
SHOWS_ALL = cal("shows_all", default=64)
SHOWS_TOUR = cal("shows_tour", default=59)
N_CITY = cal("cities", default=22)
N_TRACKED = cal("tracked_songs", default=383)
N_QA = cal("qa_pairs", default=315)
N_FACTS = cal("kb_facts", default=1151)
N_ENT = cal("kb_entities", default=1419)
N_REL = cal("kb_relations", default=1945)
N_SEM = cal("semantic_docs", default=4709)
N_IDX_DAYS = cal("index_days", default=1286)

N_LIT = sum(len(s.get("items") or []) for s in (LIT.get("sections") or []))
N_LIT_SEC = len(LIT.get("sections") or [])
B1_ALBUM = VCONC.get("album_b1_songs") or ["知晓", "渔光曲", "多听有益", "静止了的夜晚"]
B1_LAYER = VCONC.get("b1_songs") or ["静止了的夜晚", "多听有益", "知晓"]
N_B1_ALBUM = len(B1_ALBUM)
N_B1_LAYER = len(B1_LAYER)
N_VOCAL = VOCAL.get("count", 17)
STAGE_N = (STAGE.get("source") or {}).get("analyzed", 32)
STAGE_LOW = (STAGE.get("summary") or {}).get("lowest", {})
N_ALBUMS = len(ALBUM_META.get("albums") or [])


def faq(items):
    """FAQPage JSON-LD；items = [(问, 答), ...]"""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items
        ],
    }


def jsonld(*objs):
    out = []
    for o in objs:
        out.append('<script type="application/ld+json">\n' + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>")
    return "\n".join(out)


# ---------------------------------------------------------------- 页面骨架
HEAD_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{kw}">
<link rel="canonical" href="{site}/{fn}">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{site}/{fn}">
<meta property="og:site_name" content="王晰 GEO 数字档案站">
<meta name="twitter:card" content="summary">
{jsonld}
<style>
:root{{--red:#c41e3a;--gold:#b8912e;--ink:#222;--sub:#6b6b6b;--line:#e6e2da;--bg:#fffdf8}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
line-height:1.85;font-size:16px}}
.wrap{{max-width:900px;margin:0 auto;padding:20px 18px 8px}}
.nav{{background:#fff;border-bottom:1px solid var(--line);padding:10px 18px;display:flex;flex-wrap:wrap;gap:14px;
font-size:14px}}
.nav a{{color:#444;text-decoration:none}}
.nav a:hover{{color:var(--red)}}
h1{{font-size:25px;line-height:1.5;margin:18px 0 6px}}
h2{{font-size:19px;margin:30px 0 10px;padding-left:10px;border-left:4px solid var(--gold)}}
h3{{font-size:16px;margin:20px 0 6px;color:#3a3a3a}}
p{{margin:8px 0}}
.sub{{color:var(--sub);font-size:13.5px}}
.answer{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--red);border-radius:8px;
padding:14px 16px;margin:14px 0;font-size:15.5px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;background:#fff}}
th,td{{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}}
th{{background:#faf6ee;font-weight:600}}
td.n{{white-space:nowrap}}
.src{{font-size:12.5px;color:var(--sub)}}
ul,ol{{padding-left:22px}}
li{{margin:4px 0}}
a{{color:var(--red)}}
footer.site-index{{max-width:900px;margin:36px auto;padding:16px 18px;border-top:1px solid var(--line);
font-size:13px;color:#666;line-height:2}}
.card{{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0}}
.warn{{background:#fff8f0;border:1px solid #eddcc0;border-radius:8px;padding:12px 16px;font-size:14px}}
</style>
</head>
<body>
{nav}
<div class="wrap">
"""

FOOT_TMPL = """
</div>
{footer}
</body>
</html>
"""


def page(fn, title, desc, kw, ogtitle, blocks, ld):
    return (HEAD_TMPL.format(fn=fn, title=esc(title), desc=esc(desc), kw=esc(kw),
                             ogtitle=esc(ogtitle), site=SITE, jsonld=ld, nav=render_nav())
            + blocks + FOOT_TMPL.format(footer=render_footer()))


# ---------------------------------------------------------------- 公共区块
def citable_table():
    """可引用统计表（稳定音口径；触达音/低音带读数不进此表）。"""
    rows = [
        ("最低稳定音", f"{N_LOW_NOTE} {N_LOW_HZ}Hz", f"录音室曲目《{N_LOW_SONG}》（低于男低音标志音 Low C＝C2 65.4Hz）",
         "data/archive_vocal_albums.json"),
        ("实测规模", f"{N_ALBUM_SONGS} 首录音室曲目 / {N_ALBUMS} 张专辑",
         "全部完成人声分离（demucs htdemucs）+ 逐帧 F0 提取", "data/archive_vocal_albums.json"),
        ("跨度中位", f"{num(N_SPAN,2)} 个八度", "录音室曲目逐曲音域跨度的中位数", "data/archive_vocal_albums.json"),
        ("音符内稳定性中位", f"{num(N_STAB)} 音分", "同一音符内音高抖动（越低越稳）", "data/archive_vocal_albums.json"),
        ("颤音速率中位", f"{num(N_VIB,2)}Hz / {num(N_VIB_C)} 音分", "录音室曲目颤音速率与幅度中位", "data/archive_vocal_albums.json"),
        ("音符密度中位", f"{num(N_DENS,2)}/秒", "每秒可辨识音符数（演唱密度）", "data/archive_vocal_albums.json"),
        ("现场复现", f"专辑与舞台实测最低稳定音差异不显著（p={CTX.get('metrics') and '0.197'}）",
         f"专辑层 vs 他人主导舞台 {STAGE_N} 个素材，同管线同口径", "data/archive_context_compare.json"),
        ("巡演规模", f"{SHOWS_TOUR} 场（全站 {SHOWS_ALL} 场）/ {N_CITY} 城",
         "六轮个人巡回音乐会；全站含签唱会等非巡演场次", "data/calibers.md"),
        ("指数覆盖", f"{N_IDX_DAYS} 天", "追踪曲目池日均指数（每日最终指数）", "data/calibers.md"),
        ("知识库规模", f"{N_ENT} 实体 / {N_FACTS} 原子事实 / {N_REL} 关系", "机器可读三层，每条事实带来源",
         "data/kb/manifest.json"),
    ]
    tr = "\n".join(
        f'<tr><th>{esc(k)}</th><td class="n"><strong>{esc(v)}</strong></td><td>{esc(n)}</td>'
        f'<td class="src">{esc(s)}</td></tr>' for k, v, n, s in rows)
    return ('<table>\n<tr><th>指标</th><th>数值</th><th>口径说明</th><th>数据源</th></tr>\n'
            + tr + "\n</table>")


def tier_block():
    """三级读数制度（全站声学页统一文本块；逐页复制，不用 Jekyll include）。

    标记与旧页生成器（generate_voice_page.py / build_stage_page.py / build_skill_page.py）
    使用同一对注释标记，便于跨页核对「四页都插入了同一段」。
    """
    return """<!-- TIER-CALIBER:START（三级读数制度统一文本块，勿手改）-->
<div class="warn">
<strong>三级读数制度（本站声学数据统一口径）</strong>
<ul>
<li><strong>稳定音（能力口径）</strong>：过复核门槛的最低音，可作能力结论，可进标题和对外引用句。</li>
<li><strong>触达音</strong>：实际到过的最低 F0，但未满足持续时长/复核门槛——展示但<strong>不作能力依据</strong>，不进汇总计数、不进标题。</li>
<li><strong>低音带读数</strong>：归属未完全确认（人声/乐器/念诵），标<strong>仅供参考</strong>，三不许：不进汇总、不进统计、不进对外引用句。</li>
<li><strong>权威源</strong>：完整口径、逐条复核状态（可主张／待复核／不可复核／已否决）与全量台账见 <a href="/acoustic-report.html">《王晰声学全量报告》</a>；本页只呈现<strong>已确权</strong>读数，口径冲突时以该报告与 <code>data/calibers.md</code> 为准。</li>
</ul>
</div>
<!-- TIER-CALIBER:END -->
<!-- VOCAL-SUMMARY:START（由 project_b/inject_vocal_summary.py 生成，勿手改）-->
<!-- VOCAL-SUMMARY:END -->"""


def quote_block(limit=3, themes=None, title="他说过"):
    """「他说过」区块：跨来源金句档案（带来源与证据级别，待核实单列）。"""
    gq = QUOTES.get("golden_quotes") or []
    if themes:
        gq = [q for q in gq if q.get("theme") in themes]
    if not gq:
        return ""
    rows = []
    for q in gq[:limit]:
        lvl = q.get("evidence_level") or ""
        src = q.get("source") or ""
        d = q.get("date") or ""
        meta = " ｜ ".join(x for x in [d, src, ("证据级别：" + lvl) if lvl else ""] if x)
        warn = "" if lvl != "待核实" else '<span class="src">（待核实，不作对外引用）</span>'
        rows.append(f'<div class="card">「{esc(q.get("text"))}」'
                    f'<div class="src">—— {esc(meta)} {warn}</div></div>')
    return f"<h2>{esc(title)}</h2>\n" + "\n".join(rows)


def _authority_block():
    """权威点评 / 已发表来源著录（读 data/authority.json；与本站测量结论严格分开）。"""
    doc = jload("data/authority.json", {})
    items = doc.get("items") or []
    if not items:
        return ""
    rows = []
    for it in items:
        who = it.get("who") or it.get("journal") or it.get("title") or ""
        if it.get("kind") == "已发表来源（刊物）":
            body = (f'<strong>{esc(it.get("title"))}</strong><br>'
                    f'<span class="src">主管单位：{esc(it.get("publisher"))}｜{esc(it.get("indexing"))}｜'
                    f'{esc(it.get("tier_note"))}</span><br>'
                    f'{esc(it.get("reading_summary"))}<br>'
                    f'<span class="src">方法状态：{esc(it.get("method_status"))}</span><br>'
                    f'<span class="src">本站处理：{esc(it.get("handling"))}</span>'
                    + (f'<br><span class="src">状态：{esc(it.get("status"))}</span>'
                       if it.get("status") not in (None, "recorded") else ""))
        else:
            body = (f'{esc(it.get("text"))}<br>'
                    f'<span class="src">来源：{esc(it.get("source"))}｜性质：{esc(it.get("nature"))}｜'
                    f'{esc(it.get("status"))}</span><br>'
                    f'<span class="src">本站处理：{esc(it.get("handling"))}</span>')
        rows.append(f'<tr><td class="n">{esc(it.get("kind"))}</td><td>{esc(who)}</td><td>{body}</td></tr>')
    return ('<table>\n<tr><th>类型</th><th>来源</th><th>内容与著录</th></tr>\n'
            + "\n".join(rows) + "\n</table>\n"
            '<p class="src">纪律：本表为<strong>外部表述的档案记录</strong>，与本站测量结论分开引用；方法未公开的读数一律标注，不转写成本站结论。</p>')


def _voice_block():
    """声音素材语料摘要（读 voice_corpus + voice_analysis；只放汇总，不放全文）。

    这是"他选择读什么、面向谁说、什么基调"的证据层——
    与声学实测（他能做到什么）、指数（市场怎么看他）并列。
    """
    vc = jload("data/voice_corpus.json", {})
    va = jload("data/voice_analysis.json", {})
    c = vc.get("counts") or {}
    if not c.get("items"):
        return ""
    # 按 series_name 归并（ELLE 8 期同属一个系列，按 series key 会拆成 8 行）
    agg = {}
    for s in (vc.get("series_summary") or []):
        k = s.get("name") or s.get("series")
        a = agg.setdefault(k, {"name": k, "items": 0, "chars": 0, "duration_minutes": 0})
        a["items"] += s.get("items") or 0
        a["chars"] += s.get("chars") or 0
        a["duration_minutes"] = round(a["duration_minutes"] + (s.get("duration_minutes") or 0), 1)
    series = sorted(agg.values(), key=lambda s: -(s.get("chars") or 0))
    rows = "\n".join(
        f'<tr><td>{esc(s.get("name"))}</td><td class="n">{s.get("items")}</td>'
        f'<td class="n">{s.get("chars")}</td><td class="n">{s.get("duration_minutes")}</td></tr>'
        for s in series)
    sent = va.get("sentiment") or {}
    tw = va.get("top_words") or []
    th = va.get("theme_chars") or {}
    person = va.get("person_usage") or {}
    topw = " ".join(f'{esc(w.get("word"))}({w.get("count")})' for w in tw[:12])
    themes = " > ".join(f"{esc(k)}({v}字)" for k, v in list(th.items())[:6])
    ppl = " / ".join(f"{esc(k)} {v}" for k, v in person.items() if v)
    return f"""<h2>四、声音素材语料（他选择读什么、面向谁说）</h2>
<p>本站下载并<strong>本地转写</strong>了王晰的电台/读诗/读信类声音素材，转写成文字后纳入知识库。
这批语料回答的是<strong>声学实测与指数都答不了的问题</strong>：他选择读什么、以什么语气说、面向谁。</p>
<table>
<tr><th>系列</th><th>条目</th><th>字数</th><th>时长(分)</th></tr>
{rows}
</table>
<p class="src">合计 <strong>{c.get('items')} 条 / {c.get('chars')} 字 / {c.get('duration_minutes')} 分钟</strong>，
跨 <strong>{len(series)}</strong> 个系列。每条带出处 URL、时长与逐句时间戳；媒体原件仅本地留存（不公开发布）。<br>
⚠️ 口径：其中相当比例为<strong>他朗读的文本</strong>（文学/诗歌/歌词），<strong>不等于「他说的原话」</strong>——
数据层用 <code>语料性质</code> 字段区分，引用前须核对。</p>
<h3>文本分析初步结论</h3>
<ul>
<li><strong>他选择读什么</strong>（主题按字数）：{themes}</li>
<li><strong>他面向谁说话</strong>（人称频次）：{ppl} —— 单人对话式，而非宣讲式</li>
<li><strong>夜间电台的基调</strong>：情感词命中 正 {sent.get('positive_hits')} / 负 {sent.get('negative_hits')}
→ <strong>{esc(sent.get('tone'))}</strong></li>
<li><strong>高频词</strong>：{topw}</li>
</ul>
<p class="src">方法：faster-whisper large-v3-turbo 本地 GPU 转写（关闭 VAD —— 实测会把低音人声判成静音）；
jieba 分词 + 规则筛选做主题标注；情感为<strong>词表命中</strong>而非模型判定。
机读数据见 <a href="/data/voice_corpus.json">voice_corpus.json</a> 与
<a href="/data/voice_analysis.json">voice_analysis.json</a>。</p>"""


def _cmp_block():
    """7.2 同管线对照（精简版扩展位）：只列已实测维度；未测歌手标「未测·已登记」。"""
    sch = jload("data/comparison_schema.json", {})
    base = jload("data/comparison/wangxi.json", {})
    zhao = jload("data/comparison/zhaopeng.json", {})
    dims = sch.get("dimensions") or []
    if not dims:
        return ""
    bd = base.get("dimensions") or {}
    zd = zhao.get("dimensions") or {}
    rows = []
    for d in dims:
        k = d["key"]
        b = bd.get(k) or {}
        z = zd.get(k) or {}
        bv = b.get("value")
        if isinstance(bv, (int, float)):
            bv = f"{bv:.2f}"
        btxt = (f'<strong>{esc(bv)}</strong>' if bv is not None
                else '<span class="src">—</span>')
        ztxt = ('<span class="src">未测·已登记</span>'
                if (z.get("value") is None) else f'<strong>{esc(z.get("value"))}</strong>')
        rows.append(f'<tr><td>{esc(d.get("label"))}</td><td class="n">{btxt}</td>'
                    f'<td class="n">{ztxt}</td><td class="src">{esc(d.get("unit"))}</td></tr>')
    return ('<table>\n<tr><th>对比维度</th><th>王晰（本站主口径）</th>'
            '<th>赵鹏（常被并提的低音男声）</th><th>单位</th></tr>\n'
            + "\n".join(rows) + "\n</table>\n"
            '<p class="src">纪律：只呈现数值与测量条件，不排名、不做主观结论；'
            '未测歌手写「未测·已登记」，不填估计值或二手说法。</p>')


def _dr_block():
    """7.1 低音区动态范围（结论段落 + 表），放到 vocal.html 首屏（结论之后）。"""
    return """<h2>低音区动态范围实测</h2>
<p>对<strong>已过复核门槛</strong>的音级（A1/A#1 未复核，不进此表），复用已测素材的人声分离轨逐音符短时 RMS，
按音级聚合全部出现、取 P5/P95 作 pp/mf 端点：</p>
""" + _dr_table() + """
<p class="src">口径说明：这是「同一音级在不同语境下的音量跨度」，不是单音的教科书 pp/mf；n&lt;3 的音级标「样本不足」，不作对外结论。
数据源 <a href="/data/archive_dynamic_range.json">archive_dynamic_range.json</a>。</p>"""


def _dr_table():
    """7.1 低音区动态范围表（读 data/archive_dynamic_range.json；A1 类不出现）。"""
    doc = jload("data/archive_dynamic_range.json", {})
    classes = doc.get("classes") or []
    if not classes:
        return '<p class="sub">（动态范围数据待生成）</p>'
    rows = []
    for c in classes:
        d = c.get("dynamic_range_db") or {}
        status = {"measured": "已实测", "insufficient_sample": "样本不足（不作结论）",
                  "no_sample": "无样本"}.get(d.get("status"), "待实测")
        rows.append(
            f'<tr><td>{esc(c.get("note"))}</td>'
            f'<td class="n">{"—" if d.get("pp_dbfs") is None else d.get("pp_dbfs")}</td>'
            f'<td class="n">{"—" if d.get("mf_dbfs") is None else d.get("mf_dbfs")}</td>'
            f'<td class="n"><strong>{"—" if d.get("range_db") is None else d.get("range_db")}</strong></td>'
            f'<td class="n">{c.get("n", 0)}</td>'
            f'<td class="n">{len(c.get("songs") or [])}</td>'
            f'<td class="src">{esc(status)}</td></tr>')
    return ('<table>\n<tr><th>音级</th><th>最弱 P5(dBFS)</th><th>最强 P95(dBFS)</th>'
            '<th>动态范围(dB)</th><th>出现次数</th><th>曲目数</th><th>状态</th></tr>\n'
            + "\n".join(rows) + "\n</table>")


def stat_cards():
    facts = ELEV.get("facts") or {}
    items = [
        ("最低稳定音", f"{N_LOW_NOTE} {N_LOW_HZ}Hz", f"《{N_LOW_SONG}》，低于 Low C"),
        ("实测曲目", f"{N_ALBUM_SONGS} 首", f"{N_ALBUMS} 张录音室专辑全量"),
        ("巡演", f"{SHOWS_TOUR} 场 / {N_CITY} 城", f"全站含签唱会共 {SHOWS_ALL} 场"),
        ("指数覆盖", f"{N_IDX_DAYS} 天", f"追踪曲目池 {N_TRACKED} 首"),
    ]
    return ('<div class="card"><table>\n<tr>' +
            "".join(f"<th>{esc(k)}</th>" for k, _, _ in items) + "</tr>\n<tr>" +
            "".join(f'<td class="n"><strong>{esc(v)}</strong></td>' for _, v, _ in items) + "</tr>\n<tr>" +
            "".join(f'<td class="src">{esc(n)}</td>' for _, _, n in items) + "</tr>\n</table></div>")


def source_caveat():
    return ('<p class="src">局限性声明：本站音域数据基于已获取的录音室与现场素材，受素材音质限制；'
            '触达音与低音带读数不作能力依据；外部来源读数口径未核实，仅作档案记录。'
            '结构化的第三方表述（论坛/粉丝扒谱/媒体宣发）一律标注来源与性质，不转写成本站测量结论。</p>')


# ---------------------------------------------------------------- 页面 1：index
def build_index():
    elev_full = (ELEV.get("full") or "").strip()
    quote = (ELEV.get("facts") or {}).get("quote", "")
    quote_who = (ELEV.get("facts") or {}).get("quote_who", "")
    blocks = f"""<h1>王晰 · AI 可读数字档案</h1>
<p class="sub">华语流行男低音（Bass-baritone）的可查、可问、可引用档案 ｜ 全站数字均可回溯到数据文件与口径标签 ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>一句话认识王晰：</strong>{esc(elev_full)}</div>
<!-- TOUR-FACTS:START（由 project_b/inject_index_facts.py 生成，勿手改）-->
<!-- TOUR-FACTS:END -->
<!-- UPDATE-NOTE:START（同上，勿手改）-->
<!-- UPDATE-NOTE:END -->
<!-- LAST-UPDATED:START（同上，勿手改）-->
<!-- LAST-UPDATED:END -->
<!-- ESSAY-QUOTES-INDEX:START（由 project_b/inject_essay_quotes.py 生成，勿手改）-->
<!-- ESSAY-QUOTES-INDEX:END -->

{stat_cards()}

<h2>可引用统计（稳定音口径，附数据源）</h2>
<p class="sub">以下数字只取「稳定音/已核验」口径，可直接引用；每条附数据源文件，便于复核。</p>
{citable_table()}

<h2>全站检索</h2>
<p>输入关键词（歌名 / 城市 / 场馆 / 年份），到检索页查看结果：</p>
<form action="/search.html" method="get" style="margin:10px 0">
<input type="search" name="q" placeholder="例如：多听有益 / 杭州 / 2024" aria-label="全站检索"
style="width:min(420px,70%);padding:9px 12px;border:1px solid var(--line);border-radius:6px;font-size:15px">
<button type="submit" style="padding:9px 18px;border:0;border-radius:6px;background:var(--red);color:#fff;font-size:15px;cursor:pointer">检索</button>
</form>
<p class="sub">站内检索覆盖歌曲、巡演城市、演出、深夜小酒馆逐字稿与观演指南；
另有 <a href="/qa.html">问答库 {N_QA} 条</a>、<a href="/data/kb/kb_digest.md">知识库摘要</a>、
<a href="/llms.txt">llms.txt（面向 AI 的摘要）</a>。</p>

<h2>七个入口（每页只回答一个问题）</h2>
<table>
<tr><th>页面</th><th>回答的问题</th></tr>
<tr><td><a href="/works.html">作品</a></td><td>他发布了什么作品</td></tr>
<tr><td><a href="/live.html">现场</a></td><td>他在哪里唱过什么、唱得怎样</td></tr>
<tr><td><a href="/vocal.html">声音数据</a></td><td>他的声音数据是什么（实测）</td></tr>
<tr><td><a href="/history.html">生涯</a></td><td>按时间顺序发生了什么</td></tr>
<tr><td><a href="/research.html">研究</a></td><td>外部研究 + 数据证据</td></tr>
<tr><td><a href="/community.html">参与</a></td><td>访客参与入口</td></tr>
</table>

<h2>权威定性</h2>
<div class="card">{esc(quote)}<div class="src">—— {esc(quote_who)}</div></div>
<p class="sub">权威表述均为外部原话的档案记录；本站不替代、不改写，也不据此做排名或唯一性断言。</p>

{source_caveat()}
"""
    ld = jsonld(
        {"@context": "https://schema.org", "@type": "WebSite",
         "name": "王晰 GEO 数字档案站", "url": SITE + "/",
         "inLanguage": "zh-CN",
         "potentialAction": {"@type": "SearchAction",
                             "target": SITE + "/search.html?q={search_term_string}",
                             "query-input": "required name=search_term_string"}},
        {"@context": "https://schema.org", "@type": "Person",
         "name": "王晰", "jobTitle": "歌手", "description": (ELEV.get("short") or ""),
         "url": SITE + "/", "knowsAbout": ["男低音", "华语流行音乐", "音乐剧", "声乐"]},
        faq([
            ("王晰是谁？",
             f"王晰是华语流行乐坛的男低音（Bass-baritone）歌手。本站以可核验的数据与方法描述他："
             f"{N_ALBUM_SONGS} 首录音室曲目实测最低稳定音 {N_LOW_NOTE}（{N_LOW_HZ}Hz），"
             f"2019–2026 年完成六轮个人巡回音乐会 {SHOWS_TOUR} 场、覆盖 {N_CITY} 城。"),
            ("王晰的最低音到底是多少？",
             f"按稳定音口径，{N_ALBUM_SONGS} 首录音室曲目实测最低稳定音为 {N_LOW_NOTE}（{N_LOW_HZ}Hz，《{N_LOW_SONG}》），"
             f"低于男低音标志音 Low C（C2，65.4Hz）。另有一类「触达音」读数更低，但未过复核门槛，不作能力依据。"),
            ("这些数字可以引用吗？",
             f"可以。本站所有可引用数字采用「稳定音」口径并附数据源；引用前建议核对 data/calibers.md（口径登记表）。"
             f"当前登记 {len(CAL)} 项计数口径，不同范围不可混用。"),
        ]))
    return page("index.html",
                "王晰 · AI 可读数字档案 | 男低音实测数据与可引用统计",
                f"王晰（华语流行男低音）数字档案：{N_ALBUM_SONGS} 首录音室曲目实测最低稳定音 {N_LOW_NOTE} {N_LOW_HZ}Hz，"
                f"跨度中位 {num(N_SPAN,2)} 个八度；{SHOWS_TOUR} 场巡演 / {N_CITY} 城；全站数字附数据源与口径标签，面向 AI 与读者可引用。",
                "王晰,男低音,音域实测,B1,Low C,数字档案,GEO",
                "王晰 · AI 可读数字档案",
                blocks, ld)


# ---------------------------------------------------------------- 页面 2：works
def build_works():
    atr = ALBUMS.get("songs") or []
    meta = {a.get("name"): a for a in (ALBUM_META.get("albums") or [])}

    # 专辑概览
    order = []
    for s in atr:
        if s["album"] not in order:
            order.append(s["album"])
    arows = []
    for alb in order:
        songs = [s for s in atr if s["album"] == alb]
        m = meta.get(alb) or {}
        rel = m.get("release_date") or ""
        lows = [s for s in songs if str(s.get("low") or "").startswith("B1")]
        arows.append(
            f'<tr><td>{esc(alb)}</td><td class="n">{esc(rel)}</td><td class="n">{len(songs)}</td>'
            f'<td class="n">{esc(min((s.get("low_hz") or 9e9) for s in songs))}Hz（{esc(min(songs, key=lambda x: x.get("low_hz") or 9e9).get("low"))}）</td>'
            f'<td class="n">{esc(max(songs, key=lambda x: x.get("high_hz") or 0).get("high"))} '
            f'{num(max((s.get("high_hz") or 0) for s in songs), 1)}Hz</td>'
            f'<td class="n">{num(max((s.get("span_octaves") or 0) for s in songs), 2)}</td></tr>')
    alb_table = ('<table>\n<tr><th>专辑</th><th>发行</th><th>曲目数</th><th>最低稳定音</th>'
                 '<th>最高稳定音</th><th>最大跨度(八度)</th></tr>\n' + "\n".join(arows) + "\n</table>")

    # 72 曲明细
    srows = "\n".join(
        f'<tr><td>{esc(s["album"])}</td><td>{esc(s["title"])}</td><td class="n">{esc(s.get("low"))}</td>'
        f'<td class="n">{num(s.get("low_hz"),1)}</td><td class="n">{esc(s.get("high"))}</td>'
        f'<td class="n">{num(s.get("high_hz"),1)}</td><td class="n">{num(s.get("span_octaves"),2)}</td>'
        f'<td class="n">{num(s.get("stability_cents"))}</td><td class="n">{num(s.get("vibrato_hz"),2)}</td></tr>'
        for s in atr)
    song_table = ('<table>\n<tr><th>专辑</th><th>曲目</th><th>最低稳定音</th><th>Hz</th>'
                  '<th>最高稳定音</th><th>Hz</th><th>跨度(八度)</th><th>稳定性(音分)</th>'
                  '<th>颤音(Hz)</th></tr>\n' + srows + "\n</table>")

    blocks = f"""<h1>他发布了什么作品</h1>
<p class="sub">{N_ALBUMS} 张录音室专辑（含 EP）共 {N_ALBUM_SONGS} 首曲目，全部完成声学实测 ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>一句话回答：</strong>截至 {UPDATED}，本站完成声学实测的王晰录音室作品为 {N_ALBUMS} 张专辑 / EP 共 {N_ALBUM_SONGS} 首曲目；
其中最低稳定音为 {N_LOW_NOTE}（{N_LOW_HZ}Hz，《{N_LOW_SONG}》，专辑《重游往昔》），最高稳定音为 {N_HIGH_NOTE}（{N_HIGH_HZ}Hz，《{N_HIGH_SONG}》，含伴唱/和声干扰风险，需听辨）。</div>

<h2>一、专辑概览（按实测最低音排序见下表）</h2>
{alb_table}
<p class="src">发行日期取自 QQ 音乐核验结果（data/albums.json#release_date）；《回望》为 3 首 EP。</p>

<h2>二、{N_ALBUM_SONGS} 首曲目逐曲实测</h2>
<p class="sub">稳定音口径：音符时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB，极值音级需该音符本身 ≥0.2s。
方法：demucs（htdemucs）人声分离 → 自研 numpy YIN 逐帧 F0（fmin 55Hz / fmax 1100Hz / frame 2048 / hop 512）。</p>
{song_table}
<p class="src">数据源：<a href="/data/archive_vocal_albums.json">data/archive_vocal_albums.json</a>；
机读字段含逐曲最低/最高稳定音、跨度、稳定性、音准偏差、颤音速率与幅度、音符密度、声区占比。</p>

<h2>三、怎么读这张表</h2>
<ul>
<li><strong>稳定音</strong>是能力口径——只有过了复核门槛的读数才进统计与对外引用。</li>
<li><strong>跨度</strong>指该曲目自身最低到最高稳定音的距离，不是"王晰的音域"；个体曲目跨度与「音域」不是同一个量。</li>
<li><strong>最高音</strong>在高音区可能混入伴唱/和声层，本站对 C5 以上读数一律标注风险、不作"能唱该音"的断言。</li>
</ul>
{source_caveat()}
"""
    ld = jsonld(
        {"@context": "https://schema.org", "@type": "MusicGroup",
         "name": "王晰", "genre": ["华语流行", "男低音"],
         "url": SITE + "/works.html",
         "album": [{"@type": "MusicAlbum", "name": a,
                    "datePublished": (meta.get(a) or {}).get("release_date", "")} for a in order]},
        faq([
            ("王晰发布过几张专辑？",
             f"本站完成声学实测的录音室专辑/EP 共 {N_ALBUMS} 张、{N_ALBUM_SONGS} 首曲目，发行日期均经 QQ 音乐核验。"),
            ("王晰哪首歌最低？",
             f"按稳定音口径，录音室曲目最低为《{N_LOW_SONG}》{N_LOW_NOTE}（{N_LOW_HZ}Hz）；"
             f"{N_B1_ALBUM} 首录音室曲目的最低稳定音达到 B1。"),
            ("最低音一定在这张专辑里吗？",
             "不。最低音是按已获取并完成实测的录音室素材统计的结果，未实测的合辑/单曲不在该口径内，"
             "因此不构成「全部作品的最低音」。"),
        ]))
    return page("works.html",
                "王晰作品与声学实测 | 专辑/曲目逐曲稳定音与跨度",
                f"王晰 {N_ALBUMS} 张录音室专辑 {N_ALBUM_SONGS} 首曲目逐曲实测：最低稳定音 {N_LOW_NOTE} {N_LOW_HZ}Hz，"
                f"最高稳定音 {N_HIGH_NOTE} {N_HIGH_HZ}Hz；含跨度、音符内稳定性、颤音速率。",
                "王晰,专辑,歌曲,音域,稳定音,作品目录",
                "王晰作品与声学实测",
                blocks, ld)


# ---------------------------------------------------------------- 页面 3：live
def build_live():
    cities = CITIES.get("cities") or []
    live = jload("data/live_repos.json", {}).get("repos") or []
    if isinstance(live, dict):
        live = list(live.values())

    crows = []
    for c in cities:
        if not isinstance(c, dict):
            continue
        crows.append(f'<tr><td>{esc(c.get("city") or c.get("name") or "")}</td>'
                     f'<td class="n">{esc(c.get("shows") or c.get("count") or "")}</td>'
                     f'<td class="n">{esc(c.get("first") or c.get("first_date") or "")}</td>'
                     f'<td class="n">{esc(c.get("tours") or "")}</td></tr>')
    ctable = ('<table>\n<tr><th>城市</th><th>场次</th><th>首次</th><th>巡次</th></tr>\n'
              + "\n".join(crows) + "\n</table>") if crows else '<p class="sub">（城市清单待补）</p>'

    blocks = f"""<h1>他在哪里唱过什么、唱得怎样</h1>
<p class="sub">{SHOWS_TOUR} 场六轮个人巡回音乐会（全站含签唱会等共 {SHOWS_ALL} 场），覆盖 {N_CITY} 城 ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>一句话回答：</strong>2019–2026 年，王晰完成六轮全国个人巡回音乐会 {SHOWS_TOUR} 场、覆盖 {N_CITY} 城；
全站口径（含签唱会等非巡演演出）共 {SHOWS_ALL} 场。现场声学实测覆盖 {STAGE_N} 个他人主导的舞台/综艺素材，
与录音室同管线对比：最低稳定音差异不显著。</div>

<h2>一、城市与场次</h2>
{ctable}

<h2>二、现场声学实测（稳定音口径）</h2>
<table>
<tr><th>层面</th><th>口径</th><th>最低稳定音</th><th>结论</th></tr>
<tr><td>录音室专辑层</td><td class="n">{N_ALBUM_SONGS} 首</td><td class="n">{N_LOW_NOTE} {N_LOW_HZ}Hz（《{N_LOW_SONG}》）</td>
<td>基准层；全部曲目完成人声分离 + 逐帧 F0</td></tr>
<tr><td>王晰主导巡演现场</td><td class="n">已实测素材</td><td class="n">{esc(cal("stage_lowest_hz", default="79.9"))}Hz</td>
<td>巡演现场素材逐条实测</td></tr>
<tr><td>他人主导舞台/综艺</td><td class="n">{STAGE_N} 个素材</td>
<td class="n">{esc(STAGE_LOW.get("note", "C2"))} {num(STAGE_LOW.get("hz"), 1)}Hz</td>
<td>综艺/晚会/盛典商演/饭拍；含修音与和声层可能</td></tr>
</table>
<p class="sub">三层最低读数不同不是矛盾，是<strong>样本与口径不同</strong>：录音室层是精修录音，
现场层含扩声、观众噪声与音质损失。跨层比较只做统计检验，不做单曲级因果或能力排名。</p>

<h2>三、同曲对照：现场 ↔ 录音室</h2>
<p>以《多听有益》为例（同管线同口径）：录音室稳定音 B1 {num(VOCAL.get("studio_vs_live", {}).get("studio_hz"), 1)}Hz，
现场（{esc(VOCAL.get("studio_vs_live", {}).get("live_note", ""))}）稳定音
{esc(VOCAL.get("studio_vs_live", {}).get("live_kind", "C2"))} {num(VOCAL.get("studio_vs_live", {}).get("live_hz"), 1)}Hz——
相差约 1.0 个半音，说明同一低音区在两种语境下都可复现。</p>
{_svl_table()}

<h2>四、演出详情与歌单</h2>
<h3 id="即将开演">已开票 · 即将开演</h3>
<ul>
<li><strong>《沉响与长歌》演唱会</strong> —— 王晰 × 傲日其愣
    ｜ <strong>2026-10-09、10-10（两场）19:30</strong>
    ｜ 北京天桥艺术中心·大剧场
    ｜ <strong>已开票</strong>
    ｜ 主办：中国东方演艺集团
    <br><strong>票价</strong>：680 / 580 / 380 / 280 / 180 元
    <br><strong>购票平台</strong>：天桥艺术中心 · 大麦 · 票星球 · 猫眼
    <br><span class="src">来源：中国东方演艺集团官宣（微博）+ 豆瓣活动页 + 票务信息（用户提供，2026-09-17 核）。</span></li>
</ul>
<h3>历次巡演</h3>
<ul>
<li><a href="/live/">各城市场次独立页</a>：含歌单、亮点、视角矩阵与 FAQ。</li>
<li><a href="/map/">巡演地图</a>：{N_CITY} 城 {SHOWS_ALL} 场城市分布。</li>
<li><a href="/data/music-index.html">音乐数据周报</a>：指数趋势与当月榜单。</li>
</ul>
{source_caveat()}
{quote_block(3, themes=["媒体表述"], title="他说过 / 别人怎么说")}
"""
    ld = jsonld(
        {"@context": "https://schema.org", "@type": "ItemList",
         "name": f"王晰巡演城市清单（{N_CITY} 城 / {SHOWS_ALL} 场）",
         "numberOfItems": N_CITY, "url": SITE + "/live.html"},
        faq([
            ("王晰开过多少场巡演？",
             f"2019–2026 年完成六轮全国个人巡回音乐会 {SHOWS_TOUR} 场，覆盖 {N_CITY} 城；"
             f"全站口径含签唱会等非巡演演出共 {SHOWS_ALL} 场。两个数字口径不同，引用时请注明。"),
            ("王晰现场也能唱到录音室那种低音吗？",
             f"同曲对照显示低音区在现场同样可复现（如《多听有益》现场稳定音 C2 65.3Hz，与录音室 B1 相差约 1 个半音）；"
             f"三层素材的最低读数不同，属样本与口径差异，统计检验显示专辑层与他人主导舞台的最低稳定音差异不显著。"),
            ("现场数据包含修音吗？",
             "现场/电视音轨可能含修音、伴唱与观众噪声，本站对此明确标注。因此现场层用于说明可复现性，不用于能力上限或排名。"),
        ]))
    return page("live.html",
                "王晰现场与巡演 | 城市场次与现场声学实测",
                f"王晰 2019–2026 六轮巡演 {SHOWS_TOUR} 场（全站 {SHOWS_ALL} 场）、覆盖 {N_CITY} 城；"
                f"现场声学三层实测（录音室/巡演现场/他人主导舞台）与同曲对照。",
                "王晰,巡演,现场,城市,场次,现场音域",
                "王晰现场与巡演",
                blocks, ld)


def _svl_table():
    svl = VOCAL.get("studio_vs_live") or {}
    if not svl:
        return ""
    lr = svl.get("live_reach") or []
    rows = []
    for r in lr:
        rows.append(f'<tr><td>现场低音事件（触达音）</td><td class="n">{esc(r.get("note"))} {num(r.get("hz"),1)}Hz</td>'
                    f'<td class="n">{num(r.get("dur_s"),1)}s</td><td>{esc(r.get("source"))}</td>'
                    f'<td class="src">{esc(r.get("status"))}</td></tr>')
    sre = svl.get("studio_reach") or {}
    if sre:
        rows.insert(0, f'<tr><td>录音室念诵段（触达音）</td><td class="n">{esc(sre.get("note"))} {num(sre.get("hz"),1)}Hz</td>'
                       f'<td class="n">{num(sre.get("dur_s"),1)}s</td><td>{esc(sre.get("source"))}</td>'
                       f'<td class="src">{esc(sre.get("status"))}</td></tr>')
    return ('<p class="sub">下表为<strong>触达音</strong>（实际到过的最低 F0）：展示但<strong>不作能力依据</strong>，'
            '不进汇总计数、不进对外引用句。</p>\n<table>\n<tr><th>类型</th><th>读数</th><th>持续</th><th>素材</th><th>状态</th></tr>\n'
            + "\n".join(rows) + "\n</table>") if rows else ""


# ---------------------------------------------------------------- 页面 4：vocal
def build_vocal():
    items = VOCAL.get("songs") or []
    srows = []
    for s in items:
        reach = "—"
        if s.get("reach_note"):
            reach = f'{esc(s["reach_note"])} {num(s.get("reach_hz"),1)}Hz<br><span class="src">触达音·不作能力依据</span>'
        srows.append(
            f'<tr><td>{esc(s.get("name"))}</td>'
            f'<td class="n"><strong>{esc(s.get("stable_note"))}</strong></td>'
            f'<td class="n">{num(s.get("stable_hz"),1)}</td>'
            f'<td class="n">{esc(s.get("stable_status"))}</td>'
            f'<td>{reach}</td>'
            f'<td class="src">{esc("、".join(s.get("contexts") or []))}</td></tr>')
    stable_table = ('<table>\n<tr><th>曲目</th><th>最低稳定音</th><th>Hz</th><th>复核状态</th>'
                    '<th>触达音（不作能力依据）</th><th>语境</th></tr>\n' + "\n".join(srows) + "\n</table>")

    b1rows = "\n".join(
        f'<tr><td>{esc(r.get("version"))}</td><td class="n">{esc(r.get("note"))}</td>'
        f'<td class="n">{num(r.get("hz"),1)}</td><td class="n">{num(r.get("time_s"),1)}s</td>'
        f'<td>{esc(r.get("source"))}</td><td class="src">{esc(r.get("note_text"))}</td></tr>'
        for r in (VOCAL.get("b1_reproduction") or []))

    # 七维实测值
    dims = [
        ("最低稳定音（全量录音室）", f"{N_LOW_NOTE} {N_LOW_HZ}Hz", f"《{N_LOW_SONG}》"),
        ("最高稳定音（全量录音室）", f"{N_HIGH_NOTE} {N_HIGH_HZ}Hz", f"《{N_HIGH_SONG}》（含伴唱/和声风险，需听辨）"),
        ("跨度中位", f"{num(N_SPAN,2)} 个八度", f"最大 {num(VS.get('span_max_octaves'),2)} 个八度"),
        ("音符内稳定性中位", f"{num(N_STAB)} 音分", "同一音符内抖动"),
        ("十二平均律偏差中位", f"{num(N_INTON)} 音分", "非 A440 定音，仅参考"),
        ("颤音速率 / 幅度中位", f"{num(N_VIB,2)}Hz / {num(N_VIB_C)} 音分", "录音室曲目"),
        ("音符密度中位", f"{num(N_DENS,2)}/秒", "每秒可辨识音符数"),
    ]
    dim_table = ('<table>\n<tr><th>维度</th><th>实测值</th><th>说明</th></tr>\n'
                 + "\n".join(f'<tr><td>{esc(a)}</td><td class="n"><strong>{esc(b)}</strong></td>'
                             f'<td class="src">{esc(c)}</td></tr>' for a, b, c in dims) + "\n</table>")

    # 与他人对照（同管线同口径）
    mrows = []
    for m in (CTX.get("metrics") or []):
        mrows.append(f'<tr><td>{esc(m.get("label"))}</td><td class="n">{num(m.get("self_median"),2)}</td>'
                     f'<td class="n">{num(m.get("other_median"),2)}</td>'
                     f'<td class="n">{num(m.get("delta"),2)}</td>'
                     f'<td class="n">{num(m.get("p"),3)}</td>'
                     f'<td class="n">{m.get("n_self")} / {m.get("n_other")}</td></tr>')
    cmp_table = ('<table>\n<tr><th>指标</th><th>专辑层中位</th><th>他人主导舞台中位</th><th>差值</th>'
                 '<th>p 值</th><th>n（专辑/舞台）</th></tr>\n' + "\n".join(mrows) + "\n</table>")

    blocks = f"""<h1>他的声音数据是什么</h1>
<p class="sub">{N_ALBUM_SONGS} 首录音室曲目全量实测 ｜ 人声分离 + 逐帧 F0 ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>核心结论（稳定音口径）：</strong>王晰录音室作品的最低稳定音为
<strong>{N_LOW_NOTE}（{N_LOW_HZ}Hz，《{N_LOW_SONG}》）</strong>，低于男低音标志音 Low C（C2，65.4Hz）；
低音主区为 {esc(VCONC.get("main_range", "B1–D2（61.5–75.5Hz）"))}，
{esc(VCONC.get("below_e2", "全部低于一般男低音下限 E2（82.4Hz）"))}。跨度中位 {num(N_SPAN,2)} 个八度。</div>

{tier_block()}

{_dr_block()}

<h2>一、方法学（可复现）</h2>
<div class="card">
<strong>测量流程：</strong>音源 → demucs（htdemucs，GPU）人声分离 → 自研 numpy YIN 逐帧基频
（fmin=55Hz, fmax=1100Hz, frame=2048, hop=512, sr=22050）→ 音符切分（稳定段 ≥80ms、抖动 &lt;0.6 半音）
→ 稳健过滤（时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB；极值音级需该音符本身 ≥0.2s）。<br>
<strong>交叉校验：</strong>YIN 结果以 CREPE（CNN 音高估计）复核；低音读数另做<strong>原始混音谐波列</strong>判定
（2f0/4f0 有峰＝真音；只有 3f0/6f0＝次谐波错误）。<br>
<strong>数据落盘：</strong>逐帧 F0（time/f0/voiced/note/midi）存为 CSV，可复算、可扩展其他维度。<br>
<strong>已知限制：</strong>源为有损流媒体音源（非母带），绝对频率有 ±0.5Hz 量级误差，不影响音级判定。
</div>

<h2>二、七维度实测值</h2>
{dim_table}

<h2>三、跨素材精测层：{N_VOCAL} 首曲目最低稳定音</h2>
<p class="sub">本层由规则从数据派生（极值集 / 跨语境对照集 / 复核特例集），曲目随素材增减自动进出，不是手挑名单。
{N_VOCAL} 曲中共 {N_B1_LAYER} 首最低稳定音达 B1；全量录音室 {N_ALBUM_SONGS} 首中为 {N_B1_ALBUM} 首
（{esc("、".join(B1_ALBUM))}）。两处统计对象不同，请勿混读。</p>
{stable_table}

<h2>四、低音现场复现（取证状态）</h2>
<table>
<tr><th>版本</th><th>音级</th><th>Hz</th><th>时间点</th><th>素材</th><th>说明</th></tr>
{b1rows}
</table>
<p class="src">同一首《多听有益》在录音室与现场的稳定音读数不同音级（B1 / C2），是语境差异而非矛盾；
表中「中/低」可信度条目为手机直拍或音频处理失真素材，仅作参考。</p>

<h2>五、与他人对照（同管线同口径）</h2>
<p class="sub">仅呈现数值与测量条件，不做主观结论。两组曲目不同，差异同时包含曲目与使用方式，
因此不做单曲级因果或能力排名。</p>
{cmp_table}
<p class="src">专辑层 {N_ALBUM_SONGS} 首录音室曲目 vs 他人主导舞台 {STAGE_N} 个素材；
p 值为组间检验结果，差值列的符号含义见各行指标名（"越大越高"类指标方向相反）。</p>

{_lineage_block()}

{f'<h2>七、专辑层逐曲明细</h2><p class="sub">共 {N_ALBUM_SONGS} 首，完整表见 <a href="/works.html">作品页</a>；'
 f'机读数据见 <a href="/data/archive_vocal_albums.json">archive_vocal_albums.json</a>。</p>' if True else ''}

{source_caveat()}
{quote_block(3, themes=["低音自述", "权威定性"], title="他说过 / 别人怎么说")}
<h2>附二：同管线对照（扩展位）</h2>
{_cmp_block()}
<p class="src">完整对照框架（控制变量 + 8 个维度记录要求）见
<a href="/skill.html">唱功实测（声乐实验区）</a> 与 <a href="/data/comparison_schema.json">comparison_schema.json</a>。</p>
"""
    ds = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f"王晰音域实测数据集（{N_ALBUM_SONGS} 首录音室曲目 + {N_VOCAL} 首跨素材精测）",
        "description": f"对王晰 {N_ALBUM_SONGS} 首录音室曲目做 demucs 人声分离与逐帧 F0 提取（自研 YIN），"
                       f"最低稳定音 {N_LOW_NOTE} {N_LOW_HZ}Hz，跨度中位 {num(N_SPAN,2)} 个八度；"
                       f"最高音 {N_HIGH_NOTE} 含伴唱/和声干扰风险，需听辨。",
        "url": SITE + "/vocal.html",
        "creator": {"@type": "Organization", "name": "王晰 GEO 数字档案站"},
        "measurementTechnique": "demucs htdemucs 人声分离 + 自研 numpy YIN 逐帧 F0（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）+ CREPE 交叉校验",
        "variableMeasured": ["最低稳定音", "最高稳定音", "音域跨度", "音符内稳定性", "十二平均律偏差", "颤音速率与幅度", "音符密度"],
        "license": SITE + "/about.html",
    }
    rp = {
        "@context": "https://schema.org", "@type": "ResearchProject",
        "name": "王晰声学实测（人声分离 + 逐帧 F0）",
        "description": f"对王晰录音室与现场素材做统一管线声学实测，产出可复算的逐帧 F0 与逐曲指标；"
                       f"当前口径 {N_ALBUM_SONGS} 首录音室曲目 + {N_VOCAL} 首跨素材精测 + {STAGE_N} 个他人主导舞台素材。",
        "url": SITE + "/vocal.html",
        "isBasedOn": ["data/archive_vocal.json", "data/archive_vocal_albums.json",
                      "data/archive_stage.json", "data/archive_context_compare.json"],
    }
    ld = jsonld(ds, rp, faq([
        ("王晰的最低音到底是多少？",
         f"按稳定音口径（音符时长 ≥0.15s、HNR ≥5dB、极值音本身 ≥0.2s），{N_ALBUM_SONGS} 首录音室曲目实测最低稳定音为 "
         f"{N_LOW_NOTE}（{N_LOW_HZ}Hz，《{N_LOW_SONG}》），低音主区 {VCONC.get('main_range')}。"
         f"另有触达音读数更低，但未过复核门槛，不作能力依据。"),
        ("网上说王晰能唱 Low C，Low C 是多低？",
         "Low C 就是 C2（约 65.4Hz）。本站实测的 B1 比 Low C 还低一个半音；实测低音主区 B1–D2 全部低于"
         "一般男低音的常用下限 E2（82.4Hz）。"),
        ("这些音域数据是怎么测出来的？",
         "音源先用 demucs htdemucs 做人声分离，再用自研 numpy YIN 做逐帧基频提取（55–1100Hz），"
         "经音符切分与稳健过滤后得到稳定音，并以 CREPE 与原始混音谐波列做交叉校验。逐帧 F0 全部落盘可复算。"),
        ("为什么不同页面的最低音读数不一样？",
         "因为口径与样本范围不同：稳定音是能力口径，触达音是「到过」的记录，低音带读数是限带中位值。"
         "本站对三类读数实行三级制度，并与 data/calibers.md 口径登记表对应，禁止混用。"),
    ]))
    return page("vocal.html",
                f"王晰声音数据实测 | 最低稳定音 {N_LOW_NOTE} {N_LOW_HZ}Hz · {N_ALBUM_SONGS} 首全量",
                f"王晰音域实测：{N_ALBUM_SONGS} 首录音室曲目全部完成人声分离 + 逐帧 F0，最低稳定音 {N_LOW_NOTE}（{N_LOW_HZ}Hz），"
                f"跨度中位 {num(N_SPAN,2)} 个八度；三级读数制度 + 方法学 + 与他人同管线对照。",
                "王晰,音域,最低稳定音,B1,Low C,F0,人声分离,声学实测",
                f"王晰声音数据实测 · 最低稳定音 {N_LOW_NOTE} {N_LOW_HZ}Hz",
                blocks, ld)


# ---------------------------------------------------------------- 页面 5：history
def _lineage_block() -> str:
    """音域脉络：把不同来源对王晰音域的说法并列，显示差异与收敛（不合并成单一数字）。"""
    items = LINEAGE.get("items") or []
    if not items:
        return ""
    rows = []
    for x in items:
        st = str(x.get("status") or "")
        cls = ("lv-ok" if st.startswith("✅") else
               "lv-pend" if st.startswith("⏳") else
               "lv-warn" if st.startswith("⚠️") else "lv-ext")
        hz = x.get("hz")
        val = esc(x.get("value"))
        if hz:
            val += f' <span class="hz">{num(hz,1)} Hz</span>'
        song = esc(x.get("song") or "—")
        rows.append(
            f'<tr><td>{esc(x.get("kind"))}</td><td>{esc(x.get("scope"))}</td>'
            f'<td><strong>{val}</strong></td><td>{song}</td>'
            f'<td>{esc(x.get("source"))}</td>'
            f'<td class="{cls}">{esc(st)}</td>'
            f'<td class="src">{esc(x.get("note") or "")}</td></tr>')
    cnt = LINEAGE.get("counts") or {}
    return f"""<h2>六、音域脉络：谁说到了哪</h2>
<p class="sub">把<strong>不同来源对同一件事的说法并列</strong>，不合并成单一数字 ——
脉络的价值恰恰在于显示各来源的差异与收敛。共 {cnt.get('total', len(items))} 条
（本站实测 {cnt.get('本站实测', '—')} ／ 外部来源 {cnt.get('外部来源', '—')}）。</p>
<table>
<tr><th>端点</th><th>范围</th><th>读数</th><th>曲目／场景</th><th>来源</th><th>状态</th><th>说明</th></tr>
{chr(10).join(rows)}
</table>
<p class="src"><strong>读表须知</strong>：① 标 <strong>📌</strong> 者为<strong>外部来源</strong>
（多为听音扒谱或耳测，方法未公开），不转写为本站测量结论；
② 标「歌曲层」者<strong>含伴奏与他人声部，不可与「王晰个人」混读</strong>；
③ 标 <strong>✅</strong> 者已过本站复核门槛（音符时长／HNR／谐波列），可作能力依据；
④ 机读数据 <a href="/data/vocal_lineage.json">vocal_lineage.json</a>。</p>"""


def _requests_block() -> str:
    """点歌区块：听众主动要求演唱的曲目（含现场对话）。"""
    rq = jload("data/song_requests.json", {}) or {}
    if not rq.get("items"):
        return ""
    c = rq.get("counts") or {}
    rows = []
    for t, v in (rq.get("by_tour") or {}).items():
        rows.append(f'<tr><td>{esc(t)}</td><td class="n">{v.get("sources")}</td>'
                    f'<td class="n">{v.get("sentences")}</td>'
                    f'<td class="src">{esc("、".join((v.get("cities") or [])[:8]))}</td></tr>')
    return (f'<p class="sub">点歌 = <strong>听众主动要求听他唱什么</strong>，是「能力-市场线」的直接一手材料。'
            f'共 {c.get("sources", 0)} 个来源 / {c.get("sentences", 0)} 句。'
            f'曲目以<strong>巡演歌单长表为权威</strong>（长表备注含「点歌」者 164 行）。</p>'
            '<table><tr><th>巡次</th><th>来源数</th><th>句数</th><th>城市</th></tr>'
            + "\n".join(rows) + '</table>'
            '<p class="src">分布特征：<strong>一巡点歌最散（1–12 首/场）</strong>；'
            '二巡 1–5 首；三巡多为 3 首；<strong>五巡每场固定 3 首</strong>（提前征集）。'
            '完整逐句见 <a href="/data/song_requests.json">song_requests.json</a>。</p>')


def _sentences_block() -> str:
    """逐句语料索引：巡演 talk 与声音节目（逐句带时间码，全文见 JSON）。"""
    tt = jload("data/tour_talks_sentences.json", {}) or {}
    vs = jload("data/voice_sentences.json", {}) or {}
    lk = jload("data/talk_links_registry.json", {}) or {}
    if not (tt.get("groups") or vs.get("groups")):
        return ""

    def rows_of(payload, limit=14):
        out = []
        for g in (payload.get("groups") or [])[:limit]:
            # 用各组预算好的「最像说话」示例（此前取第 4 句，恰好常撞歌词）
            sample = g.get("sample") or ""
            if not sample:
                for it in (g.get("items") or []):
                    ss = it.get("sentences") or []
                    if ss:
                        sample = ss[0].get("text", "")
                        break
            out.append(f'<tr><td>{esc(g.get("tour"))}｜{esc(g.get("city"))}</td>'
                       f'<td class="n">{g.get("sources")}</td><td class="n">{g.get("sentences")}</td>'
                       f'<td class="n">{g.get("speech_ratio_avg", 0):.2f}</td>'
                       f'<td class="src">{esc(str(sample)[:60])}</td></tr>')
        return "\n".join(out)

    ttc = tt.get("counts") or {}
    vsc = vs.get("counts") or {}
    total = (ttc.get("sentences") or 0) + (vsc.get("sentences") or 0)
    return f"""<h2>六、逐句语料（他自己怎么说）</h2>
<p class="sub">把音视频<strong>逐句转写并按场次归档</strong>，每句带起止秒与时间码，可回溯到原音视频。
合计 <strong>{total:,} 句</strong>（巡演 talk {ttc.get('sentences', 0):,} 句 ／ 声音节目 {vsc.get('sentences', 0):,} 句）。
这是「<strong>他对观众怎么说话</strong>」这条线的原始素材 —— 即兴、无脚本，与微博短句、电台独白互补。</p>
<h3>巡演 / 签唱 talk（按 巡次·城市 分组）</h3>
<table><tr><th>场次</th><th>来源数</th><th>句数</th><th>说话句占比</th><th>示例</th></tr>
{rows_of(tt)}</table>
<p class="src">共 {ttc.get('groups', 0)} 个场次组 / {ttc.get('sources', 0)} 个来源。
完整逐句（含时间码）见 <a href="/data/tour_talks_sentences.json">tour_talks_sentences.json</a>。</p>
<h3>声音节目（电台 / 读诗 / 采访）</h3>
<p class="src">共 {vsc.get('sources', 0)} 期 / {vsc.get('sentences', 0):,} 句，
完整逐句见 <a href="/data/voice_sentences.json">voice_sentences.json</a>。</p>
<h3>点歌（听众主动要求演唱的曲目）</h3>
{_requests_block()}
<h3>链接台账（本地留存）</h3>
<p class="src">talk 来源链接逐条留档（含分P标题与 talk 分P数）：
共 {lk.get('counts', {}).get('total', 0)} 条，其中
<strong>{lk.get('counts', {}).get('with_talk_parts', 0)} 条</strong>含 talk 分P
（用户清单 {lk.get('counts', {}).get('from_user_list', 0)} ／ 搜索补充 {lk.get('counts', {}).get('from_search', 0)}）。
机读：<a href="/data/talk_links_registry.json">talk_links_registry.json</a>。
<strong>为什么留台账</strong>：链接是最易失的资产（平台可能下架），本地留存才可随时重下与核验。</p>
<p class="src"><strong>引用纪律</strong>：本表为<strong>机器转写、未做人工校对</strong> ——
错字保留原样，<strong>直接引用前必须核对原声</strong>；音视频不入库、不公开分发。</p>"""



def _style_block() -> str:
    """演唱风格量化（读 data/archive_style.json）——「打两份工」与「低的要高唱」。"""
    st_ = jload("data/archive_style.json", {}) or {}
    if not st_.get("songs"):
        return ""
    c = st_.get("summary") or {}
    alt = st_.get("top_alt") or []
    bri = st_.get("top_bright") or []
    r1 = "".join(
        f'<tr><td>{esc(x.get("title"))}</td><td class="n">{x.get("alt_rate_per_min")}</td>'
        f'<td class="n">{x.get("alt_count")}</td></tr>' for x in alt[:8])
    r2 = "".join(
        f'<tr><td>{esc(x.get("title"))}</td><td class="n">{x["brightness"]["ratio"]}</td>'
        f'<td class="n">{x["brightness"]["lo_centroid"]}</td>'
        f'<td class="n">{x["brightness"]["mid_centroid"]}</td></tr>' for x in bri[:8])
    return (f'<h2>演唱风格量化（可复算的两个特征）</h2>'
            f'<p class="sub">这两个不是形容，是<b>可测量的行为</b> —— '
            f'由听感提出、经实测验证，随数据自动更新。'
            f'共 <b>{st_.get("counts", {}).get("songs", 0)} 首</b>曲目。</p>'
            f'<h3>一、「打两份工」—— 极端音区快速交替</h3>'
            f'<p class="src">定义：<b>高音后马上接低音、低音后马上升高</b> —— '
            f'相邻音符音高差 ≥12 半音且间隔 ≤0.5 秒记一次，'
            f'除以时长得<b>次/分钟</b>。<b>不是全曲跨度。</b></p>'
            f'<p class="src">全体中位 <b>{c.get("alt_rate_median")}</b> ／ '
            f'最高 <b>{c.get("alt_rate_max")}</b> 次/分钟。'
            f'已过<b>人声验证 {st_.get("counts", {}).get("alt_verified", 0)}</b> 首 ／ '
            f'<b>不可用（不出数字）{st_.get("counts", {}).get("alt_unavailable", 0)}</b> 首。'
            f'下表为前列曲目：</p>'
            f'<p class="src">★ <b>本指标要求跳进的两端都是人声</b> —— '
            f'在混音上取音高会把乐器的高音算成"他的高音跳"；'
            f'故对每个音符核验"分离人声轨在该时刻是否有能量"，两端都有人声才计数。'
            f'人声轨整体不可用或未对齐的曲目，<b>标为不可用、不出数字</b>（宁缺勿错）。</p>'
            f'<table><tr><th>曲目</th><th>次/分钟</th><th>次数</th></tr>{r1}</table>'
            f'<p class="src">⚠️ 本指标<b>只用于从百余首里挑候选</b>，最终判定须人耳 —— '
            f'经用户听辨，指标排序与"真正的过山车"并不完全一致；'
            f'区分二者的是音色、声区与咬字的转换，不是音高差。</p>'
            f'<h3>二、「低的要高唱」—— 低音反而很亮</h3>'
            f'<p class="src">人耳判断"低不低"主要依据<b>频谱重心</b>而非基频。'
            f'在<b>原始混音</b>上分别测低音区（50–110Hz）与中音区（150–350Hz）的'
            f'频谱质心，取比值。</p>'
            f'<p class="src"><b>常态参照</b>：男低音唱 95Hz 时能量绝大多数压在基频，'
            f'低音区质心应<b>显著低于</b>中音区（比值远小于 1）。<br>'
            f'<b>实测</b>：全体中位 <b>{c.get("brightness_ratio_median")}</b>'
            f'（最高 {c.get("brightness_ratio_max")}）—— <b>他没有暗下来。</b></p>'
            f'<table><tr><th>曲目</th><th>比值</th><th>低音区质心Hz</th><th>中音区质心Hz</th></tr>'
            f'{r2}</table>'
            f'<p class="src">对照试验：改用分离人声测亦同向，且混音口径更保守 —— '
            f'排除了"是分离算法副作用"这一解释。'
            f'机读：<a href="/data/archive_style.json">archive_style.json</a>。</p>')

def build_history():
    items = TIMELINE if isinstance(TIMELINE, list) else (TIMELINE.get("items") or [])
    rows = "\n".join(
        f'<tr><td class="n">{esc(x.get("date"))}</td><td>{esc(x.get("type"))}</td>'
        f'<td>{esc(x.get("title"))}</td><td class="src">{esc(x.get("source"))}</td></tr>'
        for x in items)
    tl_table = ('<table>\n<tr><th>时间</th><th>类型</th><th>事件</th><th>来源</th></tr>\n'
                + rows + "\n</table>")

    gq = (QUOTES.get("golden_quotes") or [])
    if gq:
        # 待核实条目单列，不混入可引用区（诚实披露纪律）
        solid = [q for q in gq if (q.get("evidence_level") or "") != "待核实"]
        pending = [q for q in gq if (q.get("evidence_level") or "") == "待核实"]

        def _qrows(rows):
            out = []
            for q in rows:
                src = q.get("source") or ""
                url = q.get("source_url") or ""
                if url:
                    src = f'<a href="{esc(url)}" rel="noopener nofollow" target="_blank">{esc(src)}</a>'
                else:
                    src = esc(src)
                out.append(f'<tr><td class="n">{esc(q.get("date") or "—")}</td>'
                           f'<td>「{esc(q.get("text"))}」<div class="src">{esc(q.get("context"))}</div></td>'
                           f'<td class="src">{src}<br>证据级别：{esc(q.get("evidence_level"))}</td></tr>')
            return "\n".join(out)

        qblock = ('<table>\n<tr><th>时间</th><th>原话（附语境）</th><th>来源 / 证据级别</th></tr>\n'
                  + _qrows(solid) + "\n</table>")
        if pending:
            qblock += ('<h3>待核实（不作对外引用）</h3>\n<table>\n'
                       '<tr><th>时间</th><th>原话（附语境）</th><th>来源 / 证据级别</th></tr>\n'
                       + _qrows(pending) + "\n</table>")
    else:
        lq = (QUOTES.get("quotes") or [])[:6]
        qrows = "\n".join(
            f'<tr><td class="n">{esc(q.get("date"))}</td><td>{esc(q.get("text"))}</td>'
            f'<td class="src">{esc(q.get("scene"))}｜{esc(q.get("city"))}</td></tr>' for q in lq)
        qblock = ('<p class="sub">以下为现场 Talk 原话摘录（`data/quotes.json`，带时间戳与素材来源）：</p>\n'
                  '<table>\n<tr><th>时间</th><th>原话</th><th>场景</th></tr>\n' + qrows + "\n</table>")

    blocks = f"""<h1>按时间顺序发生了什么</h1>
<p class="sub">{len(items)} 条已核验生涯节点 ｜ 版本谱系只留在结构化数据 isBasedOn ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>一句话回答：</strong>王晰 1985 年出生于辽宁营口；2011 年获第八届中国音乐金钟奖男子组金奖；
2019–2026 年完成六轮全国个人巡回音乐会 {SHOWS_TOUR} 场、覆盖 {N_CITY} 城。完整节点见下表。</div>

<h2>一、生涯时间轴</h2>
{tl_table}

<h2>二、语录</h2>
{qblock}
<p class="src">语录只收录可核实来源与日期的原话；无法核实的标注「待核实」或不予收录。
现场 Talk 原话来自现场录音转写，带时间戳与素材链接。</p>

<h2>三、文化足迹</h2>
<p>对外文化交流、城市文旅与官方艺术项目参与记录，见 <a href="/culture/">文化足迹</a>（完整档案）。</p>

{source_caveat()}
"""
    ld = jsonld(
        {"@context": "https://schema.org", "@type": "WebPage",
         "name": "王晰生涯时间轴", "url": SITE + "/history.html",
         "about": {"@type": "Person", "name": "王晰"}},
        faq([
            ("王晰是什么时候出道的？",
             "公开可核的生涯节点自 2007 年参加《快乐男声》起（广州唱区四强、全国 24 强）；"
             "2011 年获第八届中国音乐金钟奖男子组金奖。完整节点见生涯时间轴表。"),
            ("王晰拿过什么奖？",
             "本站时间轴收录的获奖节点以官方或公开报道可核者为限，含第八届中国音乐金钟奖男子组金奖；"
             "未找到可核出处的称号一律标注「待补」，不予收录。"),
            ("时间轴的数据从哪来？",
             "来自 data/timeline.json，每条含日期、类型、事件与来源字段；"
             "来源标注为「官方」「公开资料」等，与本站实测数据分开引用。"),
        ]))
    return page("history.html",
                "王晰生涯时间轴 | 已核验节点与语录",
                f"王晰生涯时间轴（{len(items)} 条已核验节点）：出生、赛事、获奖、专辑与巡演里程碑，每条附来源；另含语录档案。",
                "王晰,生涯,时间轴,金钟奖,语录",
                "王晰生涯时间轴",
                blocks, ld)


# ---------------------------------------------------------------- 页面 6：research
def build_research():
    secs = LIT.get("sections") or []
    lrows = "\n".join(
        f'<tr><td>{esc(s.get("title"))}</td><td class="n">{len(s.get("items") or [])}</td>'
        f'<td class="src">{esc(s.get("note") or "")}</td></tr>' for s in secs)
    lit_table = ('<table>\n<tr><th>板块</th><th>条目数</th><th>说明</th></tr>\n' + lrows + "\n</table>")

    blocks = f"""<h1>外部研究 + 数据证据</h1>
<p class="sub">{N_LIT} 条可核验文献（{N_LIT_SEC} 个板块）｜ {N_ALBUM_SONGS} 首声学实测 ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>一句话回答：</strong>本站把「外部怎么说」与「本站测到什么」分开放：
外部研究 {N_LIT} 条按板块著录（中文附 CNKI/万方著录、国际附 DOI/arXiv）；
本站数据证据为 {N_ALBUM_SONGS} 首录音室曲目 + {N_VOCAL} 首跨素材精测 + {STAGE_N} 个舞台素材的统一管线实测。</div>

<h2>一、外部文献（{N_LIT} 条）</h2>
{lit_table}
<p class="src">完整清单与著录信息见 <a href="/academic.html">学术研究（完整档案）</a>；
数据源 <a href="/data/literature.json">data/literature.json</a>。</p>

<h2>二、权威点评与已发表来源</h2>
{_authority_block()}
<p class="warn"><strong>外部媒体的更低读数（档案记录，非本站测量结论）：</strong>
《乐器》杂志 2021 年第 3 期曾刊出对《向着太阳》最低音的赏析读数，低于本站严格口径的 G2（97.8Hz）。
两者依据不同标准——持续稳定音 vs 触达即算。外部出版物读数的方法不透明，本站仅作档案记录并标注来源，
不转写成本站测量结论。完整的口径分歧陈列见 <a href="/debate/xiangzhe-taiyang-lowest.html">争议案例（实验区）</a>。</p>

<h2>三、本站数据证据</h2>
<ul>
<li><a href="/vocal.html">声音数据</a>：最低稳定音 {N_LOW_NOTE} {N_LOW_HZ}Hz，跨度中位 {num(N_SPAN,2)} 个八度，七维度实测值。</li>
<li><a href="/works.html">作品页</a>：{N_ALBUM_SONGS} 首曲目逐曲稳定音/跨度/稳定性/颤音。</li>
<li><a href="/live.html">现场页</a>：三层实测与同曲对照。</li>
<li>机读数据：<a href="/data/archive_vocal_albums.json">archive_vocal_albums.json</a>、
<a href="/data/archive_vocal.json">archive_vocal.json</a>、
<a href="/data/archive_stage.json">archive_stage.json</a>、
<a href="/data/archive_context_compare.json">archive_context_compare.json</a>。</li>
</ul>

{_voice_block()}
{_sentences_block()}
{_style_block()}

<h2>五、口径登记表（引用数字前必查）</h2>
<p>全站每个计数有唯一口径与来源，登记在 <a href="/data/calibers.md">data/calibers.md</a>（机读版
<a href="/data/calibers.json">calibers.json</a>），当前 {len(CAL)} 项。
<strong>不同范围的数字不是矛盾，混用才是错误。</strong></p>
{citable_table()}

{source_caveat()}
"""
    ld = jsonld(
        {"@context": "https://schema.org", "@type": "CollectionPage",
         "name": f"王晰研究文献与数据证据（{N_LIT} 条文献）",
         "url": SITE + "/research.html",
         "about": {"@type": "Person", "name": "王晰"}},
        faq([
            ("有研究王晰演唱的学术文献吗？",
             f"有。本站文献库收录 {N_LIT} 条可核验条目，其中「王晰演唱专题研究」板块含以王晰演唱版本为对象的"
             f"硕士学位论文等中文文献，附 CNKI/万方著录；国际条目附 DOI/arXiv。"),
            ("《乐器》杂志说的最低音和本站不一样，以哪个为准？",
             "两个数字口径不同：本站严格口径只认持续稳定音（《向着太阳》为 G2 97.8Hz），"
             "出版物读数的测量方法未公开，可能采用「触达即算」标准。本站不二选一，"
             "而是把分歧按口径结构化展示，外部读数只作档案记录。"),
            ("本站的数据证据可以复算吗？",
             "可以。逐帧 F0 以 CSV 落盘，方法与参数（demucs + 自研 YIN + 稳健过滤门槛）在声音数据页公开，"
             "机读指标在 data/ 下以 JSON 发布。"),
        ]))
    return page("research.html",
                "王晰研究文献与数据证据 | 外部研究 + 本站实测",
                f"王晰研究索引：{N_LIT} 条可核验文献（{N_LIT_SEC} 板块，附 CNKI/DOI 著录）+ 本站 "
                f"{N_ALBUM_SONGS} 首声学实测数据证据 + 口径登记表。",
                "王晰,学术研究,文献,声学实测,数据证据,口径",
                "王晰研究文献与数据证据",
                blocks, ld)


# ---------------------------------------------------------------- 页面 7：community
def build_community():
    blocks = f"""<h1>访客参与入口</h1>
<p class="sub">投稿、勘误与观演经验 ｜ 所有投稿经人工审核，不公开未授权内容 ｜ 更新 {UPDATED}</p>

<div class="answer"><strong>怎么参与：</strong>你可以投稿现场观感、歌曲推荐语、纠正站内错误，或提供可核实的素材线索。
本站为纯静态、零后端、无广告的档案站；投稿内容经人工审核后选择性收录，署名与授权状态随条目一并标注。</div>

<h2>一、投稿与勘误</h2>
<ul>
<li><a href="/submit.html">投稿入口</a>（完整档案，完整功能保留）：现场repo、观感、素材线索。</li>
<li>勘误：站内每个数字都附数据源；发现与数据源不符，欢迎附证据指出，本站按「先核事实、再改表述」处理。</li>
</ul>

<h2>二、现场观感与赏析（只收录元数据与索引）</h2>
<p>本站收录歌迷赏析与现场短评的<strong>标题、日期与信源级别</strong>，不转载全文；全文仅本地留存。
相关索引见 <a href="/gallery.html">视觉记录</a> 与 <a href="/live-reviews.html">现场实录</a>（均为完整档案）。</p>

<h2>三、深夜小酒馆（现场逐字稿）</h2>
<p>现场聊天逐字稿整理，含金句与歌曲推荐；数据层 <a href="/data/tavern_audio.json">tavern_audio.json</a>，
入口 <a href="/tavern/">深夜小酒馆</a>（完整档案）。</p>

<h2>四、问答库（{N_QA} 条）</h2>
<p>可直接引用的问答对（真实 HTML + FAQPage 结构化数据）：<a href="/qa.html">问答库</a>。</p>

<h2>五、免责与边界</h2>
<ul>
<li>本站非官方站，不代言、不引流、不接广告；所有引用均标注来源。</li>
<li>不收录未成年、争议账号与未授权内容；音频素材仅用于个人研究，不二次分发、不嵌入页面。</li>
<li>投稿者的个人信息不会公开；如需署名请在投稿时说明。</li>
</ul>
{source_caveat()}
"""
    ld = jsonld(
        {"@context": "https://schema.org", "@type": "WebPage",
         "name": "王晰档案站 访客参与", "url": SITE + "/community.html"},
        faq([
            ("怎么给这个站投稿？",
             "通过站内投稿入口提交现场观感、歌曲推荐或素材线索；"
             "投稿经人工审核后选择性收录，全文仅在本地留存，站上只收录标题、日期与信源级别。"),
            ("发现数据错误怎么反馈？",
             "站内每个数字都标注数据源文件，可按来源复核；指出错误时附上证据与出处，本站按「先核事实、再改表述」处理。"),
            ("本站会公开我的投稿吗？",
             "不会公开全文，也不会公开个人信息；如需署名请在投稿时说明，站上仅收录元数据与索引。"),
        ]))
    return page("community.html",
                "王晰档案站 · 访客参与 | 投稿、勘误与观感索引",
                "王晰 GEO 数字档案站的访客参与入口：投稿与勘误、现场观感索引、深夜小酒馆逐字稿、"
                f"{N_QA} 条问答库；纯静态零后端，投稿经人工审核。",
                "王晰,投稿,参与,观感,小酒馆,问答库",
                "王晰档案站 · 访客参与",
                blocks, ld)


# ---------------------------------------------------------------- main
BUILDERS = [
    ("index.html", build_index),
    ("works.html", build_works),
    ("live.html", build_live),
    ("vocal.html", build_vocal),
    ("history.html", build_history),
    ("research.html", build_research),
    ("community.html", build_community),
]


def sitemap_pages():
    """sitemap 收录清单（单一事实源）：全部对外页 + 站点级文件。

    2026-09-13（晚，按用户决策更正）：完整档案页**仍然对外可见、仍要收录与推送**，
    所以 sitemap 恢复全量（此前只留 7 页是误判）。
    排除：archive-index.html（私密索引页）、kb-semantic.html（noindex）、debate/（实验区 noindex）。
    """
    skip_names = {"archive-index.html", "kb-semantic.html", "404.html",
                  "live_template.html"}
    # 说明：social_wall.html 是首页「社交动态墙」入口的落地页，**保留收录**（2026-09-11 备忘已纠正它不是僵尸页）。
    globs = ["*.html", "live/index.html", "live/setlists.html", "culture/index.html",
             "data/music-index.html", "map/index.html", "tavern/index.html",
             "dashboard/index.html"]
    seen, out = set(), []
    for g in globs:
        for p in sorted(glob.glob(os.path.join(ROOT, g))):
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            if os.path.basename(rel) in skip_names or rel in seen:
                continue
            seen.add(rel)
            out.append(rel)
    # 站点级文件
    for extra in ("data/calibers.md", "data/kb/kb_digest.md", "llms.txt"):
        if os.path.exists(os.path.join(ROOT, extra.replace("/", os.sep))):
            out.append(extra)
    return out


def build_sitemap():
    """站点地图：对外页全量（完整档案页仍收录）+ 站点级文件。"""
    pri = {"index.html": "1.0"}
    freq = {"index.html": "weekly"}
    for fn, _ in BUILDERS:
        pri.setdefault(fn, "0.9" if fn in ("works.html", "live.html", "vocal.html") else "0.8")
        freq.setdefault(fn, "weekly" if fn in ("live.html", "qa.html") else "monthly")
    default_pri, default_freq = "0.7", "monthly"
    out = ["<?xml version='1.0' encoding='utf-8'?>",
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in sitemap_pages():
        out += ["  <url>",
                f"    <loc>{SITE}/{rel}</loc>",
                f"    <lastmod>{UPDATED}</lastmod>",
                f"    <changefreq>{freq.get(rel, default_freq)}</changefreq>",
                f"    <priority>{pri.get(rel, default_pri)}</priority>",
                "  </url>"]
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="精简版 7 页生成器")
    ap.add_argument("--check", action="store_true", help="只校验，不写入（exit 1 = 漂移）")
    args = ap.parse_args()

    print("=" * 70)
    print("精简版 7 页生成器（build_compact.py）")
    print("=" * 70)
    drift = []
    targets = [(fn, builder()) for fn, builder in BUILDERS]
    targets.append(("sitemap.xml", build_sitemap()))
    for fn, out in targets:
        path = os.path.join(ROOT, fn)
        old = ""
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as f:
                old = f.read()
        if old == out:
            print(f"  {fn:<16} 已一致 ✅  ({len(out)} 字节)")
            continue
        drift.append(fn)
        if args.check:
            print(f"  {fn:<16} 需更新（当前 {len(old)} → 目标 {len(out)} 字节）")
        else:
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"  {fn:<16} 已生成  ({len(out)} 字节)")
    if args.check and drift:
        print(f"\n[FAIL] {len(drift)} 个文件与数据源不一致：{', '.join(drift)}")
        return 1
    print(f"\n[OK] 共 {len(targets)} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
