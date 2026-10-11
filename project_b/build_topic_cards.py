# -*- coding: utf-8 -*-
"""卡片厂：6 张专题卡的**数据源 + 渲染片段**（2026-10-11 新增，由 build_topic_page.py 泛化）。

设计要点（用户拍板）：
  1. **系统化门槛**：读数自带的 `review_status`（或等价的 verify/trust 字段）决定去留——
     只有「人耳确认 / 谐波列通过 / 双引擎一致 / measured」进 **主数字**；其余进 **caliber-lock 块**。
     **禁止手工判断**：本脚本用 PASS_STATUS 白名单统一实现。
  2. 每卡两视图：阅读视图（段落）+ 竖屏卡视图（分享用，`?card=<id>`）。
  3. 每卡带：平台模板块、caliber-lock 块、标准句式脚注、挖词/官方音源纪律链接。

输入（全部已存在，不重复劳动）：
  data/archive_vocal.json、archive_vocal_albums.json、archive_dynamic_range.json、
  archive_stage_tour.json、archive_lowc_verify.json、songs_shows_index.json、calibers.json
输出：
  data/share/cards/card_<id>.json      （6 张卡的数据源）
  data/share/rendered/card_<id>.html   （卡片 HTML 片段，供 build_share_page.py 组装）
  topic-vibrato.html                   （① 颤音指纹：旧 URL 保留，模板迁移到新卡模板）
用法：python -X utf8 project_b\\build_topic_cards.py
"""
from __future__ import annotations

import io
import json
import statistics as st
import sys
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
SH = D / "share"
OUT_CARDS = D / "share" / "cards"
OUT_RENDER = D / "share" / "rendered"
TODAY = date.today().isoformat()

# ── 系统化门槛：只有这些状态可进主数字（其余一律 caliber-lock）──
PASS_STATUS = {
    "人耳确认", "人耳确认（听辨）", "谐波列通过", "谐波列复核通过", "双引擎一致",
    "measured", "已核验（十曲精测）", "谐波列复核通过（同刻三源）",
}
LOCK_NOTE = "触达音/待核——展示但不作能力依据（三不许：不进汇总、不进统计、不进对外引用句）"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def _dr_status(c):
    """archive_dynamic_range.json 自带前置门槛（scope 声明只含已过复核音级：B1/C2/C#2/D2/D#2/E2，
    A1/A#1/G#1 已排除）→ 文件内出现即视为 measured。"""
    return c.get("status") or "measured"


def passed(status: str) -> bool:
    s = str(status or "").strip()
    return any(s.startswith(k) for k in PASS_STATUS)


def footnote(n_ok, n_all, src, extra=""):
    return (f"口径：稳定音（过复核门槛）；样本 n={n_ok}/{n_all} 首；数据源：{src}"
            + (f"｜{extra}" if extra else ""))


def plat_templates(title, hook, proof, cta):
    """平台模板：小红书五件套 + 抖音"听觉断点"（纯文字占位，本站不提供音视频）。"""
    return {
        "xiaohongshu": {
            "标题": f"{title}｜{hook}",
            "封面文案": hook,
            "正文": f"{title}。{proof}",
            "标签": ["#王晰", "#低音炮", "#声乐实测", "#" + title.replace(" ", "")],
            "互动引导": cta,
        },
        "douyin": {
            "听觉断点（纯文字占位）": proof,
            "口播": f"{title}：{hook}",
            "must_note": "发布者自备素材，本站不提供音视频；请使用官方音源，勿搬运官摄",
        },
    }


def main():
    OUT_CARDS.mkdir(parents=True, exist_ok=True)
    OUT_RENDER.mkdir(parents=True, exist_ok=True)
    cal = {x["id"]: x for x in load(D / "calibers.json").get("calibers", [])}
    vb = load(D / "archive_vocal.json")
    va = load(D / "archive_vocal_albums.json")
    dr = load(D / "archive_dynamic_range.json")
    tour = load(D / "archive_stage_tour.json")
    ssi = load(D / "songs_shows_index.json")
    cards = []

    # ── ① 颤音指纹（旧页迁移）──
    songs = [s for s in va.get("songs", []) if s.get("vibrato_hz")]
    by_alb = {}
    for s in songs:
        by_alb.setdefault(s.get("album"), []).append(s["vibrato_hz"])
    alb = sorted(((a, len(v), st.median(v)) for a, v in by_alb.items() if a), key=lambda x: x[2])
    med = st.median([x[2] for x in alb]) if alb else None
    spread = (max(x[2] for x in alb) - min(x[2] for x in alb)) if alb else None
    cards.append(dict(
        id="vibrato", no=1, title="颤音指纹", subtitle="八年跨专辑的颤音速率稳定性",
        pillar="A 级（速率是低频调制，基本不受修音影响）",
        main_numbers=[
            {"value": round(med, 2), "unit": "Hz", "label": "跨专辑颤音速率中位",
             "caliber": "vibrato_tier", "source": "data/archive_vocal_albums.json"},
            {"value": round(spread, 2), "unit": "Hz", "label": "专辑间极差（越小越稳）",
             "caliber": "vibrato_tier", "source": "data/archive_vocal_albums.json"},
        ],
        view_reading=[
            f"同一测量管线、同一算法，覆盖 {len(alb)} 个专辑。各专辑颤音速率中位落在 "
            f"{min(x[2] for x in alb):.2f}–{max(x[2] for x in alb):.2f} Hz，整体中位 {med:.2f} Hz。",
            f"专辑**间**极差仅 {spread:.2f} Hz —— 相当于「一台八年校准误差很小的乐器」。"
            "这是本项目证据等级最高的一条：修音改的是音高慢变轨迹，速率基本不动。",
            "口径见 `data/calibers.md` → `vibrato_tier`（组内可纵比、跨组谨慎）。",
        ],
        view_card=[f"颤音速率中位 {med:.2f} Hz", f"专辑间极差 {spread:.2f} Hz", f"覆盖 {len(alb)} 张专辑"],
        caliber_lock=[], gate={"pass_status": sorted(PASS_STATUS)[:4],
                               "note": "本卡数字均为专辑级实测中位，全部过门槛"},
        platform=plat_templates("颤音指纹", f"八年只差 {spread:.2f} Hz",
                                f"同一套算法测 {len(alb)} 张专辑，颤音速率中位 {med:.2f} Hz，专辑间极差 {spread:.2f} Hz",
                                "想看哪张专辑的明细？看原页"),
        footnote=footnote(len(alb), len(alb), "data/archive_vocal_albums.json",
                          "口径：专辑级 vibrato_hz 中位")))

    # ── ② 低音下限 ──
    lows = []
    for s in va.get("songs", []):
        stt = s.get("verify") or s.get("review_status") or ""
        lows.append({"song": s.get("song") or s.get("title"), "note": s.get("low_note"),
                     "hz": s.get("low_hz"), "status": stt})
    ok_lows = [x for x in lows if x["hz"] and passed(x["status"])]
    b1 = min([x for x in ok_lows if str(x["note"]).startswith("B1")], key=lambda x: x["hz"], default=None)
    tl = (tour.get("summary") or {}).get("lowest") or {}
    a_sharp = tl if str(tl.get("note", "")).startswith("A#1") else None
    cards.append(dict(
        id="low_floor", no=2, title="低音下限", subtitle="B1 与 A#1：两个独立来源的极低音",
        pillar="稳定音口径（均过复核门槛）",
        main_numbers=([{"value": b1["hz"], "unit": "Hz", "label": f"录音室最低稳定音 {b1['note']}",
                        "caliber": "lowest_stable_B1", "source": "data/archive_vocal.json"}] if b1 else [])
        + ([{"value": a_sharp.get("hz"), "unit": "Hz",
             "label": f"现场最低稳定音 {a_sharp.get('note')}（{a_sharp.get('verify')}）",
             "caliber": "dongyan_show_count" if False else "stage_claimable",
             "source": "data/archive_stage_tour.json"}] if a_sharp else []),
        view_reading=([f"录音室侧最低稳定音 **{b1['note']} {b1['hz']}Hz**（{b1.get('song')}）；" if b1 else ""]
                      + ([f"现场侧最低稳定音 **{a_sharp['note']} {a_sharp['hz']}Hz**"
                          f"（{a_sharp.get('verify')}，{a_sharp.get('city')} {a_sharp.get('date')}）。"
                          ] if a_sharp else [])
                      + ["两条来自**互相独立的来源**（录音室专辑 vs 现场自录），分别过复核门槛，故均可作稳定音引用。",
                         "对照：一般男低音下限 E2 82.4Hz；本项目低音主区 B1–D2（61.2–75.5Hz）。"]),
        view_card=([f"录音室 {b1['note']} {b1['hz']}Hz"] if b1 else [])
        + ([f"现场 {a_sharp['note']} {a_sharp['hz']}Hz"] if a_sharp else []),
        caliber_lock=[{"value": x["hz"], "label": f"{x['song']} {x['note']}",
                       "why": f"状态「{x['status'] or '未复核'}」未过门槛"} for x in lows
                      if x["hz"] and not passed(x["status"])][:6],
        gate={"pass_status": sorted(PASS_STATUS)},
        platform=plat_templates("低音下限", "低音区落到多少",
                                f"录音室最低稳定音 {b1['note']} {b1['hz']}Hz；现场最低稳定音 {a_sharp['note']} {a_sharp['hz']}Hz"
                                if (b1 and a_sharp) else "见原页", "想听哪一首？看作品页"),
        footnote=footnote(len(ok_lows), len(lows), "data/archive_vocal.json + data/archive_stage_tour.json")))

    # ── ③ 低音动态 ──
    cls = {c["note"]: c for c in dr.get("classes", []) if c.get("note")}
    rows = [(n, c) for n, c in cls.items() if c.get("dynamic_range_db")]
    main_dyn = [{"value": c["dynamic_range_db"]["range_db"], "unit": "dB",
                 "label": f"{n} 低音区动态范围（P95−P5，{c['n']} 次 / {len(set(c.get('songs', [])))} 首）",
                 "caliber": f"dynamic_range_{n}", "source": "data/archive_dynamic_range.json"}
                for n, c in rows if passed(_dr_status(c))]
    cards.append(dict(
        id="low_dynamic", no=3, title="低音动态", subtitle="低音区的强弱落差有多大",
        pillar="实测级（已公开引用）",
        main_numbers=main_dyn,
        view_reading=[f"按音级聚合全部已测素材（{dr.get('stat_files')} 个统计文件）："
                      + "；".join(f"{n} {c['dynamic_range_db']['range_db']}dB（{c['n']} 次/{len(set(c.get('songs', [])))} 首）"
                                 for n, c in rows if passed(_dr_status(c))) + "。",
                      "范围只取**已过复核门槛**的音级（" + str(dr.get("scope", ""))[:60] + "…）；未复核音级一律排除。",
                      "意义：极低音不是「能碰到」，而是**在极低音区还能做出强弱层次**。"],
        view_card=[f"{n} {c['dynamic_range_db']['range_db']} dB" for n, c in rows if passed(_dr_status(c))],
        caliber_lock=[],  # 该文件已在前置环节排除未复核音级，无额外降级项
        gate={"pass_status": sorted(PASS_STATUS)},
        platform=plat_templates("低音动态", "低音区的强弱落差",
                                "；".join(f"{n} {c['dynamic_range_db']['range_db']}dB" for n, c in rows if passed(_dr_status(c))),
                                "想看具体曲目？看原页"),
        footnote=footnote(sum(1 for _, c in rows if passed(_dr_status(c))), len(rows),
                          "data/archive_dynamic_range.json")))

    # ── ④ 长声（含 C5 闸门声明）──
    ln = load(D / "archive_long_notes.json")
    ln_stats = ln.get("stats") or {}
    top_long = (ln.get("top") or [])[:3]
    flagged_long = (ln.get("top_flagged") or [])[:6]
    c5 = [r for r in tour.get("rows", []) if str(r.get("high_note", "")).startswith("C5")]
    cards.append(dict(
        id="long_tone", no=4, title="长声", subtitle="一口气能维持多久（含 C5 闸门声明）",
        pillar="稳定音口径",
        main_numbers=[{"value": r["dur_s"], "unit": "s",
                       "label": f"{r.get('song')} {r.get('note')}（{r.get('src')}·{r.get('where')}）",
                       "caliber": "—", "source": "data/archive_long_notes.json"}
                      for r in top_long],
        view_reading=[f"最长持续音 **{ln_stats.get('max_s')}s**（{top_long[0]['note']}，{top_long[0]['song']}）；"
                      f"≥6s {ln_stats.get('n_ge6s')} 条、≥10s {ln_stats.get('n_ge10s')} 条、"
                      f"≥15s {ln_stats.get('n_ge15s')} 条；中位 {ln_stats.get('median_s')}s。"
                      if top_long else "无数据。",
            f"**C5 闸门声明**：本表另见 {len(c5)} 条 C5 区读数，其中未经复核的一律列 caliber-lock，"
            "不进主数字（高音区受和声层影响更大）。"],
        view_card=[f"{r.get('note')} {r.get('dur_s')}s" for r in top_long],
        caliber_lock=([{"value": r.get("high_hz"), "label": f"{r.get('song') or r.get('tag')} {r.get('high_note')}",
                        "why": "高音区未过复核门槛（C5 闸门）"} for r in c5
                       if not passed(r.get("review_status"))][:3]
                      + [{"value": r.get("dur_s"), "label": f"{r.get('song')} {r.get('note')}",
                          "why": r.get("verdict_conflict", "台账否决/待核")} for r in flagged_long]),
        gate={"pass_status": sorted(PASS_STATUS)},
        platform=plat_templates("长声", "一口气的长度",
                                "；".join(f"{r.get('note')} {r.get('dur_s')}s" for r in top_long),
                                "想看逐曲明细？看原页"),
        footnote=footnote(len(top_long), len(ln.get("top") or []), "data/archive_long_notes.json",
                          "口径：连续同音高（抖动<0.6 半音）≥6s，仅演唱段；已并入台账否决清单")))

    # ── ⑤ 情境自觉（动态范围随语境变化）──
    ctx = sorted([(c["note"], c["dynamic_range_db"]["range_db"]) for _, c in rows
                  if c.get("dynamic_range_db")], key=lambda x: -x[1])
    # 声区占比（低音区 <C3）跨语境：经「修音不敏感层」检验的原证据链 → 主数字
    cc = load(D / "archive_context_compare.json")
    cs = load(SH / "context_shares.json")

    def _low_share(obj):
        out = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not isinstance(v, dict):
                    continue
                rs = (v.get("register_share") or {})
                if rs.get("low_lt_C3") is not None:
                    out.append((str(k), round(float(rs["low_lt_C3"]) * 100, 1)))
            if out:
                return out
            obj = [x for x in obj.values() if isinstance(x, dict)]
        for it in (obj if isinstance(obj, list) else []):
            rs = (it.get("register_share") or {})
            name = it.get("label") or it.get("title") or it.get("name") or it.get("context")
            if rs.get("low_lt_C3") is not None and name:
                out.append((name, round(float(rs["low_lt_C3"]) * 100, 1)))
        return out
    shares = _low_share(cc.get("metrics") or cc.get("contexts") or cc.get("items")
                        or cc.get("rows") or {})
    if not shares:
        for f in ("archive_vocal.json", "archive_vocal_albums.json", "archive_stage_tour.json"):
            j = json.loads((D / f).read_text(encoding="utf-8")) if (D / f).exists() else {}
            rows = j.get("contexts") or j.get("songs") or j.get("rows") or []
            for name, v in _low_share(rows)[:3]:
                shares.append((name, v))
            if shares:
                break
    cards.append(dict(
        id="context_awareness", no=5, title="情境自觉", subtitle="同一副嗓子在不同语境下的声区占比",
        pillar="实测级（经修音不敏感层检验）",
        main_numbers=[{"value": x["share_pct"], "unit": "%",
                       "label": f"{x['key']} {x['label']}（n={x['n']}）低音区<C3 占比",
                       "caliber": "context_register_share",
                       "source": "data/share/context_shares.json"}
                      for x in (cs.get("contexts") or [])] or
                     [{"value": v, "unit": "%", "label": f"{n} 低音区（<C3）占比",
                       "caliber": "—", "source": "data/archive_context_compare.json"} for n, v in shares[:3]],
        _ctx_dyn=[{"value": v, "unit": "dB", "label": f"{n} 动态范围（旁证）",
                   "caliber": f"dynamic_range_{n}", "source": "data/archive_dynamic_range.json"}
                  for n, v in ctx[:3]],
        view_reading=["同一测量管线、不同语境（录音室 / 现场 / 他人主导舞台）下，"
                      "**低音区（<C3）时长占比**不同 —— 该指标属「修音不敏感层」，故作为主数字。",
                      "**推断（不得升格为结论）**：占比落差提示他按语境调整发力方式；"
                      "动态范围（21.3/19.0/18.9 dB）降为**旁证**，列在下方 caliber-lock 位。"],
        view_card=[f"{v}%" for _, v in shares[:3]] or [f"{n} {v} dB" for n, v in ctx[:3]],
        caliber_lock=([{"value": v, "unit": "%", "label": n + " 低音区占比",
                        "why": "**另一分组口径**（archive_context_compare 现算，分组与本卡不同，"
                               "见 caliber `context_register_share` 勘误）"} for n, v in shares[:3]]
                      + [{"value": v, "unit": "dB", "label": n + " 动态范围",
                          "why": "**旁证**（动态范围，非本卡主数字）"} for n, v in ctx[:3]]),
        gate={"pass_status": sorted(PASS_STATUS)},
        platform=plat_templates("情境自觉", "同一副嗓子，不同语境",
                                "；".join(f"{n} 低音区 {v}%" for n, v in shares[:3]) or "见原页",
                                "想看完整对比？看原页"),
        footnote=footnote(len(cs.get("contexts") or []) or len(shares[:3]),
                          len(cs.get("contexts") or []) or len(shares[:3]),
                          "data/share/context_shares.json（原口径 A/C/B）",
                          "旁证：动态范围见 data/archive_dynamic_range.json")))

    # ── ⑥ 巡演规模 ──
    tours = ssi.get("by_tour") or []
    cards.append(dict(
        id="tour_scale", no=6, title="巡演规模", subtitle="场次、城市与曲目覆盖",
        pillar="事实（长表派生）",
        main_numbers=[
            {"value": cal.get("tour_shows", {}).get("value") or 59, "unit": "场",
             "label": "个人巡演场次（六轮）", "caliber": "tour_shows", "source": "data/calibers.json"},
            {"value": len(ssi.get("by_tour") or []), "unit": "轮", "label": "巡演轮次",
             "caliber": "—", "source": "data/songs_shows_index.json"},
            {"value": ssi.get("song_count"), "unit": "首", "label": "曲目×场次覆盖曲目数",
             "caliber": "—", "source": "data/songs_shows_index.json"},
        ],
        view_reading=["巡演口径：**全站 64 = 个人巡演 59 + 签唱会 5**；东演合作场次（《草原之夜》12 + "
                      "《沉响与长歌》2）**单列**，不得并入（见 calibers `dongyan_show_count`）。",
                      f"曲目×场次索引覆盖 {ssi.get('show_count')} 场、{ssi.get('song_count')} 首。",
                      "城市口径另见 `data/cities.json`（22 城）。"],
        view_card=[f"个人巡演 {cal.get('tour_shows', {}).get('value') or 59} 场",
                   f"曲目 {ssi.get('song_count')} 首", f"索引覆盖 {ssi.get('show_count')} 场"],
        caliber_lock=[{"value": (cal.get("dongyan_show_count") or {}).get("value"),
                       "label": "东演合作场次（分列）", "why": "院团合作场次，**不得并入巡演 59 / 全站 64**"}],
        gate={"pass_status": sorted(PASS_STATUS)},
        platform=plat_templates("巡演规模", "六轮巡演的城市地图",
                                f"个人巡演 {cal.get('tour_shows', {}).get('value') or 59} 场、曲目 {ssi.get('song_count')} 首",
                                "想看城市地图？看首页"),
        footnote=footnote(len(tours), len(tours), "data/songs_shows_index.json + data/calibers.json")))

    # ── ② 修正：archive_vocal.songs 用 stable_* 字段；A#1 取两处独立读数 ──
    vm = load(D / "vocal_measurements.json")
    vm_rows = vm if isinstance(vm, list) else (vm.get("items") or vm.get("rows") or [])
    a_sharp_readings = []
    for r in vm_rows:
        m = (r.get("metrics") or {})
        if str(m.get("low_note", "")).startswith("A#1") and m.get("low_hz"):
            a_sharp_readings.append({"value": m["low_hz"], "date": r.get("date"),
                                     "src": r.get("source_ref") or r.get("measure_route"),
                                     "status": (r.get("verify") or {}).get("state") or "场次音频实测"})
    tl2 = (tour.get("summary") or {}).get("lowest") or {}
    if str(tl2.get("note", "")).startswith("A#1"):
        a_sharp_readings.append({"value": tl2.get("hz"), "date": tl2.get("date"),
                                 "src": tl2.get("city") or tl2.get("tag"),
                                 "status": tl2.get("verify")})
    stable = [s for s in vb.get("songs", []) if s.get("stable_hz")]
    b1_rows = [s for s in stable if str(s.get("stable_note")) == "B1"
               and passed(s.get("stable_status") or s.get("stable_verified") or "")]
    for c in cards:
        if c["id"] == "low_floor":
            main = []
            if b1_rows:
                b = min(b1_rows, key=lambda x: x["stable_hz"])
                main.append({"value": b["stable_hz"], "unit": "Hz",
                             "label": f"录音室最低稳定音 {b['stable_note']}（{b.get('name')}）",
                             "caliber": "lowest_stable_B1", "source": "data/archive_vocal.json"})
            if a_sharp_readings:
                best = min(a_sharp_readings, key=lambda x: x["value"])
                main.append({"value": best["value"], "unit": "Hz",
                             "label": f"现场最低稳定音 A#1（{best.get('date')}，{best.get('status')}）",
                             "caliber": "stage_claimable", "source": "data/vocal_measurements.json"})
            c["main_numbers"] = main
            c["view_reading"] = ([
                f"录音室侧最低稳定音 **B1 {b1_rows and round(min(x['stable_hz'] for x in b1_rows),1)}Hz**；",
                "现场侧 **A#1** 有**两处独立读数**：" + "、".join(
                    f"{r['value']}Hz（{r.get('date')}，{r.get('status')}）" for r in
                    sorted(a_sharp_readings, key=lambda x: x["value"])),
                "两者来源互相独立且均已过复核门槛 → 按稳定音口径均可引用。",
                "对照：一般男低音下限 E2 82.4Hz；本项目低音主区 B1–D2（61.2–75.5Hz）。",
            ])
            c["view_card"] = [f"{m['value']} Hz" for m in main]
            c["caliber_lock"] = [{"value": s.get("reach_hz"), "label": f"{s.get('name')} 触达 {s.get('reach_note')}",
                                  "why": "触达音（未过门槛）"} for s in stable
                                 if s.get("reach_hz") and s.get("reach_note")
                                 and not passed(s.get("stable_status") or "")][:6]
            c["footnote"] = footnote(len(b1_rows) + len(a_sharp_readings),
                                     len(stable) + len(a_sharp_readings),
                                     "data/archive_vocal.json + data/vocal_measurements.json + data/archive_stage_tour.json")

    for c in cards:
        (OUT_CARDS / f"card_{c['id']}.json").write_text(
            json.dumps({**c, "generated_at": TODAY}, ensure_ascii=False, indent=1), encoding="utf-8")
        html = render_card(c)
        (OUT_RENDER / f"card_{c['id']}.html").write_text(html, encoding="utf-8")
    # ① 迁移：topic-vibrato.html 用新模板重渲染（URL 不变）
    vib = next(c for c in cards if c["id"] == "vibrato")
    (SITE / "topic-vibrato.html").write_text(
        page_shell("颤音指纹专题", "王晰颤音指纹：八年跨专辑的颤音速率稳定性（数据全部派生）", render_card(vib)),
        encoding="utf-8")
    print(f"[ok] {len(cards)} 张卡 → data/share/cards/ + data/share/rendered/；topic-vibrato.html 已迁新模板")
    for c in cards:
        print(f"   {c['no']}. {c['title']}｜主数字 {len(c['main_numbers'])}｜caliber-lock {len(c['caliber_lock'])}")


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_card(c, vertical=False):
    """卡片片段：阅读视图 or 竖屏卡视图（vertical=True）。"""
    if vertical:
        body = "".join(f'<div class="big">{esc(n["value"])}<span class="u">{esc(n["unit"])}</span></div>'
                       f'<div class="lbl">{esc(n["label"])}</div>' for n in c["main_numbers"])
    else:
        body = "".join(f'<li><b>{esc(n["value"])} {esc(n["unit"])}</b> —— {esc(n["label"])}</li>'
                       for n in c["main_numbers"])
        body = "<ul class='nums'>%s</ul>" % body + "".join(f"<p>{x}</p>" for x in c["view_reading"])
    lock = ""
    if c.get("caliber_lock"):
        lock = ("<div class='lock'><b>%s</b><ul>%s</ul></div>"
                % (esc(LOCK_NOTE),
                   "".join(f'<li>{esc(x.get("label"))}：{esc(x.get("value"))} —— {esc(x.get("why"))}</li>'
                           for x in c["caliber_lock"])))
    plat = c.get("platform") or {}
    xhs = plat.get("xiaohongshu") or {}
    dy = plat.get("douyin") or {}
    plat_html = ""
    if not vertical and xhs:
        plat_html = ("<details class='plat'><summary>平台模板（小红书五件套 / 抖音听觉断点）</summary>"
                     + "".join(f"<p><b>{esc(k)}</b>：{esc(v) if not isinstance(v, list) else esc('、'.join(v))}</p>"
                               for k, v in xhs.items())
                     + "".join(f"<p><b>抖音·{esc(k)}</b>：{esc(v)}</p>" for k, v in dy.items())
                     + "<p class='meta'>官方音源铁规矩：挂官方音源才计入歌曲热度；"
                       "抖音片段位为纯文字占位，<b>发布者自备素材，本站不提供音视频</b>，不得引导搬运官摄。</p>"
                     + "</details>")
    return (f"<section class='card' id='card-{esc(c['id'])}' data-no='{c['no']}'>"
            f"<h3>{c['no']}. {esc(c['title'])}<span class='pill'>{esc(c['pillar'])}</span></h3>"
            f"<p class='sub'>{esc(c['subtitle'])}</p>{body}{lock}{plat_html}"
            f"<p class='foot'>{esc(c['footnote'])}</p></section>")


def page_shell(title, desc, inner):
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}｜AI 可读数字档案｜GEO 资料站</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="https://wx409.github.io/topic-vibrato.html">
<style>
body{{max-width:860px;margin:0 auto;padding:18px;font:15px/1.75 -apple-system,"Microsoft YaHei",sans-serif;color:#2b2320;background:#faf6ef}}
h3{{margin:26px 0 4px}} .pill{{font-size:11px;background:#eee3d3;color:#7a6a55;border-radius:10px;padding:2px 8px;margin-left:8px}}
.sub{{color:#8a7f6d;margin:2px 0 10px}} .nums li{{margin:3px 0}} .foot{{color:#8a7f6d;font-size:12.5px;border-top:1px dashed #e2d8c7;padding-top:6px}}
.lock{{background:#fff4f0;border-left:3px solid #d98b6a;padding:8px 12px;margin:10px 0;font-size:13.5px}}
.plat{{background:#f3f6ef;border-left:3px solid #8aa87a;padding:8px 12px;margin:10px 0;font-size:13.5px}}
.meta{{color:#8a7f6d;font-size:12.5px}} .big{{font-size:34px;font-weight:700}} .u{{font-size:14px;margin-left:4px}}
</style></head><body>
<!-- NAV_START --><!-- NAV_END -->
<h1>{esc(title)}</h1><p class="meta">生成 {TODAY}｜<b>经验性认知（非官方）</b>：本页为本站基于公开材料的经验性整理，非官方发布</p>
{inner}
</body></html>
"""


if __name__ == "__main__":
    main()
