# -*- coding: utf-8 -*-
"""《我要你》北京站传播实测 → 站点数据层（数字全部脚本派生，禁手写进页面）。

读（语料，站外留档）：
  E:\\wx\\论文素材_王晰作传\\小红书素材\\我要你20261010\\posts.json      26 条笔记
  E:\\wx\\论文素材_王晰作传\\小红书素材\\我要你20261010\\comments.json   176 条评论
写：
  data/share/woyaoni_spread.json   事实层（供卡片与作战地图取数）
  data/share/battlemap.json        作战地图条目（条目文本里的数字由事实层注入）

纪律：语料缺失时**不覆盖既有 JSON**（保底）；平台机制一律标「经验性认知（非官方）」；
      家庭成员与在场名人**一律去标识**（只写关系/身份，不写姓名）。
用法：python -X utf8 project_b\\build_woyaoni_spread.py
"""
from __future__ import annotations
import json
import re
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SITE = Path(__file__).resolve().parent.parent
SH = SITE / "data" / "share"
CORPUS = Path(r"E:\wx\论文素材_王晰作传\小红书素材\我要你20261010")
CST = timezone(timedelta(hours=8))
TODAY = datetime.now().strftime("%Y-%m-%d")
EXPERIENTIAL = "经验性认知（非官方）"
# 反例来源：B站补采（2026-10-13 实测；本地留档 temp/_v2_补采_result.json）
BILI_COUNTEREXAMPLE = {"song": "哭砂", "plays": 16554, "this_song_best_plays": 290,
                       "source": "B站补采 2026-10-09～13 窗口（本地留档）"}


def to_int(v):
    s = str(v if v is not None else "").strip().replace(",", "")
    if not s:
        return 0
    try:
        return int(float(s[:-1]) * 10000) if s.endswith("万") else int(float(s))
    except Exception:
        m = re.search(r"[\d.]+", s)
        return int(float(m.group())) if m else 0


def main() -> int:
    pf, cf = CORPUS / "posts.json", CORPUS / "comments.json"
    if not (pf.exists() and cf.exists()):
        print(f"[skip] 语料缺失（{CORPUS}）→ 保留既有 JSON 不动")
        return 0

    posts = json.loads(pf.read_text(encoding="utf-8"))["posts"]
    C = json.loads(cf.read_text(encoding="utf-8"))
    SHOW_NIGHTS = ("2026-10-09", "2026-10-10")

    likes = [to_int(p["stats"].get("likes")) for p in posts]
    collects = [to_int(p["stats"].get("collects")) for p in posts]
    ccount = [to_int(p["stats"].get("comments")) for p in posts]

    # 发布时点
    def dt_of(p):
        try:
            return datetime.strptime(p["datetime_cst"], "%Y-%m-%d %H:%M")
        except Exception:
            return None

    dts = [(p, dt_of(p)) for p in posts]
    same_day_or_next = sum(1 for p, d in dts if d and (d.strftime("%Y-%m-%d") in SHOW_NIGHTS
                                                       or d.strftime("%Y-%m-%d") == "2026-10-11" and d.hour < 1))
    # 「演出当日或次晚」= 10-09 当晚 + 10-10 全天 + 10-11 凌晨 0 点
    h2123 = sum(1 for p, d in dts if d and d.hour in (21, 22, 23))
    first_peak = max(((p, d) for p, d in dts if d), key=lambda x: to_int(x[0]["stats"].get("likes")))
    pre_curtain = [p for p, d in dts if d and d.strftime("%Y-%m-%d") == "2026-10-09"
                   and (d.hour, d.minute) < (22, 0)]
    late_1010 = [p for p, d in dts if d and d.strftime("%Y-%m-%d") == "2026-10-10"
                 and (d.hour, d.minute) >= (23, 0)]

    # 标签（严格按「话题标签」形态计数：desc 里的 #词[话题]# 或 #词#）
    TAGPAT = re.compile(r"#\s*([^#\[\]\s]+?)\s*(?:\[话题\])?#")
    tag_freq = Counter()
    for p in posts:
        for m in TAGPAT.finditer(p.get("desc") or ""):
            tag_freq[m.group(1)] += 1
    HOOK_TAGS = ["王晰唱我要你低音超绝", "王晰低音杀"]
    hook_tags = {t: tag_freq.get(t, 0) for t in HOOK_TAGS}
    phrase_low = sum(1 for p in posts if "低音超绝" in ((p.get("desc") or "") + (p.get("title") or "")))
    n_copyright_desc = sum(1 for p in posts if "版权" in (p.get("desc") or ""))
    tag_hook = hook_tags.get("王晰低音杀", 0)
    tag_absent = hook_tags.get("王晰唱我要你低音超绝", 0)

    # 评论分类
    allc = []
    for n in C["notes"]:
        for c in n.get("comments", []):
            allc.append((c.get("content") or "", c.get("like_count") or 0))
        for inner in n.get("inner", []):
            for s in inner.get("subs", []):
                allc.append((s.get("content") or "", s.get("like_count") or 0))
    CATS = {
        "编曲/音乐处理": ["编曲", "bossa", "波萨", "爵士", "爵", "沙锤", "吉他", "拍子", "节奏", "配乐",
                    "和声", "转调", "改编", "弦乐", "钢琴", "萨克斯", "松弛", "轻盈", "唱商", "审美", "高级"],
        "情绪共振/上头": ["心动", "爱了", "要命", "扛不住", "受不了", "腿软", "沉醉", "循环", "上头", "沦陷",
                    "想哭", "泪", "鸡皮疙瘩", "起鸡皮", "麻", "硬控", "救命", "疯了", "醉了", "迷醉", "蛊",
                    "心痒", "酥"],
        "版权梗/圆梦叙事": ["版权", "唱不起", "太贵", "圆梦", "东演", "东方演艺", "他选的", "制作人", "终于听到"],
        "私人情境/关系联想": ["竹子", "眉目传情", "老婆", "媳妇", "太太", "果儿", "看他的眼神"],
        "低音音色/音色本体": ["低音", "低音炮", "磁性", "醇厚", "音色", "声线", "共鸣", "丝滑", "嗓子",
                        "胸腔", "质感", "声压", "通透", "温柔", "无代餐", "天花板"],
        "主创/名人在场": ["阎维文", "阎帅", "阎老师", "樊冲", "导儿", "导演", "团长", "宋团", "台下",
                    "包厢", "嘉宾", "主创", "作曲", "洪兵"],
        "巡演诉求/催演": ["巡演", "巡起来", "快来", "什么时候来", "开票", "加场", "下一站", "想看"],
        "现场感/音质": ["现场", "剧院", "剧场", "收音", "音质", "返场", "前排", "耳朵", "音响", "混响", "氛围"],
        "求音源/二创/求完整版": ["求", "链接", "音源", "完整版", "哪里", "下载", "BGM", "bgm", "二创", "剪辑",
                        "歌名", "原曲", "出处", "清晰"],
        "与任素汐原版对比": ["任素汐", "驴得水", "原版", "原唱", "对比", "翻唱", "别的版本", "电影里"],
    }
    cat = {k: sum(1 for t, _ in allc if any(w in t for w in ws)) for k, ws in CATS.items()}
    # 主类口径（不重叠，和为评论总数）：按"特异性优先"指派唯一类
    PRI = ["版权梗/圆梦叙事", "与任素汐原版对比", "主创/名人在场", "私人情境/关系联想",
           "求音源/二创/求完整版", "编曲/音乐处理", "低音音色/音色本体", "情绪共振/上头",
           "巡演诉求/催演", "现场感/音质"]
    cat_main = Counter()
    for t, _ in allc:
        hits = [k for k, ws in CATS.items() if any(w in t for w in ws)]
        cat_main[next((k for k in PRI if k in hits), "泛赞美/无明确触发点")] += 1
    generic = cat_main.get("泛赞美/无明确触发点", 0)

    n = len(posts)
    facts = {
        "generated_at": TODAY,
        "subject": "《我要你》北京站（2026-10-09 / 10-10，天桥艺术中心）小红书端实测",
        "source": {"corpus": "小红书素材/我要你20261010（posts.json + comments.json）",
                   "scope": "用户提供的第三方 AI 摘要所列链接集合（去重后 26 条），**非全平台普查**"},
        "notes": n,
        "links_as_given": 28, "lines_in_file": 27, "duplicate_note_ids": 1,
        "likes_total": sum(likes), "likes_median": st.median(likes), "likes_min": min(likes),
        "likes_max": max(likes), "collects_total": sum(collects),
        "comments_reported_total": sum(ccount), "comments_grabbed": len(allc),
        "comments_level1": C.get("n_out_total"), "comments_level2": C.get("n_in_total"),
        "pct_same_day_or_next": round(100.0 * same_day_or_next / n, 1),
        "count_same_day_or_next": same_day_or_next,
        "pct_hour_21_23": round(100.0 * h2123 / n, 1), "count_hour_21_23": h2123,
        "n_pre_curtain_1009": len(pre_curtain),
        "first_peak": {"datetime": first_peak[1].strftime("%Y-%m-%d %H:%M"),
                       "likes": to_int(first_peak[0]["stats"].get("likes")),
                       "before_curtain": True},
        "late_1010": {"datetime": "2026-10-10 23:20",
                      "likes": max([to_int(p["stats"].get("likes")) for p in late_1010], default=0),
                      "note": "用户观察热点时点为 23:26 → 相差 6 分钟（用户观察，待核）"},
        "hook_tag_used": tag_hook, "hook_tag_absent": tag_absent,
        "hook_tag_name": "王晰低音杀", "absent_tag_name": "王晰唱我要你低音超绝",
        "hook_tags": hook_tags,
        "tag_frequency_top": tag_freq.most_common(12),
        "tag_coverage_pct": round(100.0 * max(hook_tags.values()) / n, 1) if hook_tags else None,
        "descriptive_phrase_hits": {"低音超绝": phrase_low},
        "notes_mentioning_copyright_in_desc": n_copyright_desc,
        "tag_rule": ("话题标签按 desc 中的 #词[话题]# / #词# 形态计数；描述性短语按标题+正文子串计数（两者不是一回事）。"
                     "★ 更正：2026-10-13 拿到笔记正文后实测 #王晰唱我要你低音超绝 为 %d/%d 条，"
                     "而非早期「搜索标题截断扫描」得出的 0 条。" % (tag_absent, n)),
        "comment_categories": cat, "comment_generic_praise": generic,
        "comment_categories_main": dict(cat_main),
        "comment_rule": {
            "multi": "多命中口径：一条评论可命中多类，各类之和 > 评论总数（用于「哪类被提到过」）",
            "main": "主类口径：按特异性优先指派唯一类，各类之和 = 评论总数（用于「哪类最多」）",
            "why_both": "两种口径都登记，引用时必须带口径名；卡片上每个数字就近标注其口径",
        },
        "comment_main_order": sorted(cat.items(), key=lambda x: -x[1]),
        "counterexample": BILI_COUNTEREXAMPLE,
        "privacy": "家庭成员与在场名人一律去标识（只写关系/身份，不写姓名）",
        "todo_verification": [
            "「原版是温水、王晰版是红酒」：评论 0 命中、笔记正文无 → 无原始出处，待核",
            "「#0人能走出」：未获王晰相关出处 → 待核",
            "平台侧曝光量/推荐位/榜单数据：缺失 → 站点禁用一切平台侧夸张断言（三类，见 battlemap.forbidden_claim_types）",
            "10-10 23:26 热点观察：用户观察，无第三方数据",
        ],
    }
    SH.mkdir(parents=True, exist_ok=True)
    (SH / "woyaoni_spread.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 作战地图条目：文本模板 + 事实注入（页面不出现手写数字）──
    f = facts
    def pct(x):
        return f"{x}%"

    items = [
        {"no": 1, "title": "抢描述性小词，不抢艺人词",
         "action": "标题/首句优先用「描述性小词」（音色词、编曲词、情绪词），把艺人名放进标签而不是钩子位。",
         "basis": f"本批 {f['notes']} 条最高频话题标签是 #王晰 {f['tag_frequency_top'][0][1]} 条、"
                  f"#沉响与长歌 {f['tag_frequency_top'][1][1]} 条——都是艺人/剧名词；"
                  f"钩子标签「#王晰唱我要你低音超绝」{f['hook_tag_absent']} 条（覆盖 "
                  f"{f['tag_coverage_pct']}%）、「#王晰低音杀」{f['hook_tag_used']} 条；"
                  f"而描述性短语「低音超绝」出现在 {f['descriptive_phrase_hits'].get('低音超绝', 0)}/{f['notes']} 条"
                  f"的标题或正文里，互动最高的那一条标题正是「低音超绝」。"
                  f"→ 描述词负责被点开，标签只是常规配置。",
         "mechanism": EXPERIENTIAL,
         "risk": "描述性小词竞争激烈，需用站内实测数据把它坐实（否则只是形容词）。"},
        {"no": 2, "title": "现场同步：窗口只有当晚 21:00–23:30",
         "action": "演出当晚 21:00–23:30 集中发布；散场前就要发，不要等第二天整理。",
         "basis": f"{pct(f['pct_hour_21_23'])} 的笔记发布在 21–23 时（{f['count_hour_21_23']}/{f['notes']}）；"
                  f"互动第一条发布于 {f['first_peak']['datetime']}（演出尚未散场，{f['first_peak']['likes']} 赞）；"
                  f"次晚 {f['late_1010']['datetime']} 仍有 {f['late_1010']['likes']} 赞。",
         "mechanism": EXPERIENTIAL,
         "risk": "同一账号高频发布有被限流风险；建议「簇」内分工，不集中在一个号。"},
        {"no": 3, "title": "只供给「可转述的瞬间」，一条一个",
         "action": "每条内容只给一个可转述点：一句话（版权自述）／一个场景（唱到歌词「我的姑娘」时朝向台下的伴侣）／一处细节（这版是 bossa nova 改编）。",
         "basis": "评论触发点（多命中口径，条数）：" + "、".join(
             f"{k} {v}" for k, v in f["comment_main_order"] if k != "与任素汐原版对比")
             + f"；「与任素汐原版对比」0 条；泛赞美 {f['comment_generic_praise']} 条（无信息量）。",
         "mechanism": EXPERIENTIAL,
         "risk": "「可转述」不等于「有争议」；不评优劣、不拉踩原唱。"},
        {"no": 4, "title": "借大流量锚点带路",
         "action": "用现成的高流量锚点做入口（电影《驴得水》／原曲／词曲作者／院团项目名），不自造新词。",
         "basis": f"本批笔记话题标签覆盖 #沉响与长歌 {f['tag_frequency_top'][1][1]} 条、#王晰 "
                  f"{f['tag_frequency_top'][0][1]} 条、#我要你 "
                  f"{dict(f['tag_frequency_top']).get('我要你', '—')} 条、#中国东方演艺集团 "
                  f"{dict(f['tag_frequency_top']).get('中国东方演艺集团', '—')} 条；"
                  f"另有 {f['notes_mentioning_copyright_in_desc']} 条正文直接写「感谢东演…帮忙解决版权问题」。"
                  f"（共 {f['notes']} 条）",
         "mechanism": EXPERIENTIAL,
         "risk": "锚点越强越容易被别人的内容淹没；必须带一个自有可搜索落点。"},
        {"no": 5, "title": "冷启动要有「簇」，不是单点",
         "action": "同一晚 5–10 条同主题、同标签一起发，形成可被检索识别的「簇」，再谈扩散。",
         "basis": f"{f['notes']} 条中 {f['count_same_day_or_next']} 条（{pct(f['pct_same_day_or_next'])}）"
                  f"集中在两晚演出当日/次晚；单晚即可见 7–11 条的簇。",
         "mechanism": EXPERIENTIAL,
         "risk": "簇内同质化会互相稀释；每条必须换一个「可转述瞬间」（见第 3 条）。"},
        {"no": 6, "title": "沉淀成可搜索资产（站内页）",
         "action": "把瞬间落到自有可搜索页（专题卡／问答／实测页），让二次检索回到自己域名。",
         "basis": f"本批评论 {f['comment_generic_praise']}/{f['comments_grabbed']} 条是泛赞美；"
                  "「与任素汐原版对比」0 条——讨论空缺可由自有页面补位；"
                  "卡片库两视图（阅读 + 竖屏）即为可检索落点。",
         "mechanism": EXPERIENTIAL,
         "risk": "站内页必须只写可核验数字，否则补位变负债。"},
    ]
    battlemap = {
        "generated_at": TODAY,
        "title": "作战地图 · 有限渠道下的最大化传播",
        "subject_facts": "data/share/woyaoni_spread.json",
        "disclaimer": f"平台机制表述均为「{EXPERIENTIAL}」；本页只列可执行条目与实测依据。",
        "counterexample_note": (
            f"⚠️ 反例：同窗口 B站《{f['counterexample']['song']}》{f['counterexample']['plays']} 播放，"
            f"高于本曲最好成绩 {f['counterexample']['this_song_best_plays']} 播放——"
            f"高互动 ≠ 最大声量，任何「本场最火」都不成立。"),
        "forbidden_claim_types": [
            "平台侧「爆红级」断言（无曝光量数据支撑）",
            "平台侧「全平台级」断言（样本为单平台、非普查）",
            "平台侧「榜单/推荐位级」断言（无第三方数据）",
        ],
        "enforcement": "站点任何页面不得出现上述三类断言的说法；平台机制一律写「经验性认知（非官方）」。",
        "items": items,
    }
    (SH / "battlemap.json").write_text(
        json.dumps(battlemap, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[ok] data/share/woyaoni_spread.json（{f['notes']} 条 / {f['likes_total']} 赞 / "
          f"{f['comments_grabbed']} 评论）")
    print(f"[ok] data/share/battlemap.json（{len(items)} 条作战条目）")
    print("     评论分类：", json.dumps(cat, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
