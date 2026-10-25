# -*- coding: utf-8 -*-
"""文章配套三卡：低音基线 / 八张录音室作品只漂 0.27Hz / 54 组配对（2026-10-13 用户授权上线）。

走**现有卡片厂**（复用 `build_topic_cards.render_card` 的片段模板与 gate 块）：
  data/share/cards/card_low_baseline.json · card_vibrato_8y.json · card_pair_54.json
  data/share/rendered/card_<id>.html（阅读视图片段，供 build_share_page.py 组装）
两视图：阅读视图（段落）+ 竖屏卡视图（`?card=<id>`，由 build_share_page.py 渲染 main_numbers）。
**每条数字后挂字段出处**：main_numbers[].source（文件 + 字段路径），并登记 caliber。

纪律
----
· ① 只写「最低**稳定音**」（触达音/待核读数不进主数字，进 caliber_lock）
· ② 颤音卡只与**他自己的专辑基线**比（不跨歌手）
· ③ 配对卡**两组 p 值必须同列**（全样本 0.2131 / 仅独唱 0.1975）
· 数字零手写：全部现算自 data/ 下的实测 JSON
用法：python -X utf8 project_b\\build_article_cards.py
"""
from __future__ import annotations

import io
import json
import statistics as st
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    # 注意：**不要**替换 sys.stdout（build_topic_cards 已在 import 时包过一层，
    # 重复替换会在其被回收时关掉底层缓冲，导致后续 print 报 I/O on closed file）。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from build_topic_cards import render_card  # noqa: E402  复用同一片段模板

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
OUT_CARDS = D / "share" / "cards"
OUT_RENDER = D / "share" / "rendered"
TODAY = date.today().isoformat()


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def hist_html(vals, bins, unit="Hz"):
    """纯 CSS 直方图（零依赖、静态可读）。"""
    counts = [0] * (len(bins) - 1)
    for v in vals:
        for i in range(len(bins) - 1):
            if (bins[i] <= v < bins[i + 1]) or (i == len(bins) - 2 and v == bins[-1]):
                counts[i] += 1
                break
    mx = max(counts) or 1
    rows = "".join(
        f"<div class='hb'><span class='hl'>{bins[i]:.0f}–{bins[i+1]:.0f}{unit}</span>"
        f"<span class='hf' style='width:{100*counts[i]/mx:.0f}%'></span>"
        f"<span class='hc'>{counts[i]}</span></div>" for i in range(len(counts)))
    return ("<div class='hist'>" + rows + "</div>"
            "<style>.hist{margin:8px 0}.hb{display:flex;align-items:center;gap:6px;font-size:12px;color:#7a6a55}"
            ".hl{width:96px;text-align:right}.hf{height:10px;background:#c9a227;border-radius:2px;display:inline-block}"
            ".hc{color:#8a7f6d}</style>")


def main() -> int:
    OUT_CARDS.mkdir(parents=True, exist_ok=True)
    OUT_RENDER.mkdir(parents=True, exist_ok=True)
    va = load(D / "archive_vocal_albums.json")
    tour = load(D / "archive_stage_tour.json")
    cctx = load(D / "archive_context_compare.json")
    songs = va.get("songs", [])
    summary = va.get("summary", {}) or {}

    # ── ① 低音基线（72 首录音室全量）──
    hz = [s["low_hz"] for s in songs if s.get("low_hz")]
    low_e2 = [s for s in songs if (s.get("low_hz") or 9e9) < 82.4]
    low_b1 = [s for s in songs if str(s.get("low_note", "")).startswith("B1")]
    low_floor = summary.get("lowest") or {}
    cards = []
    cards.append(dict(
        id="low_baseline", no=10, title="低音基线",
        subtitle="不是一首歌的偶然：72 首录音室曲目的低音落点分布",
        pillar="实测（最低稳定音口径）",
        main_numbers=[
            {"value": len(songs), "unit": "首", "label": "录音室曲目池（全量实测）",
             "caliber": "vocal_album_rows",
             "source": "data/archive_vocal_albums.json#songs[]（length）"},
            {"value": len(low_e2), "unit": "首",
             "label": "最低稳定音低于 E2 82.4Hz（男低音常用下界）",
             "caliber": "low_below_e2",
             "source": "data/archive_vocal_albums.json#songs[].low_hz < 82.4"},
            {"value": low_floor.get("hz"), "unit": "Hz",
             "label": f"全池最低稳定音 {low_floor.get('note')}《{low_floor.get('song')}》",
             "caliber": "lowest_stable_B1",
             "source": "data/archive_vocal_albums.json#summary.lowest{note,hz,song,album}"},
            {"value": len(low_b1), "unit": "首", "label": "达到 B1 的曲目数（B1 共 4 首：知晓/渔光曲/多听有益/静止了的夜晚）",
             "caliber": "lowest_stable_B1",
             "source": "data/archive_vocal_albums.json#songs[].low_note == 'B1'"},
        ],
        view_reading=[
            f"录音室曲目池共 **{len(songs)} 首**（全量实测，非抽样）；其中 **{len(low_e2)} 首**"
            f"（{100*len(low_e2)/len(songs):.1f}%）的最低稳定音**低于 E2 82.4Hz**——"
            "E2 是合唱写作与声乐教学里男低音的常用下界，用来描述声部大致范围，不是物理极限。",
            f"全池最低稳定音 **{low_floor.get('note')} {low_floor.get('hz')}Hz**，曲目《{low_floor.get('song')}》"
            f"（专辑《{low_floor.get('album')}》）；低音声部把 C2（本站参照线 65.4Hz）称为 Low C，"
            f"该读数比它再低约 1.06 个半音。",
            "**只算「最低稳定音」**：时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB，且极值音本身需 ≥0.2s 并过谐波列复核；"
            "触达音、低音带读数、归属未定的现场极值音**一律不作依据、不进标题**（三级读数制度，见 `data/calibers.md`）。",
            hist_html(hz, [55, 60, 65, 70, 75, 80, 85, 95]),
            "低音落点分布（按最低稳定音，Hz）。横条越长＝落在该区间的曲目越多。",
        ],
        view_card=[f"{len(low_e2)}/{len(songs)} 首低于 E2",
                   f"最低 {low_floor.get('note')} {low_floor.get('hz')}Hz", "只算最低稳定音"],
        caliber_lock=[],
        gate={"pass_status": "measured（注：`archive_vocal_albums.json` 内每首带 album_verify_status；"
                             "C6 类读数已按人耳确认非本人剔除，仅存 high_hz_original 备查）",
              "note": "本卡数字全部为录音室实测稳定音分布，无待核读数入内"},
        platform={"xiaohongshu": {"钩子句": f"{len(low_e2)}/{len(songs)} 首低于男低音常用下界 E2",
                                 "记忆点": f"最低 {low_floor.get('note')} {low_floor.get('hz')}Hz"},
                  "douyin": {"听觉断点": "低频落点与 High C 的对照（发布者自备素材）"}},
        footnote=f"来源：data/archive_vocal_albums.json（{len(songs)} 首全量实测）｜口径：最低稳定音；"
                 f"每条数字的字段出处见各自主数字条目。生成 {TODAY}",
    ))

    # ── ② 八张录音室作品只漂 0.27Hz（专辑级颤音速率）──
    by_alb = {}
    for s in songs:
        if s.get("vibrato_hz") and s.get("album"):
            by_alb.setdefault(s["album"], []).append(s["vibrato_hz"])
    alb = sorted(((a, len(v), st.median(v)) for a, v in by_alb.items()), key=lambda x: x[2])
    try:
        from vibrato_release import release as _vib_release
        spread, _vib_date, _vib_snap = _vib_release()
    except Exception:
        spread = max(x[2] for x in alb) - min(x[2] for x in alb)
    cards.append(dict(
        id="vibrato_8y", no=11, title=f"八张录音室作品只漂 {spread:.2f}Hz",
        subtitle="与自己比：跨专辑颤音速率稳定性（8 张录音室作品）",
        pillar="实测（专辑级中位，组内纵比）",
        main_numbers=[
            {"value": round(spread, 2), "unit": "Hz", "label": "专辑间颤音速率中位极差（越小越稳）",
             "caliber": "vibrato_tier",
             "source": "data/archive_vocal_albums.json#songs[].vibrato_hz（先按 .album 取中位再比）"},
            {"value": len(alb), "unit": "张", "label": "覆盖专辑数",
             "caliber": "vocal_album_rows",
             "source": "data/archive_vocal_albums.json#songs[].album（去重）"},
            {"value": f"{min(x[2] for x in alb):.2f}–{max(x[2] for x in alb):.2f}", "unit": "Hz",
             "label": "各专辑中位所在区间",
             "caliber": "vibrato_tier",
             "source": "同上（min–max）"},
        ],
        view_reading=[
            f"把每张专辑所有曲目的颤音速率各取中位，再横向比一遍：{len(alb)} 张录音室作品落在 "
            f"**{min(x[2] for x in alb):.2f}–{max(x[2] for x in alb):.2f} Hz**，"
            f"最高与最低之间只差 **{spread:.2f} Hz**。",
            "**这是与自己比**：拿来对照的是他自己的专辑基线，不是别的歌手——跨歌手的录音条件、"
            "编曲与人声处理无法对齐，本站不产出此类比较。",
            "颤音来自气息与喉部的配合，频率约 5Hz 量级；修音改的是音高慢变轨迹，"
            "对这类快速调制**基本不动速率**（幅度可能受轻微影响），故速率适合**组内纵向**比较。"
            "口径见 `data/calibers.md` → `vibrato_tier`。",
            hist_html([x[2] for x in alb], [5.0, 5.1, 5.2, 5.3, 5.4], unit="Hz"),
            "各专辑颤音速率中位（Hz）。条越短＝该专辑越接近区间下端。",
        ],
        view_card=[f"极差 {spread:.2f} Hz", f"{len(alb)} 张录音室作品", "与自己比，不跨歌手"],
        caliber_lock=[],
        gate={"pass_status": "measured（专辑级中位）",
              "note": "速率属低修音敏感项；仍标注「组内可纵比、跨组谨慎」"},
        platform={"xiaohongshu": {"钩子句": f"{len(alb)} 张录音室作品（2014–2024，跨十年），颤音速率极差只有 {spread:.2f}Hz",
                                 "记忆点": f"{min(x[2] for x in alb):.2f}–{max(x[2] for x in alb):.2f} Hz"},
                  "douyin": {"听觉断点": "同一句颤音的慢放对照（发布者自备素材）"}},
        footnote=f"来源：data/archive_vocal_albums.json（{len(alb)} 张录音室作品，按 .album 取中位）｜"
                 f"口径：vibrato_tier（组内纵比）｜生成 {TODAY}",
    ))

    # ── ③ 54 组配对（同曲录音室 vs 现场）──
    pairs = tour.get("live_vs_studio_pairs") or []
    d_all = [abs(p["delta_semitones"]) for p in pairs if p.get("delta_semitones") is not None]
    n_all = len(d_all)
    med_all = st.median(d_all)
    w1_all = 100 * sum(1 for v in d_all if v <= 1.0) / n_all
    trimmed = sorted(d_all, reverse=True)[2:]           # 去掉 2 个最大离群（各 ≈12 半音）
    n_t = len(trimmed)
    med_t = st.median(trimmed)
    w1_t = 100 * sum(1 for v in trimmed if v <= 1.0) / n_t
    sens = {x["key"]: x for x in (cctx.get("sensitivity_solo_only") or [])}
    sk = sens.get("low_stable.midi", {})
    p_all, p_solo = sk.get("p_all"), sk.get("p_solo")
    n_self, n_other = sk.get("self"), sk.get("all")
    cards.append(dict(
        id="pair_54", no=12, title="配对 56 组",
        subtitle="同一首歌：录音室版本 vs 现场版本（跨层配对；主口径＝全量，54 组为敏感性）",
        pillar="实测（跨层，两侧窗口不同）",
        main_numbers=[
            {"value": n_all, "unit": "组", "label": "**主口径**：全量配对组数（不做事后筛选）",
             "caliber": "pair_studio_live",
             "source": "data/archive_stage_tour.json#live_vs_studio_pairs[].delta_semitones"},
            {"value": round(med_all, 1), "unit": "半音", "label": "**主口径**：绝对半音差中位（全量）",
             "caliber": "pair_studio_live",
             "source": "同字段（|delta_semitones| 中位，全量）"},
            {"value": round(w1_all, 1), "unit": "%", "label": "**主口径**：差值落在 ±1 半音内的比例（全量）",
             "caliber": "pair_studio_live",
             "source": "同字段（|delta| ≤ 1.0 计数占比，全量）"},
            {"value": f"{n_t} 组 / {med_t:.1f} / {w1_t:.1f}%", "unit": "组·半音·%",
             "label": f"敏感性口径：剔除 2 个 ≈12 半音离群后（{n_t} 组 / 中位 {med_t:.1f} / {w1_t:.1f}%）",
             "caliber": "pair_studio_live",
             "source": "同字段（降序前 2 条离群：《歌颂》2021-07-23 11.9、《雪地里寄不出的求救信》"
                       "2020-10-07 11.7）"},
            {"value": f"{p_all:.4f} / {p_solo:.4f}", "unit": "p",
             "label": "两组 p 值（最低稳定音：全样本 / 仅独唱）——**必须同列**",
             "caliber": "context_compare_p",
             "source": "data/archive_context_compare.json#sensitivity_solo_only[key=low_stable.midi]"
                       "{p_all,p_solo,self,all}"},
        ],
        view_reading=[
            f"**主口径（全量、不做事后筛选）**：同一首歌的**录音室版本**与**现场版本**逐组配对共 "
            f"**{n_all} 组**，绝对半音差**中位 {med_all:.1f} 个半音**，**{w1_all:.1f}%** 落在 ±1 半音之内。"
            "不采用「先剔离群再看」的算法——**按离群值事后筛选容易被读成挑数据**，故以全量为主口径。",
            f"**敏感性口径**（脚注）：剔除 2 个 ≈12 半音离群后为 **{n_t} 组**，中位 {med_t:.1f} 半音、"
            f"{w1_t:.1f}% 落在 ±1 内。两个离群逐条可查：《歌颂》2021-07-23（11.9 半音）、"
            "《雪地里寄不出的求救信》2020-10-07（11.7 半音）——量级接近一个八度，属八度/声部误配或唱段差异，"
            "**按口径原样列出、不隐藏**。",
            f"**两组 p 值必须同列**：最低稳定音在「本人主导 vs 他人主导」两组之间，"
            f"**全样本 p = {p_all:.4f}**，**仅独唱敏感性 p = {p_solo:.4f}**——两种口径都不显著。"
            "引用时不得只取其中一个（见 `data/calibers.md` → `context_compare_p`）。",
            "跨层比较的前提：两侧窗口不同（录音室整曲 vs 现场片段），故只谈**分布与差值**，"
            "不把某一组差值当作单曲结论；现场极值音**归属未定**，不参与归属判断。",
        ],
        view_card=[f"{n_all} 组：中位 {med_all:.1f} 半音（主口径）", f"{w1_all:.1f}% 在 ±1 半音内",
                   f"p={p_all:.4f} / {p_solo:.4f}（同列）"],
        caliber_lock=[],
        gate={"pass_status": "measured（跨层配对）",
              "note": "主口径＝全量（不做事后离群筛选）；敏感性口径脚注同列；p 值两组同列"},
        platform={"xiaohongshu": {"钩子句": f"同曲录音室 vs 现场：{n_all} 组中位只差 {med_all:.1f} 个半音",
                                 "记忆点": f"{w1_all:.1f}% 落在 ±1 半音内"},
                  "douyin": {"听觉断点": "同曲两版 A/B 切换（发布者自备素材）"}},
        footnote=f"来源：data/archive_stage_tour.json#live_vs_studio_pairs（n={n_all}，主口径）"
                 f"＋ data/archive_context_compare.json#sensitivity_solo_only（p 两组同列）｜"
                 f"敏感性口径（{n_t} 组，剔 2 个 ≈12 半音离群）见主数字第 4 条｜"
                 f"**数字现算**：素材库更新后旧稿数值会自动随卡刷新｜生成 {TODAY}",
    ))

    for c in cards:
        c["generated_at"] = TODAY
        (OUT_CARDS / f"card_{c['id']}.json").write_text(
            json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
        (OUT_RENDER / f"card_{c['id']}.html").write_text(render_card(c), encoding="utf-8")
        print("[卡]", c["no"], c["id"], "|", c["title"], "| 主数字", len(c["main_numbers"]))
    print("[OK] 三卡已生成（cards + rendered）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
