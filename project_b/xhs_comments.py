# -*- coding: utf-8 -*-
"""抓取小红书笔记评论区（一级 + 二级，二级自行分页），并可分类统计。

用法：
  python -X utf8 xhs_comments.py --file "E:\\...\\我要你.txt" --out "E:\\...\\我要你20261010"
  python -X utf8 xhs_comments.py --file ... --out ... --test 1        # 只跑前 1 条（试探可用性）
  python -X utf8 xhs_comments.py --file ... --out ... --inner 0       # 不抓二级（仅一级）
  python -X utf8 xhs_comments.py --file ... --out ... --inner-all     # 所有有二级的一级评论都抓（默认只抓前 3 条）
  python -X utf8 xhs_comments.py --file ... --out ... --categorize    # 追加写 categories.json（分类统计）

修复记录（2026-10-13）：
  1) **二级评论分页**：SDK 的 get_note_all_inner_comment 有内部 bug（依赖传入 comment 自带的
     sub_comment_cursor / sub_comments 键，缺失即提前 break，导致 sub_comments 键缺失）→
     本脚本改为**自行分页**调用 get_note_inner_comment，直到 has_more=False，逐条落 raw 的 inner 段。
  2) **互动量归一化**：小红书互动量字段可能是 int 或 "1.2万"/"2k"/"1,234"/"" 等字符串，
     一律先过 to_int()（万/亿/k/K 归一化 + 去逗号）再参与比较与统计，避免 TypeError / 单位错读。

纪律：作者昵称一律匿名化（anon_id），raw 保留昵称仅供本地溯源与去重，不入 git、不上页面。
失败逐条记录 ok/msg（含 code 300011 账号异常），不伪造任何评论内容。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, r"E:\wx\私有工具\Spider_XHS-master")
sys.stdout.reconfigure(encoding="utf-8")
from xhs_utils.xhs_pc import XHSPcAuth  # noqa: E402
from apis.xhs_pc_apis import XHS_Apis  # noqa: E402

COOKIE_FILE = Path(r"E:\wx\私有工具\xhs_proxy\xhs_cookie.json")
XHS_TXT = Path(r"E:\wx\index_records\xhs.txt")
SITE = Path(r"D:\wx409.github.io")
CFG = SITE / "data" / "propagation_watch.json"


def load_cookie():
    try:
        t = XHS_TXT.read_text(encoding="utf-8").strip()
        if t:
            return t
    except Exception:
        pass
    return json.loads(COOKIE_FILE.read_text(encoding="utf-8")).get("cookie", "")


def anon(nick: str) -> str:
    """昵称匿名化：稳定短哈希（同人去重仍可用）"""
    if not nick:
        return "anon-?"
    return "anon-" + sha1(nick.encode("utf-8")).hexdigest()[:8]


def to_int(v) -> int:
    """互动量归一化：int / '1.2万' / '2k' / '1,234' / '' → int（无法解析返回 0）。"""
    if v is None:
        return 0
    if isinstance(v, bool):
        return int(v)
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


def parse_link(link):
    m = re.search(r"/(?:explore|discovery/item)/([0-9a-f]{24})", link)
    if not m:
        return None
    q = parse_qs(urlparse(link).query)
    return {"note_id": m.group(1), "xsec_token": (q.get("xsec_token") or [""])[0]}


def parse_title(link):
    m = re.search(r"【(.+?)】", link)
    return m.group(1) if m else ""


def lead_num(link):
    m = re.match(r"^\s*(\d+)", link)
    return int(m.group(1)) if m else None


def slim(c):
    u = c.get("user_info") or {}
    nick = u.get("nickname", "") or ""
    return {"id": c.get("id"), "content": c.get("content", ""),
            "like_count": to_int(c.get("like_count", 0)),
            "like_raw": c.get("like_count", 0),
            "create_time": c.get("create_time"),
            "ip_location": c.get("ip_location", ""),
            "nickname": nick, "anon": anon(nick),
            "sub_comment_count": to_int(c.get("sub_comment_count", 0)),
            "sub_comment_has_more": c.get("sub_comment_has_more", False)}


def fetch_inner(api, note_id, root_id, xsec_token, sleep_s=1.0, cap=200):
    """二级评论自行分页（不经 SDK 的 get_note_all_inner_comment）。

    返回 (subs, pages, err)。subs 为 slim 后的子评论列表，按分页顺序原样保留。
    """
    subs, cursor, pages, err = [], "", 0, ""
    cmt = {"note_id": note_id, "id": root_id}
    while pages < 20:
        ok, msg, res = api.get_note_inner_comment(cmt, cursor, xsec_token)
        if not ok or not isinstance(res, dict):
            err = str(msg)[:150]
            break
        data = res.get("data") or {}
        batch = data.get("comments") or []
        subs.extend(slim(x) for x in batch)
        pages += 1
        nxt = data.get("cursor")
        more = bool(data.get("has_more"))
        if not more or nxt in (None, "", cursor) or not batch:
            break
        cursor = str(nxt)
        time.sleep(sleep_s)
        if len(subs) >= cap:
            break
    return subs, pages, err


def categorize(comments, cats):
    """按**详表**词表分类；一条评论可命中多类。返回 {类: [命中评论索引]}"""
    hits = {k: [] for k in cats}
    for i, c in enumerate(comments):
        t = (c.get("content") or "").lower()
        for k, words in cats.items():
            if any(w.lower() in t for w in words):
                hits[k].append(i)
    return hits


def rollup_stat(detail_hits, rollup_map):
    """简表降级为**归并层**：把详表命中归并到 6 大类。

    **0 命中的类保留槽位并标 n=0 / hit=false，不删**——否则"没讨论"会被误读成"没这一类"。
    """
    out = {}
    for name, members in rollup_map.items():
        idxs = sorted({i for m in members for i in detail_hits.get(m, [])})
        out[name] = {"n": len(idxs), "hit": bool(idxs), "members": members,
                     "member_counts": {m: len(detail_hits.get(m, [])) for m in members}}
    return out


def load_cat_tables():
    """从配置读详表 / 归并表（改词只改 data/propagation_watch.json）。"""
    try:
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        c = (cfg.get("comments") or {}).get("categories") or {}
        return c.get("detail") or {}, c.get("rollup") or {}, c.get("detail_priority") or []
    except Exception:
        return {}, {}, []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test", type=int, default=0, help="只跑前 N 条（试探可用性）")
    ap.add_argument("--inner", type=int, default=3,
                    help="每条笔记抓点赞最高的前 N 条一级评论的子评论；0=不抓")
    ap.add_argument("--inner-all", action="store_true", help="忽略 --inner，抓所有有二级的一级评论")
    ap.add_argument("--max-out", type=int, default=0, help="每条笔记一级评论上限；0=全部")
    ap.add_argument("--categorize", action="store_true", help="追加写 categories.json（分类统计）")
    a = ap.parse_args()

    lines = [l.strip() for l in Path(a.file).read_text(encoding="utf-8").splitlines() if l.strip()]
    seen, notes = set(), []
    for ln in lines:
        p = parse_link(ln)
        if not p:
            print("无法解析：", ln[:60])
            continue
        if p["note_id"] in seen:
            continue
        seen.add(p["note_id"])
        notes.append({**p, "title_from_list": parse_title(ln),
                      "lead_num_from_ai": lead_num(ln), "link": ln})
    if a.test:
        notes = notes[: a.test]
    print(f"待抓评论笔记 {len(notes)} 条（去重后；文件行 {len(lines)}）")

    cookie = load_cookie()
    auth = XHSPcAuth.from_cookie(cookie)
    api = XHS_Apis(auth).bootstrap()

    out_dir = Path(a.out)
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    results, allc = [], []
    for i, n in enumerate(notes, 1):
        rec = {"note_id": n["note_id"], "xsec_token": n["xsec_token"],
               "title_from_list": n["title_from_list"], "lead_num_from_ai": n["lead_num_from_ai"],
               "ok": False, "msg": "", "n_out": 0, "n_in": 0, "comments": [], "inner": []}
        try:
            ok, msg, lst = api.get_note_all_out_comment(n["note_id"], n["xsec_token"])
            rec["ok"], rec["msg"] = bool(ok), str(msg)[:200]
            if ok and lst:
                lst = sorted(lst, key=lambda c: -to_int(c.get("like_count")))
                if a.max_out:
                    lst = lst[: a.max_out]
                rec["comments"] = [slim(c) for c in lst]
                rec["n_out"] = len(lst)
        except Exception as e:
            rec["msg"] = f"异常: {repr(e)[:150]}"
        print(f"[{i}/{len(notes)}] {n['note_id'][:10]} ok={rec['ok']} "
              f"msg={rec['msg'][:40]} 一级={rec['n_out']}")

        # 二级评论：自行分页（修复点 1）
        if rec["ok"] and a.inner and rec["comments"]:
            cands = rec["comments"] if a.inner_all else rec["comments"][: a.inner]
            for c in cands:
                if not c.get("sub_comment_count"):
                    continue
                subs, pages, err = fetch_inner(api, n["note_id"], c["id"], n["xsec_token"])
                item = {"root_id": c["id"], "root_anon": c["anon"],
                        "declared": c["sub_comment_count"], "n": len(subs),
                        "pages": pages, "subs": subs}
                if err:
                    item["error"] = err
                if len(subs) != c["sub_comment_count"]:
                    item["mismatch"] = True
                rec["inner"].append(item)
                rec["n_in"] += len(subs)
                print(f"      二级 root={c['id'][:8]} 声明={c['sub_comment_count']} "
                      f"实取={len(subs)} 页={pages}" + (f" err={err[:30]}" if err else ""))
        (out_dir / "raw" / f"comments_{n['note_id']}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        results.append({k: v for k, v in rec.items() if k not in ("comments", "inner")})
        allc.append(rec)
        time.sleep(1.5)

    out = {"crawled_at": datetime.now().isoformat(), "n_notes": len(allc),
           "n_ok": sum(1 for r in allc if r["ok"]),
           "n_out_total": sum(r["n_out"] for r in allc),
           "n_in_total": sum(r["n_in"] for r in allc),
           "declared_in_total": sum(c["sub_comment_count"] for r in allc for c in r["comments"]),
           "method_note": "二级评论自行分页（get_note_inner_comment 循环至 has_more=False）；"
                          "互动量一律过 to_int() 归一化（万/k/亿/逗号）",
           "anon_note": "nickname 仅本地溯源；对外/统计用 anon 短哈希",
           "notes": allc}
    (out_dir / "comments.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    if a.categorize:
        cats, rollup, pri = load_cat_tables()
        flat = []
        for r in allc:
            for c in r["comments"]:
                flat.append({**c, "note_id": r["note_id"], "level": 1})
            for it in r["inner"]:
                for s in it["subs"]:
                    flat.append({**s, "note_id": r["note_id"], "level": 2,
                                 "root_id": it["root_id"]})
        hits = categorize(flat, cats)
        # detail 栏：详表多命中 + 主类（按 detail_priority 取第一个命中）
        stat = {k: {"n": len(v), "hit": bool(v),
                    "examples": [flat[i]["content"][:40] for i in v[:3]]}
                for k, v in hits.items()}
        order = pri or list(cats.keys())
        per_item = {i: [k for k, idxs in hits.items() if i in idxs] for i in range(len(flat))}
        main = {k: 0 for k in cats}
        for i in range(len(flat)):
            chosen = next((p for p in order if p in per_item[i]),
                          "纯赞美/无明确触发点" if "纯赞美/无明确触发点" in cats else None)
            if chosen:
                main[chosen] = main.get(chosen, 0) + 1
        # rollup 栏：归并层（0 命中类保留 n=0 槽位）
        roll = rollup_stat(hits, rollup)
        for name, v in roll.items():
            idxs = sorted({i for m in v["members"] for i in hits.get(m, [])})
            v["examples"] = [flat[i]["content"][:40] for i in idxs[:3]]
        (out_dir / "categories.json").write_text(json.dumps({
            "generated_at": datetime.now().isoformat(),
            "scope": "一级 + 二级（展平）", "n_total": len(flat),
            "n_level1": sum(1 for x in flat if x["level"] == 1),
            "n_level2": sum(1 for x in flat if x["level"] == 2),
            "detail_label": "detail", "rollup_label": "rollup",
            "detail": {"rule_source": "data/propagation_watch.json comments.categories.detail"
                                       "（关键词逐字取自 temp/v3_分析.py CATS）",
                       "multi_hit": stat, "main_class": main},
            "rollup": {"rule_source": "data/propagation_watch.json comments.categories.rollup",
                       "stat": roll,
                       "note": "0 命中的类保留槽位并标 n=0，不删"},
            "flat": flat}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("detail（展平 %d 条：一级 %d / 二级 %d）：%s" % (
            len(flat), sum(1 for x in flat if x["level"] == 1),
            sum(1 for x in flat if x["level"] == 2),
            "｜".join(f"{k} {v['n']}" for k, v in stat.items())))
        print("rollup：%s" % "｜".join(
            f"{k} {v['n']}" + ("" if v["hit"] else "（n=0，保留槽位）") for k, v in roll.items()))

    print(f"\n完成：成功 {out['n_ok']}/{len(allc)}；一级评论合计 {out['n_out_total']}，"
          f"二级实取 {out['n_in_total']}（平台声明 {out['declared_in_total']}）")
    print("→", out_dir / "comments.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
