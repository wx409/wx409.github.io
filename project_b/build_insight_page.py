# -*- coding: utf-8 -*-
"""P1-1 洞察层渲染：把「结论 ＋ 多形态文案 ＋ 证据 ＋ 禁忌」渲染成一页 → insight.html

数据源（全部现成）：
  data/share/conclusion_copy.json（结论与文案，P0-3）
  data/text_profile.json（语言画像，P0-1）
  data/share/insight_charts.json（图指纹，P1-3；图在 assets/insight/）
  data/cross_source_wording.json（跨源措辞差表，P1-2）
  data/share/hook_candidates.json（钩子候选池，P0-2）

纪律：**不进主导航、进底部全站索引**；不得出现禁词与感叹号；平台机制标「经验性认知（非官方）」；
      数字一律来自上述 JSON（禁手写）。
用法：python -X utf8 project_b\\build_insight_page.py
"""
from __future__ import annotations
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
OUT = SITE / "insight.html"
TODAY = date.today().isoformat()

BANNED_RE = re.compile("炸裂|绝了|天花板|孤本|无人能及|爆火|引爆|全网|上热点|封神|顶流|yyds|[!！]")


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def e(x) -> str:
    return html.escape(str(x if x is not None else "—"))


CC = load(D / "share" / "conclusion_copy.json", {}) or {}
TP = load(D / "text_profile.json", {}) or {}
CH = load(D / "share" / "insight_charts.json", {}) or {}
CW = load(D / "cross_source_wording.json", {}) or {}
HK = load(D / "share" / "hook_candidates.json", {}) or {}

FMT_ORDER = ["传记体", "小红书", "微博", "抖音"]
BODY = []
A = BODY.append

A('<h1>洞察层：结论、成稿文案与出处</h1>')
A(f'<p class="sub">本站把「数据结论」直接做成<b>可发布的东西</b>：每条结论配一段传记体、一条小红书、一条微博、'
  f'一份短视频脚本骨架，并逐条附上可核验的证据字段与禁忌。'
  f'共 {len(CC.get("conclusions") or [])} 条结论，数字全部由脚本从站内数据现算。</p>')
A('<div class="tocband">本页分区：① 结论与成稿文案　② 语言画像（分期与跨源）　③ 跨源措辞差表　'
  '④ 钩子候选池　⑤ 出处与纪律</div>')
A('<blockquote>平台机制相关表述一律为<b>经验性认知（非官方）</b>；本页不使用平台侧量级断言。'
  '文案中不出现评价词与感叹号。指数类数字均为<b>追踪曲目池口径</b>。</blockquote>')

# ── ① 结论与成稿文案 ──
A('<h2>① 结论与成稿文案</h2>')
for i, c in enumerate(CC.get("conclusions") or [], 1):
    A(f'<div class="card"><h3>{i}. {e(c.get("title"))}</h3>')
    A(f'<p><b>结论</b>：{e(c.get("conclusion"))}</p>')
    A(f'<p class="meta"><b>证据</b>：<code>{e(c.get("evidence"))}</code></p>')
    A(f'<div class="lock"><b>禁忌</b>：{e(c.get("taboos"))}</div>')
    for fmt in FMT_ORDER:
        txt = (c.get("copy") or {}).get(fmt)
        if not txt:
            continue
        A(f'<p class="meta" style="margin-bottom:2px"><b>{fmt}</b></p><pre style="white-space:pre-wrap;'
          f'background:#fff;border:1px solid #eadfc9;border-radius:6px;padding:9px 11px;margin:4px 0 10px;'
          f'font:13.5px/1.7 inherit">{e(txt)}</pre>')
    if c.get("audience"):
        A(f'<p class="meta">目标人群：{e(c.get("audience"))}</p>')
    A('</div>')

# ── ② 语言画像 ──
ov = TP.get("overall") or {}
A('<h2>② 语言画像（分期与跨源）</h2>')
A(f'<p>统计范围：全量文本语料 <b>{e(ov.get("n_docs"))}</b> 条、切出 <b>{e(ov.get("n_sent"))}</b> 句。'
  f'总体短句率（≤15 字）<b>{e(ov.get("short_sent_pct"))}%</b>、问句率 <b>{e(ov.get("question_pct"))}%</b>、'
  f'含「我」的句子占 <b>{e(ov.get("first_person_pct"))}%</b>。</p>')
A('<div class="tw"><table><tr><th>分期</th><th>样本（条）</th><th>句子数</th><th>短句率</th>'
  '<th>问句率</th><th>含「我」的句子</th><th>句长中位（字）</th></tr>')
for k, v in (TP.get("by_year_bin") or {}).items():
    A(f'<tr><td>{e(k)}</td><td>{e(v.get("n_docs"))}</td><td>{e(v.get("n_sent"))}</td>'
      f'<td>{e(v.get("short_sent_pct"))}%</td><td>{e(v.get("question_pct"))}%</td>'
      f'<td>{e(v.get("first_person_pct"))}%</td><td>{e(v.get("sent_len_median"))}</td></tr>')
A('</table></div>')
A('<h3>跨源三层对照</h3>')
A('<div class="tw"><table><tr><th>层</th><th>条/句</th><th>短句率</th><th>含「我」的句子</th>'
  '<th>句长中位</th><th>容器（字段映射已确认）</th></tr>')
for k, v in (TP.get("cross_source") or {}).items():
    A(f'<tr><td>{e(k)}</td><td>{e(v.get("n_docs"))} 条 / {e(v.get("n_sent"))} 句</td>'
      f'<td>{e(v.get("short_sent_pct")) if v.get("short_sent_pct") is not None else "—"}</td>'
      f'<td>{e(v.get("first_person_pct")) if v.get("first_person_pct") is not None else "—"}</td>'
      f'<td>{e(v.get("sent_len_median"))}</td><td class="meta">{e(v.get("container"))}</td></tr>')
A('</table></div>')
A('<blockquote>曲目层（巡演长表）是曲名文本，不做句式统计，只用于曲目词表交叉；三层措辞天然不同，'
  '本页只作对照，不评优劣。</blockquote>')
A('<h3>时间演变图（脚本生成）</h3>')
for ch in (CH.get("charts") or []):
    f = ch.get("file") or ""
    nm = f.split("/")[-1]
    A(f'<p><img src="{e(f)}" alt="{e(nm)}" style="max-width:100%;border:1px solid #eadfc9;border-radius:6px">'
      f'<br><span class="meta">{e(nm)}｜sha256 {e(str(ch.get("sha256"))[:16])}…</span></p>')
A('<p class="meta">图上数字均可在 <code>data/text_profile.json</code> 与 '
  '<code>data/share/insight_charts.json</code> 中找到（后者含 PNG sha256 指纹）。</p>')

# ── ③ 跨源措辞差表 ──
A('<h2>③ 跨源措辞差表（同一事件的三层写法）</h2>')
A(f'<p class="meta">字段映射已人工确认（登记于 <code>data/cross_source_wording.json#field_map</code>）：'
  f'活动表取 <code>rows[].title＋city＋note</code>；talk 句在 '
  f'<code>groups[].items[].sentences[]</code>；长表为按日期为键的字典 <code>setlists</code>。</p>')
A('<div class="tw"><table><tr><th>日期</th><th>巡次·城市</th><th>口语层（talk 原句）</th>'
  '<th>事务层（活动表标题）</th><th>曲目层</th></tr>')
for r in (CW.get("events") or []):
    tl = r.get("talk_layer") or {}
    al = r.get("act_layer") or {}
    ll = r.get("list_layer") or {}
    A(f'<tr><td>{e(r.get("date"))}</td><td>{e(r.get("tour"))}·{e(r.get("city"))}</td>'
      f'<td>「{e(str(tl.get("sample"))[:40])}」<span class="meta">{e(tl.get("timecode"))}</span></td>'
      f'<td>{e(al.get("title")) or "（该层无记录）"}</td>'
      f'<td>{e(r.get("n_songs"))} 首：{e("、".join(ll.get("songs_head") or []))}</td></tr>')
A('</table></div>')

# ── ④ 钩子候选池 ──
cnt = HK.get("counts") or {}
A('<h2>④ 钩子候选池</h2>')
A(f'<p>原始候选 {e(cnt.get("candidates_raw"))} 条，入选 <b>{e(cnt.get("kept"))}</b> 条；'
  f'丢弃：{e(json.dumps(cnt.get("dropped"), ensure_ascii=False))}。'
  f'每条都有出处（文件与字段/时间戳），并已与已发词条去重。</p>')
A('<div class="tw"><table><tr><th>钩子</th><th>来源</th><th>原句</th><th>出处</th><th>风险/禁忌</th></tr>')
_hooks = HK.get("hooks") or []
_shown, _skipped = [], 0
for h in _hooks:
    blob = " ".join(str(h.get(k) or "") for k in ("hook", "quote", "risk", "evidence"))
    # 2026-10-14：优先用**生成期打好的 raw_noise 标记**（hook_miner.noise_flags，只标记不改写），
    # 正则黑名单只作兜底。含平台侧措辞/感叹号/断裂空格的原始语料不在本页展示（池里保留原句）。
    if h.get("raw_noise") or BANNED_RE.search(blob):
        _skipped += 1
        continue
    _shown.append(h)
for h in _shown[:40]:
    A(f'<tr><td>{e(h.get("hook"))}</td><td class="meta">{e(h.get("kind"))}</td>'
      f'<td class="meta">{e(str(h.get("quote"))[:60])}</td>'
      f'<td class="meta"><code>{e(str(h.get("evidence"))[:110])}</code></td>'
      f'<td class="meta">{e(h.get("risk"))}</td></tr>')
A('</table></div>')
if _skipped:
    A(f'<p class="meta">另有 {_skipped} 条候选因原句含平台侧措辞或感叹号未在本页展示；'
      f'完整候选见 <code>data/share/hook_candidates.json</code>（保留原句未改写）。</p>')

# ── ⑤ 出处与纪律 ──
A('<h2>⑤ 出处与纪律</h2>')
A('<ul class="nums">'
  '<li>结论与文案：<code>data/share/conclusion_copy.json</code>（生成器 <code>project_b/build_conclusion_copy.py</code>）</li>'
  '<li>语言画像：<code>data/text_profile.json</code>（生成器 <code>project_b/build_language_profile.py</code>）</li>'
  '<li>措辞差表：<code>data/cross_source_wording.json</code>（生成器 <code>project_b/build_cross_wording.py</code>）</li>'
  '<li>钩子候选：<code>data/share/hook_candidates.json</code>（生成器 <code>project_b/build_hook_candidates.py</code>）</li>'
  '<li>图与指纹：<code>assets/insight/</code>、<code>data/share/insight_charts.json</code></li>'
  '</ul>')
A('<div class="plat">纪律：极值音一律写「最低稳定音」；触达音与待核读数不作能力依据；跨夜对照样本极小已标注；'
  '平台机制为经验性认知（非官方）；不写平台侧量级断言；文案中不出现评价词与感叹号。</div>')

body = "\n".join(BODY)

hits = sorted({m.group(0) for m in BANNED_RE.finditer(body)})
if hits:
    print("[!] 禁词/感叹号命中：", hits)
    sys.exit(1)

DESC = ("把数据结论做成可发布的成品：每条结论配传记体、小红书、微博与短视频脚本骨架，"
        "并逐条给出可核验证据与禁忌；另含语言画像分期、跨源措辞差表与钩子候选池。")
LD = {
    "@context": "https://schema.org", "@type": "Article",
    "headline": "洞察层：结论、成稿文案与出处",
    "description": DESC,
    "inLanguage": "zh-CN", "datePublished": TODAY, "dateModified": TODAY,
    "mainEntityOfPage": "https://wx409.github.io/insight.html",
    "author": {"@id": "https://wx409.github.io/#person"},
    "publisher": {"@type": "Organization", "name": "王晰数字档案（GEO 资料站）",
                  "url": "https://wx409.github.io"},
    "isBasedOn": ["https://wx409.github.io/data/share/conclusion_copy.json",
                  "https://wx409.github.io/data/text_profile.json",
                  "https://wx409.github.io/data/cross_source_wording.json",
                  "https://wx409.github.io/data/share/hook_candidates.json",
                  "https://wx409.github.io/data/calibers.md"],
    "citation": [
        {"@type": "Dataset", "name": "结论与成稿文案（conclusion_copy.json）",
         "url": "https://wx409.github.io/data/share/conclusion_copy.json"},
        {"@type": "Dataset", "name": "语言画像（text_profile.json）",
         "url": "https://wx409.github.io/data/text_profile.json"},
        {"@type": "Dataset", "name": "跨源措辞差表（cross_source_wording.json）",
         "url": "https://wx409.github.io/data/cross_source_wording.json"},
    ],
}

STYLE = re.search(r"<style>(.*?)</style>",
                  (SITE / "singing.html").read_text(encoding="utf-8"), re.S).group(1)

page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>洞察层：结论、成稿文案与出处｜AI 可读数字档案｜GEO 资料站</title>
<meta name="description" content="{html.escape(DESC)[:190]}">
<link rel="canonical" href="https://wx409.github.io/insight.html">
<meta property="og:title" content="洞察层：结论、成稿文案与出处">
<meta property="og:description" content="{html.escape(DESC)[:190]}">
<meta property="og:url" content="https://wx409.github.io/insight.html">
<meta property="og:type" content="article">
<style>{STYLE}</style>
<script type="application/ld+json">{json.dumps(LD, ensure_ascii=False)}</script>
</head><body>
<!-- NAV_START -->
<!-- NAV_END -->
{body}
<!-- FOOTER_NAV_START -->
<!-- FOOTER_NAV_END -->
</body></html>
"""
OUT.write_text(page, encoding="utf-8")
print(f"[ok] insight.html {len(page)} 字节｜结论 {len(CC.get('conclusions') or [])}｜"
      f"措辞事件 {len(CW.get('events') or [])}｜钩子 {cnt.get('kept')}｜图 {(CH.get('charts') or []) and len(CH['charts'])}")
print("[ok] 禁词/感叹号自检：0 命中")
