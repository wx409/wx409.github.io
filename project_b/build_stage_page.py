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
CROSS = ROOT / "data" / "archive_crosscheck.json"
CTX = ROOT / "data" / "archive_context_compare.json"
TOUR = ROOT / "data" / "archive_stage_tour.json"
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


def tour_layer_html() -> str:
    """王晰主导巡演现场层（第一层，2026-09-11）：全部数字由 data/archive_stage_tour.json 派生。"""
    try:
        t = json.loads(TOUR.read_text(encoding="utf-8"))
    except Exception:
        return ""
    s = t.get("summary") or {}
    rows = t.get("rows") or []
    if not rows or not s.get("lowest"):
        return ""
    lo = s["lowest"]
    n = s.get("n_materials")
    ver = s.get("n_verified")
    def dash(v):
        return "—" if v is None or v == "" else v

    tour_rows = "\n".join(
        f'<tr><td>{esc(x["tour"])}</td><td>{esc("、".join(x.get("cities") or []))}</td>'
        f'<td>{esc((x.get("dates") or ["", ""])[0])}~{esc((x.get("dates") or ["", ""])[1])}</td>'
        f'<td>{x.get("n_materials")}</td>'
        f'<td class="low">{esc(x.get("lowest_note"))}（{x.get("lowest_hz")} Hz）</td>'
        f'<td>{dash(x.get("span_median_octaves"))}</td><td>{dash(x.get("stability_median_cents"))}</td>'
        f'<td>{dash(x.get("vibrato_rate_hz_median"))}</td></tr>'
        for x in t.get("by_tour") or [])
    detail_rows = "\n".join(
        f'<tr><td>{esc(r["tour"])}</td><td>{esc(r["city"])}</td><td>{esc(r["date"])}</td>'
        f'<td class="low">{esc(r["low_note"])}</td><td>{r.get("low_hz")}</td>'
        f'<td>{esc(dash(r.get("high_note")))}</td><td>{dash(r.get("span_octaves"))}</td>'
        f'<td>{dash(r.get("stability_cents"))}</td>'
        f'<td>{str(r.get("vibrato_hz")) + "/" + str(r.get("vibrato_cents")) if r.get("vibrato_hz") else "—"}</td>'
        f'<td>{esc(r.get("a3_final_note"))}</td>'
        f'<td>{esc(dash(r.get("source_layer")))}</td>'
        + (f'<td><a href="https://www.bilibili.com/video/{esc(r.get("bv"))}" rel="noopener nofollow" target="_blank">B站原链接</a></td>'
           if r.get("bv") else "<td>—</td>")
        + '</tr>'
        for r in rows)
    song_blocks = []
    for sg in t.get("by_song") or []:
        if (sg.get("n_versions") or 0) < 2:
            continue
        items = "".join(
            f'<li>{esc(v["tour"])}｜{esc(v["city"])} {esc(v["date"])}：'
            f'<strong>{esc(v["low_note"])} {v.get("low_hz")} Hz</strong>'
            f'（{("跨度 " + str(v.get("span_octaves")) + " 八度，") if v.get("span_octaves") else ""}{esc(v.get("verify"))}）</li>'
            for v in sg.get("versions") or [])
        song_blocks.append(f'<h3>{esc(sg["song"])}｜{sg["n_versions"]} 个现场版本</h3><ul>{items}</ul>')
    sync_rows = "\n".join(
        f'<tr><td>{esc(a["tour"])}「{esc(a.get("theme"))}」</td><td>{a.get("shows")}</td>'
        f'<td>{esc(a.get("album"))}（{esc(a.get("album_ym"))}）'
        + ("<sup>同月发行·口径待核</sup>" if a.get("album_same_month") else "")
        + f'</td><td>{a.get("album_songs_in_setlist")}/{a.get("album_songs_total")}</td>'
        f'<td>{a.get("coverage_pct")}%</td>'
        f'<td>{esc(a.get("album_prev"))} {a.get("album_prev_hits")}/{a.get("album_prev_total")}</td>'
        f'<td>{a.get("earlier_tour_songs")} 首（{a.get("earlier_tour_share_pct")}%）</td></tr>'
        for a in t.get("album_tour_sync") or [])
    live_rows = "\n".join(
        f'<li>{esc(r.get("version"))}：<strong>{esc(r.get("note"))} {r.get("hz")} Hz</strong>'
        f'（可信度 {esc(r.get("trust"))}）</li>'
        for r in (t.get("live_vs_studio") or []) if r.get("kind") == "B1 复现")
    sv = next((r for r in (t.get("live_vs_studio") or []) if r.get("kind") == "同曲对照"), None)
    return f'''<h2>一、王晰主导巡演现场（能力证据层）</h2>
<div class="hl">
<strong>现场最低稳定音 {esc(lo["note"])}（{lo["hz"]} Hz）</strong>——《{esc(lo["song"])}》{esc(lo["city"])} {esc(lo["date"])}。
复核状态：<strong>{esc(lo["verify"])}</strong>{f'，CREPE 交叉校验 {lo["crepe_hz"]} Hz' if lo.get("crepe_hz") else ""}。<br>
本层已有 {n} 条素材（场次音频实测 {s.get("n_stage_measured")} + 十曲精测并入 {s.get("n_from_precision")}），覆盖 {s.get("n_tours")} 个巡次、{s.get("n_songs")} 首曲目，其中 {ver} 条过复核门槛；
跨度中位 {s.get("span_median_octaves")} 个八度、音符内稳定性中位 {s.get("stability_median_cents")} 音分、颤音 {s.get("vibrato_rate_hz_median")} Hz / {s.get("vibrato_extent_cents_median")} 音分（仅场次音频实测口径的指标参与该项统计）。
</div>
<div class="method">
<strong>为什么这一层才算「现场能力」：</strong>巡演由他本人主导——选曲、调性、编排、曲目位置由他决定，唱什么、唱到多低是他自己的选择。
他人主导的舞台（综艺/晚会/商演/饭拍）由节目组选曲、电视混音、伴唱叠加共同决定，<strong>只能作互证，不能当作他的现场能力上限</strong>。
两层的测量管线完全相同（人声分离 → 逐帧 F0 → 稳健过滤），差别只在语料归属。
</div>
<h3>巡次汇总</h3>
<table>
<tr><th>巡次</th><th>城市</th><th>实测素材日期</th><th>n</th><th>最低稳定音</th><th>跨度中位</th><th>稳定性(音分)</th><th>颤音(Hz)</th></tr>
{tour_rows}
</table>
{"".join(song_blocks)}
<h3>巡演 × 专辑：每巡唱的是什么</h3>
<p class="sub" style="margin-top:0">「最近发行」= 该巡开始前最近发行的专辑（发行日期为 QQ 音乐核验的精确日期，见 <code>data/album_release_verify.md</code>）；「属前巡曲目」= 该巡曲目中已在此前巡次出现过的比例。</p>
<table>
<tr><th>巡次</th><th>场次</th><th>最近发行专辑</th><th>进歌单</th><th>覆盖率</th><th>上一张对照</th><th>属前巡曲目</th></tr>
{sync_rows}
</table>
{"<h3>现场 vs 录音室（B1 复现）</h3><ul>" + live_rows + "</ul>" if live_rows else ""}
{f'<p>同曲对照：录音室 {sv.get("studio_hz")} Hz ↔ 现场 {sv.get("live_hz")} Hz（{esc(sv.get("live_note"))}）——{esc(sv.get("note"))}</p>' if sv else ""}
<h3>逐素材明细</h3>
<table>
<tr><th>巡次</th><th>城市</th><th>日期</th><th>最低稳定音</th><th>Hz</th><th>最高稳定音</th><th>跨度</th><th>稳定性</th><th>颤音(Hz/音分)</th><th>复核</th><th>测量入口</th><th>来源</th></tr>
{detail_rows}
</table>
<p class="sub" style="margin-top:0">本层两个测量入口、同一口径：<strong>场次音频实测</strong>（巡演现场音轨 → 人声分离 → 逐帧 F0，含跨度/颤音等全指标）与
<strong>十曲精测</strong>（早前逐曲核验的现场个案，只有最低稳定音读数，相应列显示 —）。两者都按「最低稳定音」口径引用。</p>
<p class="sub" style="margin-top:0">⚠️ 标「待复核」「仅参考」的读数只列不判，不作能力依据；现场素材为公开视频音轨，非官方音源。</p>

'''



def cross_section() -> str:
    """双重校验：同一首歌「舞台版 vs QQ音乐官方版」"""
    if not CROSS.exists():
        return ""
    c = json.loads(CROSS.read_text(encoding="utf-8"))
    rows = []
    for p in c["pairs"]:
        f = lambda v, d=2: "—" if v is None else f"{v:.{d}f}"
        rows.append(f'<tr><td>{esc(p["song"])}</td><td>{esc(p.get("qq_name",""))[:26]}</td>'
                    f'<td>{esc(p["stage_low_note"])}（{f(p["stage_low"],0)}）</td>'
                    f'<td class="low">{esc(p["qq_low_note"])}（{f(p["qq_low"],0)}）</td>'
                    f'<td>{f(p["stage_span"])}</td><td>{f(p["qq_span"])}</td>'
                    f'<td>{f(p["stage_stab"],1)}</td><td>{f(p["qq_stab"],1)}</td>'
                    f'<td>{f(p["stage_vib"])}</td><td>{f(p["qq_vib"])}</td>'
                    f'<td>{esc(p.get("tier",""))[:10]}</td></tr>')
    table = "\n".join(rows)
    return f'''<h2>六、双重校验：同一首歌「舞台版 vs QQ音乐官方版」</h2>
<img src="assets/voice/crosscheck.png" alt="同一首歌舞台版与QQ音乐官方版的最低音、跨度、稳定性散点对照图">
<div class="hl">
<strong>结论：测量管线没有系统性偏差。</strong>可配对 <strong>{c["n_pairs"]} 组</strong>同曲：最低稳定音中位差 <strong>0.00 半音</strong>、
音域跨度 +0.09 八度、音符内稳定性 <strong>0.00 音分</strong>、颤音速率 −0.07Hz（均为中位差）。<br>
<strong>关键个案《渡荆门送别》</strong>：舞台版 C#2 69.7Hz ↔ QQ官方版（《经典咏流传》节目音源）<strong>C#2 69.7Hz，完全一致</strong>——
说明该曲的最低稳定音结论不受音源条件影响。
</div>
<table>
<tr><th>曲目</th><th>QQ 官方版</th><th>舞台最低音（MIDI）</th><th>QQ 最低音（MIDI）</th><th>舞台跨度</th><th>QQ跨度</th><th>舞台稳定性</th><th>QQ稳定性</th><th>舞台颤音</th><th>QQ颤音</th><th>来源等级</th></tr>
{table}
</table>
<div class="method">
<strong>怎么读：</strong>① 两侧都是「有损流媒体音源」，差别在录制/播出条件（现场·电视 vs 官方发行或节目官方音源）；
② 中位差≈0 说明管线稳定；个别曲目差 4–6 个半音，核查后多为<strong>不同场次/不同编配</strong>（并非同一录音）；
③ 跨来源不做「谁更准/谁更稳」的结论；④ 标注「待核」的 QQ 版本疑为粉丝上传，仅作交叉核对。
</div>'''

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
            f'<td><a href="{esc(x["url"])}" rel="noopener nofollow" target="_blank">{esc(x.get("song") or x["title"][:38])}</a></td>'
            f'<td class="low">{esc(x["low"])}</td><td>{x["low_hz"]:.1f}</td>'
            f'<td>{esc(x["high"])}</td><td>{x["high_hz"]:.0f}</td>'
            f'<td>{x["span"]:.2f}</td><td>{x["notes"]}</td><td>{x["density"]:.2f}</td>'
            f'<td>{x["stability"]:.1f}</td><td>{vib}</td></tr>')
    item_table = "\n".join(item_rows)

    # 情境对比：逐曲中位（与 voice.html 同一统计对象，避免"均值 vs 中位"混读）
    try:
        _ctx = json.loads(CTX.read_text(encoding="utf-8"))
        _mm = {m["key"]: m for m in _ctx["metrics"]}
        def _pair(key, pct=False):
            m = _mm[key]
            f = (lambda x: f"{x*100:.0f}%") if pct else (lambda x: f"{x:.2f}")
            return {"self": f(m["self_median"]), "other": f(m["other_median"]),
                    "p": m.get("p"), "r": m.get("r")}
        reg = {"low_lt_C3": _pair("register_share.low_lt_C3", True),
               "high_ge_C4": _pair("register_share.high_ge_C4", True)}
        span = _pair("span_octaves")
    except Exception:
        reg = {"low_lt_C3": {"self": "—", "other": "—"}, "high_ge_C4": {"self": "—", "other": "—"}}
        span = {"self": "—", "other": "—"}

    # ResearchProject + FAQPage（与 voice.html 共享同一套结构化数据措辞）
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from research_ld import research_project, faq_page, dataset_ref

    # 巡演现场层（第一层）：数据与 HTML 都必须在下方 rp/faq 之前就位
    tour_html = tour_layer_html()
    try:
        _tj = json.loads(TOUR.read_text(encoding="utf-8"))
        tour_n = (_tj.get("summary") or {}).get("n_materials")
        _t_lo = (_tj.get("summary") or {}).get("lowest") or {}
        _t_ver = (_tj.get("summary") or {}).get("n_verified")
    except Exception:
        tour_n, _t_lo, _t_ver = None, {}, None

    _p_low = (reg["low_lt_C3"].get("p") if isinstance(reg.get("low_lt_C3"), dict) else None)
    try:
        _lowp = _mm["low_stable.midi"].get("p")
    except Exception:
        _lowp = None
    rp = research_project(
        name="王晰声学档案：现场音域双层实测（王晰主导巡演现场 + 他人主导舞台）",
        url="https://wx409.github.io/stage.html",
        description=(
            f"同一测量管线分两层语料：能力层为王晰本人主导的巡演现场（{tour_n or '—'} 条已实测素材，"
            f"现场最低稳定音 {_t_lo.get('note','—')}（{_t_lo.get('hz','—')} Hz））；"
            f"对照层为他人主导场景的 {src['analyzed']} 个舞台素材，"
            "并与 72 首录音室曲目做 Mann–Whitney U 组间对比，用于区分「能力极限」与「使用模式」两类差异。"
        ),
        date_modified=d["generated_at"],
        dataset_url="https://wx409.github.io/data/archive_stage.json",
        based_on=[{
            "@type": "Dataset",
            "name": "方法版本 v1（单点最低值）",
            "version": "v1",
            "description": "方法版本记录，供版本谱系与学术引用追溯；结果以本页现行稳健口径为准。",
        }],
        parts=[
            dataset_ref("王晰主导巡演现场逐素材指标", "https://wx409.github.io/data/archive_stage_tour.json"),
            dataset_ref("32 个舞台素材逐条指标", "https://wx409.github.io/data/archive_stage.json"),
            dataset_ref("专辑 vs 舞台情境对比统计", "https://wx409.github.io/data/archive_context_compare.json"),
            dataset_ref("舞台版 vs QQ 音乐官方版双重校验", "https://wx409.github.io/data/archive_crosscheck.json"),
        ],
        keywords=["王晰", "现场音域", "巡演现场", "舞台实测", "综艺", "晚会", "F0", "人声分离", "情境对比"],
        method=(d.get("method") or {}).get("separation", "") + "；" + (d.get("method") or {}).get("f0", ""),
        scope_note=("最低音组间差异不显著，不可推断「他人主导的舞台唱不到低音」；"
                    "最高音读数含伴唱/和声干扰风险，需听辨。"),
    )
    faq = faq_page([
        ("王晰在巡演现场唱得到多低？",
         (f"以他本人主导的巡演现场语料为准：现行已实测 {tour_n} 条素材中，最低稳定音为 "
          f"{_t_lo.get('note','—')}（{_t_lo.get('hz','—')} Hz），实测于《{_t_lo.get('song','—')}》"
          f"{_t_lo.get('city','')} {_t_lo.get('date','')} 场，复核状态为{_t_lo.get('verify','—')}"
          + (f"，并做了 CREPE 交叉校验（{_t_lo.get('crepe_hz')} Hz）" if _t_lo.get("crepe_hz") else "")
          + f"；{tour_n} 条中 {_t_ver} 条过复核门槛。"
          "能力主张只看「最低稳定音」口径（音符本身 ≥0.2s、HNR ≥5dB、强度达标），未过门槛的读数只列不判。")
         if _t_lo else "巡演现场层数据待首次实测。"),
        ("为什么要把「巡演现场」和「他人主导舞台」分开？",
         "巡演由他本人主导：选曲、调性、编排与曲目位置由他决定，属于他自己的现场选择；"
         "综艺/晚会/商演/饭拍由节目组选曲、电视混音与伴唱叠加共同决定，"
         "因此那一层只作互证，不能当作他的现场能力上限。两层使用完全相同的测量管线，差别只在语料归属。"),
        ("他人主导的综艺/晚会上，王晰的音域会变窄吗？",
         (f"按现行稳健口径，「王晰主导（录音室专辑）」与「他人主导（舞台）」的最低稳定音差异不显著"
          f"（p={_lowp:.3f}），" if isinstance(_lowp, float) else "按现行稳健口径，最低稳定音差异不显著，")
         + "因此不能推断他人主导时音域变窄。统计上显著的是使用模式：高音区占比、跨度、音符内稳定性。"),
        ("为什么舞台上的高音区占比明显更高？",
         "综艺与晚会的编曲常升 key、加和声层、缩短单音时长，舞台曲目库与录音室专辑本身不同。"
         "这是曲目库与舞台使用模式带来的客观结果，多重因素叠加，不指向「刻意删掉低音」之类的推断。"),
        ("舞台版和录音室版的差异，是测量误差吗？",
         "已做双重校验：同一首歌的舞台版与 QQ 音乐官方版配对比对 24 组，"
         "最低稳定音中位差 0.00 半音、跨度差 +0.09 八度、音符内稳定性差 0.00 音分，测量系统本身一致。"),
        ("舞台实测里出现过的 B1 可信吗？",
         "现场 B1 只在已核验的个案中复现（杭州站），且需满足稳定音口径（时长 ≥0.2s、HNR ≥5dB）；"
         "低于 B1 理论值 61.74Hz 的孤立读数一律列为待复核，不纳入结论。"),
    ], url="https://wx409.github.io/stage.html")
    ld_extra = "\n".join(
        '<script type="application/ld+json">\n' + json.dumps(x, ensure_ascii=False, indent=2) + '\n</script>'
        for x in (rp, faq)
    )

    cross_html = cross_section()
    flagged = s.get("lowest_flagged") or []
    flag_html = ""
    if flagged:
        # 复核结论（低音复核_LowC.py 产出）：把「待复核」升级为「已复核判定」
        verify = {}
        try:
            _v = json.loads((ROOT / "data" / "archive_lowc_verify.json").read_text(encoding="utf-8"))
            verify = {x["name"]: x for x in _v.get("rows", [])}
        except Exception:
            verify = {}
        parts = []
        for x in flagged:
            hit = next((v for k, v in verify.items() if k.startswith(x.get("bvid", "")) or x["title"][:8] in k), None)
            if hit and hit.get("verdict") == "YIN_SUBHARMONIC":
                parts.append(f'{esc(x["title"])[:24]}（{esc(x["note"])} {x["hz"]}Hz）——'
                             f'<strong>已复核为「1/3 次谐波错误」</strong>：'
                             f'CREPE 在同一时刻读到 {hit.get("crepe_at_yin_hz")}Hz，'
                             f'真值约 {float(x["hz"]) * 3:.0f}Hz，<strong>确认不计入</strong>')
            else:
                parts.append(f'{esc(x["title"])[:24]}（{esc(x["note"])} {x["hz"]}Hz）——待人工听辨')
        lst = "；".join(parts)
        flag_html = ''          # 2026-09-10：相关素材已移出统计，页面不留解释


    ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"王晰现场音域实测数据集（王晰主导巡演现场 {tour_n or '—'} 条 + 他人主导舞台 {src['analyzed']} 个素材）",
        "description": (f"分两层：能力层为王晰本人主导的巡演现场 {tour_n or '—'} 条已实测素材（最低稳定音 "
                        f"{_t_lo.get('note','—')}（{_t_lo.get('hz','—')}Hz））；对照层为他人主导场景（综艺/晚会/盛典商演/饭拍）"
                        f"{src['analyzed']} 个素材：最低音读数（<strong>取证状态见表</strong>） {s['lowest']['note']}（{s['lowest']['hz']}Hz），"
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
<title>王晰现场音域实测｜巡演现场（能力层）与综艺晚会（对照层）双层实测</title>
<meta name="description" content="王晰现场音域双层实测：能力层为他本人主导的巡演现场 {tour_n or '—'} 条素材（最低稳定音 {_t_lo.get('note','—')} {_t_lo.get('hz','—')}Hz）；对照层为综艺/晚会/盛典商演/饭拍 {src['analyzed']} 个素材（可信最低稳定音 {esc(s['lowest']['note'])} {s['lowest']['hz']}Hz，跨度中位 {s['span_median']} 个八度）。含巡次汇总、同曲跨巡对比、巡演×专辑对照、逐条明细与分层口径说明。">
<link rel="canonical" href="https://wx409.github.io/stage.html">
<meta property="og:title" content="王晰现场音域实测 · 双层">
<meta property="og:description" content="能力层：巡演现场 {tour_n or '—'} 条素材，最低稳定音 {_t_lo.get('note','—')} {_t_lo.get('hz','—')}Hz；对照层：他人主导 {src['analyzed']} 个素材，可信最低 {esc(s['lowest']['note'])}，跨度中位 {s['span_median']} 个八度。">
<meta property="og:type" content="article">
<meta property="og:image" content="https://wx409.github.io/assets/voice/stage_range.png">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
{ld_extra}
<style>
.ttl-note{{font-size:11.5px;color:#8a7f6d;margin-top:2px}}{STYLE}</style>
</head>
<body>
<!-- NAV_START --><!-- NAV_END -->

<h1>🎤 现场音域实测 · 双层</h1>
<p class="sub">能力层：王晰主导巡演现场（{tour_n if tour_n else '—'} 条已实测素材）｜对照层：他人主导综艺 / 晚会 / 盛典商演 / 饭拍（{src['analyzed']} 个素材）· 更新 {esc(d['generated_at'])}</p>

{tour_html}

<div class="hl">
<strong>他人主导层的声学画像：</strong>可信最低稳定音 <strong>{esc(s['lowest']['note'])}（{s['lowest']['hz']} Hz，《{esc(s['lowest']['title'])}》）</strong>；
最高稳定音 <strong>{esc(s['highest']['note'])}（{s['highest']['hz']} Hz，《{esc(s['highest']['title'])}》）</strong>（含和声层可能）；
音域跨度中位 <strong>{s['span_median']} 个八度</strong>；音符内稳定性中位 <strong>{s['stability_median']} 音分</strong>；
颤音 <strong>{s['vibrato_hz_median']} Hz / {s['vibrato_cents_median']:.0f} 音分</strong>。
</div>

<img src="assets/voice/stage_range.png" alt="王晰他人主导现场 32 个素材实测音域长图，横轴频率、纵轴按分类与最低音排序">

<div class="card">
<strong>📐 声区分布（按时长加权，全组平均）</strong>：低音区（&lt;C3）<strong>{s['register_mean']['low_lt_C3']*100:.0f}%</strong>、
中音区（C3–B3）<strong>{s['register_mean']['mid_C3_B3']*100:.0f}%</strong>、
高音区（≥C4）<strong>{s['register_mean']['high_ge_C4']*100:.0f}%</strong>。
对比：他自己的录音室专辑为 23% / 63% / 4%（见 <a href="/voice.html">音域实测</a> 板块四）。
</div>

{flag_html}

<h2>二、他人主导层：语料来源与筛选</h2>
<p>来源：B站收藏夹「{esc(src['fav_title'])}」（fid={esc(src['fav_id'])}，共 {src['fav_count']} 条）。
自动归类 + 逐条人工校准后，纳入实测 <strong>{src['analyzed']} 个</strong>：
综艺 {len([x for x in d['items'] if x['cat']=='综艺'])}、
晚会 {len([x for x in d['items'] if x['cat']=='晚会'])}、
盛典商演 {len([x for x in d['items'] if x['cat']=='盛典商演'])}、
饭拍直拍 {len([x for x in d['items'] if x['cat']=='饭拍直拍'])}。
另有棚版混音 8 条（非现场，单列不计入）与他人分析视频/混剪 3 条（非原始音源，排除）。</p>

<h2>三、分类对比</h2>
<table>
<tr><th>分类</th><th>n</th><th>最低音中位(MIDI)</th><th>最高音中位(MIDI)</th><th>跨度中位</th><th>稳定性(音分)</th><th>密度(/s)</th><th>低音区占比</th><th>高音区占比</th></tr>
{cat_rows}
</table>
<p class="sub" style="margin-top:0">MIDI 参考：C3=48、C4=60、E4=64、C5=72、E5=76、C6=84。</p>

<h2>四、逐条明细（{src['analyzed']} 个素材）</h2>
<table>
<tr><th>#</th><th>分类</th><th>曲目（点击回 B站）</th><th>最低音</th><th>Hz</th><th>最高音</th><th>Hz</th><th>跨度</th><th>音符</th><th>密度</th><th>稳定性</th><th>颤音</th></tr>
{item_table}
</table>

<p class="sub" style="margin-top:0">⚠️ 上表「最高音」列（含 C5 及以上）存在<strong>伴唱/和声干扰风险</strong>，需人工听辨后再引用；「最低音」为 v2 稳健口径的稳定音。</p>

<h2>五、与「王晰主导」的对照</h2>
<div class="hl">
<strong>⚠️ 注意：</strong>「最低稳定音」的组间差异<strong>不显著</strong>（p=0.197）——两组在低音能力上没有统计意义上的差别。<br>
<strong>稳健的差异在「使用模式」而非「能力极限」</strong>：低音区（&lt;C3）占比 <strong>{reg['low_lt_C3']['self']} → {reg['low_lt_C3']['other']}（逐曲中位）</strong>、
高音区（≥C4）占比 <strong>{reg['high_ge_C4']['self']} → {reg['high_ge_C4']['other']}（逐曲中位）</strong>、最高音中位 <strong>F#4 → E5</strong>、跨度中位 <strong>{span['self']} → {span['other']} 个八度</strong>。
<span style="color:#8a7f6d">（此处为「逐曲中位」口径；上方声区分布卡片是「按时长加权的全组平均」，两者统计对象不同：本组加权平均高音区 {s['register_mean']['high_ge_C4']*100:.0f}%、低音区 {s['register_mean']['low_lt_C3']*100:.0f}%，不可与逐曲中位混读。）</span>
</div>
<p>上述差异是<strong>曲目库与舞台使用模式带来的客观结果，多重因素叠加</strong>（选曲、编配、调性、播出条件、伴唱叠加等），
不宜简化为单一因果。可确定的是：他的低音更多出现在自己主导的专辑里，而舞台素材整体偏中高音区——
这是「媒介情境如何改变声学呈现」的观察，而非对任何一方动机的推断。</p>
<p>另一项跨情境稳定的指标：<strong>颤音速率 5.17 → {s['vibrato_hz_median']} Hz（p=0.441，无显著差异）</strong>，
属极具辨识度的演唱习惯特征（<em>属演唱习惯，不作生物特征解读</em>）。详见 <a href="/voice.html">音域实测</a> 板块四（含统计检验与敏感性分析）。</p>

{cross_html}

<h2>七、方法与边界</h2>
<div class="method">
<strong>流程：</strong>B站音轨（yt-dlp 取最佳音频）→ 44.1k wav → demucs(htdemucs) 人声分离 → 自研 numpy YIN 逐帧 F0（fmin=55/fmax=1100/frame=2048/hop=512）→ 音符切分（稳定段 ≥80ms、抖动 &lt;0.6 半音）→ 稳健过滤（时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB；极值音级需该音符本身 ≥0.2s）。<br>
<strong>边界：</strong>① 素材为现场/电视/饭拍音轨，含观众噪声、伴奏比例差异、可能的修音与和声叠加——「稳定性更高」不能读成「现场唱得更准」；
② 本组含 4 个合唱/对唱（其中 1 个因人声轨无法可靠分离已移出统计，见下条），人声轨包含所有演唱者，其最高音可能来自其他歌手；
③ 低③ <strong>人声轨无法可靠分离的合唱素材，不纳入音高统计</strong>（此类素材的最低音读数易出现次谐波误锁，且最高音可能来自其他歌手）。于 B1 的孤立读数已单列「待复核」；
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
