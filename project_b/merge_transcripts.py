# -*- coding: utf-8 -*-
"""转写加工JSON → 数据资产层合并（交付物2：数据合并脚本）

合并目标（全部幂等去重）：
  data/live_repos.json        → 新增 type:"transcript" 记录（关联原视频URL）
  data/quotes.json            → 金句墙数据源（自动候选，verified=false，待人工审核）
  data/timeline.json          → 分钟级现场叙事事件（type:"speech"）
  data/qa_bank.json           → FAQ（category: 现场发言）
  data/tour/<date>-<city>.json → 单场演出事件簇（transcripts/quotes/faqs/timeline_events）

用法：
  python merge_transcripts.py <加工JSON...> [--city 城市] [--raw 原始转写JSON...]
    --city  覆盖城市（默认从 venue 猜测，供单场簇文件名/拼音）
    --raw   原始转写JSON（3.1格式），归档 transcript 全文到单场簇

红线：只合并 copyright 已判为可公开的条目（由 transcript_pipeline --merge 把关）。
"""
import argparse, io, json, re, sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(r"D:\wx409.github.io")
LIVE_REPOS = ROOT / "data" / "live_repos.json"
QUOTES = ROOT / "data" / "quotes.json"
TIMELINE = ROOT / "data" / "timeline.json"
QA_BANK = ROOT / "data" / "qa_bank.json"
TOUR_DIR = ROOT / "data" / "tour"

CITY_PINYIN = {
    "重庆": "chongqing", "北京": "beijing", "上海": "shanghai", "广州": "guangzhou",
    "深圳": "shenzhen", "南京": "nanjing", "杭州": "hangzhou", "武汉": "wuhan",
    "长沙": "changsha", "成都": "chengdu", "南昌": "nanchang", "三亚": "sanya",
    "郑州": "zhengzhou", "昆明": "kunming", "南宁": "nanning", "延边": "yanbian",
    "澳门": "macao", "苏州": "suzhou", "乌鲁木齐": "wulumuqi", "伊宁": "yining",
    "舟山": "zhoushan", "庐山": "lushan", "莫斯科": "moscow", "河南": "henan",
}


def load_json(path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def guess_city(venue, tour_stops):
    """从 venue 或 faqs 的 tour_stop 猜测城市；失败返回 ''"""
    v = str(venue or "")
    for c in CITY_PINYIN:
        if c in v:
            return c
    for ts in tour_stops:
        m = re.search(r"-\d{4}-\d{2}-\d{2}-([a-z]+)$", ts)
        if m:
            for c, py in CITY_PINYIN.items():
                if py == m.group(1):
                    return c
    return ""


def merge_one(proc, city, raw_transcripts):
    """合并单个加工JSON，返回统计 dict"""
    meta = proc.get("meta") or {}
    date = str(meta.get("date") or "")
    venue = str(meta.get("venue") or "")
    url = str(meta.get("source_url") or "")
    src_type = str(meta.get("source_type") or "")
    if not date:
        print("!! meta.date 缺失，跳过"); return None
    city = city or guess_city(venue, [f.get("tour_stop", "") for f in proc.get("faqs") or []])
    pinyin = CITY_PINYIN.get(city, "")
    stat = {"quotes": 0, "faqs": 0, "timeline": 0, "repo": 0, "tour": 0}

    # ---- 1) live_repos.json：transcript 记录 ----
    lr = load_json(LIVE_REPOS, {"repos": {}})
    lst = lr.setdefault("repos", {}).setdefault(date, [])
    if url and not any(r.get("url") == url and r.get("type") == "transcript" for r in lst):
        lst.append({"type": "transcript", "title": f"语音转写：{meta.get('segment') or '全场'}（{src_type}）",
                    "platform": "转写", "url": url, "level": "verified",
                    "note": f"ASR转写·待人工审核·{date}"})
        stat["repo"] += 1
    save_json(LIVE_REPOS, lr)

    # ---- 2) quotes.json：金句墙 ----
    qs = load_json(QUOTES, {"quotes": []})
    qlist = qs.setdefault("quotes", [])
    exist_q = {(q.get("source_transcript_id"), q.get("text")) for q in qlist}
    for it in proc.get("quotes") or []:
        key = (it.get("source_transcript_id", ""), it.get("text", ""))
        if key in exist_q or not it.get("text"):
            continue
        qlist.append({"text": it["text"], "scene": it.get("scene", ""), "sentiment": it.get("sentiment", ""),
                      "source_transcript_id": it.get("source_transcript_id", ""),
                      "verified": False, "date": date, "city": city, "source_url": url})
        exist_q.add(key)
        stat["quotes"] += 1
    save_json(QUOTES, qs)

    # ---- 3) timeline.json：分钟级现场叙事 ----
    tl = load_json(TIMELINE, [])
    exist_t = {(t.get("date"), t.get("title")) for t in tl}
    for ev in proc.get("timeline_events") or []:
        title = ev.get("label", "")
        key = (date, title)
        if key in exist_t or not title:
            continue
        tl.append({"date": date, "type": ev.get("type", "speech"), "title": title,
                   "source": f"语音转写 {url or meta.get('segment','')}", "stage": "现场"})
        exist_t.add(key)
        stat["timeline"] += 1
    save_json(TIMELINE, tl)

    # ---- 4) qa_bank.json：FAQ（仅新增时才写入，避免无变化重写导致格式diff） ----
    qb = load_json(QA_BANK, {"meta": {}, "items": []})
    items = qb.setdefault("items", [])
    exist_qid = {q.get("id") for q in items}
    exist_qn = {q.get("question") for q in items}
    n = len([i for i in items if str(i.get("id", "")).startswith("t_")])
    for fq in proc.get("faqs") or []:
        question = fq.get("question", "")
        if not question or question in exist_qn:
            continue
        n += 1
        items.append({"id": f"t_{n:03d}", "question": question, "aliases": [question],
                      "category": "现场发言", "keywords": [question[:10]],
                      "answer": fq.get("answer", ""),
                      "sources": [f"语音转写 {url or date}"],
                      "verified": "待审核", "confidence": "ASR转写候选"})
        exist_qid.add(f"t_{n:03d}")
        exist_qn.add(question)
        stat["faqs"] += 1
    if stat["faqs"]:
        qb.setdefault("meta", {})["count"] = len(items)
        save_json(QA_BANK, qb)

    # ---- 5) data/tour/<date>-<city>.json：单场事件簇 ----
    if pinyin:
        tour_file = TOUR_DIR / f"{date}-{pinyin}.json"
        cluster = load_json(tour_file, {"meta": {}, "quotes": [], "faqs": [], "timeline_events": [], "transcripts": []})
        cluster["meta"] = {"date": date, "city": city, "venue": venue, "tour": meta.get("tour", ""),
                           "source_url": url, "source_type": src_type,
                           "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        cq = {(q.get("source_transcript_id"), q.get("text")) for q in cluster["quotes"]}
        for it in proc.get("quotes") or []:
            if (it.get("source_transcript_id", ""), it.get("text", "")) not in cq and it.get("text"):
                cluster["quotes"].append({k: it.get(k) for k in ("text", "scene", "sentiment", "source_transcript_id", "verified")})
                cq.add((it.get("source_transcript_id", ""), it.get("text", "")))
                stat["tour"] += 1
        for fq in proc.get("faqs") or []:
            if not any(x.get("question") == fq.get("question") for x in cluster["faqs"]):
                cluster["faqs"].append(fq)
        for ev in proc.get("timeline_events") or []:
            if not any(x.get("label") == ev.get("label") for x in cluster["timeline_events"]):
                cluster["timeline_events"].append(ev)
        # 原始转写全文归档（可选）
        for raw in raw_transcripts:
            rm = raw.get("meta") or {}
            if str(rm.get("date", "")) == date and url == str(rm.get("source_url", "")):
                if not any(t.get("source_url") == url for t in cluster["transcripts"]):
                    cluster["transcripts"].append({"source_url": url, "segment": rm.get("segment", ""),
                                                   "engine": rm.get("engine", "faster-whisper"),
                                                   "items": raw.get("transcript", [])})
        save_json(tour_file, cluster)

    return stat


def main():
    ap = argparse.ArgumentParser(description="转写加工JSON → 数据资产层合并")
    ap.add_argument("files", nargs="*", help="加工JSON文件（3.2格式）")
    ap.add_argument("--city", default="", help="城市（默认从 venue/faqs 猜测）")
    ap.add_argument("--raw", nargs="*", default=[], help="原始转写JSON（3.1格式，归档全文到单场簇）")
    args = ap.parse_args()
    if not args.files:
        ap.print_help(); return

    raws = []
    for rp in args.raw:
        try:
            raws.append(json.loads(Path(rp).read_text(encoding="utf-8")))
        except Exception as e:
            print(f"!! 原始转写读取失败 {rp}: {e}")

    total = {"quotes": 0, "faqs": 0, "timeline": 0, "repo": 0, "tour": 0}
    for fp in args.files:
        try:
            proc = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"!! 解析失败 {fp}: {e}"); continue
        st = merge_one(proc, args.city, raws)
        if st:
            for k in total:
                total[k] += st[k]
            print(f"[合并] {Path(fp).name}: 金句+{st['quotes']} FAQ+{st['faqs']} 时间轴+{st['timeline']} "
                  f"repo+{st['repo']} 单场簇+{st['tour']}")
    print(f"[OK] 累计：金句+{total['quotes']} FAQ+{total['faqs']} 时间轴+{total['timeline']} "
          f"repo+{total['repo']} 单场簇+{total['tour']}")


if __name__ == "__main__":
    main()
