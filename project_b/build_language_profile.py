# -*- coding: utf-8 -*-
"""P0-1 语言特征层：口吻/句式 + 高频意象与情绪词 + 早期 vs 近期分年对照 + 跨源对照

数据源（全部现有资产，不另造）：
  · `E:\\wx\\wx_textmine_out\\corpus.jsonl`（5155 帖，6 源）
  · `data/tour_talks_sentences.json`（巡演 talk 逐句，= 口语层）
  · `data/activity_master.json`（活动表，= 事务层）
  · `data/setlists.json`（巡演长表派生，= 曲目文本层，只做词表）
输出：
  · `E:\\wx\\wx_textmine_out\\language_profile.json`（全量，含逐源逐窗）
  · `data/text_profile.json`（站内精简版，公开字段不含本地路径）

纪律：每项带 n 与年分箱；纯计数与比例，不做评价；不写死数字（全部现算）。
"""
from __future__ import annotations
import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
TM = Path(r"E:\wx\wx_textmine_out")
CORPUS = TM / "corpus.jsonl"
OUT_FULL = TM / "language_profile.json"
OUT_SITE = D / "text_profile.json"

SENT_SPLIT = re.compile(r"[。！？!?…\n]+")
# 切句时**保留终止符**，否则端到端的「？」会被吞掉 → 问句率恒为 0（2026-10-14 修）
SENT_TOKEN = re.compile(r"[^。！？!?…\n]+[。！？!?…]?")
SHORT_MAX = 15
FIRST_PERSON = ("我", "我们", "咱", "自己", "本人")
QUESTION = ("？", "?")

# 意象词（具体可指的物/场景）与情绪词（感受）——词典显式列出，便于复核与增补
IMAGERY = {
    "夜": ["夜", "深夜", "夜里", "月", "月光", "星"], "海": ["海", "浪", "潮", "港"],
    "风": ["风", "秋", "冬", "春", "夏"], "路": ["路", "远方", "旅途", "车站", "机场"],
    "酒/茶": ["酒", "一杯", "茶", "咖啡"], "舞台": ["舞台", "灯光", "麦克", "返场", "开票"],
    "城市": ["北京", "上海", "广州", "成都", "重庆", "杭州", "南京", "深圳", "长沙", "厦门"],
    "乐器": ["吉他", "钢琴", "大提琴", "贝斯", "鼓", "沙锤"],
    "身体": ["嗓子", "声音", "气息", "耳朵", "眼睛", "眼泪"],
}
EMOTION = {
    "感谢": ["感谢", "谢谢", "感恩", "多谢"], "想念": ["想念", "思念", "怀念", "想你们"],
    "坚持": ["坚持", "努力", "不放弃", "加油", "拼"], "自嘲/自谦": ["哈哈", "嘿嘿", "不敢当", "惭愧"],
    "歉意": ["抱歉", "对不起", "不好意思", "见谅"], "期待": ["期待", "希望", "盼", "等待"],
    "疲惫": ["累", "疲惫", "辛苦"], "告别": ["告别", "再见", "收官", "最后一站"],
    "开心": ["开心", "高兴", "快乐", "幸福", "激动"],
}


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def sents(text: str) -> list[str]:
    """切句并保留终止符（问句率依赖终止符）。"""
    return [m.group(0).strip() for m in SENT_TOKEN.finditer(str(text or "")) if len(m.group(0).strip()) >= 2]


def slice_stats(docs: list[dict]) -> dict:
    """docs: [{text, date}] → 句式/词表统计（每项带 n）"""
    ss, docs_n, chars = [], 0, 0
    img, emo = Counter(), Counter()
    for d in docs:
        t = d.get("text") or ""
        if not t.strip():
            continue
        docs_n += 1
        chars += len(t)
        ss.extend(sents(t))
        for k, ws in IMAGERY.items():
            if any(w in t for w in ws):
                img[k] += 1
        for k, ws in EMOTION.items():
            if any(w in t for w in ws):
                emo[k] += 1
    n_sent = len(ss)
    if not n_sent:
        return {"n_docs": docs_n, "n_sent": 0}
    lens = [len(s) for s in ss]
    return {
        "n_docs": docs_n, "n_sent": n_sent, "chars": chars,
        "chars_per_doc_median": round(st.median([len(d.get("text") or "") for d in docs if (d.get("text") or "").strip()]), 1),
        "sent_len_median": round(st.median(lens), 1),
        "short_sent_pct": round(100.0 * sum(1 for x in lens if x <= SHORT_MAX) / n_sent, 1),
        "question_pct": round(100.0 * sum(1 for s in ss if s.endswith(QUESTION)) / n_sent, 1),
        "first_person_pct": round(100.0 * sum(1 for s in ss if any(w in s for w in FIRST_PERSON)) / n_sent, 1),
        "imagery_top": img.most_common(10), "imagery_doc_pct": {k: round(100.0 * v / docs_n, 1) for k, v in img.most_common(10)},
        "emotion_top": emo.most_common(10), "emotion_doc_pct": {k: round(100.0 * v / docs_n, 1) for k, v in emo.most_common(10)},
    }


# ── 1. 主语料 ──
docs_all = []
for line in CORPUS.read_text(encoding="utf-8").splitlines():
    if line.strip():
        o = json.loads(line)
        docs_all.append({"text": o.get("text") or "", "date": str(o.get("date") or ""), "source": o.get("source") or ""})

by_source = {}
for d in docs_all:
    by_source.setdefault(d["source"], []).append(d)
by_year = {}
for d in docs_all:
    y = (d["date"] or "")[:4]
    if y.isdigit():
        by_year.setdefault(y, []).append(d)

# 早期 vs 近期（按年分箱：2014–2019 / 2020–2023 / 2024–2026）
BINS = {"2014-2019 早期": range(2014, 2020), "2020-2023 中期": range(2020, 2024), "2024-2026 近期": range(2024, 2027)}
bins = {name: [d for d in docs_all if (d["date"] or "")[:4].isdigit() and int((d["date"])[:4]) in yrs] for name, yrs in BINS.items()}

# ── 2. 跨源层（字段映射**人工确认过**；见 build_cross_wording.py 的 FIELD_MAP）──
#   2026-10-14 修正：初版按 sentences/rows/items 与 shows/rows/items 探测，三层里有两层取到 0 条。
cross = {}
talks = load(D / "tour_talks_sentences.json")
if talks is not None:
    td = []
    for g in (talks.get("groups") or []):                      # ← 句子在 groups[].items[].sentences[]
        for it in (g.get("items") or []):
            for s in (it.get("sentences") or []):
                if (s.get("text") or "").strip():
                    td.append({"text": s["text"], "date": ""})
    cross["巡演Talk（口语层）"] = {**slice_stats(td), "file": "data/tour_talks_sentences.json",
                                 "container": "groups[].items[].sentences[]",
                                 "groups": len(talks.get("groups") or []),
                                 "file_counts": talks.get("counts")}
act = load(D / "activity_master.json")
if act is not None:
    rows = act.get("rows") or []                              # ← 该文件没有 name/desc/venue 字段
    ad = []
    for r in rows:
        if isinstance(r, dict):
            ad.append({"text": " ".join(str(r.get(k) or "") for k in ("title", "city", "note")),
                       "date": str(r.get("date") or "")})
    cross["活动表（事务层）"] = {**slice_stats(ad), "file": "data/activity_master.json",
                                "container": "rows[]（title＋city＋note）"}
sl = load(D / "setlists.json")
if sl is not None:
    sets = sl.get("setlists") or {}                           # ← 按日期为键的字典
    names = []
    for _k, v in (sets.items() if isinstance(sets, dict) else []):
        if isinstance(v, dict):
            names += [str(x.get("title") or "") for x in (v.get("songs") or []) if isinstance(x, dict)]
    cross["巡演长表（曲目层）"] = {"file": "data/setlists.json", "container": "setlists（日期为键）",
                                 "n_songs": len([x for x in names if x]), "n_docs": len(sets), "n_sent": 0,
                                 "shows": sl.get("show_count"),
                                 "note": "曲名文本，不做句式统计；仅用于曲目词表交叉"}

full = {
    "schema": 1, "generated_from": "wx_textmine_out/corpus.jsonl + data/tour_talks_sentences.json + data/activity_master.json + data/setlists.json",
    "caliber": {"sent_split": "。！？!?…换行", "short_max_chars": SHORT_MAX,
                "first_person": list(FIRST_PERSON), "note": "纯计数与比例；每项带 n 与年分箱"},
    "overall": slice_stats(docs_all),
    "by_source": {k: slice_stats(v) for k, v in sorted(by_source.items(), key=lambda x: -len(x[1]))},
    "by_year_bin": {k: slice_stats(v) for k, v in bins.items()},
    "by_year": {k: {"n_docs": len(v), **{kk: vv for kk, vv in slice_stats(v).items() if kk in
                                         ("n_sent", "sent_len_median", "short_sent_pct", "question_pct", "first_person_pct")}}
                for k, v in sorted(by_year.items())},
    "cross_source": cross,
    "imagery_lexicon": IMAGERY, "emotion_lexicon": EMOTION,
}
OUT_FULL.write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")

# 站内精简版（公开字段；不含本地绝对路径）
site = {"schema": 1, "generated_from": "文本挖掘语料（本地 corpu）＋巡演 talk 逐句＋活动表＋巡演长表",
        "caliber": full["caliber"], "overall": full["overall"], "by_source": full["by_source"],
        "by_year_bin": full["by_year_bin"], "by_year": full["by_year"],
        "cross_source": {k: {kk: vv for kk, vv in v.items() if kk != "file"} for k, v in cross.items()}}
OUT_SITE.write_text(json.dumps(site, ensure_ascii=False, indent=1), encoding="utf-8")

o = full["overall"]
print(f"[ok] {OUT_FULL.name}｜源 {len(full['by_source'])}｜年 {len(full['by_year'])}｜跨源 {len(cross)}")
print(f"[ok] {OUT_SITE.name}")
print(f"总体：n_docs={o['n_docs']} n_sent={o['n_sent']} 短句率={o['short_sent_pct']}% 问句率={o['question_pct']}% 第一人称={o['first_person_pct']}%")
for k, v in full["by_year_bin"].items():
    print(f"  {k}: n={v.get('n_docs')} 短句率={v.get('short_sent_pct')}% 问句率={v.get('question_pct')}% 第一人称={v.get('first_person_pct')}%")
print("  意象 Top5:", o["imagery_top"][:5])
print("  情绪 Top5:", o["emotion_top"][:5])
