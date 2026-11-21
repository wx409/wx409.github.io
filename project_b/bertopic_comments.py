#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bertopic_comments.py —— 评论主题图谱（BERTopic 风格：bge 向量 + HDBSCAN + c-TF-IDF）

输出：data/comment_topics.json
用法：python -X utf8 project_b\\bertopic_comments.py --sample 10000
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DB = Path(r"E:\wx\私有\王晰语料库\comments.db")
OUT = ROOT / "data" / "comment_topics.json"


def clean(t):
    t = re.sub(r"@[\w\-\u4e00-\u9fa5]+", "", t or "")
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[^\u4e00-\u9fa5]", "", t)
    t = re.sub(r"(.)\1{2,}", r"\1", t)
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=10000)
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    seen = set()
    rows = []
    spam = re.compile(r"vlog|mv|xxxg|movado|tcl|mirenl|直播回放|抽奖", re.I)
    for (t,) in con.execute(
            "SELECT text FROM posts WHERE platform='weibo-comment' AND length(text) BETWEEN 10 AND 160"):
        t = clean(t)
        if not t or t in seen:
            continue
        zh = sum(1 for c in t if "\u4e00" <= c <= "\u9fa5")
        if len(t) < 12 or spam.search(t):
            continue
        seen.add(t)
        rows.append(t)
    random.seed(42)
    if len(rows) > a.sample:
        rows = random.sample(rows, a.sample)
    print("样本", len(rows))

    import jieba
    from sklearn.feature_extraction.text import CountVectorizer
    from sentence_transformers import SentenceTransformer
    from bertopic import BERTopic

    model = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
    emb = model.encode(rows, normalize_embeddings=True, show_progress_bar=True, batch_size=64)
    vec = CountVectorizer(tokenizer=jieba.lcut, token_pattern=None, min_df=1, max_df=1.0, ngram_range=(1, 1))
    topic_model = BERTopic(embedding_model=None, vectorizer_model=vec, min_topic_size=25,
                           nr_topics=25, calculate_probabilities=False, verbose=True)
    topics, _ = topic_model.fit_transform(rows, embeddings=emb)
    info = topic_model.get_topic_info()
    out = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "sample": len(rows), "topics": []}
    for _, r in info.iterrows():
        tid = int(r["Topic"])
        if tid == -1:
            continue
        words = [w for w, _ in (topic_model.get_topic(tid) or [])[:12]]
        idx = [i for i, t in enumerate(topics) if t == tid][:80]
        samples = [rows[i] for i in idx[:3]]
        out["topics"].append({"id": tid, "count": int(r["Count"]), "words": words, "samples": samples})
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("主题", len(out["topics"]), "→", OUT)
    for t in out["topics"][:8]:
        print(t["count"], "|", "、".join(t["words"][:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
