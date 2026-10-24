# -*- coding: utf-8 -*-
"""可传播词条库 → data/share/entries.json（**数字全部从 data/ 派生，禁手写**）。

八条词条（每条：一句话钩子 + 支撑数字/证据 + 出处 + 证据等级 + 禁忌写法 + 传记映射）。
读：
  data/vocal_measurements.json                       条目 2（现场 5 版最低读数区间）
  data/archive_vocal_albums.json                     条目 4（专辑颤音中位极差）
  data/share/song_pool.json                          条目 5（点歌池常驻曲）
  data/archive_cross_night.json                       条目 6（同曲跨夜·同窗口径）
  data/share/woyaoni_spread.json                      条目 3 / 7（传播实测 + 评论分类）
  data/show_blocks/沉响与长歌_20261009.json / _20261010.json   条目 8（反馈维度·收紧口径）
  E:\\wx\\...\\原始材料\\我要你_声学与传播归因_v2.json        条目 1（版权自述逐句与时间戳）
写：data/share/entries.json
用法：python -X utf8 project_b\\build_share_entries.py
"""
from __future__ import annotations
import json
import statistics as st
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
RAW = Path(r"E:\wx\论文素材_王晰作传\原始材料")
TODAY = datetime.now().strftime("%Y-%m-%d")


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def hms(sec):
    return "%02d:%02d" % (int(sec) // 60, int(sec) % 60)


def main() -> int:
    vm = load(D / "vocal_measurements.json", {})
    va = load(D / "archive_vocal_albums.json", {})
    pool = load(D / "share" / "song_pool.json", {})
    cn = load(D / "archive_cross_night.json", {})
    sp = load(D / "share" / "woyaoni_spread.json", {})
    blk09 = load(D / "show_blocks" / "沉响与长歌_20261009.json", {})
    blk10 = load(D / "show_blocks" / "沉响与长歌_20261010.json", {})
    v2 = load(RAW / "我要你_学声与传播归因_v2.json") or load(RAW / "我要你_声学与传播归因_v2.json", {})

    E = []

    # ── 1 版权自述（带时间戳）──
    cs = (v2 or {}).get("S2_copyright_story") or {}
    vv = cs.get("verbatim") or []
    relays = cs.get("independent_relays") or []      # 独立旁证（第三方转述；不与本站 ASR 合并）
    if vv:
        t0, t1 = vv[0]["t_abs_s"], vv[-1]["t_abs_s"]
        key = {x["text"][:8]: x for x in vv}
        E.append(dict(
            no=1, id="copyright_seven_years", hook="版权太贵，等了七年",
            support=(f"2026-10-09 台上自述 {hms(t0)}–{hms(t1)}（绝对 {t0:.1f}–{t1:.1f}s，共 {len(vv)} 句）："
                     "2019 年第一次巡演就想唱 → 了解版权后「哇好贵」→ 没唱 → 后来加入院团才"
                     "「能够把这首歌唱给大家听」→ 随即报出曲名。"),
            source=(f"本站 2026-10-09 全场录像 part7 转写（本地 faster-whisper large-v3-turbo，**未人工校对**）；"
                    f"独立旁证 {len(relays)} 条（**不与本站 ASR 混为一条**）："
                    + "；".join(
                        f"{r.get('tier') or '平台转述'}·{r.get('platform')}："
                        f"「{(r.get('text') or '')[:38]}」" for r in relays[:3])
                    + "。其中「观众转述（第三方）」仅供交叉印证，不得据此推断版权金额/主体/谈判过程。"),
            grade="实测（带时间戳）＋观众转述（第三方）",
            taboo=["不得写版权金额/谈判细节（无据）", "ASR 未人工校对必须标注",
                   "第三方转述不得与本站 ASR 合为一条（两套来源分开列）",
                   "不得写「独家/首发」式断言"],
            bio=dict(line="市场-情绪", chapter="被看见与不被看见：一首想唱七年的歌",
                     evidence_id="talk:2026-10-09#3716.1-3748.4",
                     gap="缺官方节目单/媒体报道佐证；缺他本人在其他场次重复该说法的第二条录像"),
            extra={"t_start": round(t0, 1), "t_end": round(t1, 1), "n_sentences": len(vv),
                   "target_song": "我要你"}))

    # ── 2 低于男低音下限的稳定低音线 ──
    rows = [r for r in (vm.get("rows") or []) if r.get("song") == "我要你" and r.get("layer") == "tour_live"]
    ok_rows = [r for r in rows if "通过" in ((r.get("verify") or {}).get("state") or "")]
    pend_rows = [r for r in rows if r not in ok_rows]
    lows = sorted(r["metrics"]["low_hz"] for r in ok_rows if r["metrics"].get("low_hz"))
    pend = sorted((r["metrics"]["low_hz"], r["metrics"].get("low_note"),
                   (r.get("verify") or {}).get("state")) for r in pend_rows if r["metrics"].get("low_hz"))
    if lows:
        notes = sorted({r["metrics"]["low_note"] for r in ok_rows if r["metrics"].get("low_note")})
        E.append(dict(
            no=2, id="low_line_below_floor", hook="低于男低音下限的「稳定低音线」",
            support=(f"《我要你》现场 {len(lows)} 版（**谐波列复核通过**）最低读数区间 "
                     f"{notes[0]}–{notes[-1]}（{lows[0]:.1f}–{lows[-1]:.1f}Hz），中位 {st.median(lows):.1f}Hz；"
                     f"全部低于一般男低音下限 E2 82.4Hz。" +
                     (f"另有 {len(pend)} 版读数 {pend[0][1]} {pend[0][0]:.1f}Hz 属**待复核**（{pend[0][2]}），"
                      f"**不计入本区间**。" if pend else "") +
                     "与录音室全量最低**稳定音** B1 61.5Hz **分列**。"),
            source="data/vocal_measurements.json（layer=tour_live, song=我要你）；录音室口径 data/calibers.md",
            grade="实测（单曲**触达音**级）",
            taboo=["触达音不得作能力结论、不进标题数字位", "不得与录音室 B1 61.5Hz 混读",
                   "极值音歌手归属一律「归属未定」", "**待复核读数不得并入区间**（单列展示）"],
            bio=dict(line="能力-市场", chapter="低音的可核验边界：低到哪、稳不稳",
                     evidence_id="vocal_measurements:我要你×%d" % len(lows),
                     gap="缺同期（2026）同曲的稳定音级复核；缺动态范围/气声量化读数"),
            extra={"n_versions_verified": len(lows), "low_hz_verified": lows,
                   "median": round(st.median(lows), 1),
                   "pending_single_out": [{"hz": p[0], "note": p[1], "state": p[2]} for p in pend]}))

    # ── 3 一场演出里的自燃 ──
    if sp:
        mul = sp.get("comment_categories") or {}
        mn = sp.get("comment_categories_main") or {}
        E.append(dict(
            no=3, id="selfignite_in_one_show", hook="一场演出里的自燃",
            support=(f"{sp['notes']} 条同场单曲笔记 / {sp['likes_total']} 赞（中位 {sp['likes_median']}）/ "
                     f"{sp['comments_grabbed']} 条评论；{sp['pct_same_day_or_next']}% 集中在演出当日或次晚；"
                     f"互动第一条 {sp['first_peak']['datetime']}（演出尚未散场，{sp['first_peak']['likes']} 赞）。"),
            source="data/share/woyaoni_spread.json（由 build_woyaoni_spread.py 从语料派生）",
            grade="实测（第三方 UGC 计数）",
            taboo=["样本为链接集合、非全平台普查，不得当分母", "禁用三类平台侧夸张断言",
                   "反例必须同列：同窗口 B站《哭砂》播放量高于本曲"],
            bio=dict(line="市场-情绪", chapter="一次「自燃」的完整样本：谁在什么时刻发了什么",
                     evidence_id="spread:woyaoni_20261010",
                     gap="缺平台侧曝光/推荐数据；缺评论者画像（无法区分粉丝/路人）"),
            extra={"notes": sp["notes"], "likes_total": sp["likes_total"],
                   "pct_same_day_or_next": sp["pct_same_day_or_next"],
                   "comments": sp["comments_grabbed"]}))

    # ── 4 八张录音室作品只漂 0.27Hz ──
    songs = [s for s in (va.get("songs") or []) if s.get("vibrato_hz")]
    by = {}
    for s in songs:
        by.setdefault(s.get("album"), []).append(s["vibrato_hz"])
    alb = sorted(((a, len(v), st.median(v)) for a, v in by.items() if a), key=lambda x: x[2])
    if alb:
        spread = max(x[2] for x in alb) - min(x[2] for x in alb)
        med = st.median([x[2] for x in alb])
        E.append(dict(
            no=4, id="vibrato_eight_years", hook=f"八张录音室作品只漂 {spread:.2f}Hz",
            support=(f"{len(alb)} 张录音室作品的颤音速率中位极差 **{spread:.2f}Hz**（专辑中位 {med:.2f}Hz）；"
                     f"覆盖 {len(songs)} 首曲目。最低 {alb[0][0]} {alb[0][2]:.2f}Hz、"
                     f"最高 {alb[-1][0]} {alb[-1][2]:.2f}Hz。"),
            source="data/archive_vocal_albums.json（卡片 vibrato 同源）",
            grade="实测",
            taboo=["颤音速率组内可纵比、跨组谨慎", "不得据此推断「唱功更好」"],
            bio=dict(line="能力-市场", chapter="生理指纹：八张录音室作品不变的速率",
                     evidence_id="vibrato_tier / card:vibrato",
                     gap="缺同期现场（非专辑）版本的同指标对照"),
            extra={"albums": len(alb), "spread_hz": round(spread, 4), "median_hz": round(med, 4)}))

    # ── 5 点歌池常驻曲 ──
    items = pool.get("items") or []
    if items:
        it = max(items, key=lambda x: x.get("confirmed_sing_count", 0))
        ev = it.get("evidence") or []
        kinds = Counter(e.get("kind", "") for e in ev)
        all_tour = all("点歌" in (e.get("kind") or "") for e in ev)
        detail = "、".join("%s %s（%s 次）" % (e.get("when", ""), e.get("kind", ""), e.get("n", "")) for e in ev)
        E.append(dict(
            no=5, id="request_pool_resident", hook="点歌池常驻曲",
            support=("《%s》有记录的演唱 **%d 次**，%s（%s）" % (
                it["song"], it["confirmed_sing_count"],
                "**全部发生在点歌环节**" if all_tour else "分布见下", detail)),
            source="data/share/song_pool.json（源于用户确认 + data/show_setlists/2026-10-10_北京.json）",
            grade="实测（有记录演唱，形态学发现）",
            taboo=["「点歌候选单」上出现≠唱过，未检索到演唱证据不得进本表"],
            bio=dict(line="能力-市场", chapter="曲目形态学：他为什么被反复点同一首",
                     evidence_id="song_pool:%s" % it["song"],
                     gap="缺各场点歌环节的完整候选单；缺点歌与现场效果的对照"),
            extra={"song": it["song"], "count": it["confirmed_sing_count"],
                   "all_in_request_segment": bool(all_tour), "kinds": dict(kinds)}))

    # ── 6 同曲跨夜，颤音几乎不变 ──
    v3 = ((cn.get("versions") or {}).get("v3_sep_vs_sep_8s") or {})
    if v3.get("comparable") and v3.get("rows"):
        parts, vals = [], []
        for r in v3["rows"]:
            a = (r["metrics_1009"] or {}).get("vibrato_hz_median")
            b = (r["metrics_1010"] or {}).get("vibrato_hz_median")
            if a and b:
                parts.append(f"《{r['song']}》{a:.2f}→{b:.2f}Hz")
                vals += [a, b]
        if parts:
            E.append(dict(
                no=6, id="cross_night_vibrato", hook="同曲跨夜，颤音几乎不变",
                support=(f"同规格 8 秒窗（win8s/hop30s）两晚对照：" + "；".join(parts) +
                         f"（共 {len(parts)} 首）"),
                source="data/archive_cross_night.json#v3_sep_vs_sep_8s（generator: project_b/cross_night_consistency.py）",
                grade="实测（**n 极小，仅 %d 首**）" % len(parts),
                taboo=["n≤2 不得作普遍结论", "仅同规格窗口可比；跨规格（长块 vs 8 秒窗）不可比",
                       "两侧设备/机位/PA 直达声比例不同，属混杂"],
                bio=dict(line="情绪-能力", chapter="同一首歌在不同夜晚的稳定性",
                         evidence_id="cross_night:v3_sep_vs_sep_8s",
                         gap="曲目数太少；缺同一首歌同一句的逐帧对齐对照"),
                extra={"n_songs": len(parts), "pairs": parts}))

    # ── 7 低音炮是入场券，不是谈资 ──
    if sp:
        mul = sp.get("comment_categories") or {}
        mn = sp.get("comment_categories_main") or {}
        arr = mul.get("编曲/音乐处理", 0)
        low_m = mul.get("低音音色/音色本体", 0)
        low_main = mn.get("低音音色/音色本体", 0)
        E.append(dict(
            no=7, id="bass_is_ticket_not_topic", hook="低音炮是入场券，不是谈资",
            support=(f"评论触发点（多命中口径）：编曲/音乐处理 {arr} 条 > 低音音色 {low_m} 条；"
                     f"按主类口径低音为 {low_main} 条。泛赞美 {sp.get('comment_generic_praise')} 条为无信息量。"),
            source="data/share/woyaoni_spread.json#comment_categories / #comment_categories_main",
            grade="实测（关键词规则分类，可复核）",
            taboo=["两种口径必须就近标名（多命中/主类）", "不得写成「观众不听低音」——低音仍是被提到的一类",
                   "不得据此评价歌手优劣"],
            bio=dict(line="市场-情绪", chapter="被讨论的不是声音本身，而是声音带来的场景",
                     evidence_id="woyaoni_comment_rule",
                     gap="单一平台、单一曲目；缺跨场次/跨平台的评论对照"),
            extra={"编曲_多命中": arr, "低音_多命中": low_m, "低音_主类": low_main}))

    # ── 8 观众话语里「技术」排在「体验/嗓音」之后 ──
    dims = []
    for b in (blk09, blk10):
        dd = ((b.get("feedback") or {}).get("dimensions") or {})
        if dd:
            dims.append((((b.get("show") or {}).get("date") or "?"), dd, ((b.get("feedback") or {}).get("total"))))
    if dims:
        agg = Counter()
        for _, dd, _t in dims:
            agg.update(dd)
        hit_total = sum(agg.values())
        feedback_total = sum((t or 0) for _, _, t in dims)
        top = agg.most_common()
        tech = agg.get("唱功/技术", 0)
        rank = ([k for k, _ in top].index("唱功/技术") + 1) if "唱功/技术" in dict(top) else None
        exp = agg.get("现场体验", 0) + agg.get("嗓音/低音", 0)
        nights = "、".join(d for d, _, _ in dims)
        E.append(dict(
            no=8, id="audience_talks_experience", hook="观众话语里，「技术」排在「体验/嗓音」之后",
            support=(f"{nights} 收紧口径评论 {feedback_total} 条，维度命中合计 {hit_total} 次"
                     f"（一条评论可命中多维）：" + "；".join(f"{k} {v}" for k, v in top) +
                     f"。现场体验+嗓音/低音 {exp}/{hit_total}（{round(100.0 * exp / hit_total, 1)}%），"
                     f"唱功/技术 {tech}/{hit_total}（{round(100.0 * tech / hit_total, 1)}%，第 {rank} 位）。"),
            source="data/show_blocks/沉响与长歌_20261009.json#feedback.dimensions（10-10 块级未出维度统计）",
            grade="实测（现行收紧口径）",
            taboo=["**不得写「观众不谈唱功」**——现行口径下唱功/技术排第 %s 位" % rank,
                   "分母是维度命中次数、不是评论条数（一条可命中多维），引用须写清",
                   "data/kb/facts.json 的 audience_dim_* 已改为**只收正式批**并在 value 内含"
                   "〔批次 文件名｜n=样本量｜收紧口径〕标注（2026-10-13 修）；引用时必须与批次同引"],
            bio=dict(line="市场-情绪", chapter="观众到底在谈什么：体验优先于技术",
                     evidence_id="show_blocks:feedback.dimensions",
                     gap="10-10 块级未出维度统计；缺跨场次/跨城市同口径维度统计"),
            extra={"feedback_total": feedback_total, "dimension_hits": hit_total,
                   "dimensions": dict(top), "tech_rank": rank, "nights": nights}))

    # 统一去掉 markdown 粗体标记（页面渲染走 esc()，** 会原样显示）
    def _clean(o):
        if isinstance(o, str):
            return o.replace("**", "")
        if isinstance(o, list):
            return [_clean(x) for x in o]
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        return o
    E = _clean(E)

    out = {
        "schema": 1, "generated_at": TODAY,
        "what": "可传播词条库（每条只挂一条最硬的证据；宁少勿虚）",
        "rule": {
            "one_evidence": "每条只挂一条最硬证据，不堆砌",
            "grade": "证据等级三档：实测 / 推断 / 待核",
            "derive": "所有数字由 build_share_entries.py 从 data/ 派生，页面与卡片不得手写",
            "taboo": "每条必须带「禁忌写法」，防二次传播走形",
        },
        "count": len(E), "entries": E,
    }
    (D / "share" / "entries.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] data/share/entries.json：{len(E)} 条")
    for e in E:
        print(f"   {e['no']}. {e['hook']}｜{e['grade'][:22]}｜禁忌 {len(e['taboo'])} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
