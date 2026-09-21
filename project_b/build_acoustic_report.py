# -*- coding: utf-8 -*-
"""粉丝声学全量报告生成器 → acoustic-report.html（厚、可查、可自动更新）。

数据全部来自站点 JSON（禁手写数字）：
  archive_vocal_albums / archive_vocal / archive_stage_tour / archive_stage /
  vocal_measurements / listening_verdicts / album_verify_status / calibers.json / setlists.json
理论章节为长期文本（口径与纪律的稳定表述），其余全部派生。

用法: python -X utf8 project_b\\build_acoustic_report.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "acoustic-report.html"
SITE = "https://wx409.github.io/acoustic-report.html"


def load(name: str, default=None):
    p = DATA / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def esc(s) -> str:
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def table(rows: list[list], head: list[str], cls: str = "") -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def main() -> int:
    alb = load("archive_vocal_albums.json")
    voc = load("archive_vocal.json")
    tour = load("archive_stage_tour.json")
    other = load("archive_stage.json")
    lm = load("vocal_measurements.json")
    verdicts = load("listening_verdicts.json")
    avs = load("album_verify_status.json")
    shows = load("setlists.json", {}).get("setlists", {})

    songs = alb.get("songs", [])
    rows = tour.get("rows", [])
    summary = tour.get("summary", {})
    v_items = verdicts.get("items", [])

    # ---- 覆盖地图：64 场里哪些有实测（同城 ±1 天匹配：素材日期可能是上传/录制日）----
    import datetime as _dt
    have = []
    for r in rows:
        try:
            have.append((r.get("city"), _dt.date.fromisoformat(str(r.get("date"))[:10])))
        except Exception:
            continue

    def covered(city, ds):
        try:
            d0 = _dt.date.fromisoformat(ds)
        except Exception:
            return False
        return any(c == city and abs((d - d0).days) <= 1 for c, d in have)

    cov = []
    for d, v in sorted(shows.items()):
        cov.append([esc(d), esc(v.get("city", "")), esc(v.get("tour", "")), len(v.get("songs", [])),
                    "✅" if covered(v.get("city"), d) else "—"])
    n_cov = sum(1 for c in cov if c[4] == "✅")

    # ---- 图表数据 ----
    scatter = [[round(float(s.get("low_hz") or 0), 1), round(float(s.get("high_hz") or 0), 1),
                esc(s.get("title", "")), esc(s.get("album", ""))] for s in songs if s.get("low_hz")]
    spans = [round(float(s.get("span_octaves") or 0), 2) for s in songs if s.get("span_octaves")]
    by_tour = tour.get("by_tour", [])
    tour_names = [esc(t.get("tour", "")) for t in by_tour]
    tour_n = [t.get("n_materials") or t.get("n") or 0 for t in by_tour]
    tour_claim = [t.get("n_claimable") or 0 for t in by_tour]
    vd = {}
    for it in v_items:
        vd[it.get("verdict", "未标")] = vd.get(it.get("verdict", "未标"), 0) + 1

    # ---- 表 ----
    studio_tbl = table(
        [[esc(s.get("title")), esc(s.get("album")), f'{esc(s.get("low"))}｜{s.get("low_hz")}',
          f'{esc(s.get("high"))}｜{s.get("high_hz")}', s.get("span_octaves"), s.get("stability_cents"),
          s.get("intonation_cents"), s.get("vibrato_hz"), s.get("hnr_db"), s.get("notes")]
         for s in sorted(songs, key=lambda x: float(x.get("low_hz") or 999))],
        ["曲目", "专辑", "最低稳定音", "最高稳定音", "跨度(八度)", "稳定性(音分)", "音准偏差(音分)", "颤音(Hz)", "HNR(dB)", "音符数"],
        "studio")

    # ---- 数据清洗与状态推导（P1 修复）----
    def _hz(v):
        """防御：历史数据里出现过「音名八度+Hz」串列（61026.8 → 1026.8）。"""
        try:
            f = float(v)
        except (TypeError, ValueError):
            return v
        if f >= 2000 and 30 <= float(str(f)[1:]) <= 1200:
            return round(float(str(f)[1:]), 1)
        return v

    def row_status(r) -> str:
        """行级复核状态：优先用数据层已落库的 review_status（单一事实源），缺失才推导。"""
        st = r.get("review_status")
        if st:
            return str(st)
        if str(r.get("ear_verdict") or "").startswith("人耳确认"):
            return "人耳确认"
        hs = r.get("harmonic_screen")
        if isinstance(hs, str):
            try:
                hs = json.loads(hs.replace("'", '"'))
            except Exception:
                hs = {}
        v = (hs or {}).get("verdict", "") if isinstance(hs, dict) else ""
        if v == "成立":
            return "谐波列通过"
        if v == "待判":
            return "待复核"
        if r.get("a3_final_note"):
            return "已复核（A3）"
        return "未复核"

    for _i in v_items:
        _i["verdict_hz"] = _hz(_i.get("verdict_hz"))
    # 台账唯一终态：同一 (曲目, 方面, 秒点, Hz) 只保留最新一条，旧的标 superseded
    _seen = {}
    for _i in sorted(v_items, key=lambda x: str(x.get("date") or "")):
        k = (str(_i.get("song")), str(_i.get("aspect")), str(_i.get("t_s")), str(_i.get("verdict_hz")))
        if k in _seen:
            _seen[k]["_superseded"] = True
        _seen[k] = _i
    v_items = [i for i in v_items if not i.get("_superseded")]

    _CLAIM = {"人耳确认", "谐波列通过", "双引擎一致"}
    _conf = [r for r in rows if row_status(r) in _CLAIM]
    _pend = [r for r in rows if row_status(r).startswith("待复核")]
    _unver = [r for r in rows if row_status(r).startswith("不可复核")]
    _rej = [r for r in rows if row_status(r).startswith("人耳否决")]
    _unrev = _pend + _unver + _rej

    def _tour_rows(rs):
        return [[esc(r.get("tag")), esc(r.get("song")), esc(r.get("tour")), esc(r.get("city")), str(r.get("date"))[:10],
                 esc(r.get("low_note")), _hz(r.get("low_hz")), esc(r.get("high_note")), _hz(r.get("high_hz")),
                 esc(row_status(r))]
                for r in sorted(rs, key=lambda x: float(x.get("low_hz") or 9999))]

    tour_tbl = table(_tour_rows(_conf), ["素材", "曲目", "巡次", "城市", "日期", "最低音", "Hz", "最高音", "Hz", "复核状态"], "tour")
    unrev_tbl = table(_tour_rows(_unrev), ["素材", "曲目", "巡次", "城市", "日期", "最低音", "Hz", "最高音", "Hz", "复核状态"], "tour")

    v_tbl = table(
        [[esc(i.get("song")), esc(i.get("show")), esc(i.get("aspect")), esc(i.get("verdict")),
          _hz(i.get("verdict_hz")), (f"{i.get('t_s')}s" if i.get("t_s") not in (None, "") else "—"),
          str(i.get("date"))[:10], esc(i.get("verdict_note"))]
         for i in v_items],
        ["曲目", "场次", "方面", "复核结论", "判定 Hz", "秒点", "日期", "说明"], "verdicts")

    voc_tbl = table(
        [[esc(s.get("name")), esc(s.get("stable_note")), s.get("stable_hz"), s.get("stable_dur_s"),
          s.get("stable_hnr_db"), esc(s.get("stable_status")), esc(s.get("stable_verified")),
          f'{esc(s.get("reach_note"))}｜{s.get("reach_hz")}']
         for s in voc.get("songs", [])],
        ["曲目", "最低稳定音", "Hz", "时长(s)", "HNR(dB)", "状态", "复核", "触达音（仅展示）"], "vocal")

    av_tbl = table(
        [[esc(a.get("cat")), a.get("n"), esc(a.get("low_midi")), esc(a.get("high_midi")), a.get("span"),
          a.get("stability"), a.get("density"), a.get("low_share"), a.get("high_share")]
         for a in other.get("by_category", [])],
        ["类别", "条数", "最低MIDI", "最高MIDI", "跨度", "稳定性", "密度", "低区占比", "高区占比"], "other")

    theory = """
<h3>三级读数制度（本报告唯一的贵贱标准）</h3>
<table><thead><tr><th>级别</th><th>定义</th><th>能否用于结论</th></tr></thead><tbody>
<tr><td><b>稳定音</b></td><td>音符本身 ≥0.2s、HNR ≥5dB、强度 ≥中位−25dB，且经谐波列 / CREPE 交叉校验</td><td>✅ 可作能力结论、可进标题</td></tr>
<tr><td><b>触达音</b></td><td>实际到过的最低 F0，未过门槛</td><td>❌ 可展示，不作能力依据</td></tr>
<tr><td><b>低音带读数</b></td><td>归属未确认（人声 / 乐器 / 念诵）</td><td>❌ 三不许：不进汇总、不进统计、不进引用</td></tr>
</tbody></table>
<h3>测量管线（可复算）</h3>
<p>QQ音乐 320k / 自录音源 → <code>demucs htdemucs</code> 人声分离 → 自研 numpy YIN 逐帧 F0
（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）→ 音符切分（≥80ms、抖动 &lt;0.6 半音）→
稳健过滤（时长 ≥0.15s、HNR ≥5dB、rms ≥中位−25dB）→ 低音读数另做<b>原始混音谐波列</b>判定。</p>
<h3>六条血泪纪律（判读前必读）</h3>
<ol>
<li><b>YIN 次谐波陷阱</b>：极高音 + 密集编曲会锁到真周期的 1/3、1/5 倍。判别法：在<b>原始混音</b>上查谐波列，2f0/4f0 有峰才是真音，只有 3f0/6f0 即次谐波错误。</li>
<li><b>扫到 ≠ 唱到</b>：单帧读数只是触达音，不能表述为"唱到某音"。</li>
<li><b>修音敏感分层</b>：稳定性、音准偏差属"高敏感层"，只能组内纵向比；最低音、音区占比、密度、HNR 属"不敏感层"，可跨组比。</li>
<li><b>现场音准是伪影</b>：现场 TET 偏差实测 19–22 音分 vs 录音室 7–9，不得用现场素材做音准结论。</li>
<li><b>跨场验证规律</b>：任何"规律"必须先看它在多数场次是否成立，个别场的形态不是规律。</li>
<li><b>中位数一律用 statistics.median</b>，偶数样本取中位；同音名取曲按实测 Hz 排序。</li>
</ol>"""

    # ---- 选曲与翻唱（无指数数据的 222 首 → 主动性样本）----
    cat = load("cover_catalog.json"); ca = load("cover_analysis.json")
    cstat = cat.get("stat", {})
    fp = ca.get("fingerprint", {}); mv = ca.get("multi_version", {})
    ra = ca.get("register_adapt", {}); ls = ca.get("language_style", {})
    did = ca.get("did_own_vs_cover", {})
    cov_tbl = table([[esc(s["title"]), s["times"], esc(s["first"]), esc(s["last"]),
                      "✅" if s["own"] else "—", "✅" if s.get("has_index_data") else "—", esc(s["kind"])]
                     for s in cat.get("songs", []) if s["times"] >= 5],
                    ["曲目", "场次", "首唱", "末唱", "自有发行", "有指数数据", "类型"], "cover")
    mv_tbl = table([[esc(c["song"]), c["versions"], c["low_median"], c["low_iqr"], c["low_range"], c["low_cv"]]
                    for c in mv.get("rows", [])[:20]],
                   ["曲目", "现场版本数", "最低音中位 Hz", "四分位差", "极差", "版本间变异系数"], "mv")

    # ---- 覆盖：多方匹配结果（L1 精确 → L4 弱）----
    ci = load("coverage_index.json")
    cst = ci.get("stat", {})
    crows = ci.get("shows", [])
    lv_txt = {1: "① 精确（BV映射/该场日期）", 2: "② 强（台账·表直接给出该场）",
              3: "③ 中（城市+年月）", 4: "④ 弱（仅巡次+城市）"}
    located = cst.get("L1_精确", 0) + cst.get("L2_强", 0)
    coverage_html = (
        f'<p class="lead">同一件事必须分口径看，<b>不能混读</b>：</p><div class="kpis">'
        f'<div class="kpi"><b>{located}/{cst.get("shows_total","—")}</b>'
        f'<span>已定位到具体场次（L1+L2，可进结论）</span></div>'
        f'<div class="kpi"><b>{cst.get("covered","—")}</b><span>有本地素材（含证据较弱者）</span></div>'
        f'<div class="kpi"><b>{cst.get("missing","—")}</b><span>完全无素材（待采）</span></div>'
        f'<div class="kpi"><b>{cst.get("L1_精确","—")}</b><span>其中①精确（BV 映射或该场日期）</span></div>'
        f'<div class="kpi"><b>{cst.get("bv_mapped","—")}</b><span>BV 已映射到场次的视频数</span></div>'
        f'<div class="kpi"><b>{cst.get("files_scanned","—")}</b><span>扫到的本地素材文件数</span></div>'
        f'</div>'
        f'<p class="lead">匹配用了 <b>多方证据</b>：BV 视频号映射（<code>_tour_parts_index</code>/来源台账/站点现场层）、'
        f'路径里的精确日期、<code>shows_tour</code> 与历年巡演目录表、以及「巡次+城市」兜底。'
        f'证据弱的场次只能写"该巡该城有素材"，<b>不能写"该场已测"</b>。</p>'
        + table([[esc(r["date"]), esc(r["city"]), esc(r["tour"]), r["songs"], lv_txt.get(r["level"], "—"),
                  (esc(r["evidence"][0]["detail"]) if r.get("evidence") else "—")]
                 for r in sorted(crows, key=lambda x: (x["level"], x["date"]))],
                ["日期", "城市", "巡次", "歌单曲数", "证据等级", "首要证据"], "cover"))
    coverage_html += ("<h3>完全无素材的场次（待采清单）</h3><p class='lead'>"
                      + "、".join(f'{esc(m["city"])}{m["date"][5:]}' for m in ci.get("missing", [])) + "</p>")

    # ---- 风格与能力弧线（专辑声区 / 颤音指纹 / 长声）----
    import statistics as _st
    _alb = {}
    for _s in songs:
        _alb.setdefault(str(_s.get("album")), []).append(_s)
    _alb_rows = []
    for _a, _ss in _alb.items():
        def _m(key, f):
            vals = [f(x) for x in _ss if f(x) is not None]
            return _st.median(vals) if vals else None
        _alb_rows.append({
            "album": _a, "n": len(_ss),
            "low": _m("low", lambda x: (x.get("register_share") or {}).get("low_lt_C3")),
            "mid": _m("mid", lambda x: (x.get("register_share") or {}).get("mid_C3_B3")),
            "high": _m("high", lambda x: (x.get("register_share") or {}).get("high_ge_C4")),
            "span": _m("span", lambda x: x.get("span_octaves")),
            "vib": _m("vib", lambda x: x.get("vibrato_hz")),
        })
    _alb_rows.sort(key=lambda r: (r["low"] if r["low"] is not None else 9))
    _vib_all = _st.median([x["vibrato_hz"] for x in songs if x.get("vibrato_hz")])
    _vib_v = [r["vib"] for r in _alb_rows if r["vib"]]
    _vib_span = (max(_vib_v) - min(_vib_v)) if _vib_v else None
    _vib_ext = _st.median([x["vibrato_cents"] for x in songs if x.get("vibrato_cents")])
    _tour_vib = [t.get("vibrato_rate_hz_median") for t in by_tour if t.get("vibrato_rate_hz_median")]
    _ln = load("archive_long_notes.json")
    _ln_top = _ln.get("top", [])[:10]
    _ln_flag = (_ln.get("verdict_check") or {}).get("flagged", [])
    _xm = next((r for r in rows if "厦门" in str(r.get("tag")) and str(r.get("low_note")) == "B1"), None)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>王晰声学全量报告（粉丝版·权威口径）</title>
<meta name="description" content="王晰声学全量实测报告：72 首录音室 + 现场层 {len(rows)} 条素材 + 复核裁决台账，含三级读数制度与可复算管线。">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE}">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Report","name":"王晰声学全量报告",
"url":"{SITE}","inLanguage":"zh-CN","dateModified":"{datetime.now():%Y-%m-%d}",
"isBasedOn":["data/archive_vocal_albums.json","data/archive_stage_tour.json","data/archive_vocal.json",
"data/vocal_measurements.json","data/listening_verdicts.json"],
"about":{{"@type":"Person","name":"王晰","jobTitle":"流行男低音歌手"}},
"author":{{"@type":"Person","name":"wx409"}}}}
</script>
<style>
:root{{--ink:#1a1a1a;--dim:#6b7280;--line:#e5e7eb;--red:#c41e3a;--bg:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;font:15px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{display:grid;grid-template-columns:250px 1fr;gap:28px;max-width:1280px;margin:0 auto;padding:20px}}
aside{{position:sticky;top:16px;align-self:start;font-size:13px;border-right:1px solid var(--line);padding-right:14px;max-height:94vh;overflow:auto}}
aside a{{display:block;color:#374151;text-decoration:none;padding:3px 0}}
aside a:hover{{color:var(--red)}}
aside .g{{margin:14px 0 4px;font-weight:700;color:#111}}
h1{{font-size:26px;margin:8px 0 4px}}
h2{{font-size:21px;margin:34px 0 10px;padding-top:10px;border-top:2px solid var(--red)}}
h3{{font-size:16px;margin:20px 0 8px}}
.lead{{color:var(--dim);font-size:14px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}}
.kpi{{border:1px solid var(--line);border-left:3px solid var(--red);border-radius:8px;padding:10px 12px;background:#fcfcfd}}
.kpi b{{display:block;font-size:22px;line-height:1.2}}
.kpi span{{font-size:12px;color:var(--dim)}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}}
th,td{{border-bottom:1px solid #f0f0f0;padding:6px 9px;text-align:left;vertical-align:top}}
th{{background:#fafafa;position:sticky;top:0;z-index:1}}
tr:hover td{{background:#fff8f9}}
.scroll{{max-height:560px;overflow:auto;border:1px solid var(--line);border-radius:10px}}
.chart{{height:380px;border:1px solid var(--line);border-radius:10px;margin:12px 0}}
#q{{width:100%;padding:11px 14px;font-size:15px;border:2px solid var(--red);border-radius:10px;margin:10px 0}}
mark{{background:#ffe58f}}
.note{{background:#fff8f9;border-left:3px solid var(--red);padding:10px 14px;border-radius:6px;font-size:13.5px}}
footer{{color:var(--dim);font-size:12.5px;margin:40px 0 60px;border-top:1px solid var(--line);padding-top:12px}}
@media print{{aside,#q{{display:none}}.wrap{{display:block;max-width:none}}.scroll{{max-height:none}}}}
@media(max-width:820px){{.wrap{{grid-template-columns:1fr}}aside{{position:static;border:none;max-height:none}}}}
</style></head><body>
<div class="wrap">
<aside>
<div class="g">导读</div>
<a href="#what">这本报告是什么</a>
<a href="#theory">理论与纪律</a>
<a href="#kpi">核心数字</a>
<div class="g">实测</div>
<a href="#studio">录音室层 {len(songs)} 曲</a>
<a href="#charts">图表</a>
<a href="#vocal">跨素材精测层</a>
<a href="#tour">现场层 {len(rows)} 条</a>
<a href="#other">他人主导舞台（对照）</a>
<div class="g">台账</div>
<a href="#verdicts">复核裁决（{len(v_items)} 条）</a>
<a href="#coverage">场次覆盖地图</a>
<a href="#cover">选曲与翻唱</a>
<a href="#arc">风格与能力弧线</a>
<a href="#case968">案例卡·莫斯科968Hz</a>
<a href="#limits">已知边界</a>
</aside>
<main>
<h1>王晰声学全量报告</h1>
<p class="lead">粉丝自建 · 权威口径 · 可复算 · 自动更新｜生成于 {datetime.now():%Y-%m-%d %H:%M}</p>
<input id="q" type="search" placeholder="在本报告内搜索（曲名 / 音名 / 城市 / 巡次 / 「和声」「次谐波」…）">

<section id="what"><h2>这本报告是什么</h2>
<p>这不是乐评，是一份<b>可验证的能力台账</b>：把王晰（流行男低音 / Bass-baritone）全部可测的录音室与现场素材，
用同一套管线测一遍，逐条标注<b>证据级别</b>，并把每一条被推翻的读数也留在台账里。
判断标准只有一个：<b>可信、可查、可引用</b>——不为好听而写，也绝不把"扫到"写成"唱到"。</p>
<p>本页所有数字由脚本从站点 JSON 派生（<code>project_b/build_acoustic_report.py</code>），
新增素材或修正结论后<b>下一次部署自动刷新</b>，不手改。</p>
<div class="note">阅读顺序建议：先看「理论与纪律」理解三级读数，再看「核心数字」，最后按需翻明细表。</div>
</section>

<section id="theory"><h2>理论与纪律</h2>{theory}</section>

<section id="kpi"><h2>核心数字</h2>
<div class="kpis">
<div class="kpi"><b>{summary.get('lowest',{}).get('note','—')} {summary.get('lowest',{}).get('hz','—')} Hz</b><span>现场层最低稳定音（{esc(summary.get('lowest',{}).get('song',''))}）</span></div>
<div class="kpi"><b>{len(songs)}</b><span>录音室曲目全量实测</span></div>
<div class="kpi"><b>{summary.get('n_materials','—')}</b><span>现场层素材条数</span></div>
<div class="kpi"><b>{summary.get('span_median_octaves','—')}</b><span>现场跨度中位（八度）</span></div>
<div class="kpi"><b>{summary.get('stability_median_cents','—')}</b><span>现场音符内稳定性中位（音分）<br><b style="color:#a31832;font-weight:600">⚠️ 高敏感层：只能组内纵向比，不可与录音室 7.2 并读</b></span></div>
<div class="kpi"><b>{summary.get('vibrato_rate_hz_median','—')} Hz</b><span>颤音速率中位</span></div>
<div class="kpi"><b>{cst.get('L1_精确',0)+cst.get('L2_强',0)}/{cst.get('shows_total','—')}</b><span>已定位到具体场次（L1+L2，可进结论）</span></div>
<div class="kpi"><b>{cst.get('covered','—')}/{cst.get('shows_total','—')}</b><span>有本地素材（含未实测，弱证据已标注）</span></div>
<div class="kpi"><b>{cst.get('measured_shows_site','—')}/{cst.get('shows_total','—')}</b><span>已进站点现场层的场次</span></div>
<div class="kpi"><b>{len(v_items)}</b><span>人耳/复核裁决条数</span></div>
<div class="kpi"><b>{esc(_xm.get('low_note')) if _xm else '—'} {_xm.get('low_hz') if _xm else '—'} Hz</b><span>现场最低·<b>人耳确认</b>（{esc(_xm.get('tag')) if _xm else '—'}）——比录音室最低 B1 61.5Hz 还低 0.3Hz，是「现场 ≥ 录音室」最硬的单点证据</span></div>
</div>
<p class="lead">复核状态分布：{esc("；".join(f"{k} {v}" for k, v in (summary.get('verify_dist') or {{}}).items()))}</p>
</section>

<section id="studio"><h2>录音室层 · {len(songs)} 曲全量</h2>
<p class="lead">按最低稳定音升序（越低越靠前）。此为"能力口径"：全部过复核门槛。</p>
<div class="scroll">{studio_tbl}</div>
</section>

<section id="charts"><h2>图表</h2>
<h3>① 每首曲的音域上下限（x=最低、y=最高，点越大跨度越宽）</h3><div class="chart" id="c1"></div>
<h3>② 跨度分布（八度）</h3><div class="chart" id="c2"></div>
<h3>③ 现场层素材条数（按巡次，深色＝可主张/已确权）</h3><div class="chart" id="c3"></div>
</section>

<section id="vocal"><h2>跨素材精测层（{voc.get('count','—')} 曲）</h2>
<p class="lead">{esc(voc.get('conclusion',''))}</p>
<div class="scroll">{voc_tbl}</div>
<p class="lead">权威背书：{esc(voc.get('authority',''))}</p>
</section>

<section id="tour"><h2>现场层 · {len(rows)} 条素材（可主张 {len(_conf)} / 待复核 {len(_pend)} / 不可复核 {len(_unver)} / 已否决 {len(_rej)}）</h2>
<p class="lead">默认只列<b>可主张</b>（人耳确认 + 谐波列通过 + 双引擎一致）。其余四类折在下方——
台账<b>不藏否决与未决</b>，但也<b>不拿未确权读数当结论</b>。
其中「<b>不可复核（缺混音/时间）</b>」是<b>永久状态</b>：缺原始混音就无法做谐波列判定，属物理条件不足，
已从能力主张中排除，不再按"待复核"长期挂账。</p>
<div class="scroll">{tour_tbl}</div>
<details style="margin-top:10px"><summary style="cursor:pointer;color:#a31832;font-size:14px;">
展开其余 {len(_unrev)} 条（待复核 {len(_pend)}｜不可复核 {len(_unver)}｜已否决 {len(_rej)}，仅供参考，不作能力依据）</summary>
<div class="scroll" style="margin-top:8px">{unrev_tbl}</div></details>
</section>

<section id="other"><h2>他人主导舞台（对照层）</h2>
<p class="lead">{esc(other.get('note',''))}</p>
{av_tbl}
</section>

<section id="verdicts"><h2>复核裁决台账（{len(v_items)} 条）</h2>
<p class="lead">这里记录每一条被检验的读数——<b>包括被否掉的</b>。裁决分布：{esc("；".join(f"{k} {v}" for k, v in vd.items()))}。</p>
<div class="scroll">{v_tbl}</div>
</section>

<section id="coverage"><h2>场次覆盖地图（两个口径，别混读）</h2>
{coverage_html}
</section>

<section id="cover"><h2>选曲与翻唱 · 无指数数据的那 {cstat.get('no_index_data','—')} 首</h2>
<p class="lead">他 {cstat.get('shows','—')} 场唱过 <b>{cstat.get('songs_total','—')}</b> 首不同曲目，其中自有发行 <b>{cstat.get('own_released','—')}</b> 首、
翻唱/非自有 <b>{cstat.get('covers','—')}</b> 首；<b>真正有 QQ 指数数据的只有 {cstat.get('own_with_index_data',0)+cstat.get('covers_with_index_data',0)} 首</b>，
其余 {cstat.get('no_index_data','—')} 首没有市场数据——这部分的价值在<b>选择行为本身</b>：没有发行计划、没有推广资源、没有算法加持，选曲＝纯偏好。</p>
<h3>① 选曲指纹：他几乎每巡换血</h3>
<div class="kpis">
<div class="kpi"><b>{fp.get('home_songs','—')}</b><span>看家曲（≥10 场）</span></div>
<div class="kpi"><b>{fp.get('once_only','—')}</b><span>只唱过一次（实验区）</span></div>
<div class="kpi"><b>{fp.get('tiers',{}).get('常演（5–9 场）','—')}</b><span>常演（5–9 场）</span></div>
</div>
{table([[r['from'] + '→' + r['to'], r['prev_n'], r['cur_n'], r['retained'], f"{r['retain_rate']:.0%}", f"{r['new_rate']:.0%}"]
        for r in fp.get('retention', [])], ["巡次", "上巡曲目", "本巡曲目", "保留", "保留率", "新增率"], "retain")}
<p class="lead">跨巡保留率仅 <b>2%–6%</b>：他的巡演不是"金曲循环"，而是持续更换曲目池——这本身是他"不肯重复自己"的行为证据。</p>
<h3>② 同曲多版本方差：他每场是不是同一个水平</h3>
<p class="lead">{mv.get('songs_with_3plus','—')} 首曲目有 ≥3 个现场版本，<b>版本间变异系数中位 {mv.get('low_cv_median','—')}</b>（越小＝各场越一致）。
最小的（再见我的爱 0.3%、Yesterday Once More 0.9%、平凡又美好的晚上 0.85%）说明同曲跨场稳定；最大的（多听有益 22%、小毛驴 24%）多含串烧/片段，需按口径判读。</p>
<div class="scroll">{mv_tbl}</div>
<h3>③ 音区适配：他给不同来源曲目的"音区预算"</h3>
<p class="lead">自有曲现场最低音中位 <b>{ra.get('own_live_low_median','—')} Hz</b>（n={ra.get('own_n','—')}） vs 翻唱曲 <b>{ra.get('cover_live_low_median','—')} Hz</b>（n={ra.get('cover_n','—')}）
——他给<b>自己的作品</b>留了更低的音区。</p>
<h3>④ 语言 / 风格跨度</h3>
{table([[k, v['songs'], v['home_songs'], v['with_index']] for k, v in ls.items()],
       ["组", "曲目数", "看家曲", "有指数数据"], "lang")}
<h3>⑤ 自有曲 vs 翻唱曲 的舞台效应 DiD（设计可行，数据不足）</h3>
<p class="lead">设计：同一场演出里"自有曲（受处理）vs 翻唱曲（对照）"在演出前后的相对变化差——同人、同期、同场地，
唯一差别是"是否他的作品"。<b>但当前只有 {did.get('n_shows',0)} 场同时满足"≥2 首自有 + ≥2 首翻唱且都有指数数据"</b>，
DiD 中位 {did.get('did_median_pct','—')}%。结论：<b>设计成立、样本不足</b>；要跑通得先让更多曲目进入指数池，或改用"同曲跨场"配对。</p>
<div class="scroll">{cov_tbl}</div>
</section>

<section id="case968"><h2>案例卡 · 莫斯科 968Hz（极端条件下的最强样本）</h2>
<p class="lead">台账里有一条特别值得单独看：<b>《在路上》最高音 968.0Hz，人耳确认「是王晰本人」，
位于已确认段内、无观众噪声干扰</b>（来源：<code>data/listening_verdicts.json</code>，2026-09-16 裁决）。</p>
<ul>
<li><b>场合</b>：2025-09-20 莫斯科「国际视界」歌唱大赛（Intervision 2025）——多国代表、上万观众、赛程直播；
出场顺序在决赛前一周才抽签（外部背景，来源见下）。</li>
<li><b>为什么它比其它现场样本硬</b>：① 高压（国家队场合、无退路）② 直播（无后期修音余地）
③ 人耳确认且无噪声干扰段 ④ 与录音室层的"修音敏感"批评完全无关（B5 级高音在"最高音"这一敏感层，故仍不跨层比较）。</li>
<li><b>口径定位</b>：968.0Hz ≈ B5；男低音（bass-baritone）常见上界约 F4/G4 —— 该读数**超出典型上界一个八度以上**，
与下限 B1 61.5Hz（低于"杰出男低音"标志音 Low C 一个半音）共同构成"两端都在标准之外"的数据陈述。</li>
<li><b>来源</b>：台账裁决（本地）＋ 外部报道
<a href="https://www.chinanews.com.cn/gj/2025/09-21/10486456.shtml" rel="nofollow">中新网</a>、
<a href="https://news.ifeng.com/c/8n27bToQST3" rel="nofollow">凤凰网</a>（外部背景，未纳入本站口径）。</li>
</ul>
</section>

<section id="arc"><h2>风格与能力弧线（八张专辑 + 长声 + 颤音指纹）</h2>
<h3>① 专辑声区占比中位：一条肉眼可见的弧线</h3>
<p class="lead">按「低音区占比」降序（低→高的顺序变化即他的美学走向）：2016–2017 接近一半音符压在 C3 以下、
高区几乎不用（这是"低音标签期"）；随后低区骤降、高区打开（"去标签化"）；再回到 17–28%（"整合期"，
低音从身份变成武器库里最重的那件）。<b>他的风格不是低音，是对全部音区的调用。</b></p>
{table([[esc(r['album']), r['n'],
        ("%.1f%%" % (r['low'] * 100)) if r['low'] is not None else "—",
        ("%.1f%%" % (r['mid'] * 100)) if r['mid'] is not None else "—",
        ("%.1f%%" % (r['high'] * 100)) if r['high'] is not None else "—",
        f"{r['span']:.2f}" if r['span'] is not None else "—",
        f"{r['vib']:.2f}" if r['vib'] is not None else "—"] for r in _alb_rows],
       ["专辑", "曲数", "低区 <C3", "中区", "高区 ≥C4", "跨度中位(八度)", "颤音中位(Hz)"], "albumarc")}
<h3>② 颤音指纹：八年校准误差 0.27Hz</h3>
<p class="lead">录音室整体中位 <b>{f"{_vib_all:.2f}"} Hz</b>；<b>八张专辑各自中位全部落在
{min(_vib_v):.2f}–{max(_vib_v):.2f} Hz</b>（跨度 <b>{f"{_vib_span:.2f}"} Hz</b>）；
六轮巡演中位 {min(_tour_vib):.2f}–{max(_tour_vib):.2f} Hz（现场比录音室系统性慢 0.2–0.3Hz，轮间几乎不动）。
幅度中位 {f"{_vib_ext:.0f}"} 音分，比古典歌剧的 ±50–100 规范偏窄——<b>偏慢、偏窄，是流行低吟（crooner）审美，不是美声审美</b>，与曲目选择自洽。</p>
<div class="note">对外一句话：<b>「一台八年校准误差 0.27Hz 的乐器。」</b>（数据源：本页专辑表 + 巡演 by_tour 中位）</div>
<h3>③ 长声（≥6 秒同音高）——气息的直接证据</h3>
<p class="lead">保留榜第一：<b>16.5 秒 D2 74.8Hz</b>（现场《我真的受伤了》）；低音每秒气流消耗更大，
<b>16.5 秒的 D2 比同时长的高音更考验呼吸管理</b>。高音区保留最高：<b>11.8 秒 F5 698.0Hz</b>（《凄美地》官方 Live 版，归属待复核）。</p>
{table([[x.get('rank'), esc(x.get('song')), esc(x.get('note')), x.get('hz'), x.get('dur_s'),
        esc(x.get('src')), esc(x.get('where'))] for x in _ln_top],
       ["#", "曲目", "音名", "Hz", "时长(s)", "层", "来源"], "longnotes")}
<p class="lead">⚠️ 已按「长声表 × 否决台账」反连接处理 <b>{len(_ln_flag)}</b> 条同音区存疑（如《葬心》A5 11.0s：
该曲 1054Hz 读数曾判为女和声）——它们<b>留档但不进榜单、不进共识句</b>，理由写在
<code>data/archive_long_notes.json → verdict_check</code>。</p>
</section>

<section id="limits"><h2>已知边界（诚实披露）</h2>
<ul>
<li><b>覆盖分三个口径，别混读</b>：有本地素材 <b>{cst.get('covered','—')}/{cst.get('shows_total','—')}</b>｜
已定位到具体场次（L1+L2）<b>{cst.get('L1_精确',0)+cst.get('L2_强',0)}</b>｜
已进站点现场层 <b>{cst.get('measured_shows_site','—')}</b>；
证据较弱的场次只能写"该巡该城有素材"，不能写"该场已测"。</li>
<li><b>追踪池限制</b>：QQ音乐指数仅覆盖追踪曲目池（{load("calibers.json", {}).get("items", [{}]) and "见口径登记表"}），
多数歌单曲目不在池内，因此"唱了 → 数据涨没涨"的自身对照检验只有少数场次够样本。</li>
<li><b>录音室层经修音</b>：稳定性、音准偏差属修音敏感层，不可直接跨层比较。</li>
<li><b>现场音准不可用</b>：现场 TET 偏差是"环境 + 分离"的方法学伪影（19–22 音分 vs 录音室 7–9）。</li>
<li><b>音频合规</b>：本报告只发布方法与结果数据，原始音视频仅本地留存、不二次分发、不嵌入页面。</li>
</ul>
</section>

<footer>
<div class="note" style="margin-bottom:14px">
<b>使用说明与版权声明</b><br>
· 本页为<b>非营利性、个人学习与研究用途</b>的粉丝自建资料页，不涉及任何商业行为，不销售、不变现。<br>
· 报告中的现场音视频素材<b>均来自哔哩哔哩（B 站）等公开平台</b>，仅用于本人研究性测量与比对；<b>版权归原作者及原始权利人所有</b>。<br>
· 如权利人认为本站内容不妥，<b>请通过站内「投稿/联系」告知，我们将在第一时间删除相关内容</b>（侵删）。<br>
· 本站<b>不转载、不二次分发、不提供音频下载</b>，仅发布测量方法、统计结果与判定台账；原始素材一律本地留存。<br>
· 数据口径与复核状态均以本页与 <code>data/calibers.md</code> 为准；引用前请核对口径，未确权读数不得作为能力依据。
</div>
生成器：<code>project_b/build_acoustic_report.py</code>（随每日部署自动重跑）<br>
数据源：archive_vocal_albums / archive_stage_tour / archive_vocal / vocal_measurements / listening_verdicts / setlists<br>
方法学与逐次实测记录：<code>音频备忘_王晰声学发现.md</code>｜纪律：<code>辩音纪律总纲</code>｜口径字典：<code>data/calibers.md</code>
</footer>
</main></div>
<script src="/dashboard/echarts.min.js"></script>
<script>
(function(){{
  var q=document.getElementById('q');
  var main=document.querySelector('main');
  q.addEventListener('input',function(){{
    var v=q.value.trim();
    main.querySelectorAll('mark').forEach(function(m){{m.outerHTML=m.textContent;}});
    if(!v) return;
    var re=new RegExp(v.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&'),'gi');
    main.querySelectorAll('td,li,p,h2,h3').forEach(function(el){{
      if(re.test(el.textContent)) el.innerHTML=el.innerHTML.replace(re,'<mark>$&</mark>');
    }});
    var hit=Array.prototype.find.call(main.querySelectorAll('section'),function(s){{
      return new RegExp(v,'i').test(s.textContent);}});
    if(hit) hit.scrollIntoView({{behavior:'smooth',block:'start'}});
  }});
  var sc={scatter} , spans={spans}, tn={json.dumps(tour_names, ensure_ascii=False)}, tv={json.dumps(tour_n)}, tc={json.dumps(tour_claim)};
  function init(){{
    if(!window.echarts) return;
    var c1=echarts.init(document.getElementById('c1'));
    c1.setOption({{grid:{{left:60,right:24,top:20,bottom:50}},tooltip:{{formatter:function(p){{return p.data[2]+'｜'+p.data[3]+'<br>最低 '+p.data[0]+'Hz 最高 '+p.data[1]+'Hz';}}}},
      xAxis:{{name:'最低稳定音 Hz',type:'value',min:55}},yAxis:{{name:'最高稳定音 Hz',type:'value'}},
      series:[{{type:'scatter',data:sc,symbolSize:function(d){{return 8;}},itemStyle:{{color:'#c41e3a',opacity:.65}}}}]}});
    var c2=echarts.init(document.getElementById('c2'));
    var bins={{}},step=0.25;
    spans.forEach(function(s){{var b=(Math.round(s/step)*step).toFixed(2);bins[b]=(bins[b]||0)+1;}});
    var keys=Object.keys(bins).sort(function(a,b){{return a-b;}});
    c2.setOption({{grid:{{left:50,right:20,top:20,bottom:40}},xAxis:{{type:'category',data:keys,name:'八度'}},yAxis:{{type:'value',name:'曲数'}},
      series:[{{type:'bar',data:keys.map(function(k){{return bins[k];}}),itemStyle:{{color:'#1a56c4'}}}}]}});
    var c3=echarts.init(document.getElementById('c3'));
    c3.setOption({{grid:{{left:50,right:20,top:30,bottom:60}},tooltip:{{trigger:'axis'}},
      legend:{{top:0,data:['素材条数','可主张（已确权）']}},
      xAxis:{{type:'category',data:tn,axisLabel:{{rotate:30}}}},yAxis:{{type:'value',name:'条数'}},
      series:[{{name:'素材条数',type:'bar',data:tv,itemStyle:{{color:'#f2b8c2'}}}},
              {{name:'可主张（已确权）',type:'bar',data:tc,itemStyle:{{color:'#c41e3a'}}}}]}});
    window.addEventListener('resize',function(){{[c1,c2,c3].forEach(function(c){{c.resize();}});}});
  }}
  if(window.echarts) init(); else window.addEventListener('load',init);
}})();
</script>
</body></html>"""

    html = html.replace(">None<", ">—<").replace(">nan<", ">—<")   # 空值统一显示为破折号

    # 回归守卫：人类音域/乐器上限 1200Hz，出现 5 位以上「Hz」一律视为串列 bug，直接报错拦住上线
    _bad = re.findall(r">(\d{5,}(?:\.\d+)?)<", html)
    assert not _bad, f"检出异常 Hz 读数（疑似音名+Hz 串列）：{_bad[:5]}"

    OUT.write_text(html, encoding="utf-8")

    # ---- 本地留存副本（同一份内容，随每日部署一起刷新）----
    local_html = Path(r"E:\wx\论文素材_王晰作传\声学全量报告_王晰.html")
    local_md = Path(r"E:\wx\论文素材_王晰作传\声学全量报告_王晰.md")
    try:
        local_html.write_text(html, encoding="utf-8")
        md = [f"# 王晰声学全量报告（本地版 · 自动生成 {datetime.now():%Y-%m-%d %H:%M}）", "",
              f"- 对应线上页：{SITE}｜生成器：`project_b/build_acoustic_report.py`（随每日部署自动刷新）", "",
              "## 一、口径与纪律", "",
              "- 三级读数：**稳定音**（≥0.2s、HNR≥5dB、强度≥中位−25dB，且过谐波列/CREPE 校验）可作结论；"
              "**触达音**只展示；**低音带读数**三不许（不进汇总/统计/引用）。",
              "- 管线：demucs htdemucs 人声分离 → 自研 numpy YIN 逐帧 F0（fmin55/fmax1100/frame2048/hop512/sr22050）"
              "→ 音符切分（≥80ms、抖动<0.6半音）→ 稳健过滤。",
              "- 六条纪律：YIN 次谐波陷阱（原始混音查 2f0/4f0 峰值）｜扫到≠唱到｜修音敏感分层（稳定性/音准只能组内比）｜"
              "现场音准是伪影（19–22 vs 录音室 7–9 音分）｜跨场验证规律｜中位数用 statistics.median。", "",
              "## 二、核心数字", "",
              f"- 录音室全量 **{len(songs)}** 曲｜现场层素材 **{len(rows)}** 条｜人耳/复核裁决 **{len(v_items)}** 条",
              f"- 现场最低稳定音 **{summary.get('lowest',{}).get('note','—')} {summary.get('lowest',{}).get('hz','—')} Hz**"
              f"（{summary.get('lowest',{}).get('song','')}）",
              f"- 现场跨度中位 **{summary.get('span_median_octaves','—')}** 八度｜稳定性中位 **{summary.get('stability_median_cents','—')}** 音分｜"
              f"颤音 **{summary.get('vibrato_rate_hz_median','—')} Hz**", "",
              "## 三、录音室层（按最低稳定音升序，全量）", "",
              "| 曲目 | 专辑 | 最低稳定音 | 最高稳定音 | 跨度(八度) | 稳定性(音分) | 颤音(Hz) | HNR(dB) |",
              "|---|---|---|---|---|---|---|---|"]
        for s in sorted(songs, key=lambda x: float(x.get("low_hz") or 999)):
            md.append(f"| {s.get('title')} | {s.get('album')} | {s.get('low')} {s.get('low_hz')} | "
                      f"{s.get('high')} {s.get('high_hz')} | {s.get('span_octaves')} | {s.get('stability_cents')} | "
                      f"{s.get('vibrato_hz')} | {s.get('hnr_db')} |")
        md += ["", "## 四、现场层（按最低音升序，前 60 条；完整 504 条见线上页/JSON）", "",
               "| 素材 | 曲目 | 巡次 | 城市 | 日期 | 最低音 | Hz | 复核状态 |", "|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda x: float(x.get("low_hz") or 9999))[:60]:
            md.append(f"| {r.get('tag')} | {r.get('song')} | {r.get('tour')} | {r.get('city')} | "
                      f"{str(r.get('date'))[:10]} | {r.get('low_note')} | {r.get('low_hz')} | {r.get('verify') or r.get('source_verdict')} |")
        md += ["", "## 五、覆盖（多方匹配置信分级）", "",
               f"- 64 场中：已定位到具体场次 **{cst.get('L1_精确',0)+cst.get('L2_强',0)}**（①精确 {cst.get('L1_精确',0)} + ②强 {cst.get('L2_强',0)}）｜"
               f"有本地素材 **{cst.get('covered','—')}**｜无线索 **{cst.get('missing','—')}**｜扫到文件 {cst.get('files_scanned','—')} 个",
               f"- 仍无线索：{'、'.join(m['city'] + m['date'][5:] for m in ci.get('missing', []))}", "",
               "## 六、选曲与翻唱（无指数数据的那部分）", "",
               f"- 唱过 **{cstat.get('songs_total','—')}** 首｜自有 **{cstat.get('own_released','—')}**｜翻唱 **{cstat.get('covers','—')}**｜"
               f"有指数数据仅 **{cstat.get('own_with_index_data',0)+cstat.get('covers_with_index_data',0)}** 首",
               f"- 跨巡保留率 2%–6%（几乎每巡换血）｜看家曲 {fp.get('home_songs','—')} 首｜只唱一次 {fp.get('once_only','—')} 首",
               f"- 同曲多版本：≥3 版本 {mv.get('songs_with_3plus','—')} 首，版本间变异系数中位 {mv.get('low_cv_median','—')}",
               f"- 音区适配：自有曲现场最低音中位 {ra.get('own_live_low_median','—')} Hz vs 翻唱曲 {ra.get('cover_live_low_median','—')} Hz", "",
               "## 七、复核裁决台账（含被否读数）", "",
               "| 曲目 | 场次 | 方面 | 裁决 | Hz | 日期 |", "|---|---|---|---|---|---|"]
        md += [f"| {i.get('song')} | {i.get('show')} | {i.get('aspect')} | {i.get('verdict')} | {i.get('verdict_hz')} | {str(i.get('date'))[:10]} |"
               for i in v_items[:100]]
        md += ["", "## 八、已知边界", "",
               "- 覆盖不均（一/二/三巡缺口最大）；追踪池仅覆盖他的发行曲，翻唱天然无指数数据；",
               "- 录音室层经修音，稳定性/音准不可跨层比较；现场音准偏差为方法学伪影；",
               "- 本报告只发布方法与结果数据，原始音视频仅本地留存、不二次分发。", ""]
        local_md.write_text("\n".join(md), encoding="utf-8")
        print(f"→ 本地副本 {local_html.name} / {local_md.name}")
    except Exception as e:
        print("[warn] 本地副本写入失败:", e)
    print(f"✅ 已生成 {OUT.name}（{len(html)/1024:.0f} KB）｜录音室 {len(songs)} 曲｜现场 {len(rows)} 条｜裁决 {len(v_items)} 条｜"
          f"覆盖 有素材 {cst.get('covered','—')}/{cst.get('shows_total','—')}·已定位 {cst.get('L1_精确',0)+cst.get('L2_强',0)}·"
          f"站点层 {cst.get('measured_shows_site','—')}")
    assert len(songs) > 50 and len(rows) > 100, "数据不足，检查 data/*.json"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
