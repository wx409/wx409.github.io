#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topic_cluster.py —— 评论主题图谱（bge 向量 + KMeans + c-TF-IDF，BERTopic 同思路的稳定实现）"""
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
    ap.add_argument("--sample", type=int, default=12000)
    ap.add_argument("--clusters", type=int, default=24)
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    seen, rows = set(), []
    spam = re.compile(r"vlog|mv|xxxg|movado|tcl|mirenl|直播回放|抽奖", re.I)
    for (t,) in con.execute("SELECT text FROM posts WHERE platform='weibo-comment' AND length(text) BETWEEN 10 AND 160"):
        t = clean(t)
        if len(t) < 12 or t in seen or spam.search(t):
            continue
        seen.add(t)
        rows.append(t)
    random.seed(42)
    if len(rows) > a.sample:
        rows = random.sample(rows, a.sample)
    print("样本", len(rows))

    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import CountVectorizer
    import jieba

    model = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
    emb = model.encode(rows, normalize_embeddings=True, show_progress_bar=True, batch_size=64)
    km = KMeans(n_clusters=a.clusters, random_state=42, n_init=10)
    labels = km.fit_predict(emb)
    out = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "sample": len(rows), "topics": []}
    from sklearn.feature_extraction.text import TfidfVectorizer
    stop = list("的了是我你他她它在有就和都也不很还这那啊吧吗呀哦嗯哈一个什么怎么就是特别真的可以没有我们你们他们")
    tfv = TfidfVectorizer(tokenizer=jieba.lcut, token_pattern=None, stop_words=stop,
                          min_df=2, max_df=0.6, sublinear_tf=True)
    Xall = tfv.fit_transform(rows)
    names = tfv.get_feature_names_out()
    for c in range(a.clusters):
        docs = [rows[i] for i in range(len(rows)) if labels[i] == c]
        if len(docs) < 30:
            continue
        try:
            mean = Xall[labels == c].mean(axis=0).A1
            words = [w for _, w in sorted(zip(mean, names), reverse=True)[:10]]
        except Exception:
            words = []
        out["topics"].append({"id": c, "count": len(docs), "words": words, "samples": docs[:3]})
    out["topics"].sort(key=lambda x: -x["count"])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("主题", len(out["topics"]), "→", OUT)
    for t in out["topics"][:10]:
        print(t["count"], "|", "、".join(t["words"][:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
