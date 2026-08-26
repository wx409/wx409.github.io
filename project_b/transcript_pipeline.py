# -*- coding: utf-8 -*-
"""音视频转写对接管道：版权预筛 + 加工JSON校验 + 待审核清单 + 触发合并

框架（王晰 GEO 档案站·音视频转写对接）：
  转写输出(3.1) → DeepSeek 加工(3.2，prompts/transcript_postprocess.md) → 本管道：
    ① 版权预筛（source_url/type → copyright_level + 公开范围 + 信源级别）
    ② 格式校验 + 生成待审核清单（Markdown 表格，人工打勾）
    ③ 审核通过的条目 → merge_transcripts.py 合并到数据层 → 站点重建

用法：
  python transcript_pipeline.py --precheck <加工JSON...>      # 版权预筛+校验+生成候选
  python transcript_pipeline.py --review                       # 列出/刷新审核清单
  python transcript_pipeline.py --merge                        # 合并清单中 [x] 通过的条目
  python transcript_pipeline.py --demo                         # 生成样例加工JSON（测试用）
"""
import argparse, io, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
REVIEW_DIR = ROOT / "temp" / "transcripts_review"
CANDIDATES = REVIEW_DIR / "candidates.json"   # 待审条目汇总（管道内部状态）
REVIEW_MD = REVIEW_DIR / "review.md"          # 人工审核清单（打勾后 --merge 读取）

CITY_PINYIN = {
    "重庆": "chongqing", "北京": "beijing", "上海": "shanghai", "广州": "guangzhou",
    "深圳": "shenzhen", "南京": "nanjing", "杭州": "hangzhou", "武汉": "wuhan",
    "长沙": "changsha", "成都": "chengdu", "南昌": "nanchang", "三亚": "sanya",
    "郑州": "zhengzhou", "昆明": "kunming", "南宁": "nanning", "延边": "yanbian",
    "澳门": "macao", "苏州": "suzhou", "乌鲁木齐": "wulumuqi", "伊宁": "yining",
    "舟山": "zhoushan", "庐山": "lushan", "莫斯科": "moscow", "河南": "henan",
}


# ============ 交付物3：版权预筛 ============
def classify_copyright(source_url, source_type):
    """按「转写文本公开程度 ≤ 原音频公开程度」红线，判定版权级别/公开范围/信源级别。"""
    url = str(source_url or "").lower().strip()
    st = str(source_type or "").lower().strip()
    # 红线：付费/会员内容，不转写或仅记录存在性
    if any(k in url for k in ("bangumi", "/vip", "movie.bilibili", "paid")):
        return {"copyright_level": "internal_only", "publish": False, "source_level": "-",
                "rule": "付费/会员内容：仅记录存在性，不公开"}
    # 无公开 URL（本地录音/已删视频）
    if not (url.startswith("http") or url.startswith("bv")):
        return {"copyright_level": "internal_only", "publish": False, "source_level": "single",
                "rule": "本地录音/无公开来源：仅本地存档，用于内部交叉验证"}
    # 官方直拍/采访/工作室
    if st in ("official", "studio", "interview"):
        return {"copyright_level": "public", "publish": True, "source_level": "official",
                "rule": "官方直拍/采访：全文转写，网站公开"}
    # 官方媒体报道
    if st == "media":
        return {"copyright_level": "public", "publish": True, "source_level": "official",
                "rule": "官方媒体报道：全文转写，标注来源，网站公开"}
    # 授权/公开饭拍
    if st == "fan_recording":
        return {"copyright_level": "authorized", "publish": "summary", "source_level": "verified",
                "rule": "授权/公开饭拍：仅公开摘要+关键引语，标注BV号，可复核"}
    # 兜底
    return {"copyright_level": "internal_only", "publish": False, "source_level": "single",
            "rule": "来源不明：仅本地存档"}


# ============ 格式校验 ============
def validate_processed(proc):
    """校验加工JSON（3.2），返回 (ok, errors)"""
    errs = []
    if not isinstance(proc, dict):
        return False, ["顶层不是对象"]
    for key in ("quotes", "faqs", "timeline_events", "conflicts"):
        if key not in proc:
            errs.append(f"缺少 {key}[]")
        elif not isinstance(proc.get(key), list):
            errs.append(f"{key} 不是数组")
    q = proc.get("quotes") or []
    for i, it in enumerate(q):
        if not it.get("text") or not it.get("source_transcript_id"):
            errs.append(f"quotes[{i}] 缺 text/source_transcript_id")
    return not errs, errs


def pinyin(city):
    return CITY_PINYIN.get(city, "")


# ============ 审核清单 ============
def build_review_md(entries):
    """entries: [{path, meta, copyright, stats}] → 审核清单 Markdown"""
    L = ["# 音视频转写 · 待审核清单", "",
         f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 人工逐行打勾（`[ ]`→`[x]`）后运行 `--merge`", "",
         "| 编号 | 来源 | 日期/城市 | 版权建议 | 公开范围 | 信源 | 金句/FAQ/时间轴/冲突 | 通过 |",
         "|---|---|---|---|---|---|---|---|"]
    for i, e in enumerate(entries, 1):
        m = e["meta"]
        cp = e["copyright"]
        st = e["stats"]
        L.append(f"| T{i:03d} | {e['path']} | {m.get('date','')} {m.get('venue','')} | "
                 f"{cp['copyright_level']} | {cp['publish']} | {cp['source_level']} | "
                 f"{st['quotes']}/{st['faqs']}/{st['timeline']}/{st['conflicts']} | [ ] |")
    L += ["", "## 审核口径", "- `[x]` = 通过 → `--merge` 时并入数据层；`[ ]` = 未通过/需修改 → 跳过。",
          "- 版权红线：转写文本公开程度 ≤ 原音频公开程度；`internal_only` 条目默认不合并到公开数据层。",
          "- 金句/FAQ 发布前建议人工复核原句；冲突结论以转写证据为准、措辞克制。", ""]
    return "\n".join(L)


def collect_candidates(files):
    """读加工JSON列表 → 版权预筛 + 校验 → 汇总候选"""
    entries = []
    for fp in files:
        p = Path(fp)
        if not p.exists():
            print(f"!! 文件不存在: {p}"); continue
        try:
            proc = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"!! 解析失败 {p}: {e}"); continue
        ok, errs = validate_processed(proc)
        if not ok:
            print(f"!! 格式问题 {p}: {'; '.join(errs)}"); continue
        meta = proc.get("meta") or {}
        cp = classify_copyright(meta.get("source_url", ""), meta.get("source_type", ""))
        stats = {"quotes": len(proc.get("quotes") or []), "faqs": len(proc.get("faqs") or []),
                 "timeline": len(proc.get("timeline_events") or []), "conflicts": len(proc.get("conflicts") or [])}
        entries.append({"path": str(p), "meta": meta, "copyright": cp, "stats": stats, "processed": proc})
        print(f"[候选] {p.name} | {cp['copyright_level']} / {cp['publish']} / {cp['source_level']} | "
              f"金句{stats['quotes']} FAQ{stats['faqs']} 时间轴{stats['timeline']} 冲突{stats['conflicts']}")
    return entries


# ============ 规则金句提取器（零 token，直接可用） ============
# 不调 LLM：长度 + 价值词 + 边界句（开场/谢幕）启发式，产出候选 quotes。
# DeepSeek 加工层仍可作为增强（更精准的语义金句/FAQ/冲突），两者可接力。
FLOW_WORDS = ["接下来", "下一首", "请大家", "让我介绍", "掌声鼓励", "给大家带来"]
GREETING = ("大家好", "谢谢大家", "欢迎", "谢谢你们来")
VALUE_WORDS = {
    "warm": ["谢谢", "感谢", "爱", "幸福", "温暖", "祝福", "开心", "喜欢", "珍惜"],
    "sad": ["哭", "泪", "难过", "舍不得", "伤感", "哽咽"],
    "humorous": ["哈哈", "好笑", "开玩笑", "逗你"],
    "passionate": ["永远", "一直", "坚持", "热爱", "梦想", "音乐", "唱歌", "约定"],
    "proud": ["骄傲", "自豪", "荣幸", "第一次"],
}
BOUNDARY_FIRST_N, BOUNDARY_LAST_N = 2, 2
MIN_LEN, MAX_LEN = 12, 150


def extract_quotes_rules(transcript):
    """零 LLM 规则金句提取：输入句级列表（{start,end,text} 或 {text}），输出候选 quotes[]。
    兼容 DSH 格式：start 可为秒数或 HH:MM:SS 字符串（提取只依赖文本与顺序位置）。"""
    quotes = []
    n = len(transcript)
    for i, seg in enumerate(transcript):
        text = (seg.get("text") or "").strip()
        if not (MIN_LEN <= len(text) <= MAX_LEN):
            continue
        # 短寒暄排除（"大家好，我是王晰"这类）
        if len(text) <= 16 and any(w in text for w in GREETING):
            continue
        # 流程句排除（报幕/过渡）
        if any(w in text for w in FLOW_WORDS) and len(text) < 40:
            continue
        senti, hit = "neutral", False
        for s, words in VALUE_WORDS.items():
            if any(w in text for w in words):
                senti, hit = s, True
        is_first = i < BOUNDARY_FIRST_N
        is_last = i >= n - BOUNDARY_LAST_N
        # 门槛：开场/谢幕句需 ≥25 字或有价值词；串场句必须有价值词
        if is_first or is_last:
            if len(text) < 25 and not hit:
                continue
        elif not hit:
            continue
        scene = "开场" if is_first else ("谢幕" if is_last else "串场")
        quotes.append({
            "text": text, "scene": scene, "sentiment": senti,
            "source_transcript_id": f"T{i + 1:03d}", "verified": False,
        })
    return quotes


def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="音视频转写对接管道")
    ap.add_argument("--precheck", nargs="*", default=None, help="加工JSON文件列表，做版权预筛+校验+生成清单")
    ap.add_argument("--review", action="store_true", help="查看/刷新审核清单")
    ap.add_argument("--merge", action="store_true", help="合并审核清单中 [x] 通过的条目（调 merge_transcripts）")
    ap.add_argument("--ingest-txt", nargs="*", default=None,
                    help="把清洗后的 talk 文本(.txt) 解析为 DSH 格式 JSON（段落实体；配合 --date/--venue/--tour/--source-url）")
    ap.add_argument("--date", default="", help="ingest 时写入 meta.date")
    ap.add_argument("--venue", default="", help="ingest 时写入 meta.venue")
    ap.add_argument("--tour", default="", help="ingest 时写入 meta.tour")
    ap.add_argument("--source-url", default="", help="ingest 时写入 meta.source_url（有公开URL时版权可判为可发布）")
    ap.add_argument("--source-type", default="fan_recording", help="ingest 时写入 meta.source_type")
    ap.add_argument("--extract-quotes", nargs="*", default=None,
                    help="规则金句提取（零token）：输入原始转写JSON（transcript[] 或 segments[]），输出候选 quotes 加工JSON")
    ap.add_argument("--curate-import", nargs="*", default=None,
                    help="策展JSON转加工候选：segments[].anchor→quotes，segments→timeline_events（prompts/speech_curation.md 产物）")
    ap.add_argument("--demo", action="store_true", help="生成样例加工JSON（测试用）")
    args = ap.parse_args()

    if args.ingest_txt is not None:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        from transcript_fix import apply_fixes, count_fixes
        for fp in args.ingest_txt:
            p = Path(fp)
            if not p.exists():
                print(f"!! 文件不存在: {p}"); continue
            lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()]
            meta = {"file": p.name, "engine": "whisper", "date": args.date or "",
                    "venue": args.venue or "", "tour": args.tour or "",
                    "source_type": args.source_type or "fan_recording"}
            if args.source_url:
                meta["source_url"] = args.source_url
            segments = []
            n_fix = 0
            for ln in lines:
                if not ln or ln.startswith("#"):
                    m = re.match(r"^#\s*engine=(\S+)", ln)
                    if m:
                        meta["engine"] = m.group(1)
                    continue
                fixed_n, _pairs = count_fixes(ln, None)
                n_fix += fixed_n
                segments.append({"start": "", "end": "", "text": apply_fixes(ln), "speaker": "王晰"})
            out = {"meta": meta, "segments": segments}
            out_path = REVIEW_DIR / f"{p.stem}.json"
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[ingest] {p.name}: {len(segments)} 段（ASR纠错 {n_fix} 处）-> {out_path}（engine={meta['engine']}）")
        return

    if args.extract_quotes is not None:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        for fp in args.extract_quotes:
            p = Path(fp)
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"!! 读取失败 {p}: {e}"); continue
            meta = raw.get("meta") or {}
            qs = extract_quotes_rules(raw.get("transcript") or raw.get("segments") or [])
            out = {"meta": meta, "quotes": qs, "faqs": [], "timeline_events": [], "conflicts": []}
            out_path = REVIEW_DIR / f"{p.stem}_quotes.json"
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[金句] {p.name}: 规则提取 {len(qs)} 条候选 -> {out_path}")
            print(f"       （可直接 --precheck {out_path} 进审核；DeepSeek 层可再增强 FAQ/时间轴/冲突）")
        return

    if args.curate_import is not None:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        for fp in args.curate_import:
            p = Path(fp)
            try:
                cu = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"!! 读取失败 {p}: {e}"); continue
            meta = cu.get("meta") or {}
            date = str(meta.get("date") or "")
            segs = cu.get("segments") or []
            quotes, timeline = [], []
            for j, seg in enumerate(segs, 1):
                anchor = (seg.get("anchor") or "").strip()
                if anchor:
                    quotes.append({"text": anchor, "scene": seg.get("scene", "串场"),
                                   "sentiment": "neutral", "source_transcript_id": f"C{j:03d}", "verified": False})
                st = seg.get("start") or ""
                if date and st:
                    timeline.append({"time": f"{date}T{st}", "type": "speech",
                                     "label": f"{seg.get('scene','致辞')}：{anchor[:18] if anchor else ''}",
                                     "quote_ref": f"C{j:03d}"})
            out = {"meta": meta, "quotes": quotes, "faqs": [], "timeline_events": timeline, "conflicts": []}
            out_path = REVIEW_DIR / f"{p.stem}_curated.json"
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[策展] {p.name}: 锚点金句 {len(quotes)} 条 / 时间轴 {len(timeline)} 条 -> {out_path}")
            print(f"       （可直接 --precheck {out_path} 进审核；若 meta.date 缺失请先在策展JSON补 meta.date）")
        return

    if args.demo:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        demo = {
            "meta": {"source_url": "BV1nzjM6iEtS", "source_type": "fan_recording",
                     "tour": "六巡回", "date": "2026-06-13", "venue": "重庆施光南大剧院", "segment": "中场致辞"},
            "quotes": [{"text": "第四次来到重庆，第一次开启六巡，无数次与你们重逢。",
                        "scene": "中场致辞", "sentiment": "warm", "source_transcript_id": "T001", "verified": False}],
            "faqs": [{"question": "王晰六巡重庆站中场致辞说了什么？",
                      "answer": "第四次来到重庆，第一次开启六巡……（转写 T001，2026-06-13）",
                      "tour_stop": "2026-06-13-chongqing"}],
            "timeline_events": [{"time": "2026-06-13T21:23:45", "type": "speech",
                                 "label": "中场致辞：重逢与庆幸", "quote_ref": "T001"}],
            "conflicts": [],
        }
        demo_path = REVIEW_DIR / "demo_processed.json"
        demo_path.write_text(json.dumps(demo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[demo] 样例加工JSON -> {demo_path}")
        return

    if args.precheck is not None:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        entries = collect_candidates(args.precheck)
        CANDIDATES.write_text(json.dumps(
            [{"path": e["path"], "meta": e["meta"], "copyright": e["copyright"], "stats": e["stats"]}
             for e in entries], ensure_ascii=False, indent=1), encoding="utf-8")
        REVIEW_MD.write_text(build_review_md(entries), encoding="utf-8")
        print(f"[OK] 候选 {len(entries)} 条 -> 审核清单 {REVIEW_MD}")
        return

    if args.review:
        if not REVIEW_MD.exists():
            print("无审核清单，先 --precheck"); return
        print(REVIEW_MD.read_text(encoding="utf-8"))
        return

    if args.merge:
        if not REVIEW_MD.exists() or not CANDIDATES.exists():
            print("无审核清单，先 --precheck"); return
        cands = json.loads(CANDIDATES.read_text(encoding="utf-8"))
        md = REVIEW_MD.read_text(encoding="utf-8")
        # 解析清单：T001..Tnnn 行的 [x]
        approved = set()
        for m in re.finditer(r"\| T(\d{3}) \|[^\n]*\| \[x\] \|", md):
            approved.add(int(m.group(1)))
        if not approved:
            print("清单中无 [x] 通过的条目（请先人工打勾）"); return
        sel = [c for i, c in enumerate(cands, 1) if i in approved and c["copyright"]["publish"]]
        internal = [c for i, c in enumerate(cands, 1) if i in approved and not c["copyright"]["publish"]]
        if internal:
            print(f"跳过 {len(internal)} 条 internal_only（不公开，仅本地存档）")
        if not sel:
            print("无可合并的公开条目"); return
        # 调 merge_transcripts
        import subprocess, sys as _sys
        files = [c["path"] for c in sel]
        r = subprocess.run([_sys.executable, "-X", "utf8",
                            str(ROOT / "project_b" / "merge_transcripts.py"), *files],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout)
        if r.stderr.strip():
            print("[stderr]", r.stderr.strip()[-500:])
        return

    ap.print_help()


if __name__ == "__main__":
    main()
