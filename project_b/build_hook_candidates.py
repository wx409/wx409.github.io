# -*- coding: utf-8 -*-
"""P0-2 钩子抽取层：从全量语料 + 现场 talk 抽**可转述句** → data/share/hook_candidates.json

复用 `hook_miner.py` 的规则与打分（RULES / hits / score / novelty_index / hook_id / hun），
只新增一个来源：**全量文本语料** `E:\\wx\\wx_textmine_out\\corpus.jsonl`（5155 帖）
＋ **巡演 talk 逐句** `data/tour_talks_sentences.json`。

产出每条候选固定字段（与 hook_miner 对齐）：
  hook（≤25 字，事实型）｜quote（原句）｜evidence（文件+字段/时间戳，**可定位**）｜
  small_words｜audience｜score_*｜risk｜kind｜source
并**与已发内容去重**：`data/share/entries.json`（词条）＋ `data/hooks_pool.json` ＋ `data/hooks_pick.json`。

用法：python -X utf8 project_b\\build_hook_candidates.py [--min-rules 2] [--cap 60]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
sys.path.insert(0, str(SITE / "project_b"))
import hook_miner as hm                                        # noqa: E402

CORPUS = Path(r"E:\wx\wx_textmine_out\corpus.jsonl")
TALK_SENT = D / "tour_talks_sentences.json"
ENTRIES = D / "share" / "entries.json"
OUT_JSON = D / "share" / "hook_candidates.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\传播监测") / f"钩子候选_{date.today().isoformat()}.md"

SENT = re.compile(r"[^。！？!?…\n]+[。！？!?…]?")
FIRST = re.compile(r"(我|咱|自己)")
HYPE = hm.HYPE
PRIVATE = hm.PRIVATE


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def clean(s: str) -> str:
    s = re.sub(r"#([^#]{1,20})#", r"\1", str(s or ""))       # 微博话题
    s = re.sub(r"\[[^\]]{1,8}\]", "", s)                       # 表情占位
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"@[A-Za-z0-9_\u4e00-\u9fa5\-·]+", "", s)
    s = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]+", "", s)              # 语料脚注序号
    return re.sub(r"\s+", " ", s).strip()


def short_hook(sent: str, span: str, maxlen: int = 25) -> str:
    """生成 ≤25 字的短钩子：整句够短就用整句；过长则在标点处切，避免截断到数字中间。"""
    s = sent.strip(" ,.、。；;：:~ ")
    if len(s) <= maxlen:
        return s
    i = s.find(span[:6]) if span else -1
    if i > 0:
        # 从命中词往前找一个标点边界，保证是完整小句
        j = max([s.rfind(c, 0, i) for c in "，。！？,.; "] or [-1])
        s = s[j + 1:] if j >= 0 else s
    cut = s[:maxlen]
    k = max([cut.rfind(c) for c in "，。！？,.; " if cut.rfind(c) > 6] or [-1])
    if k > 0:
        cut = cut[:k]
    cut = cut.strip(" ,.、。；;：:~ ")
    return cut if len(cut) >= 8 else s[:maxlen].strip(" ,.、。；;：:~ ")


ANNOUNCE = re.compile(r"(延期|开票|退票|购票|公告|通知|售票|票务|巡演信息|演出信息|上线|发行|合作联系|商务)")


def sentence_kind(s: str, kinds: list[str]) -> bool:
    """只要「可转述」的钩子类型：冲突/自嘲/道具/数字四条里至少一条。"""
    if ANNOUNCE.search(s) and "自嘲口吻" not in kinds:
        return False
    return any(k in kinds for k in ("冲突标记", "自嘲口吻", "道具动作", "数字标记"))


def redact(s: str) -> str:
    """公开 JSON 不得含本地绝对路径（治本：写入前净化）。"""
    s = str(s or "")
    s = re.sub(r"[A-Za-z]:\\[^）)\s]*wx_textmine_out[^）)\s]*", "（文本挖掘产物目录）", s)
    s = re.sub(r"[A-Za-z]:\\[^）)\s]*wx409\.github\.io[^）)\s]*", "（仓库根）", s)
    s = re.sub(r"[A-Za-z]:\\[^）)\s]*论文素材_王晰作传[^）)\s]*", "（论文素材目录）", s)
    s = re.sub(r"[A-Za-z]:\\[^）)\s]*", "（本地路径）", s)
    return s


def published_texts() -> set[str]:
    """已发内容（词条 + 已入池 + 已勾选）的归一化文本，用于去重。"""
    out = set()
    e = load(ENTRIES) or {}
    for it in (e.get("items") or e.get("entries") or []):
        for k in ("hook", "title", "text", "headline"):
            if it.get(k):
                out.add(hm.hun(str(it[k])))
    for f in (D / "hooks_pool.json", D / "hooks_pick.json"):
        d = load(f) or {}
        for it in (d.get("hooks") or d.get("items") or []):
            if isinstance(it, dict) and it.get("hook"):
                out.add(hm.hun(str(it["hook"])))
    return {x for x in out if len(x) >= 6}


def is_dup(hook: str, published: set[str]) -> bool:
    h = hm.hun(hook)
    if len(h) < 6:
        return True
    for p in published:
        if h in p or p in h:
            return True
        # 6-gram 重叠（防换词重发）
        if len(h) >= 8 and len(p) >= 8 and any(h[i:i + 8] in p for i in range(0, len(h) - 8 + 1, 3)):
            return True
    return False


def corpus_candidates(min_rules: int, cap: int) -> list[dict]:
    out = []
    for line in CORPUS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        txt = clean(o.get("text"))
        if not txt:
            continue
        for seg in SENT.finditer(txt):
            s = seg.group(0).strip()
            if not (12 <= len(s) <= 70):
                continue
            if not FIRST.search(s):
                continue
            h = hm.hits(s)
            kinds = [k for k, v in h.items() if v]
            if len(kinds) < min_rules or not sentence_kind(s, kinds):
                continue
            span = ""
            for k in ("道具动作", "自嘲口吻", "冲突标记", "数字标记", "时间标记"):
                m = re.search(hm.RULES[k], s)
                if m:
                    span = m.group(0)
                    break
            out.append({
                "hook": short_hook(s, span), "quote": s,
                "evidence": f"E:\\wx\\wx_textmine_out\\corpus.jsonl（id={o.get('id')}｜"
                            f"date={o.get('date')}｜source={o.get('source')}｜title={str(o.get('title'))[:40]}）",
                "small_words": kinds, "audience": "泛路人 / 粉丝",
                "kind": "corpus", "source": o.get("source") or "", "date": str(o.get("date") or ""),
                "t_abs_s": None, "t_hms": "",
            })
            if len(out) >= cap * 4:
                break
        if len(out) >= cap * 4:
            break
    return out


def talk_candidates(cap: int) -> list[dict]:
    out = []
    d = load(TALK_SENT)
    rows = d if isinstance(d, list) else ((d or {}).get("sentences") or (d or {}).get("rows") or (d or {}).get("items") or [])
    for r in rows:
        if not isinstance(r, dict):
            continue
        s = clean(r.get("text") or r.get("sentence") or r.get("content"))
        if not (12 <= len(s) <= 70) or not FIRST.search(s):
            continue
        h = hm.hits(s)
        if sum(1 for v in h.values() if v) < 2:
            continue
        out.append({
            "hook": short_hook(s, ""), "quote": s,
            "evidence": f"data/tour_talks_sentences.json（date={r.get('date') or r.get('show_date') or '—'}｜"
                        f"t={r.get('start') or r.get('t_start') or '—'}｜src={str(r.get('file') or r.get('src') or '')[:40]}）",
            "small_words": [k for k, v in h.items() if v], "audience": "泛路人",
            "kind": "talk", "source": "tour_talk", "date": str(r.get("date") or r.get("show_date") or ""),
            "t_abs_s": r.get("start") or r.get("t_start"), "t_hms": "",
        })
        if len(out) >= cap * 2:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-rules", type=int, default=2)
    ap.add_argument("--cap", type=int, default=60)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    published = published_texts()
    used = hm.novelty_index()
    cands = []
    # 复用 hook_miner 既有四路（版权三段式 / talk / 评论 / 声学）
    for fn in (getattr(hm, "copyright_story_candidates", None), getattr(hm, "comment_candidates", None),
               getattr(hm, "acoustic_candidates", None)):
        if fn is None:
            continue
        try:
            cands += list(fn())
        except Exception as e:
            print(f"[warn] {fn.__name__} 失败：{e!r}"[:140])
    try:
        cands += list(hm.talk_candidates(hm.load_talk_lines()))
    except Exception as e:
        print(f"[warn] talk_candidates 失败：{e!r}"[:140])
    cands += corpus_candidates(a.min_rules, a.cap)
    cands += talk_candidates(a.cap)

    rows, dropped, seen = [], Counter(), set()
    for c in cands:
        hook = str(c.get("hook") or "").strip()
        if not hook or len(hook) > 28:
            dropped["长度"] += 1
            continue
        if any(x in hook for x in HYPE) or any(x in str(c.get("quote") or "") for x in PRIVATE):
            dropped["禁词/隐私"] += 1
            continue
        h = hm.hun(hook)
        if h in seen or any(h[:10] == x[:10] for x in seen if len(x) >= 10 and len(h) >= 10):
            dropped["池内重复"] += 1
            continue
        if is_dup(hook, published):
            dropped["与已发重复"] += 1
            continue
        seen.add(h)
        try:
            s = hm.score(c, used)
            c.update(s if isinstance(s, dict) else {})
        except Exception:
            pass
        c["hook"] = hook
        c["hook_id"] = hm.hook_id(hook, len(rows))
        c.setdefault("review_status", "candidate")
        # 钩子型标记数（冲突/自嘲/道具）——供人筛选，不参与 hook_miner 的打分口径
        sw = c.get("small_words") or []
        c["hook_markers"] = [k for k in sw if k in ("冲突标记", "自嘲口吻", "道具动作")]
        c["hook_marker_n"] = len(c["hook_markers"])
        c["why"] = "命中：" + "、".join(sw) if sw else ""
        # 原始语料噪声标记（**只标记、不改写**；与 hook_miner.noise_flags 同口径）
        try:
            _flags = hm.noise_flags(" ".join(str(c.get(k) or "") for k in ("hook", "quote", "evidence")))
        except Exception:
            _flags = []
        c["raw_noise"] = bool(_flags)
        c["raw_noise_reasons"] = _flags
        c["evidence"] = redact(c.get("evidence"))
        rows.append(c)

    # 排序：先按 hook_miner 总分，再按「钩子型标记数」（冲突/自嘲/道具优先）
    rows.sort(key=lambda x: (-(x.get("score_total") or 0), -(x.get("hook_marker_n") or 0)))
    # 来源均衡：同一 kind 最多 cap/5（至少 4），避免被单一来源淹没
    keep, per = [], Counter()
    kcap = max(4, a.cap // 5)
    for r in rows:
        k = r.get("kind") or "?"
        if per[k] >= kcap:
            continue
        per[k] += 1
        keep.append(r)
    # 若均衡后仍不足目标数，按分数补齐
    if len(keep) < min(a.cap, len(rows)):
        for r in rows:
            if r in keep:
                continue
            keep.append(r)
            if len(keep) >= a.cap:
                break
    keep = keep[:a.cap]

    res = {"schema": 1, "generated_at": date.today().isoformat(),
           "sources": {"corpus": "文本挖掘语料库 corpus.jsonl（逐帖）", "talk": "data/tour_talks_sentences.json",
                       "hook_miner": "project_b/hook_miner.py（规则与打分复用）"},
           "caliber": {"min_rules_hit": a.min_rules, "hook_max_chars": 28,
                       "dedup_against": ["data/share/entries.json", "data/hooks_pool.json", "data/hooks_pick.json"],
                       "note": "钩子必须是可核验事实；含禁词/隐私词的候选直接丢弃"},
           "counts": {"candidates_raw": len(cands), "kept": len(keep),
                      "dropped": dict(dropped), "by_kind": dict(Counter(r.get("kind") for r in keep))},
           "hooks": keep}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [f"# 钩子候选（{date.today().isoformat()}）", "",
             f"- 原始候选 {len(cands)}｜入选 {len(keep)}｜丢弃 {dict(dropped)}",
             f"- 来源构成：{dict(Counter(r.get('kind') for r in keep))}", ""]
    for i, r in enumerate(keep, 1):
        lines += [f"## {i:02d}. {r['hook']}（{r.get('kind')}｜总分 {r.get('score_total')}）",
                  f"- 原句：{r.get('quote') or '—'}",
                  f"- 出处：{r.get('evidence')}",
                  f"- 小词：{'、'.join(r.get('small_words') or []) or '—'}｜人群：{r.get('audience') or '—'}",
                  f"- 风险：{r.get('risk') or '—'}", ""]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    if not a.quiet:
        print(f"[池] {OUT_JSON} → {len(keep)} 条（原始 {len(cands)}，丢弃 {dict(dropped)}）")
        print(f"[人读] {OUT_MD}")
        print("  来源：", dict(Counter(r.get("kind") for r in keep)))
        for r in keep[:5]:
            print(f"   · [{r.get('kind')}|{r.get('score_total')}] {r['hook']}")
    return 0 if len(keep) >= 30 else 1


if __name__ == "__main__":
    sys.exit(main())
