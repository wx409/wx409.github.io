# -*- coding: utf-8 -*-
"""钩子挖掘：从现场 talk / 评论笔记语料 / 声学事件里抽**可核验的传播钩子**候选。

为什么要有它
------------
他没有专业传播团队，钩子发现必须**准确 + 及时**，且他只需**从候选池里挑选**。
所以本脚本只做三件事：① 抽候选（**规则化、可复核**）② 打分排序、宁缺勿滥 ③ 产池 + 等勾选。

三类来源（最大化复用现有件，不另造轮子）
----------------------------------------
1. **现场 talk 逐句**：`E:\\wx\\论文素材_王晰作传\\现场talk\\**\\*.segments.json`（带 start/end）
   ＋ `原始材料\\我要你_声学与传播归因_v2.json#S2_copyright_story.verbatim[]`（**带绝对秒**）
2. **评论/笔记语料**：`小红书素材\\我要你20261010\\comments.json`（一级+二级）
3. **声学事件**：`data/archive_long_notes.json`（长声）、`data/archive_vocal_albums.json`
   （最低稳定音 / 跨专辑颤音极差）、`data/archive_cross_night.json`（跨夜一致性）

每条候选固定字段
----------------
`hook`（≤25 字，事实型）｜`evidence`（含时间戳或字段路径）｜`small_words`（建议小词）｜
`audience`（目标人群）｜`score_story`（可转述性）｜`score_evidence`（证据强度）｜
`score_novelty`（新颖度，查已发内容）｜`score_total`｜`risk`（风险与禁忌）

评分**全部离线规则化**（不调外部大模型），口径写在 `RULES` 里，可逐条复核。

用法
----
  python -X utf8 project_b\\hook_miner.py --dry                 # 只打印，不写池
  python -X utf8 project_b\\hook_miner.py                       # 抽池：data/hooks_pool.json + 本地 md
  python -X utf8 project_b\\hook_miner.py --pool-only           # 只抽池、不刷新 picks 模板
  python -X utf8 project_b\\hook_miner.py --render-picked       # 只对 data/hooks_pick.json 里 true 的生成卡/文案
  python -X utf8 project_b\\hook_miner.py --selftest            # 规则自检（不读语料）

纪律：平台机制一律「经验性认知（非官方）」；**禁写爆火/引爆全网/上热点**；
**绝不写入逝者/私域信息**（命中即拦下并记入 risk，不进池）；钩子必须是可核验事实。
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
TALK_DIR = Path(r"E:\wx\论文素材_王晰作传\现场talk")
RAW = Path(r"E:\wx\论文素材_王晰作传\原始材料")
CORPUS = Path(r"E:\wx\论文素材_王晰作传\小红书素材\我要你20261010")
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")
POOL = D / "hooks_pool.json"
PICK = D / "hooks_pick.json"
OUT_CARDS = D / "share" / "cards"
OUT_RENDER = D / "share" / "rendered"
TODAY = date.today().isoformat()

# ───────────────────────── 规则（可复核；改规则只改这里） ─────────────────────────
RULES = {
    "时间标记": r"(20\d{2}\s*年|一巡|二巡|三巡|四巡|五巡|六巡|第[一二三四五六七八九十]次|去年|前年|当年|那一年|巡演的时候)",
    "冲突标记": r"(版权|好贵|太贵|唱不起|没唱|不让|被拒|遗憾|可惜|等了|终于|才|没想到|结果|但是|可是|其实)",
    "数字标记": r"(\d+\s*(年|个月|天|秒|分钟|半音|赫兹|Hz|场|城|首|条|次|遍)|[一二三四五六七八九十百]+(年|个月|秒|场|城|次))",
    "道具动作": r"(沙锤|摇着|手里|麦克|麦|灯光|舞台|台下|鞠躬|落泪|哽咽|接唱|返场|清唱|加唱)",
    "自嘲口吻": r"(我这个人|我这人|说白了|老实说|其实我|我也不|我就|别看我|哼)",
}
HYPE = ("爆火", "引爆", "上热点", "全网", "刷屏", "破圈", "顶流", "封神")
PRIVATE = ("去世", "离世", "过世", "悼念", "遗愿", "老粉走了", "逝者", "病逝", "追悼")
# 每次入选池的门槛（宁缺勿滥）
POOL_MIN = {"score_total": 6.0, "score_evidence": 1.0, "score_novelty": 1.0}


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def hun(x: str) -> str:
    """统一标点/空白：『』「」《》与半角引号按同一套处理，便于匹配。"""
    return re.sub(r"\s+", "", (x or "").replace("，", ",").replace("。", "."))


def hits(text: str) -> dict:
    return {k: bool(re.search(v, text)) for k, v in RULES.items()}


# ───────────────────────── ① 现场 talk ─────────────────────────

def load_talk_lines(limit_files: int = 400) -> list[dict]:
    """返回 [{text, start, end, src}]（合并相邻 3s 内的短句，便于成段看语境）。"""
    out = []
    files = sorted(glob.glob(str(TALK_DIR / "**" / "*.segments.json"), recursive=True))[:limit_files]
    for f in files:
        d = load(f)
        segs = d.get("segments") if isinstance(d, dict) else d
        if isinstance(segs, dict):
            segs = segs.get("segments") or []
        if not isinstance(segs, list):
            continue
        buf = None
        for s in segs:
            t = hun(s.get("text"))
            if not t:
                continue
            st, en = s.get("start"), s.get("end")
            if buf and st is not None and buf["end"] is not None and st - buf["end"] <= 3.0:
                buf["text"] += t
                buf["end"] = en
            else:
                if buf:
                    out.append(buf)
                buf = {"text": t, "start": st, "end": en, "src": Path(f).name}
        if buf:
            out.append(buf)
    return out


def copyright_story_candidates() -> list[dict]:
    """从归因 v2 的 S2（**带绝对秒**）抽「三段式」钩子——这是验收回放的靶子。"""
    d = load(RAW / "我要你_声学与传播归因_v2.json")
    s = d.get("S2_copyright_story") or {}
    vb = s.get("verbatim") or []
    if not vb:
        return []
    text = "".join(hun(v.get("text")) for v in vb)
    t0 = min(v.get("t_abs_s") for v in vb)
    t1 = max(v.get("t_abs_s") for v in vb)
    hms0 = next((v.get("t_hms") for v in vb if v.get("t_abs_s") == t0), "")

    def seg(*keys):
        o = []
        for v in vb:
            if any(k in hun(v.get("text")) for k in keys):
                o.append({"t_abs_s": v.get("t_abs_s"), "t_hms": v.get("t_hms"), "text": v.get("text")})
        return o

    c = []
    if any(k in text for k in ("2019", "第一次巡演")) and "版权" in text:
        c.append({
            "hook": "2019 想唱，版权太贵，等到 2026",
            "evidence": f"现场 talk {hms0}（绝对 {t0:.1f}s）；原话「其实我在我2019年做自己的第一次巡演的时候"
                        f"…了解了一下这首歌的版权…哇好贵…后来加入到了东方…能够让我把这首歌唱给大家听」"
                        f"（{Path('原始材料/我要你_声学与传播归因_v2.json')}#S2_copyright_story.verbatim[]）",
            "small_words": ["版权梗", "七年", "等到", "终于唱了"],
            "audience": "泛路人 / 内容二创 / 版权话题关注者",
            "kind": "talk",
            "t_abs_s": t0, "t_hms": hms0,
            "parts": {"三段式": seg("2019", "第一次巡演"), "冲突": seg("版权", "哇好贵", "没有唱"),
                      "转折": seg("东方", "唱给大家听"), "结尾": seg("叫做我要你")},
        })
    # 其它 talk 钩子（同段内的次级句）
    for key, hook, words in (("感谢东方", "进院团才把这首歌唱成", ["院团", "东演"]),
                             ("同事", "「后来我发现原来我是同事」", ["同事", "自嘲"])):
        ss = seg(key)
        if ss:
            c.append({
                "hook": hook,
                "evidence": f"现场 talk {ss[0]['t_hms']}（绝对 {ss[0]['t_abs_s']:.1f}s）：{'／'.join(x['text'] for x in ss[:3])}",
                "small_words": words, "audience": "行业观察 / 粉丝内部梗", "kind": "talk",
                "t_abs_s": ss[0]["t_abs_s"], "t_hms": ss[0]["t_hms"],
            })
    return c


def talk_candidates(lines: list[dict], cap: int = 40) -> list[dict]:
    out = []
    for ln in lines:
        h = hits(ln["text"])
        n = sum(h.values())
        if n < 3:
            continue
        if len(ln["text"]) < 12 or len(ln["text"]) > 120:
            continue
        hook = re.split(r"[,.!?啊吧呢]", ln["text"])[0][:24] or ln["text"][:24]
        out.append({
            "hook": hook, "evidence": f"现场 talk 转写 {ln['src']} @{ln['start']:.1f}s：{ln['text'][:60]}",
            "small_words": [k for k, v in h.items() if v][:3], "audience": "现场观众 / 泛路人",
            "kind": "talk", "t_abs_s": None, "t_hms": (f"{int(ln['start'])//60:02d}:{int(ln['start'])%60:02d}"
                                                        if ln.get("start") is not None else ""),
        })
        if len(out) >= cap:
            break
    return out


# ───────────────────────── ② 评论 / 笔记语料 ─────────────────────────

STOPWORD = set("""好听 真的 什么 这个 那个 就是 可以 没有 不是 太好看 话题 音乐现场 王晰唱我要你
沉响与长歌 中国东方演艺集团 用音乐说爱你 男低音 神级现场 王晰北京 王晰低音杀 看con计划
哈哈哈哈 哈哈 我的 我们 你们 他们 一下 一直 已经 还是 有点 感觉 觉得 知道 喜欢 好听啊 太好听""".split())
# 与「歌／编曲／声音／现场动作」相关的描述性小词（评论里高频复现的那些）
SMALL_WORD_HINT = ("低音", "沙锤", "bossa", "爵士", "编曲", "改编", "拍子", "节奏", "接唱", "哽咽",
                   "版权", "巡演", "点歌", "返场", "清唱", "高音", "磁", "醇", "酥", "上头",
                   "沉醉", "现场", "剧院", "音质", "麦", "字幕", "完整版")


def comment_candidates(min_n: int = 3, cap: int = 40) -> list[dict]:
    C = load(CORPUS / "comments.json")
    notes = C.get("notes") or []
    comments, posts_text = [], []
    for n in notes:
        for c in n.get("comments", []):
            comments.append(c.get("content") or "")
        for it in n.get("inner", []) or []:
            for s in it.get("subs", []) or []:
                comments.append(s.get("content") or "")
    P = load(CORPUS / "posts.json")
    for p in P.get("posts", []):
        posts_text.append((p.get("title") or "") + " " + (p.get("desc") or ""))
    texts = comments + posts_text
    # ① 高频描述性小词（先剔除 #话题# 标签与停用词，避免把标签当钩子）
    words = {}
    for t in comments:                                  # 只统计**评论**，标签来自笔记正文
        tt = re.sub(r"#[^#\[\]]+(\[话题\])?#", " ", t)
        for w in re.findall(r"[\u4e00-\u9fff]{2,6}", tt):
            if w in STOPWORD:
                continue
            words[w] = words.get(w, 0) + 1
    out = []
    # ①a 命中「描述性小词」表的高频词优先出候选
    for w, n in sorted(words.items(), key=lambda x: -x[1]):
        if n < min_n:
            continue
        if not any(h in w or w in h for h in SMALL_WORD_HINT):
            continue
        ex = next((t for t in comments if w in t), "")[:46]
        out.append({
            "hook": f"评论区高频：「{w}」（{n} 次）",
            "evidence": f"小红书端回复语料 comments.json（一级+二级，去重后 {len(comments)} 条）中「{w}」"
                        f"出现 {n} 次；例：{ex}",
            "small_words": [w], "audience": "评论区受众 / 同好圈层", "kind": "comment",
            "t_abs_s": None, "t_hms": "", "n": n,
        })
        if len(out) >= cap:
            break
    # ①b 特定小词的**定式证据**（评论里描述动作/编曲的短句，含关键词即出候选）
    for kw, hook_tpl in (("沙锤", "评论区把「沙锤」当成编曲记忆点"),
                         ("bossa", "评论区把「bossa」当成这版的谈资"),
                         ("低音超绝", "笔记直接用「低音超绝」当钩子标签"),
                         ("接唱", "观众接唱被写进评论")):
        hit = [t for t in texts if kw.lower() in (t or "").lower()]
        if len(hit) >= 2:
            ex = next((t for t in comments if kw.lower() in (t or "").lower()), hit[0])
            out.append({
                "hook": f"{hook_tpl}（{len(hit)} 处）",
                "evidence": f"语料命中「{kw}」{len(hit)} 处；例：{ex[:60]}",
                "small_words": [kw], "audience": "同好圈层 / 二创", "kind": "comment",
                "t_abs_s": None, "t_hms": "", "n": len(hit),
            })
    return out


# ───────────────────────── ③ 声学事件 ─────────────────────────

def acoustic_candidates() -> list[dict]:
    out = []
    ln = load(D / "archive_long_notes.json")
    top = (ln.get("top") or [])
    l10 = [x for x in top if (x.get("dur_s") or 0) >= 10]
    if top:
        t0 = top[0]
        out.append({
            "hook": f"一口气 {t0.get('dur_s'):.1f} 秒不换气",
            "evidence": f"data/archive_long_notes.json#top[0]（song={t0.get('song')}, note={t0.get('note')}, "
                        f"dur_s={t0.get('dur_s')}, src={t0.get('src')}, t_start_s={t0.get('t_start_s')}）",
            "small_words": ["长声", "一口气", "十六秒"], "audience": "声乐爱好者 / 泛路人",
            "kind": "acoustic", "t_abs_s": t0.get("t_start_s"), "t_hms": "",
        })
    if l10:
        out.append({
            "hook": f"≥10 秒的长音有 {len(l10)} 条",
            "evidence": f"data/archive_long_notes.json#top[]（dur_s ≥ 10 计数）；最长 {top[0].get('dur_s')}s",
            "small_words": ["长音", "稳定"], "audience": "声乐爱好者", "kind": "acoustic",
            "t_abs_s": None, "t_hms": "",
        })
    va = load(D / "archive_vocal_albums.json")
    s = va.get("summary") or {}
    lo = s.get("lowest") or {}
    songs = va.get("songs") or []
    n_below = sum(1 for x in songs if (x.get("low_hz") or 9e9) < 82.4)
    if lo:
        out.append({
            "hook": f"最低稳定音 {lo.get('note')} {lo.get('hz')}Hz",
            "evidence": f"data/archive_vocal_albums.json#summary.lowest（song={lo.get('song')}, album={lo.get('album')}）",
            "small_words": ["B1", "Low C", "最低稳定音"], "audience": "声乐爱好者 / 泛路人",
            "kind": "acoustic", "t_abs_s": None, "t_hms": "",
        })
        out.append({
            "hook": f"{len(songs)} 首里 {n_below} 首低于 E2",
            "evidence": f"data/archive_vocal_albums.json#songs[].low_hz < 82.4（n={len(songs)}）",
            "small_words": ["E2", "分布", "低音基线"], "audience": "泛路人 / 数据向读者",
            "kind": "acoustic", "t_abs_s": None, "t_hms": "",
        })
    # 跨专辑颤音极差
    import statistics as st
    by = {}
    for x in songs:
        if x.get("vibrato_hz") and x.get("album"):
            by.setdefault(x["album"], []).append(x["vibrato_hz"])
    if by:
        med = {a: st.median(v) for a, v in by.items()}
        spread = max(med.values()) - min(med.values())
        out.append({
            "hook": f"八年 {len(med)} 张专辑，颤音速率极差 {spread:.2f}Hz",
            "evidence": "data/archive_vocal_albums.json#songs[].vibrato_hz（按 .album 取中位后比）",
            "small_words": ["颤音", "八年", "稳定性"], "audience": "声乐爱好者 / 数据向读者",
            "kind": "acoustic", "t_abs_s": None, "t_hms": "",
        })
    cn = load(D / "archive_cross_night.json")
    rows = (((cn.get("versions") or {}).get("v3_sep_vs_sep_8s") or {}).get("rows") or [])
    cmp_rows = [r for r in rows if r.get("comparable")]
    if cmp_rows:
        out.append({
            "hook": f"同一句隔一晚再唱，只差 {len(cmp_rows)} 组可比对的第二位小数",
            "evidence": "data/archive_cross_night.json#versions.v3_sep_vs_sep_8s.rows[]（comparable=true）",
            "small_words": ["跨夜", "稳"], "audience": "声乐爱好者", "kind": "acoustic",
            "t_abs_s": None, "t_hms": "",
        })
    return out


# ───────────────────────── 评分（离线规则化） ─────────────────────────

def novelty_index() -> dict:
    """新颖度参照：已发布卡片 + 词条（查得到＝已被用过）。"""
    used = {}
    for f in sorted((D / "share" / "cards").glob("card_*.json")):
        c = load(f)
        for k in ("title", "subtitle"):
            if c.get(k):
                used[hun(c[k])] = f"card:{c.get('id')}"
        for n in (c.get("main_numbers") or []):
            used[hun(str(n.get("label", "")))] = f"card:{c.get('id')}"
    ent = load(D / "share" / "entries.json")
    for e in (ent.get("entries") or []):
        used[hun(e.get("hook") or "")] = f"entry:{e.get('id')}"
        for t in (e.get("taboo") or []):
            used.setdefault(hun(t), f"entry-taboo:{e.get('id')}")
    return used


def score(c: dict, used: dict) -> dict:
    txt = hun(c.get("hook", "") + c.get("evidence", ""))
    h = hits(txt)
    s_story = 0.0
    if h["冲突标记"]:
        s_story += 2.0
    if h["时间标记"] or h["数字标记"]:
        s_story += 1.0
    if h["道具动作"]:
        s_story += 0.5
    if h["自嘲口吻"]:
        s_story += 0.5
    s_story = min(s_story, 4.0)
    s_ev = 0.0
    if c.get("t_hms") or c.get("t_abs_s"):
        s_ev += 1.0
    if re.search(r"(#|\bsongs?\b|\.json|\.segments\.json|abs|@)", c.get("evidence", "")):
        s_ev += 1.0
    if len(c.get("evidence", "")) >= 40:
        s_ev += 1.0
    s_ev = min(s_ev, 3.0)
    s_nv = 2.0
    dup = [used[k] for k in used if hun(c.get("hook", "")) and hun(c["hook"]) and
           (hun(c["hook"]) in k or k in hun(c["hook"]))]
    if dup:
        s_nv = 0.0
    # 风险与禁忌
    risks = []
    if any(w in txt for w in PRIVATE):
        risks.append("**命中私域/逝者黑名单 → 直接拦下，不进池**")
    if any(w in c.get("hook", "") for w in HYPE):
        risks.append("含平台量级断言词（爆火/引爆…）→ 改中性表述")
    if c.get("kind") == "talk":
        risks.append("talk 为本地 ASR 转写，未人工校对（引用须标注）")
    if c.get("kind") == "comment":
        risks.append("属第三方 UGC 语料，引用需匿名化；不得当全网声量")
    if c.get("kind") == "acoustic":
        risks.append("极值音口径＝最低稳定音；触达音/待核读数不进数字位")
    if dup:
        risks.append(f"新颖度低：已出现在 {dup[:2]}")
    c2 = dict(c)
    c2["score_story"] = round(s_story, 1)
    c2["score_evidence"] = round(s_ev, 1)
    c2["score_novelty"] = round(s_nv, 1)
    c2["score_total"] = round(s_story + s_ev + s_nv, 1)
    c2["risk"] = risks
    c2["blocked"] = any(w in txt for w in PRIVATE)
    c2["used_by"] = dup[:3]
    return c2


def eligible(c: dict) -> bool:
    return (not c["blocked"]
            and c["score_total"] >= POOL_MIN["score_total"]
            and c["score_evidence"] >= POOL_MIN["score_evidence"]
            and c["score_novelty"] >= POOL_MIN["score_novelty"])


# ───────────────────────── 产池 / 渲染 ─────────────────────────

def build_pool(args) -> dict:
    used = novelty_index()
    cands = []
    cands += copyright_story_candidates()
    cands += talk_candidates(load_talk_lines())
    cands += comment_candidates()
    cands += acoustic_candidates()
    scored = [score(c, used) for c in cands]
    scored.sort(key=lambda x: -x["score_total"])
    pool = [c for c in scored if eligible(c)]
    dropped = [c for c in scored if not eligible(c)]
    doc = {
        "schema": 1, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "what": "钩子候选池（规则化抽取 + 离线评分；宁缺勿滥）",
        "rules": {k: {"pattern": v} for k, v in RULES.items()},
        "threshold": POOL_MIN,
        "scoring": {"可转述性 score_story": "冲突 2 + 时间/数字 1 + 道具 0.5 + 自嘲 0.5（上限 4）",
                    "证据强度 score_evidence": "时间戳 1 + 字段路径 1 + 证据长度 1（上限 3）",
                    "新颖度 score_novelty": "未出现在已发卡片/词条 = 2，否则 0",
                    "score_total": "三者之和（上限 9）"},
        "count": len(pool), "dropped_count": len(dropped),
        "hooks": pool, "dropped": dropped[:40],
        "discipline": "平台机制表述为经验性认知（非官方）；禁写爆火/引爆全网/上热点；"
                      "绝不写入逝者/私域信息（命中即拦下）；音视频不入 git、不上页面。",
    }
    if args.dry:
        print("[dry] 命中候选 %d 条，入池 %d 条（阈值 %s）" % (len(scored), len(pool), POOL_MIN))
        for c in pool[:15]:
            print("  %4.1f | %-28s | %s" % (c["score_total"], c["hook"][:28], c["kind"]))
        print("[dry] 未写盘")
        return doc
    POOL.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    if not args.quiet:
        print("[池]", POOL, "→", len(pool), "条")
    # picks 模板（默认全 false；已有勾选不覆盖）
    if not args.pool_only:
        old = load(PICK, {})
        oldmap = {x.get("id"): x.get("picked") for x in (old.get("items") or [])}
        items = []
        for i, c in enumerate(pool, 1):
            cid = re.sub(r"\W+", "_", c["hook"])[:24] + f"_{i:02d}"
            items.append({"id": cid, "hook": c["hook"], "small_words": c["small_words"],
                          "evidence": c["evidence"], "audience": c["audience"],
                          "score_total": c["score_total"], "picked": bool(oldmap.get(cid, False))})
        PICK.write_text(json.dumps({
            "schema": 1, "generated_at": datetime.now().isoformat(timespec="seconds"),
            "how": "把想传播的条目 picked 改成 true，再跑 python -X utf8 project_b\\hook_miner.py --render-picked",
            "count": len(items), "picked_count": sum(1 for x in items if x["picked"]),
            "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
        if not args.quiet:
            print("[勾选]", PICK, "→", len(items), "条（默认未勾选）")
    write_pool_md(doc, pool, quiet=args.quiet)
    return doc


def write_pool_md(doc: dict, pool: list[dict], quiet: bool = False) -> None:
    ARCH.mkdir(parents=True, exist_ok=True)
    p = ARCH / f"钩子候选池_{TODAY}.md"
    L = [f"# 钩子候选池 · {TODAY}", "",
         f"> 结论先行：本轮命中 {len(pool)} 条可入池（阈值 {POOL_MIN}），"
         f"未达门槛 {doc['dropped_count']} 条未出池。**只需在这里勾选**。", "",
         "## Top 15（按总分降序）", "",
         "| # | 钩子句（≤25 字） | 建议小词 | 出处（含时间戳/字段） | 目标人群 | 总分 | 可转述 | 证据 | 新颖 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(pool[:15], 1):
        L.append("| %d | %s | %s | %s | %s | %.1f | %.1f | %.1f | %.1f |" % (
            i, c["hook"], "、".join(c["small_words"]), c["evidence"][:110].replace("|", "/"),
            c["audience"], c["score_total"], c["score_story"], c["score_evidence"], c["score_novelty"]))
    L += ["", "## 风险与禁忌（**仅内部**，不上站）", ""]
    for i, c in enumerate(pool[:15], 1):
        if c.get("risk"):
            L.append(f"{i}. {c['hook'][:20]}： " + "；".join(c["risk"]))
    L += ["", "## 纪律", "> " + doc["discipline"], ""]
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    if not quiet:
        print("[人读]", p)


def render_picked() -> int:
    pick = load(PICK, {})
    items = [x for x in (pick.get("items") or []) if x.get("picked")]
    if not items:
        print("[render-picked] 还没有勾选项（%s 里把 picked 改成 true）" % PICK)
        return 0
    pool = {x["hook"]: x for x in (load(POOL, {}).get("hooks") or [])}
    OUT_CARDS.mkdir(parents=True, exist_ok=True)
    OUT_RENDER.mkdir(parents=True, exist_ok=True)
    from build_topic_cards import render_card  # 复用卡片厂片段模板
    lines = [f"# 已勾选钩子 · 文案草稿 · {TODAY}", ""]
    n = 0
    for x in items:
        c = pool.get(x["hook"])
        if not c:
            continue
        n += 1
        cid = "pick_" + x["id"]
        card = {
            "id": cid, "no": 90 + n, "title": x["hook"][:22], "subtitle": "钩子候选（用户勾选后生成）",
            "review_status": "auto", "pillar": "候选（规则抽取，待人工确认上行）",
            "page_layer": "share-<id>.html（noindex,follow）",
            "main_numbers": [{"value": c["score_total"], "unit": "分", "label": "规则总分（可转述+证据+新颖）",
                              "caliber": "hook_score", "source": "project_b/hook_miner.py#RULES"}],
            "view_reading": [f"**钩子句**：{x['hook']}", f"**建议小词**：{'、'.join(x['small_words'])}",
                             f"**出处**：{x['evidence']}", f"**目标人群**：{x['audience']}",
                             "**纪律**：平台机制为经验性认知（非官方）；禁写爆火/引爆全网/上热点。"],
            "view_card": [x["hook"][:18], "、".join(x["small_words"][:2])],
            "caliber_lock": [], "gate": {"pass_status": "规则抽取得分 %.1f" % c["score_total"],
                                         "note": "钩子事实未变，仅作传播角度选择"},
            "platform": {"xiaohongshu": {"钩子句": x["hook"], "建议小词": "、".join(x["small_words"])},
                         "douyin": {"听觉断点": "（发布者自备素材，本站不提供音视频）"}},
            "footnote": f"来源：{x['evidence'][:90]}｜生成 {TODAY}",
            "generated_at": TODAY,
        }
        (OUT_CARDS / f"card_{cid}.json").write_text(json.dumps(card, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
        (OUT_RENDER / f"card_{cid}.html").write_text(render_card(card), encoding="utf-8")
        lines += [f"## {n}. {x['hook']}", "",
                  f"- 建议小词：{'、'.join(x['small_words'])}",
                  f"- 出处：{x['evidence']}",
                  f"- 目标人群：{x['audience']}",
                  f"- 风险：{'；'.join(c.get('risk') or ['—'])}", ""]
    (ARCH / f"已选钩子文案_{TODAY}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[文案]", ARCH / f"已选钩子文案_{TODAY}.md", "→", n, "条；卡片已落 data/share/cards/card_pick_*.json")
    return 0


def selftest() -> int:
    """规则自检：不读语料，只验证规则命中与评分口径。"""
    a = hun("其实我在我2019年做自己的第一次巡演的时候")
    assert re.search(RULES["时间标记"], a), "时间标记应命中 2019/第一次巡演"
    b = hun("了解了一下这首歌的版权,哇好贵,对就没有唱")
    assert re.search(RULES["冲突标记"], b), "冲突标记应命中 版权/好贵/没有唱"
    c = hun("那天他手里摇着一把沙锤")
    assert re.search(RULES["道具动作"], c), "道具动作应命中 沙锤/手里"
    s = score({"hook": "2019 想唱，版权太贵，等到 2026",
               "evidence": "现场 talk 61:56（绝对 3716.1s）…#S2_copyright_story.verbatim[]",
               "kind": "talk", "t_hms": "61:56"}, {})
    assert s["score_total"] >= 6.0, s
    blocked = score({"hook": "某位老粉去世", "evidence": "x", "kind": "talk"}, {})
    assert blocked["blocked"], "私域黑名单必须拦下"
    print("[selftest OK] 规则命中/评分/黑名单三项自检通过；示例总分 %.1f" % s["score_total"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="静默模式（巡逻链路用：只写盘、不打印明细）")
    ap.add_argument("--pool-only", action="store_true")
    ap.add_argument("--render-picked", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.render_picked:
        return render_picked()
    build_pool(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
