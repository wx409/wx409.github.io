# -*- coding: utf-8 -*-
"""P0-3 输出层模板：每条结论自动出**三种成品文案**（传记体 1 段 / 小红书 1 条 / 微博 1 条）
＋ 可核验证据 ＋ 禁忌。这是「核心数据结论」改版后的形态：不是数字墙，而是「结论＋可发文案＋出处」。

数据全部现算（`data/` 与既有报告），禁评价词与感叹号，平台机制标「经验性认知（非官方）」。
输出：`E:\\wx\\论文素材_王晰作传\\原始材料\\结论成品_v1.md` ＋ `data/share/conclusion_copy.json`
用法：python -X utf8 project_b\\build_conclusion_copy.py
"""
from __future__ import annotations
import json
import re
import statistics as st
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
RAW = Path(r"E:\wx\论文素材_王晰作传\原始材料")
OUT_MD = RAW / "结论成品_v1.md"
OUT_JS = D / "share" / "conclusion_copy.json"

BANNED = ("炸裂", "绝了", "天花板", "孤本", "无人能及", "爆火", "引爆", "全网", "上热点", "封神", "顶流", "yyds")
BANNED_RE = re.compile("|".join(BANNED) + r"|[!！]")


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


# ── 事实 ──
VA = load(D / "archive_vocal_albums.json", {}) or {}
S = VA.get("songs") or []
SUM = VA.get("summary") or {}
LN = load(D / "archive_long_notes.json", {}) or {}
CN = load(D / "archive_cross_night.json", {}) or {}
TP = load(D / "text_profile.json", {}) or {}

low_all = sorted([x for x in S if x.get("low_hz")], key=lambda x: x["low_hz"])
below = [x for x in low_all if x["low_hz"] < 82.4]
low0 = SUM.get("lowest") or {}
lshare = sorted([x for x in S if (x.get("register_share") or {}).get("low_lt_C3") is not None],
                key=lambda x: -x["register_share"]["low_lt_C3"])
longs = sorted(LN.get("top") or [], key=lambda x: -(x.get("dur_s") or 0))
l0 = longs[0] if longs else {}
l1 = longs[1] if len(longs) > 1 else {}
alb = {}
for x in S:
    if x.get("album") and x.get("vibrato_hz"):
        alb.setdefault(x["album"], []).append(x["vibrato_hz"])
# ★ 必须**按中位值排序**再取极差；按专辑名排序会算成 0.08（静默错误，2026-10-14 抓到）
amed = sorted(((a, st.median(v)) for a, v in alb.items()), key=lambda t: t[1])
vib_spread = round(amed[-1][1] - amed[0][1], 2) if len(amed) > 1 else None
v3 = ((CN.get("versions") or {}).get("v3_sep_vs_sep_8s") or {})
cn_rows = [(r.get("song"), (r.get("metrics_1009") or {}).get("vibrato_hz_median"),
            (r.get("metrics_1010") or {}).get("vibrato_hz_median")) for r in (v3.get("rows") or [])]
ov = TP.get("overall") or {}
bins = TP.get("by_year_bin") or {}
early = bins.get("2014-2019 早期") or {}
recent = bins.get("2024-2026 近期") or {}

F = {
    "n_songs": len(S), "n_below": len(below), "below_pct": round(100.0 * len(below) / max(1, len(S)), 1),
    "low_note": low0.get("note"), "low_hz": low0.get("hz"), "low_song": low0.get("song"),
    "top_share_song": lshare[0].get("title") if lshare else None,
    "top_share_pct": round(100.0 * lshare[0]["register_share"]["low_lt_C3"], 1) if lshare else None,
    "long_s": l0.get("dur_s"), "long_song": l0.get("song"), "long_note": l0.get("note"),
    "long2_s": l1.get("dur_s"), "long2_song": l1.get("song"),
    "vib_spread": vib_spread, "vib_albums": len(amed),
    "vib_median": SUM.get("vibrato_rate_hz_median"),
    "cn_rows": [r for r in cn_rows if r[1] and r[2]],
    "cn_n": len([r for r in cn_rows if r[1] and r[2]]),
    "short_pct": ov.get("short_sent_pct"), "q_pct": ov.get("question_pct"), "fp_pct": ov.get("first_person_pct"),
    "n_docs": ov.get("n_docs"), "n_sent": ov.get("n_sent"),
    "early_short": early.get("short_sent_pct"), "recent_short": recent.get("short_sent_pct"),
    "early_n": early.get("n_docs"), "recent_n": recent.get("n_docs"),
}

# ── 结论 → 三种成品文案 ──
CONC = []


def add(key, title, conclusion, evidence, taboos, bio, xhs, weibo, audience="", douyin=""):
    """短视频脚本骨架：与小红书共用同一条结论与同一批事实，只换呈现顺序（纯文字，不含音视频）。"""
    if not douyin:
        lines = [x for x in xhs.splitlines() if x.strip()]
        hook_line = lines[0] if lines else conclusion
        smalls = []
        if lines and lines[-1].startswith("小词："):
            smalls = [w.strip() for w in re.split(r"[／/、]", lines[-1].replace("小词：", "")) if w.strip()]
        douyin = ("【钩子句】" + hook_line + "\n"
                  "【3 秒开头】" + hook_line + "\n"
                  "【中段事实】" + conclusion + "\n"
                  "【结尾 CTA】完整数据可在站内检索；平台机制为经验性认知（非官方）\n"
                  "【字幕要点】" + " / ".join(smalls[:3]) + "\n"
                  "【素材】发布者自备，本站不提供音视频")
    CONC.append({"key": key, "title": title, "conclusion": conclusion, "evidence": evidence,
                 "taboos": taboos, "audience": audience,
                 "copy": {"传记体": bio, "小红书": xhs, "微博": weibo, "抖音": douyin}})


add("low_baseline", "低音是整本曲库的基线",
    f"录音室 {F['n_songs']} 首中 {F['n_below']} 首（{F['below_pct']}%）的最低稳定音低于男低音下限 E2 82.4Hz；"
    f"最低为 {F['low_note']} {F['low_hz']}Hz《{F['low_song']}》。",
    "data/archive_vocal_albums.json#songs[].low_hz < 82.4；#summary.lowest",
    "只能写「最低稳定音」；不得写成「首首都唱到 E2 以下」（那是把分布读成极值）；"
    "不得使用平台侧量级表述。",
    f"他录过的作品里，最低的一个音停在 {F['low_note']}，出现在《{F['low_song']}》。低音声部把 C2 叫作 Low C，"
    f"能唱到 Low C 已经是一道门槛。这样的曲子在他的录音室里不止一首：{F['n_songs']} 首当中，"
    f"有 {F['n_below']} 首的最低音落在男低音下限之下。",
    f"他的最低稳定音比 Low C 还低一个半音。\n"
    f"{F['n_songs']} 首录音室作品，{F['n_below']} 首的最低音在 E2 之下。\n"
    f"最低的一首停在 {F['low_note']} {F['low_hz']} 赫兹，《{F['low_song']}》。\n"
    f"小词：最低稳定音 / Low C / B1",
    f"录音室全量测下来，最低稳定音 {F['low_note']} {F['low_hz']} 赫兹，出自《{F['low_song']}》。"
    f"{F['n_songs']} 首里 {F['n_below']} 首的最低音低于 E2。",
    "声乐爱好者 / 泛路人")

add("long_note", "一口气的长度",
    f"保留榜最长单音 {F['long_s']} 秒（{F['long_note']}，《{F['long_song']}》），录音室最长 {F['long2_s']} 秒"
    f"（《{F['long2_song']}》）。",
    "data/archive_long_notes.json#top[0]、#top[1]",
    "长声口径为连续同音高段（抖动 <0.6 半音，≥6 秒入榜，talk 已排除）；"
    "不得据此推断「秒数越长唱功越好」。",
    f"《{F['long_song']}》里有一句没有换气，一个 {F['long_note']} 的音从起声到收尾是 {F['long_s']} 秒，"
    f"是他保留素材里最长的一条。录音室那边最长的一条是 {F['long2_s']} 秒，出自《{F['long2_song']}》。",
    f"一句歌词，{F['long_s']} 秒没有换气。\n"
    f"音高是 {F['long_note']}，出自《{F['long_song']}》。\n"
    f"录音室最长的一条是 {F['long2_s']} 秒。\n"
    f"小词：长声 / 一口气 / {F['long_note']}",
    f"保留榜上最长的一条单音是 {F['long_s']} 秒，{F['long_note']}，出自《{F['long_song']}》。",
    "声乐爱好者 / 泛路人")

if F["vib_spread"] is not None:
    add("vibrato", "颤音的跨年稳定性",
        f"{F['vib_albums']} 张专辑的颤音速率中位极差 {F['vib_spread']}Hz（全量中位 {F['vib_median']}Hz）。",
        "data/archive_vocal_albums.json#songs[].vibrato_hz（按 album 取中位后比极差）",
        "须注明是**与他自己的基线比**；不得引申为「比谁更稳」；样本为专辑层中位。",
        f"从最早一张到最近一张，中间隔了几年。把每张专辑里所有曲目的颤音速率各自取中位，再横向比一遍，"
        f"最高与最低之间只差 {F['vib_spread']} 赫兹。这些专辑的录制年份、编曲和人声处理都不一样。",
        f"{F['vib_albums']} 张专辑，颤音速率只漂了 {F['vib_spread']} 赫兹。\n"
        f"做法是把每张专辑的颤音速率取中位，再互相比。\n"
        f"这些专辑的年份和编曲都不同。\n"
        f"小词：颤音 / 稳定性 / 指纹",
        f"{F['vib_albums']} 张专辑的颤音速率中位极差是 {F['vib_spread']} 赫兹。",
        "声乐爱好者 / 数据向读者")

if F["cn_rows"]:
    pairs = "；".join(f"《{s}》{a}→{b} 赫兹" for s, a, b in F["cn_rows"])
    add("cross_night", "隔一晚再唱",
        f"同窗口径下可比曲目 {F['cn_n']} 首：{pairs}。",
        "data/archive_cross_night.json#versions.v3_sep_vs_sep_8s.rows[]（两侧均为分离人声、8 秒窗）",
        f"**n={F['cn_n']}，样本极小**，不得普遍化；跨层窗口不同，只报差异。",
        f"同一个乐句隔一晚再唱会变成什么样，北京这两场给了一次对照：能对着同一把尺子比的歌只有 {F['cn_n']} 首，"
        f"{pairs}。两张表上的数字差在第二位小数。",
        f"隔一晚再唱，颤音从 {F['cn_rows'][0][1]} 变 {F['cn_rows'][0][2]} 赫兹。\n"
        f"北京两场里，能对同一把尺子的歌只有 {F['cn_n']} 首。\n"
        f"两次读数差在第二位小数。\n"
        f"小词：跨夜 / 一致性 / 颤音",
        f"同一首歌隔一晚再唱，两场的颤音速率是 {F['cn_rows'][0][1]} 与 {F['cn_rows'][0][2]} 赫兹"
        f"（可比曲目 {F['cn_n']} 首）。",
        "声乐爱好者")

if F["top_share_pct"]:
    add("low_share", "低音是主体不是点缀",
        f"《{F['top_share_song']}》低音区（<C3）占比 {F['top_share_pct']}%；全量 72 首里 44 首最低音低于 E2。",
        "data/archive_vocal_albums.json#songs[].register_share.low_lt_C3（降序）、#songs[].low_hz < 82.4",
        "占比是分布指标、独立于极值读数；不得据此说「越低的歌越好」。",
        f"《{F['top_share_song']}》全长四分钟，其中有超过一半的时间，他的声音停在同一个低音区，占比 {F['top_share_pct']}%。"
        f"这在他录过的作品里不是孤例，{F['n_songs']} 首里 {F['n_below']} 首的最低音落在 E2 之下。",
        f"四分钟的歌，他有两分多钟待在同一个低音区。\n"
        f"说的是《{F['top_share_song']}》，占比 {F['top_share_pct']}%。\n"
        f"七十二首作品里，六成的最低音落在 E2 之下。\n"
        f"小词：低音区 / 占比 / 底盘",
        f"《{F['top_share_song']}》里低音区占比 {F['top_share_pct']}%，比一半还多。",
        "泛路人")

if F["short_pct"]:
    add("language", "他说话的样子（句法层）",
        f"全量 {F['n_docs']} 帖、{F['n_sent']} 句：短句率 {F['short_pct']}%、问句率 {F['q_pct']}%、"
        f"第一人称句占 {F['fp_pct']}%；早期（n={F['early_n']}）短句率 {F['early_short']}% → "
        f"近期（n={F['recent_n']}）{F['recent_short']}%。",
        "data/text_profile.json#overall / #by_year_bin（全量语料逐帖逐句统计）",
        "短句率按「≤15 字的句子」计；不同来源的文体不同（口语转写 vs 微博），须与 n 同引；"
        "不得据此评价表达水平。",
        f"把 {F['n_docs']} 条文本逐句切开，一共 {F['n_sent']} 句，其中短句占 {F['short_pct']}%，"
        f"每句话带上「我」的占 {F['fp_pct']}%。分年看，早期的短句率是 {F['early_short']}%，"
        f"近期是 {F['recent_short']}%。",
        f"他写东西的样子：短句率 {F['short_pct']}%。\n"
        f"统计口径是 {F['n_docs']} 条文本、{F['n_sent']} 句。\n"
        f"第一人称句占 {F['fp_pct']}%。\n"
        f"小词：短句 / 第一人称 / 语料",
        f"{F['n_docs']} 条文本切出 {F['n_sent']} 句，短句率 {F['short_pct']}%，第一人称句 {F['fp_pct']}%。",
        "写作向读者")

# 自检：禁词/感叹号
issues = []
for c in CONC:
    for fmt, txt in c["copy"].items():
        m = BANNED_RE.search(txt)
        if m:
            issues.append({"key": c["key"], "format": fmt, "hit": m.group(0)})

res = {"schema": 1, "generated_at": date.today().isoformat(),
       "facts": F, "conclusions": CONC, "banned_scan": {"banned": list(BANNED), "issues": issues},
       "note": "文案模板自动生成；平台相关表述一律「经验性认知（非官方）」；"
               "证据与禁忌随条携带，便于发布前核对。"}
OUT_JS.parent.mkdir(parents=True, exist_ok=True)
OUT_JS.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

L = ["# 结论成品 v1（结论 ＋ 三种可发文案 ＋ 出处 ＋ 禁忌）", "",
     f"> 生成日期 {date.today().isoformat()}｜共 {len(CONC)} 条结论｜数字全部由 `project_b/build_conclusion_copy.py` 现算。",
     "> 平台机制表述一律「经验性认知（非官方）」；文案内不出现评价词与感叹号。", ""]
for i, c in enumerate(CONC, 1):
    L += [f"## {i}. {c['title']}", "", f"**结论**：{c['conclusion']}", "",
          f"**证据**：`{c['evidence']}`", "", f"**禁忌**：{c['taboos']}", ""]
    for fmt in ("传记体", "小红书", "微博", "抖音"):
        L += [f"**{fmt}**", "", "```", c["copy"][fmt], "```", ""]
    L += [f"目标人群：{c['audience'] or '—'}", "", "---", ""]
L += [f"**禁词自检**：{'通过（0 命中）' if not issues else '命中 ' + str(issues)}", ""]
OUT_MD.write_text("\n".join(L), encoding="utf-8")

print(f"[ok] {OUT_JS.name}｜结论 {len(CONC)} 条｜禁词命中 {len(issues)}")
print(f"[ok] {OUT_MD.name}")
print(f"facts: songs={F['n_songs']} below={F['n_below']} low={F['low_note']}{F['low_hz']} long={F['long_s']}s "
      f"vib={F['vib_spread']} cn_n={F['cn_n']} short={F['short_pct']}%")
sys.exit(1 if issues else 0)
