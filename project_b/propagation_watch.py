# -*- coding: utf-8 -*-
"""传播监测线：搜 → 抓正文+评论 → 量化 → 摘要 → 异常通知（复用既有工具，不另造）。

用法：
  python -X utf8 project_b\\propagation_watch.py --dry                    # 只打印将执行的动作与阈值判定
  python -X utf8 project_b\\propagation_watch.py --mode links             # 小红书按链接路径（最稳）
  python -X utf8 project_b\\propagation_watch.py --since 72               # 时间窗（小时）
  python -X utf8 project_b\\propagation_watch.py --eval-retrieval         # A 六项检索升级 · 升级前后对照（离线语料）
  python -X utf8 project_b\\propagation_watch.py --window "2026-10-10 20:00-24:00"   # 定向窗补采/判定
  python -X utf8 project_b\\propagation_watch.py --rule2                  # liked 归一化 + 单条赞>中位×3 模拟

A 六项检索升级（参数全部在 data/propagation_watch.json 的 retrieval 段）：
  ① 多查询扩展（每目标 3–5 变体）
  ② BM25（纯 python 实现，无新依赖）＋ 本机 bge-small-zh 语义检索（复用 tools/build_kb_vectors.py
     同款模型 BAAI/bge-small-zh-v1.5，不引新依赖）＋ RRF 融合
  ③ noteId/BV 去重 + 标题归一化后 Jaccard≥0.85 去重（跨平台转发算一条，记出现次数）
  ④ 重排：相关性 × 互动分位 × 时间衰减；**原始平台顺序作对照保留**
  ⑤ 首轮簇状不成立 → 高频新词自动二次检索（≤2 轮）
  ⑥ 参数全部进 data/propagation_watch.json

纪律：音视频不入 git、不上页面；作者名匿名化；**无平台侧数据不得写"上热点/爆火"**；
      平台机制表述标「经验性认知（非官方）」；极值音归属一律"归属未定"；
      触达音不进标题数字位；cookie 失效走既有三态（站点通知 + 本地日志）；失败如实记录，不伪造。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
CFG = SITE / "data" / "propagation_watch.json"
DIGEST = SITE / "data" / "propagation_digest.json"
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")
CORPUS = Path(r"E:\wx\论文素材_王晰作传\小红书素材\我要你20261010")
LOG = SITE / "temp" / "propagation_watch.log"
CST = timezone(timedelta(hours=8))


def log(m):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.open("a", encoding="utf-8").write(line + "\n")


def notify(title, body):
    try:
        sys.path.insert(0, str(SITE / "project_b"))
        import notify
        notify.record(title, body)
        log("已写站点通知（文案只写机制，不写爆火）")
    except Exception as e:
        log(f"通知失败（不致命）：{e}")


def cookie_ok(plat):
    if plat == "xhs":
        r = subprocess.run([sys.executable, "-X", "utf8", "tools/sync_xhs_cookie.py", "--check"],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore",
                           cwd=str(SITE))
        out = (r.stdout or "") + (r.stderr or "")
        for s in ("有效", "失效", "被风控"):
            if s in out:
                return s
        return "无法判定"
    return "未检查"


# ───────────────────────── 通用：数字归一化 / 指纹 ─────────────────────────

def to_int(v) -> int:
    """互动量归一化：int / '1.2万' / '2k' / '1,234' / '' → int（无法解析返回 0）。

    修复点 2：`liked` 字段混有字符串（如 "1.2万"），直接求中位会 TypeError。
    """
    if v is None or isinstance(v, bool):
        return int(v) if isinstance(v, bool) else 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().replace(",", "").replace("+", "").replace(" ", "")
    if not s:
        return 0
    mult = 1
    for suf, m in (("万", 10000), ("w", 10000), ("W", 10000), ("亿", 100000000),
                   ("k", 1000), ("K", 1000)):
        if s.endswith(suf):
            mult, s = m, s[: -len(suf)]
            break
    try:
        return int(round(float(s) * mult))
    except Exception:
        m = re.search(r"[\d.]+", s)
        return int(round(float(m.group()) * mult)) if m else 0


def med(xs):
    import statistics
    xs = list(xs)
    return statistics.median(xs) if xs else None


def norm_note_id(s: str) -> str:
    """noteId 归一化：小红书 24 位 hex；B站 BV 号统一大写。"""
    s = (s or "").strip()
    m = re.search(r"([0-9a-f]{24})", s, re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"(BV[0-9A-Za-z]{10})", s, re.I)
    if m:
        return m.group(1).upper()
    return s.lower()


def norm_title(t: str) -> str:
    """标题归一化：去作者尾巴/装饰/话题标签/空白与标点。"""
    t = t or ""
    t = re.sub(r"[-–—|｜].*$", " ", t)                     # 去 "- 作者 | 小红书"
    t = re.sub(r"#([^#\[\]]+?)(\[话题\])?#", r"\1", t)      # 去 #话题#
    t = re.sub(r"[\s\u3000]+", "", t)
    t = re.sub(r"[^\w\u4e00-\u9fff]+", "", t)
    return t.lower()


def toks(text: str) -> list:
    """中文字符 bigram + 英文/数字整词 + 单字（保底）。"""
    text = (text or "").lower()
    out = re.findall(r"[a-z0-9]+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    out += ["".join(p) for p in zip(cjk, cjk[1:])]
    if len(cjk) == 1:
        out.append(cjk[0])
    return out


def jaccard(a: str, b: str) -> float:
    A, B = set(toks(norm_title(a))), set(toks(norm_title(b)))
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


# ───────────────────────── BM25（纯 python，无新依赖） ─────────────────────────

def build_bm25(docs, k1=1.5, b=0.75):
    N = len(docs)
    tf = [Counter(toks(d)) for d in docs]
    dl = [sum(t.values()) for t in tf]
    avgdl = (sum(dl) / N) if N else 0.0
    df = Counter()
    for t in tf:
        df.update(t.keys())
    idf = {w: math.log(1 + (N - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def score(q):
        qs = Counter(toks(q))
        s = [0.0] * N
        for i in range(N):
            denom = tf[i].get("__len__", 0)
            acc = 0.0
            for w, qc in qs.items():
                f = tf[i].get(w, 0)
                if not f:
                    continue
                acc += idf.get(w, 0.0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl[i] / (avgdl or 1)))
            s[i] = acc
        return s

    return score


# ───────────────────────── 语义检索（本机 bge-small-zh） ─────────────────────────

class Sem:
    """本机 bge-small-zh-v1.5（与 tools/build_kb_vectors.py 同款模型，离线）。"""

    def __init__(self, model_name="BAAI/bge-small-zh-v1.5"):
        self.model_name = model_name
        self.model = None
        self.err = ""
        self.emb = None

    def load(self):
        if self.model is not None or self.err:
            return self.model is not None
        try:
            import os
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, device="cpu")
            return True
        except Exception as e:
            self.err = repr(e)[:200]
            return False

    def encode(self, texts):
        import numpy as np
        if self.emb is None:
            v = self.model.encode(list(texts), normalize_embeddings=True, batch_size=32,
                                  show_progress_bar=False)
            self.emb = np.asarray(v, dtype="float32")
        return self.emb

    def score(self, docs, query):
        import numpy as np
        M = self.encode(docs)
        q = np.asarray(self.model.encode([query], normalize_embeddings=True,
                                         show_progress_bar=False), dtype="float32")[0]
        return (M @ q).tolist()


# ───────────────────────── RRF 融合 ─────────────────────────

def rrf(rank_lists, k=60, weights=None):
    """Reciprocal Rank Fusion：rank_lists = [[doc_idx,...], ...]（各自已按降序排好）。"""
    weights = weights or [1.0] * len(rank_lists)
    acc = defaultdict(float)
    for w, rl in zip(weights, rank_lists):
        for pos, idx in enumerate(rl):
            acc[idx] += w / (k + pos + 1)
    return sorted(acc.items(), key=lambda kv: -kv[1])


# ───────────────────────── 去重（noteId/BV + 标题 Jaccard） ─────────────────────────

def dedupe(items, thr=0.85):
    """items: [{doc_idx, note_id, title, ...}]，返回去重后列表（含 dup_count）。

    口径：**只在「笔记层」去重**——noteId（24 位 hex / BV 号）相同的算同一条，
    标题归一化后 Jaccard≥thr 的视为同源（跨平台转发算一条，记 dup_count）。
    评论按自身 id 唯一，不参与标题去重（同一笔记下多条不同评论是不同信息，不得合并）。
    """
    seen_id, out = {}, []
    for it in items:
        nid = norm_note_id(it.get("note_id") or it.get("url") or "")
        is_note = bool(it.get("title"))
        if is_note and nid and nid in seen_id:
            out[seen_id[nid]]["dup_count"] += 1
            continue
        if is_note:
            hit = None
            for o in out:
                if o.get("title") and jaccard(o.get("title", ""), it.get("title", "")) >= thr:
                    hit = o
                    break
            if hit is not None:
                hit["dup_count"] += 1
                hit.setdefault("dup_of", []).append(it.get("doc_idx"))
                continue
        it = dict(it, dup_count=1)
        out.append(it)
        if is_note and nid:
            seen_id[nid] = len(out) - 1
    return out


# ───────────────────────── 语料装载（离线，只读本地既有产物） ─────────────────────────

def load_corpus(corpus_dir: Path):
    """从小红书素材目录装载文档：帖子 + 一级/二级评论（扁平）。"""
    posts_p, cmts_p = corpus_dir / "posts.json", corpus_dir / "comments.json"
    docs = []
    if posts_p.exists():
        P = json.loads(posts_p.read_text(encoding="utf-8"))
        for p in P.get("posts", []):
            dt = p.get("datetime_cst") or p.get("date") or ""
            docs.append({"kind": "post", "doc_idx": len(docs), "note_id": p.get("note_id"),
                         "title": p.get("title", ""), "text": (p.get("title", "") + " " +
                                                               (p.get("desc") or "")),
                         "author": p.get("author", ""), "dt": dt,
                         "likes": to_int((p.get("stats") or {}).get("likes")),
                         "collects": to_int((p.get("stats") or {}).get("collects")),
                         "comments": to_int((p.get("stats") or {}).get("comments"))})
    if cmts_p.exists():
        C = json.loads(cmts_p.read_text(encoding="utf-8"))
        for n in C.get("notes", []):
            for c in n.get("comments", []):
                docs.append({"kind": "comment", "level": 1, "doc_idx": len(docs),
                             "note_id": n.get("note_id"), "title": "",
                             "text": c.get("content", ""), "author": c.get("anon", ""),
                             "dt": _fmt_ms(c.get("create_time")), "likes": to_int(c.get("like_count")),
                             "collects": 0, "comments": 0})
            for it in n.get("inner", []):
                for s in it.get("subs", []):
                    docs.append({"kind": "comment", "level": 2, "doc_idx": len(docs),
                                 "note_id": n.get("note_id"), "title": "",
                                 "text": s.get("content", ""), "author": s.get("anon", ""),
                                 "dt": _fmt_ms(s.get("create_time")), "likes": to_int(s.get("like_count")),
                                 "collects": 0, "comments": 0})
    return docs


def _fmt_ms(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, CST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


# ───────────────────────── 基线（升级前）：关键词子串直搜 + 平台原序 ─────────────────────────

def baseline_search(docs, cfg):
    """升级前：单查询（目标原词）＋子串命中，返回按**原始平台顺序**的命中列表。

    "召回条数" = 语料中命中任一目标词/钩子词/演出词的文档条数。
    """
    words = []
    for grp in ("songs", "hook_words", "show_words"):
        words += [w.lower() for w in (cfg.get("keywords", {}).get(grp) or [])]
    hits = [d for d in docs if any(w in (d.get("text") or "").lower() for w in words)]
    return hits


# ───────────────────────── 升级后：变体扩展 + BM25 + bge + RRF + 去重 + 重排 ─────────────────────────

def upgraded_search(docs, cfg, rounds=2):
    r = cfg.get("retrieval") or {}
    texts = [d["text"] for d in docs]
    variants = r.get("query_variants") or {}
    rc = r.get("rrf") or {}
    k = int(rc.get("k", 60))
    w_bm25 = float(rc.get("w_bm25", 1.0))
    w_sem = float(rc.get("w_sem", 1.0))
    w_rrf = float((r.get("rerank") or {}).get("w_rrf", 1.0))
    w_int = float((r.get("rerank") or {}).get("w_interaction", 0.3))
    w_time = float((r.get("rerank") or {}).get("w_time", 0.2))
    halflife = float(((r.get("rerank") or {}).get("time_decay") or {}).get("half_life_hours", 48))
    dedup_thr = float((r.get("dedup") or {}).get("jaccard", 0.85))
    bm25 = build_bm25(texts, **(r.get("bm25") or {}))
    sem = Sem((r.get("semantic") or {}).get("model", "BAAI/bge-small-zh-v1.5"))
    sem_ok = sem.load()
    if not sem_ok:
        log(f"    ⚠ 语义检索不可用（{sem.err[:80]}）→ 本轮只跑 BM25，如实记录不伪造")

    trace = []
    targets = list(variants.items())
    rank_lists, contrib, per_target = [], {}, {}
    top_n = int((r.get("recall") or {}).get("bm25_topn", 50))
    gate_min = float((r.get("recall") or {}).get("bm25_min", 0.5))
    gated_n = {}
    for i, (target, vs) in enumerate(targets):
        qs = [target] + [v for v in vs if v and v != target]
        qs = qs[: int(((r.get("expansion") or {}).get("max_variants", 5)))]
        acc = defaultdict(float)
        for q in qs:
            order = sorted(range(len(docs)), key=lambda j: -bm25(q)[j])
            for pos, j in enumerate(order):
                acc[j] += w_bm25 / (k + pos + 1)
        if sem_ok:
            for q in qs:
                sims = sem.score(texts, q)
                order = sorted(range(len(docs)), key=lambda j: -sims[j])
                for pos, j in enumerate(order):
                    acc[j] += w_sem / (k + pos + 1)
        ranked = sorted(acc.items(), key=lambda kv: -kv[1])
        bm = bm25(target)
        # 相关性闸门：BM25 与目标词有实质重叠（> gate_min）或落在每目标 top_n 内；
        # 防"多目标 RRF 长尾把无关文档也捞进来"（否则召回会被稀释成近似全量）
        keep = [j for j, _ in ranked if bm[j] > gate_min][:top_n]
        if not keep:
            keep = [j for j, sc in ranked[:top_n] if bm[j] > 0]
        gated_n[target] = len(keep)
        contrib[target] = {j: acc[j] for j in keep}
        per_target[target] = contrib[target]
        rank_lists.append(keep)
        trace.append({"round": 1, "target": target, "queries": qs, "n_ranked": len(ranked),
                      "n_gated": len(keep), "gate_bm25_min": gate_min, "gate_topn": top_n})

    gate_union = set()
    for t in per_target:
        gate_union |= set(per_target[t].keys())
    fused = rrf(rank_lists, k=k) if rank_lists else []

    # ③ 去重 + ④ 重排
    like_pool = [d["likes"] for d in docs] or [0]
    likes_sorted = sorted(like_pool)
    def pct(v):
        if not likes_sorted:
            return 0.0
        return sum(1 for x in likes_sorted if x <= v) / len(likes_sorted)
    now = datetime.now(CST)
    cand = []
    for j, sc in fused:
        d = docs[j]
        tid = norm_note_id(d.get("note_id") or "")
        cand.append({"doc_idx": j, "note_id": tid, "title": d.get("title") or "",
                     "kind": d["kind"], "dt": d.get("dt", ""), "likes": d["likes"],
                     "rrf": round(sc, 6), "text": (d.get("text") or "")[:80]})
    cand.sort(key=lambda c: -c["rrf"])
    ded = dedupe(cand, thr=dedup_thr)
    for c in ded:
        try:
            dt = datetime.strptime(c["dt"], "%Y-%m-%d %H:%M").replace(tzinfo=CST)
            age_h = max(0.0, (now - dt).total_seconds() / 3600)
        except Exception:
            age_h = None
        decay = 0.5 ** (age_h / halflife) if (age_h is not None and halflife > 0) else 0.0
        c["interaction_pct"] = round(pct(c["likes"]), 4)
        c["time_decay"] = round(decay, 4)
        c["score"] = round(w_rrf * c["rrf"] + w_int * c["interaction_pct"] + w_time * decay, 6)
    ded.sort(key=lambda c: -c["score"])
    for c in ded:
        c["matched_targets"] = sorted([t for t, d in per_target.items() if c["doc_idx"] in d],
                                      key=lambda t: -per_target[t].get(c["doc_idx"], 0))[:4]
    merged = [{"note_id": c["note_id"], "title": c.get("title", ""), "dup_count": c.get("dup_count", 1),
               "merged_doc_idx": c.get("dup_of", [])} for c in ded if c.get("dup_count", 1) > 1]
    return {"candidates": ded, "trace": trace, "sem_ok": sem_ok, "fused_n": len(fused),
            "gated_n": gated_n, "gated_union": sorted(gate_union),
            "gated_union_n": len(gate_union), "merged_notes": merged}


# ───────────────────────── A 六项：升级前后对照 + 二次检索 ─────────────────────────

def eval_retrieval(cfg, out_path: Path) -> dict:
    docs = load_corpus(CORPUS)
    names = {g: [w for w in (cfg.get("keywords", {}).get(g) or [])]
             for g in ("songs", "hook_words", "show_words")}
    base = baseline_search(docs, cfg)
    base_rank = [d["doc_idx"] for d in base]
    base_set = set(base_rank)
    up = upgraded_search(docs, cfg)
    up_rank = [c["doc_idx"] for c in up["candidates"]]
    up_set = set(up_rank)

    # 同语料同相关集下的对照：基线=子串命中集；升级=闸门集 → 去重集
    recall_before = len(base_set)
    recall_gated = up["gated_union_n"]
    recall_after = len(up_set)
    new_hits = [c for c in up["candidates"] if c["doc_idx"] not in base_set]
    dup_collapsed = up["fused_n"] - len(up["candidates"])
    dropped_by_gate = sorted(base_set - set(up["gated_union"]))
    dropped_info = [{"doc_idx": j, "kind": docs[j]["kind"], "dt": docs[j]["dt"],
                     "text": (docs[j]["text"] or "")[:50]} for j in dropped_by_gate]
    by_layer = dict(Counter(c["kind"] for c in up["candidates"]))
    base_layers = dict(Counter(docs[j]["kind"] for j in base_set))

    top_base = [{"doc_idx": d["doc_idx"], "kind": d["kind"], "dt": d.get("dt", ""),
                 "likes": d["likes"], "text": (d.get("text") or "")[:60]} for d in base[:20]]
    top_up = [{"rank": i + 1, "doc_idx": c["doc_idx"], "kind": c["kind"], "dt": c["dt"],
               "likes": c["likes"], "score": c["score"], "dup_count": c.get("dup_count", 1),
               "matched_targets": c.get("matched_targets", []),
               "text": c["text"]} for i, c in enumerate(up["candidates"][:20])]

    # ⑤ 首轮簇状不成立 → 高频新词自动二次检索（≤2 轮）
    rounds = int(((cfg.get("retrieval") or {}).get("expansion") or {}).get("new_word_rounds", 2))
    cluster = cluster_check(docs, cfg)
    extra_words, round_trace = [], []
    if not cluster["cluster_found"]:
        stops = set(["的", "了", "是", "我", "你", "他", "这", "那", "啊", "吧", "吗", "好", "太",
                     "真的", "一个", "什么", "怎么", "就是", "已经", "可以", "不是", "没有"])
        pool = Counter()
        for d in docs:
            for t in toks(d.get("text") or ""):
                if len(t) >= 2 and t not in stops:
                    pool[t] += 1
        extra_words = [w for w, _ in pool.most_common(int(((cfg.get("retrieval") or {}).get(
            "expansion") or {}).get("new_word_topk", 12)))]
        for rd in range(1, rounds + 1):
            ws = extra_words[: 4 * rd]
            sub = [d for d in docs if any(w in (d.get("text") or "") for w in ws)]
            round_trace.append({"round": rd, "query": " ".join(ws), "n_hits": len(sub),
                                "new_vs_round0": len({d["doc_idx"] for d in sub} - base_set)})
    res = {
        "generated_at": datetime.now().isoformat(),
        "corpus": {"dir": str(CORPUS), "n_docs": len(docs),
                   "by_kind": dict(Counter(d["kind"] for d in docs)),
                   "n_post": sum(1 for d in docs if d["kind"] == "post"),
                   "n_comment": sum(1 for d in docs if d["kind"] == "comment")},
        "before": {"label": "升级前：单查询 + 子串命中 + 平台原序",
                   "n_recall": recall_before, "by_layer": base_layers,
                   "keywords": names, "top20": top_base},
        "after": {"label": "升级后：多变体 BM25 + bge 语义 + RRF + 相关性闸门 + 笔记层去重 + 重排",
                  "n_fused": up["fused_n"], "n_gated": recall_gated,
                  "n_recall_after_dedup": recall_after, "by_layer": by_layer,
                  "semantic_available": up["sem_ok"],
                  "dedup": {"scope": "仅在笔记层（noteId/标题 Jaccard）",
                            "threshold": ((cfg.get("retrieval") or {}).get("dedup") or {}).get("jaccard"),
                            "collapsed": dup_collapsed,
                            "merged_notes": up.get("merged_notes", []),
                            "caveat": "该阈值会合并**不同 noteId 但标题近乎相同**的笔记"
                                      "（本轮 4 条，标题都是「王晰 我要你」类泛化标题）→ "
                                      "是否算「同源转发」待人工确认；如不算，unique 应为 38 而非 34"},
                  "gate": {"per_target": up["gated_n"],
                           "note": "每目标只保留 BM25>bm25_min 的前 bm25_topn 条（防多目标 RRF 长尾稀释召回）"},
                  "top20": top_up, "trace": up["trace"]},
        "delta": {"recall_before": recall_before, "recall_after": recall_after,
                  "recall_delta": recall_after - recall_before,
                  "recall_delta_pct": round(100.0 * (recall_after - recall_before) / max(1, recall_before), 2),
                  "gate_retained": len(base_set & set(up["gated_union"])),
                  "dropped_by_gate": len(dropped_info), "dropped_by_gate_sample": dropped_info[:8],
                  "new_hits_not_in_baseline": len(new_hits),
                  "new_hits_sample": [{"doc_idx": c["doc_idx"], "kind": c["kind"],
                                       "matched_targets": c.get("matched_targets", []),
                                       "text": c["text"]} for c in new_hits[:8]],
                  "top10_overlap": len(set(base_rank[:10]) & set(up_rank[:10])),
                  "base_missed_by_up": len(base_set - up_set),
                  "note": "两处口径差必须同列：①**真实性提升**＝变体扩展/语义把同指但原措辞不含关键词的文档纳入"
                          "（见 new_hits）②**数值下降**＝相关性闸门剔除伪命中 + 笔记层去重折叠同源。"
                          "排序提升另见 top10_overlap（基线平台原序 vs 升级重排）"},
        "cluster_round1": cluster,
        "round2_auto_new_words": {"triggered": not cluster["cluster_found"],
                                  "new_words": extra_words, "trace": round_trace},
        "verdict": "",
    }
    d = res["delta"]
    if d["new_hits_not_in_baseline"] > 0:
        res["verdict"] = (f"召回：{d['recall_before']} → {d['recall_after']} 条"
                          f"（{d['recall_delta']:+d}，{d['recall_delta_pct']}%）。"
                          f"真实性提升 {d['new_hits_not_in_baseline']} 条（变体/语义新纳入，基线子串搜不到）；"
                          f"相关性闸门剔除伪命中 {d['dropped_by_gate']} 条、笔记层去重折叠 {dup_collapsed} 条同源"
                          f"（这是条数下降的原因，不是漏召回）；"
                          f"Top10 重合 {d['top10_overlap']}/10（平台原序 vs 重排，排序确有变化）")
    else:
        res["verdict"] = (f"召回无提升（{d['recall_before']} → {d['recall_after']}）："
                          "变体扩展未带来基线搜不到的新增；仅排序变化，见 top20 对照与 top10 重合")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


# ───────────────────────── 簇状判定 + 定向窗 ─────────────────────────

def cluster_check(docs, cfg):
    """簇状：cluster_hours 小时内 ≥ cluster_n_in_hours 条。按 30 分钟桶并合并滑窗。"""
    th = cfg.get("thresholds") or {}
    n_needed = int(th.get("cluster_n_in_hours", 5))
    win_h = float(th.get("cluster_hours", 6))
    times = []
    for d in docs:
        try:
            times.append(datetime.strptime(d["dt"], "%Y-%m-%d %H:%M").replace(tzinfo=CST))
        except Exception:
            continue
    times.sort()
    best, best_at = 0, ""
    for i, t0 in enumerate(times):
        c = sum(1 for t in times if timedelta(0) <= (t - t0) <= timedelta(hours=win_h))
        if c > best:
            best, best_at = c, t0.strftime("%Y-%m-%d %H:%M")
    return {"cluster_found": best >= n_needed, "max_in_window": best, "window_start": best_at,
            "need": n_needed, "window_hours": win_h}


def window_probe(cfg, win: str) -> dict:
    """定向窗：解析 "2026-10-10 20:00-24:00" → 统计发布/评论条数、簇状、单条突增。"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})\s*[-–~]\s*(\d{1,2}):(\d{2})", win.strip())
    if not m:
        return {"error": f"窗口格式应为 '2026-10-10 20:00-24:00'，收到 {win!r}"}
    day, h1, m1, h2, m2 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
    t0 = datetime.strptime(f"{day} {h1:02d}:{m1:02d}", "%Y-%m-%d %H:%M").replace(tzinfo=CST)
    t1 = (t0.replace(hour=0, minute=0) + timedelta(days=1)) if h2 >= 24 else \
        datetime.strptime(f"{day} {h2:02d}:{m2:02d}", "%Y-%m-%d %H:%M").replace(tzinfo=CST)
    docs = load_corpus(CORPUS)
    def _t(d):
        try:
            return datetime.strptime(d["dt"], "%Y-%m-%d %H:%M").replace(tzinfo=CST)
        except Exception:
            return None
    for d in docs:
        d["t"] = _t(d)
    inw, out_ = [], []
    for d in docs:
        if d["t"] is None:
            continue
        (inw if t0 <= d["t"] < t1 else out_).append(d)

    # 单条突增：liked 归一化后 > 中位×3 —— **帖与评论分两层各算中位**（量纲不同）
    ratio = float((cfg.get("thresholds") or {}).get("hot_ratio_vs_median", 3.0))
    posts_all = [d for d in docs if d["kind"] == "post"]
    cmts_all = [d for d in docs if d["kind"] == "comment"]
    post_med = med([d["likes"] for d in posts_all]) or 0
    cmt_med = med([d["likes"] for d in cmts_all]) or 0
    post_thr = round(post_med * ratio, 2) if post_med else None
    cmt_thr = round(cmt_med * ratio, 2) if cmt_med else None
    spikes_all = ([d for d in posts_all if post_med and d["likes"] > ratio * post_med] +
                  [d for d in cmts_all if cmt_med and d["likes"] > ratio * cmt_med])
    spikes_all.sort(key=lambda d: d["dt"])
    spikes_win = [d for d in spikes_all if t0 <= d["t"] < t1]

    # 30 分钟桶（锚定窗口起点，避免"23:30–24:00"跨锚点误读）+ 锚点滑窗
    n_needed = int((cfg.get("thresholds") or {}).get("cluster_n_in_hours", 5))
    bucket_min = int((cfg.get("thresholds") or {}).get("cluster_bucket_minutes", 30))
    bounds = []
    cur = t0
    while cur < t1:
        nxt = cur + timedelta(minutes=bucket_min)
        if nxt > t1:
            nxt = t1
        bounds.append((cur, nxt))
        cur = nxt
    def _bucket_rows(items):
        rows = []
        for b0, b1 in bounds:
            sel = [d for d in items if b0 <= d["t"] < b1]
            rows.append({"bucket": f"{b0:%H:%M}–{b1:%H:%M}", "n": len(sel),
                         "dt": [d["dt"] for d in sel]})
        return rows
    buckets_posts = _bucket_rows([d for d in inw if d["kind"] == "post"])
    buckets_cmts = _bucket_rows([d for d in inw if d["kind"] == "comment"])
    # 锚点滑窗（以窗内任一时间点为起点的 bucket_min 滑窗最大条数）
    times = sorted(d["t"] for d in inw)
    max_slide, slide_at, slide_items = 0, "", []
    for t0s in times:
        sel = [d for d in inw if t0s <= d["t"] < t0s + timedelta(minutes=bucket_min)]
        if len(sel) > max_slide:
            max_slide, slide_at = len(sel), f"{t0s:%H:%M}"
            slide_items = [d["dt"] for d in sel]

    # 锚点（用户记忆的热点进入时点）前后各 bucket_min 的对照
    anchor_res = None
    probe = next((w for w in (cfg.get("window_probes") or []) if w.get("hot_entry_remembered")), None)
    if probe and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", str(probe.get("hot_entry_remembered"))):
        ta = datetime.strptime(str(probe["hot_entry_remembered"]), "%Y-%m-%d %H:%M").replace(tzinfo=CST)
        before = [d for d in inw if ta - timedelta(minutes=bucket_min) <= d["t"] < ta]
        after = [d for d in inw if ta <= d["t"] < ta + timedelta(minutes=bucket_min)]
        anchor_res = {"anchor": f"{ta:%Y-%m-%d %H:%M}",
                      "before_30min": {"n": len(before), "dt": [d["dt"] for d in before]},
                      "after_30min": {"n": len(after), "dt": [d["dt"] for d in after]}}

    posts_in = [{"dt": d["dt"], "likes": d["likes"], "title": (d.get("title") or "")[:40]}
                for d in sorted(inw, key=lambda x: x["t"]) if d["kind"] == "post"]
    cmts_in = [{"dt": d["dt"], "likes": d["likes"], "level": d.get("level"),
                "text": (d.get("text") or "")[:40]} for d in sorted(inw, key=lambda x: x["t"])
               if d["kind"] == "comment"]
    maxb = max([r["n"] for r in buckets_posts + buckets_cmts], default=0)
    res = {
        "window": f"{t0:%Y-%m-%d %H:%M} – {t1:%H:%M}", "n_in_window": len(inw),
        "n_post": len(posts_in), "n_comment": len(cmts_in),
        "likes_median_posts": post_med, "likes_median_comments": cmt_med,
        "hot_ratio": ratio,
        "spike_threshold_posts": post_thr, "spike_threshold_comments": cmt_thr,
        "spikes_all_batch": [{"dt": d["dt"], "likes": d["likes"], "kind": d["kind"]} for d in spikes_all],
        "spikes_in_window": [{"dt": d["dt"], "likes": d["likes"], "kind": d["kind"]} for d in spikes_win],
        "buckets_30min_posts": buckets_posts, "buckets_30min_comments": buckets_cmts,
        "max_per_30min_any": maxb, "max_per_30min_sliding": max_slide,
        "sliding_start": slide_at, "sliding_items": slide_items,
        "anchor_probe": anchor_res,
        "cluster_need": n_needed,
        "posts_in_window": posts_in, "comments_in_window": cmts_in,
        "verdict": "",
        "discipline": "样本为 AI 摘要给的 26 条链接及其评论，非平台全量；"
                      "无平台侧曝光/推荐/榜单数据，不得据此写「上热点/爆火」。",
    }
    cluster = max_slide >= n_needed
    spike = bool(spikes_win)
    if cluster or spike:
        parts = []
        if cluster:
            parts.append("簇状（%d 分钟滑窗最大 %d 条，起 %s）" % (bucket_min, max_slide, slide_at))
        if spike:
            parts.append("单条突增（评论层 %s，帖层无）" % "＋".join(
                f"{d['dt']} {d['likes']}赞" for d in spikes_win))
        res["verdict"] = ("窗口内出现 " + "＋".join(parts) +
                          "；属样本内观测，仍需平台侧数据确认（经验性认知（非官方））")
    else:
        res["verdict"] = ("窗口内无簇状、亦无单条突增（帖 >中位×%s / 评论 >中位×%s）；"
                          "**我们的样本无法证实，需平台侧数据**——这不等于反证「没有热点」"
                          % (ratio, ratio))
    return res


def rule2(cfg) -> dict:
    """liked 归一化 + 「单条赞 > 中位×3」规则二模拟（含 10-09 / 10-10 各自是否触发）。

    口径纪律：**帖的赞与评论的赞不同量纲**（帖中位 45.5 vs 评论中位 1），
    因此分「帖子层」「评论层」两套中位与阈值，不混读。
    """
    docs = load_corpus(CORPUS)
    ratio = float((cfg.get("thresholds") or {}).get("hot_ratio_vs_median", 3.0))
    posts = [d for d in docs if d["kind"] == "post"]
    cmts = [d for d in docs if d["kind"] == "comment"]

    def layer(items, label):
        likes = [d["likes"] for d in items]
        m = med(likes)
        thr = round(m * ratio, 2) if m else None
        hits = [d for d in items if m and d["likes"] > ratio * m]
        per_day = {}
        for day in sorted({d["dt"][:10] for d in items if d["dt"]}):
            sub = [d for d in items if d["dt"][:10] == day]
            md = med([d["likes"] for d in sub])
            trig = [d for d in sub if md and d["likes"] > ratio * md]
            per_day[day] = {"n": len(sub), "median": md,
                            "threshold": (round(md * ratio, 2) if md else None),
                            "triggered": bool(trig),
                            "hits": [{"dt": d["dt"], "likes": d["likes"],
                                      "title": (d.get("title") or "")[:36]} for d in
                                     sorted(trig, key=lambda x: -x["likes"])]}
        return {"layer": label, "n": len(items), "median": m, "max": max(likes) if likes else None,
                "sum": sum(likes), "threshold": thr, "triggered": bool(hits),
                "hits": [{"dt": d["dt"], "likes": d["likes"], "kind": d["kind"],
                          "title": (d.get("title") or "")[:36], "text": (d.get("text") or "")[:30]}
                         for d in sorted(hits, key=lambda x: -x["likes"])],
                "per_day": per_day}

    out = {"hot_ratio_vs_median": ratio,
           "normalization": "likes 先过 to_int()（万/k/亿/千分位）再参与中位与比较；"
                            "原始字段为字符串（如 '1.2万'）时直接求中位会 TypeError",
           "dimension_note": "帖 vs 评论不同量纲 → 分两层各算中位与阈值，不混读",
           "posts": layer(posts, "帖子"), "comments": layer(cmts, "评论")}
    out["per_day_posts"] = out["posts"]["per_day"]
    out["note"] = ("「单条赞 > 中位×3」是**经验性认知（非官方）**的热度代理；"
                   "样本非平台全量，命中不等于上热点/爆火。")
    return out


# ───────────────────────── main ─────────────────────────

def run_dry(cfg, a):
    log(f"=== 传播监测（{'dry' if a.dry else '实跑'}｜窗 {a.win}h｜模式 {a.mode}）===")
    log("关键词组：曲名 %d｜钩子词 %d｜演出词 %d" % (
        len(cfg["keywords"]["songs"]), len(cfg["keywords"]["hook_words"]),
        len(cfg["keywords"]["show_words"])))
    acts = []
    for plat, c in (cfg.get("platforms") or {}).items():
        if not c.get("enabled"):
            continue
        st = cookie_ok(plat) if plat in ("xhs", "weibo") else "不适用"
        log(f"  {plat}：cookie 三态 = {st}")
        if st in ("失效", "被风控"):
            notify(f"⚠ {plat} cookie 需要更新", f"传播监测：{plat} 登录态 {st}；"
                   "请 F12 复制 Cookie 粘进 wb.txt/xhs.txt 并跑对应 sync 脚本")
            continue
        tool = c.get("tool")
        if plat == "xhs" and a.mode == "search" and c.get("why"):
            log(f"    ⚠ 搜索路径受限（{c['why'][:32]}…）→ 退避 + 限速后仍失败则如实记录")
        acts.append((plat, tool))
    log("限速：%.1f–%.1f s/请求｜退避基数 %ss｜最多 %d 次" % (
        cfg["rate_limit"]["sleep_min_s"], cfg["rate_limit"]["sleep_max_s"],
        cfg["rate_limit"]["backoff_base_s"], cfg["rate_limit"]["max_retries"]))
    if a.dry:
        for plat, tool in acts:
            log(f"  （dry）将调用：{tool}")
        log("  （dry）将调用：%s（评论，含二级自行分页）" % (cfg.get("comments") or {}).get("tool"))
        log("  （dry）检索升级：多变体 + BM25 + bge-small-zh + RRF + 去重 + 重排")
        log("（dry）不抓取、不写摘要、不通知")
        return 0
    if a.eval_retrieval:
        out = ARCH / "检索升级_升级前后对照_20261013.json"
        r = eval_retrieval(cfg, out)
        log(f"检索升级对照：{r['verdict']}")
        log("→ " + str(out))
        return 0
    if a.rule2:
        r = rule2(cfg)
        out = ARCH / "规则二_liked归一化_20261013.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        p, c = r["posts"], r["comments"]
        log(f"规则二（分帖/评论两层）：帖 中位 {p['median']} 阈值 {p['threshold']} 触发={p['triggered']}；"
            f"评论 中位 {c['median']} 阈值 {c['threshold']} 触发={c['triggered']}")
        log("   帖按日：10-09 触发=%s｜10-10 触发=%s" % (
            p["per_day"].get("2026-10-09", {}).get("triggered"),
            p["per_day"].get("2026-10-10", {}).get("triggered")))
        log("→ " + str(out))
        return 0
    if a.window:
        r = window_probe(cfg, a.window)
        out = ARCH / f"定向窗_{re.sub(r'[^0-9]', '', a.window)[:12]}_20261013.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"定向窗 {a.window}：窗内 {r.get('n_in_window')} 条（帖 {r.get('n_post')}/评 {r.get('n_comment')}）"
            f"｜滑窗最大 {r.get('max_per_30min_sliding')}（起 {r.get('sliding_start')}）"
            f"｜{r.get('verdict', '')[:100]}")
        log("→ " + str(out))
        return 0
    log("!! 实抓需平台侧可用性；抓取/评论走既有工具，摘要与通知见 --eval-retrieval/--rule2/--window")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--mode", default="links", choices=["links", "search"])
    ap.add_argument("--since", type=int, default=0)
    ap.add_argument("--eval-retrieval", action="store_true", help="A 六项：升级前后检索对照")
    ap.add_argument("--window", default="", help="定向窗，如 '2026-10-10 20:00-24:00'")
    ap.add_argument("--rule2", action="store_true", help="liked 归一化 + 单条赞>中位×3 模拟")
    a = ap.parse_args()
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    a.win = a.since or cfg.get("time_window_hours", 72)
    if a.eval_retrieval or a.window or a.rule2:
        a.dry = False
    return run_dry(cfg, a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
