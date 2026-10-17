# -*- coding: utf-8 -*-
"""copy_style_audit.py —— 从**真语料**量出小红书「人味标尺」→ data/share/copy_style.json

语料：E:\\wx\\论文素材_王晰作传\\小红书素材\\我要你20261010\\posts.json（笔记）+ comments.json（评论）
统计项（都是可复核的计数/比例）：
  · 行数与每行字数（小红书风格＝短行＋换行；统计 行数中位 / 每行字数 P50/P90 / 每行≤20 字占比）
  · emoji：是否用、用几个（中位/P90）；含 emoji 的笔记占比
  · 第一人称比例（我/我们/咱/自己）、感叹号比例、问号比例
  · 话题标签：个数中位/区间、**是否在末尾**（标签出现在最后 20% 文本位置的占比）
  · 结构：是否有「标题句 + 空行 + 正文」（首行短且其后有空行的占比）
  · 公众号召/CTA、@ 提及、链接出现率（用于判"能否直接发"）
输出：data/share/copy_style.json（供 build_copy_pipeline.py 约束生成，**不靠感觉**）
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
SRC = Path(r"E:\wx\论文素材_王晰作传\小红书素材\我要你20261010")
OUT = SITE / "data" / "share" / "copy_style.json"

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")
TAG = re.compile(r"#([^\s#]{1,30})")
FP = ("我", "我们", "咱", "自己", "本人")


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def main() -> int:
    posts = json.loads((SRC / "posts.json").read_text(encoding="utf-8"))
    comments = json.loads((SRC / "comments.json").read_text(encoding="utf-8"))
    P = posts if isinstance(posts, list) else (posts.get("items") or posts.get("posts") or [])
    # ★ comments.json 结构：{"notes": [{"comments": [...]}], "n_out_total": …}
    if isinstance(comments, dict) and comments.get("notes"):
        C = [c for n in comments["notes"] for c in (n.get("comments") or [])]
    else:
        C = comments if isinstance(comments, list) else (comments.get("items") or [])
    print(f"[语料] 笔记 {len(P)} 条｜评论 {len(C)} 条")

    def text_of(x):
        return str(x.get("desc") or x.get("text") or x.get("content") or x.get("title") or "").strip()

    texts = [t for t in (text_of(x) for x in P) if t]
    lines_n, line_lens, emoji_n, tags_n, tag_at_end = [], [], [], [], []
    fp_notes = excl = q_notes = 0
    title_blank = 0
    at_notes = link_notes = 0
    for t in texts:
        ls = [x for x in t.split("\n") if x.strip()]
        lines_n.append(len(ls))
        line_lens += [len(x.strip()) for x in ls]
        e = len(EMOJI.findall(t))
        emoji_n.append(e)
        tg = TAG.findall(t)
        tags_n.append(len(tg))
        if tg:
            last = t.rfind("#")
            tag_at_end.append(1 if last >= 0.75 * len(t) else 0)
        if any(k in t for k in FP):
            fp_notes += 1
        if "！" in t or "!" in t:
            excl += 1
        if "？" in t or "?" in t:
            q_notes += 1
        if len(ls) >= 2 and len(ls[0]) <= 30 and ("\n\n" in t or len(ls[0]) <= 20):
            title_blank += 1
        if "@" in t:
            at_notes += 1
        if "http" in t:
            link_notes += 1

    ctexts = [t for t in (text_of(x) for x in C) if t]
    c_fp = sum(1 for t in ctexts if any(k in t for k in FP))
    c_ex = sum(1 for t in ctexts if "！" in t or "!" in t)

    def q(xs, p):
        xs = sorted(xs)
        if not xs:
            return None
        k = min(len(xs) - 1, max(0, int(round((len(xs) - 1) * p))))
        return xs[k]

    doc = {
        "schema": 1,
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "source": str(SRC),
        "n_posts": len(texts), "n_comments": len(ctexts),
        "ruler": {
            "lines_median": st.median(lines_n) if lines_n else None,
            "lines_p10": q(lines_n, 0.1), "lines_p90": q(lines_n, 0.9),
            "line_len_p50": q(line_lens, 0.5), "line_len_p90": q(line_lens, 0.9),
            "line_le20_pct": pct(sum(1 for x in line_lens if x <= 20), len(line_lens)),
            "emoji_notes_pct": pct(sum(1 for n in emoji_n if n > 0), len(emoji_n)),
            "emoji_median": st.median(emoji_n) if emoji_n else 0,
            "emoji_p90": q(emoji_n, 0.9),
            "emoji_max": max(emoji_n) if emoji_n else 0,
            "tags_median": st.median(tags_n) if tags_n else 0,
            "tags_p10": q(tags_n, 0.1), "tags_p90": q(tags_n, 0.9),
            "tags_at_tail_pct": pct(sum(tag_at_end), len(tag_at_end)),
            "first_person_notes_pct": pct(fp_notes, len(texts)),
            "exclam_notes_pct": pct(excl, len(texts)),
            "question_notes_pct": pct(q_notes, len(texts)),
            "title_blank_structure_pct": pct(title_blank, len(texts)),
            "at_mention_pct": pct(at_notes, len(texts)),
            "link_pct": pct(link_notes, len(texts)),
        },
        "comments": {"n": len(ctexts),
                     "first_person_pct": pct(c_fp, len(ctexts)),
                     "exclam_pct": pct(c_ex, len(ctexts))},
        "constraints": {},   # 由下面按 ruler 生成
        "note": "约束值取「真语料中位/P90」的保守合并；生成时按 constraints 硬约束，越界即重写。",
    }
    r = doc["ruler"]
    doc["constraints"] = {
        "line_max_chars": int(min(20, max(14, round((r["line_len_p50"] or 19) / 2) * 2))),
        "lines_range": [max(3, int(r["lines_p10"] or 3) + 1),
                        max(5, int(r["lines_p90"] or 6))],
        "emoji_max": int(min(4, max(1, (r["emoji_p90"] or 2)))),
        "tags_range": [max(2, int((r["tags_median"] or 4) - 1)),
                       int((r["tags_median"] or 4) + 1)],
        "tags_at_tail": True,
        "first_person_min_lines": 1,
        "exclam_max": 1,
        "no_long_paragraph": True,
        "title_then_blank_line": (r["title_blank_structure_pct"] or 0) >= 40,
        "fill_in_slots": [1, 3],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(doc["ruler"], ensure_ascii=False, indent=1))
    print("约束：", json.dumps(doc["constraints"], ensure_ascii=False))
    print(f"[OK] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
