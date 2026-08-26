# -*- coding: utf-8 -*-
"""观众评论多层面分析（论文友好）：聚合微博/小红书/B站/Bing/手动收集评论，
输出「高频主题归纳 + 独特观点 + 评价维度 + 情感倾向 + 观众画像 + 代表性格言」。

分层与省 token 设计：
- L1 统计层：全部本地规则计算（关键词频次/歌名提及/维度/情感/画像/金句），零 token；
- L2 归纳层：可选调用 DeepSeek（key 在 temp/deepseek_key.json，同生成器约定），
  一次调用完成「学术化主题归纳 + 独特观点筛选 + 论文使用建议」，输入为压缩后的统计摘要+精选评论；
  无 key 时自动降级为纯规则输出，并在报告中标注「LLM 层未启用」。
- 缓存：输入文件指纹不变则复用分析结果（省重跑）。

用法：
  python project_b/analyze_audience_comments.py --date 2026-08-23 --city 广州 [--llm] [--no-cache]
输出：
  temp/audience_analysis/<date>_<city>.json   结构化分析（机器可读，论文数据表）
  temp/audience_analysis/<date>_<city>.md     论文友好报告（人读）
"""
import argparse, json, re, sys, io, hashlib
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(r"D:\wx409.github.io")
FB = Path(r"E:\wx\私有工具\show_feedback")
XHS_CLS = ROOT / "temp" / "_xhs_classified.json"
XHS_LINKS = Path(r"E:\wx\私有工具\xhs_archive\按链接")  # fetch_xhs_links.py 按链接归档（content.txt 正文）
GZ = ROOT / "temp" / "_gz_quotes.json"
OUT_DIR = ROOT / "temp" / "audience_analysis"
KEY_FILE = ROOT / "temp" / "deepseek_key.json"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ---------- 领域词表（评价维度） ----------
DIMS = {
    "嗓音/低音": ["低音", "嗓音", "声音", "音色", "声压", "低沉", "磁性", "质感", "共鸣", "低音炮", "浑厚", "醇厚"],
    "唱功/技术": ["唱功", "气息", "稳定", "高音", "转音", "实力", "开口", "专业", "唱得", "驾驭", "声乐", "教授", "大师课"],
    "选曲/歌单": ["选曲", "歌单", "翻唱", "经典", "老歌", "金曲", "粤语", "限定", "首唱", "加演", "安可", "返场", "合唱", "合体"],
    "舞台/造型": ["舞台", "灯光", "舞美", "视觉", "造型", "西装", "服化", "布景", "话筒", "金话筒", "手麦"],
    "互动/氛围": ["互动", "聊天", "话痨", "点歌", "签售", "聊天", "氛围", "浪漫", "温柔", "沉浸", "治愈", "心动", "幸福"],
    "情怀/回忆": ["回忆", "青春", "记忆", "考古", "岁月", "老粉", "十年", "重逢", "陪伴", "一路", "年华", "变老"],
    "现场体验": ["现场", "震撼", "好听", "值回", "完美", "绝了", "上头", "惊艳", "好听", "值", "感动", "哭"],
}
POS_WORDS = ["好听", "震撼", "值", "绝", "封神", "感动", "完美", "牛", "沉浸", "惊喜", "精彩", "安可", "浪漫",
             "治愈", "值回", "难忘", "上头", "惊艳", "幸福", "好听", "喜欢", "爱", "期待", "感谢", "开心", "爽"]
NEG_WORDS = ["差", "失望", "一般", "不值", "翻车", "拉胯", "后悔", "退票", "糟糕", "敷衍", "遗憾", "可惜"]
NEW_FAN = ["第一次", "第一场", "路人", "初识", "新入坑", "第一次听", "第一场", "不懂"]
OLD_FAN = ["老粉", "十年", "多年", "重逢", "又见", "再次", "回来了", "陪伴", "一路", "变老", "年华", "考古", "回忆"]
NOISE = ["全文", "视频", "微博视频", "链接", "分享", "转发微博"]
SONGS_EXTRA = ["Autumn Leaves", "Besame Mucho", "Close to You", "Yesterday Once More", "Your Man",
               "一生守候", "让她降落", "情网", "夜色", "月半弯", "橄榄树", "女人花+水中花", "平凡又美好的晚上",
               "心动", "像雾像雨又像风", "花儿为什么这样红", "生日快乐", "再见我的爱人", "相思河畔", "珍晰",
               "小河", "神魂颠倒", "黎明前的黑暗", "云与海", "山楂树", "玫瑰", "南屏晚钟", "哭砂", "凄美地"]


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- 数据聚合 ----------
def load_feedback(date, city):
    """聚合各来源评论为统一条目列表 [{platform, text, user, url, date}]"""
    import audience_anon
    items = []
    # 兼容目录名两种日期格式：2026-08-23_广州 与 20260823_广州
    d = None
    for cand in (FB / f"{date}_{city}", FB / f"{date.replace('-', '')}_{city}"):
        if cand.exists():
            d = cand
            break
    if d is not None:
        for name in ("weibo_feedback.json", "bili_feedback.json", "bing_feedback.json"):
            p = d / name
            if p.exists():
                try:
                    blob = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                platform = {"weibo": "微博", "bili": "B站", "bing": "网页"}.get(name.split("_")[0], "网页")
                for r in blob:
                    if isinstance(r, dict) and r.get("text"):
                        items.append({"platform": platform, "text": str(r["text"]),
                                      "user": str(r.get("user", "")), "url": str(r.get("url", "")),
                                      "date": date})
        ap = d / "all_feedback.json"
        if ap.exists():
            try:
                blob = json.loads(ap.read_text(encoding="utf-8"))
            except Exception:
                blob = None
            if isinstance(blob, dict):
                pmap = {"weibo": "微博", "xhs": "小红书", "bili": "B站", "bing": "网页", "douyin": "抖音"}
                for k, lst in blob.items():
                    for r in lst or []:
                        if isinstance(r, dict) and r.get("text"):
                            items.append({"platform": pmap.get(k, k), "text": str(r["text"]),
                                          "user": str(r.get("user", "")), "url": str(r.get("url", "")),
                                          "date": date})
    # 按链接归档：fetch_xhs_links.py 下载到本地的笔记正文（title+desc），鲜活观众反馈
    if XHS_LINKS.exists():
        for d in sorted(XHS_LINKS.iterdir()):
            if not d.is_dir():
                continue
            ct = d / "content.txt"
            if not ct.exists():
                continue
            try:
                meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").exists() else {}
            except Exception:
                meta = {}
            txt = ct.read_text(encoding="utf-8", errors="ignore").strip()
            if txt:
                items.append({"platform": "小红书", "text": audience_anon.strip_nick(txt),
                              "user": str(meta.get("author", "")), "url": str(meta.get("link", "")),
                              "date": date})
    if XHS_CLS.exists():
        xd = json.loads(XHS_CLS.read_text(encoding="utf-8"))

        def _flat():
            for g in xd.get("song_groups", {}).values():  # 值是多层数组，需展开
                yield from g
            yield from xd.get("general", [])
            yield from xd.get("short", [])

        for x in _flat():
            items.append({"platform": "小红书", "text": audience_anon.strip_nick(str(x)),
                          "user": "", "url": "", "date": date})
    if GZ.exists():
        gd = json.loads(GZ.read_text(encoding="utf-8"))
        for q in gd.get("quotes", []):
            items.append({"platform": "小红书(精选)", "text": str(q.get("text", "")),
                          "user": "", "url": "", "date": date})
    return items


def dedup(items):
    seen, out = set(), []
    for it in items:
        key = re.sub(r"[\s\u200b\u3000]+", "", it["text"])[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


# ---------- L1 统计层（零 token） ----------
def analyze(items):
    n = len(items)
    plat = Counter(i["platform"] for i in items)
    dim_hits = defaultdict(list)
    for it in items:
        t = it["text"]
        for dim, kws in DIMS.items():
            for kw in kws:
                if kw in t:
                    dim_hits[dim].append(it)
                    break
    dim_count = {k: len(v) for k, v in dim_hits.items()}

    # 歌名提及（简繁归一；排除巡演主题《回》等非歌曲词）
    TRAD = {"情網": "情网", "讓": "让", "緣": "缘", "淚": "泪", "裏": "里", "與": "与",
            "過": "过", "風": "风", "聲": "声", "們": "们", "說": "说", "來": "来",
            "為": "为", "時": "时", "當": "当", "還": "还", "從": "从", "夢": "梦"}
    NON_SONG = {"回"}

    def norm_song(s):
        return "".join(TRAD.get(c, c) for c in s)

    song_hits = Counter()
    for it in items:
        t = it["text"]
        for m in re.findall(r"[《「『]([^》」』]{1,20})[》」』]", t):
            ns = norm_song(m.strip())
            if ns and ns not in NON_SONG:
                song_hits[ns] += 1
        for s in SONGS_EXTRA:
            if s in t or norm_song(s) in norm_song(t):
                song_hits[norm_song(s)] += 1
    song_top = song_hits.most_common(12)

    # 情感
    pos = neg = neu = 0
    for it in items:
        t = it["text"]
        p = sum(1 for w in POS_WORDS if w in t)
        q = sum(1 for w in NEG_WORDS if w in t)
        if p > q:
            pos += 1
        elif q > p:
            neg += 1
        else:
            neu += 1

    # 观众画像
    newf = sum(1 for it in items if any(w in it["text"] for w in NEW_FAN))
    oldf = sum(1 for it in items if any(w in it["text"] for w in OLD_FAN))

    # 主题词频（领域词之外的普通词）
    theme_kws = ["歌单", "现场", "低音", "嗓音", "选曲", "舞台", "造型", "互动", "聊天", "回忆", "翻唱",
                 "合唱", "加演", "安可", "情怀", "氛围", "粤语", "首唱", "金话筒", "大师课", "拼盘", "合作"]
    theme = Counter()
    for it in items:
        for kw in theme_kws:
            if kw in it["text"]:
                theme[kw] += 1
    theme_top = theme.most_common(10)

    # 金句候选（20-100字，含情感词，无噪音）
    VIDEO_NOISE = ["微博视频", "4K", "直拍", "专栏", "视频", "字幕", "混剪", "饭拍", "📽", "🎬"]
    gems = []
    for it in items:
        t = re.sub(r"\s+", " ", it["text"]).strip()
        t = re.sub(r"^(?:@[^：:]+[：:]\s*)", "", t).strip()
        if not (20 <= len(t) <= 100):
            continue
        if any(w in t for w in NOISE + VIDEO_NOISE):
            continue
        if any(w in t for w in ("好听", "震撼", "绝", "感动", "浪漫", "治愈", "温柔", "幸福", "心动", "回忆", "值")):
            gems.append(it)
    gems = dedup(gems)[:15]

    # 独特低频评论（观点性：无视频噪音、提及的领域词少、或文本较长）
    freq_words = Counter()
    for it in items:
        for kw in theme_kws + [s for s in SONGS_EXTRA if len(s) > 2]:
            if kw in it["text"]:
                freq_words[kw] += 1
    unique = []
    for it in items:
        t = re.sub(r"\s+", " ", it["text"]).strip()
        if any(w in t for w in VIDEO_NOISE):
            continue
        if not (25 <= len(t) <= 120):
            continue
        hits = sum(1 for kw in theme_kws if kw in t)
        rare = [kw for kw in freq_words if kw in t and freq_words[kw] <= 1]
        if hits <= 2 and (rare or len(t) >= 60):
            unique.append(it)
    unique = dedup(unique)[:10]

    # 叙事性长评（≥120 字、第一人称经历叙述，论文「个案素材」层）
    long_narr = []
    for it in items:
        t = re.sub(r"\s+", " ", it["text"]).strip()
        if len(t) < 120 or any(w in t for w in VIDEO_NOISE):
            continue
        if any(w in t for w in ("我", "我们", "第一次", "记得", "当年", "后来", "现场", "最后")):
            long_narr.append(it)
    long_narr = dedup(long_narr)[:5]

    return {
        "total": n, "platforms": dict(plat),
        "dimensions": dict(sorted(dim_count.items(), key=lambda x: -x[1])),
        "song_top": song_top, "theme_top": theme_top,
        "sentiment": {"pos": pos, "neg": neg, "neu": neu},
        "audience": {"new_fan": newf, "old_fan": oldf},
        "gems": [{"platform": i["platform"], "text": i["text"][:100]} for i in gems],
        "unique_views": [{"platform": i["platform"], "text": i["text"][:120], "url": i["url"]} for i in unique],
        "long_narratives": [{"platform": i["platform"], "text": i["text"][:400], "url": i["url"]} for i in long_narr],
    }


# ---------- L2 归纳层（LLM 可选，省 token） ----------
def llm_summarize(stats):
    try:
        key = json.loads(KEY_FILE.read_text(encoding="utf-8")).get("api_key", "").strip()
    except Exception:
        key = ""
    if not key:
        return None
    import urllib.request
    top_songs = "、".join(f"{s}({c})" for s, c in stats["song_top"][:8])
    dims = "；".join(f"{k}:{v}" for k, v in stats["dimensions"].items())
    gems = "\n".join(f"- {g['text']}" for g in stats["gems"][:12])
    uniq = "\n".join(f"- {u['text']}" for u in stats["unique_views"][:8])
    prompt = (
        "你是音乐社会学/流行文化研究助手。以下是中国男低音歌手王晰「回」巡回音乐会某站的观众评论分析统计"
        f"（共{stats['total']}条：{'、'.join(f'{k}{v}条' for k, v in stats['platforms'].items())}）。\n"
        f"讨论最多的歌曲：{top_songs}\n评价维度分布：{dims}\n"
        f"高频代表评论：\n{gems}\n独特评论：\n{uniq}\n"
        "请输出 JSON（不要其他文字）：{\n"
        ' "themes": [{"name": "主题名", "summary": "30-60字学术化归纳，说明观众如何评价该主题"}], 最多5个,\n'
        ' "unique_insights": [{"view": "独特观点一句话", "why": "为什么独特/有何研究价值"}], 最多4条,\n'
        ' "paper_notes": [{"topic": "可写入论文的论点", "evidence": "对应证据简述"}] 最多4条\n}'
    )
    body = json.dumps({"model": DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.3, "response_format": {"type": "json_object"}}).encode("utf-8")
    req = urllib.request.Request(DEEPSEEK_API, data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        content = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    return json.loads(content)


# ---------- 报告 ----------
def render_md(date, city, stats, llm):
    L = []
    L.append(f"# 王晰「回」巡回音乐会·{city}站（{date}）观众评价分析")
    L.append("")
    L.append(f"> 数据：共 **{stats['total']} 条**评论（{'、'.join(f'{k} {v}条' for k, v in stats['platforms'].items())}）；"
             "采集自公开平台，昵称已匿名化，仅供学术研究。")
    L.append("")
    L.append("## 摘要")
    if llm:
        themes = "；".join(f"{t['name']}（{t['summary']}）" for t in llm.get("themes", [])[:3])
        L.append(f"- **高频主题**：{themes}")
    else:
        L.append("- **高频主题**：见下方统计（LLM 归纳层未启用，可配置 temp/deepseek_key.json 后加 --llm 重跑）")
    dims_top = "、".join(f"{k}（{v}条）" for k, v in list(stats["dimensions"].items())[:5])
    L.append(f"- **评价维度**：{dims_top}")
    sp = stats["sentiment"]
    L.append(f"- **情感倾向**：正面 {sp['pos']} / 中性 {sp['neu']} / 负面 {sp['neg']}"
             f"（正面占比 {sp['pos'] / max(stats['total'], 1) * 100:.0f}%）")
    L.append("")
    L.append("## 1. 数据概况")
    L.append("")
    L.append("| 平台 | 条数 |")
    L.append("|---|---|")
    for k, v in sorted(stats["platforms"].items(), key=lambda x: -x[1]):
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## 2. 高频主题（说得最多的）")
    L.append("")
    L.append("| 主题关键词 | 提及 |")
    L.append("|---|---|")
    for k, v in stats["theme_top"]:
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## 3. 被讨论最多的歌曲")
    L.append("")
    L.append("| 歌曲 | 提及 |")
    L.append("|---|---|")
    for s, c in stats["song_top"]:
        L.append(f"| 《{s}》 | {c} |")
    L.append("")
    L.append("## 4. 评价维度分布")
    L.append("")
    L.append("| 维度 | 评论数 |")
    L.append("|---|---|")
    for k, v in stats["dimensions"].items():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## 5. 观众构成画像")
    L.append("")
    L.append(f"- 新粉/路人信号（「第一次」「第一场」等）：{stats['audience']['new_fan']} 条")
    L.append(f"- 老粉/情怀信号（「重逢」「变老」「陪伴」等）：{stats['audience']['old_fan']} 条")
    L.append("")
    L.append("## 6. 代表性格言（可直接引用）")
    L.append("")
    for g in stats["gems"][:10]:
        L.append(f"- 「{g['text']}」（{g['platform']}，匿名化）")
    L.append("")
    L.append("## 7. 独特观点（说得比较独特的）")
    L.append("")
    for u in stats["unique_views"][:8]:
        extra = f"（{u['platform']}）" if u["platform"] else ""
        L.append(f"- {u['text']} {extra}")
    L.append("")
    L.append("## 7b. 叙事性长评（个案素材）")
    L.append("")
    for n in stats["long_narratives"][:5]:
        extra = f"（{n['platform']}）" if n["platform"] else ""
        L.append(f"- {n['text']} {extra}")
    L.append("")
    L.append("## 8. 论文使用建议")
    if llm:
        for n in llm.get("paper_notes", []):
            L.append(f"- **{n.get('topic', '')}**：{n.get('evidence', '')}")
        if llm.get("unique_insights"):
            L.append("")
            L.append("### 独特观点（LLM 分析）")
            for u in llm.get("unique_insights", []):
                L.append(f"- {u.get('view', '')}（价值：{u.get('why', '')}）")
    else:
        L.append("- LLM 归纳层未启用。配置 `temp/deepseek_key.json`（{\"api_key\": \"...\"}）后加 `--llm` 重跑，"
                 "可获得学术化主题归纳、独特观点筛选与论文论点建议。")
    L.append("")
    L.append("## 附录：方法与数据清单")
    L.append("")
    L.append("- 分析口径：公开平台评论聚合，本地规则统计（维度/情感/画像词表），LLM 层仅做归纳措辞，数据未人工修饰。")
    L.append("- 数据来源：微博/B站/Bing 收集（`E:\\wx\\私有工具\\show_feedback`）、小红书分类（`temp/_xhs_classified.json`）、")
    L.append("  小红书按链接归档正文（`E:\\wx\\私有工具\\xhs_archive\\按链接`，fetch_xhs_links.py 下载）、")
    L.append("  精选摘录（`temp/_gz_quotes.json`）。")
    L.append("- 匿名化：昵称不展示；微博条目保留可回源链接（公开内容）。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="观众评论多层面分析（论文友好）")
    ap.add_argument("--date", default="2026-08-23")
    ap.add_argument("--city", default="广州")
    ap.add_argument("--llm", action="store_true", help="启用 DeepSeek 归纳层")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    items = dedup(load_feedback(args.date, args.city))
    print(f"聚合评论 {len(items)} 条（去重后）")
    if not items:
        print("无评论数据，退出"); return

    fingerprint = hashlib.md5(
        json.dumps([{"p": i["platform"], "t": i["text"]} for i in items], ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:12]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_out = OUT_DIR / f"{args.date}_{args.city}.json"
    md_out = OUT_DIR / f"{args.date}_{args.city}.md"

    if not args.no_cache and json_out.exists():
        cached = json.loads(json_out.read_text(encoding="utf-8"))
        if cached.get("fingerprint") == fingerprint and (not args.llm or cached.get("llm")):
            print(f"缓存命中，复用: {json_out}")
            print(md_out.read_text(encoding="utf-8")[:300])
            return

    stats = analyze(items)
    llm = llm_summarize(stats) if args.llm else None
    if args.llm and not llm:
        print("LLM 层未启用（temp/deepseek_key.json 缺失或无 key），降级为规则统计")
    stats["fingerprint"] = fingerprint
    payload = {"fingerprint": fingerprint, "date": args.date, "city": args.city,
               "stats": stats, "llm": llm}
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    md_out.write_text(render_md(args.date, args.city, stats, llm), encoding="utf-8")
    print(f"[OK] 结构化分析 -> {json_out}")
    print(f"[OK] 论文报告     -> {md_out}")


if __name__ == "__main__":
    main()
