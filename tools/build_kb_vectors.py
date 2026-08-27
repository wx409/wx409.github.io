# -*- coding: utf-8 -*-
"""知识库语义索引构建器：bge-small-zh 向量 + 语义近邻图 + 文档索引

思路（零后端语义检索）：
  Python 端一次性完成重活（embedding/近邻），产物纯静态供前端零模型检索：
    data/kb/semantic/docs.json        文档清单（id/type/text，供前端 n-gram 向量与展示）
    data/kb/semantic/vectors.bin      int8 量化向量（512 维，doc 数 × 512 字节）
    data/kb/semantic/graph.json       每文档 top-8 语义近邻（bge 余弦）
    data/kb/semantic/manifest.json    形状/来源/统计
  前端 kb_semantic.js：char-bigram TF 向量余弦（纯 JS）+ 别名扩展 + 语义近邻延伸。

用法：
  python tools/build_kb_vectors.py [--no-neighbors]
模型：BAAI/bge-small-zh-v1.5（512维，经 hf-mirror.com 下载，一次缓存后离线可用）
"""
import base64, io, json, os, sys, time
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

ROOT = Path(r"D:\wx409.github.io")
KB = ROOT / "data" / "kb"
SEM = KB / "semantic"

def load(p, fb):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return fb

def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)

def build_docs():
    docs = []
    ents = load(KB / "entities.json", {}).get("entities", {})
    facts = load(KB / "facts.json", [])
    rels = load(KB / "relations.json", [])
    qa = load(ROOT / "data" / "qa_bank.json", {}).get("items", [])
    seen = set()
    def add(did, dtype, text):
        if did in seen or not text or len(text) < 2:
            return
        seen.add(did)
        docs.append({"id": did, "type": dtype, "text": text[:300]})
    # 实体（人/歌/专辑/巡演/机构/场馆/城市/事件/媒体/金句/小酒馆）
    for eid, e in ents.items():
        attrs = " ".join(str(v) for v in (e.get("attrs") or {}).values() if v)
        add(eid, e.get("type", "entity"), "%s %s %s" % (e.get("name", ""), " ".join(e.get("aliases", [])), attrs))
    # 事实（含时效/来源/置信度）
    for f in facts:
        add(f["id"], "fact", "%s %s %s %s %s" % (
            f.get("subject", ""), f.get("property", ""), f.get("value", ""),
            f.get("valid_from", ""), f.get("valid_to", "") or ""))
    # 关系（歌↔演出等）
    for r in rels[:4000]:
        add("rel:%s" % r["source"] + r["target"], "relation", "%s %s %s %s" % (
            r.get("source", ""), r.get("type", ""), r.get("target", ""), r.get("context", "")))
    # 问答
    for i, q in enumerate(qa):
        add("qa:%d" % i, "qa", "%s %s" % (q.get("question", ""), q.get("answer", "")))
    log("文档数: %d" % len(docs))
    return docs

def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    SEM.mkdir(parents=True, exist_ok=True)
    docs = build_docs()
    from sentence_transformers import SentenceTransformer
    t0 = time.time()
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
    log("模型加载 %.0f 秒" % (time.time() - t0))
    texts = [d["text"] for d in docs]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=64)
    log("编码完成: %s (%d 维)" % (str(emb.shape), emb.shape[1]))
    # int8 量化（scale=127，余弦近似足够）
    import numpy as np
    q = np.clip(np.round(emb * 127.0), -127, 127).astype(np.int8)
    (SEM / "vectors.bin").write_bytes(q.tobytes())
    (SEM / "docs.json").write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    # 语义近邻图（内积 = 余弦，因向量已归一化；int8 内积近似）
    topk = 8
    graph = {}
    sims = q.astype(np.float32) @ q.astype(np.float32).T
    for i in range(len(docs)):
        order = np.argsort(-sims[i])[1:topk + 1]
        graph[docs[i]["id"]] = [docs[j]["id"] for j in order if sims[i][j] > 0]
    (SEM / "graph.json").write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    (SEM / "manifest.json").write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": "BAAI/bge-small-zh-v1.5", "dim": int(emb.shape[1]),
        "quant": "int8 scale=127", "doc_count": len(docs),
        "topk": topk, "size_bytes": len(q.tobytes()),
        "types": {t: sum(1 for d in docs if d["type"] == t) for t in sorted(set(d["type"] for d in docs))},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log("语义索引完成: docs=%d, vectors=%.2fMB, 用时 %.0f 秒" % (
        len(docs), len(q.tobytes()) / 1048576, time.time() - t0))
    # 质量抽查：与事实层互查
    check(docs, q)

def check(docs, q):
    import numpy as np
    probes = ["王晰哪年获得青歌赛冠军", "王晰加入乐华娱乐的时间", "一生守候在哪些演出唱过"]
    for p in probes:
        import re
        def bigrams(s):
            s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)
            return set(s[i:i + 2] for i in range(max(0, len(s) - 1)))
        pb = bigrams(p)
        best = []
        for i, d in enumerate(docs):
            db = bigrams(d["text"])
            j = len(pb & db) / max(1, len(pb | db))
            best.append((j, i, d))
        best.sort(key=lambda x: -x[0])
        print("  [%s] -> %s (%.2f)" % (p, best[0][2]["text"][:50], best[0][0]))

if __name__ == "__main__":
    main()
