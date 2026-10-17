# -*- coding: utf-8 -*-
"""build_copy_pipeline.py —— 「一键成稿」流水线 v2（**人味优先**，预览用，不自动发布）

设计原则（2026-10-17 用户要求）：
  1. **人味标尺来自真语料**：读 `data/share/copy_style.json`（由 copy_style_audit.py 从
     小红书 26 条笔记 + 121 条可读评论统计），生成时按 `constraints` **硬约束**；
  2. **反 AI 味硬规则**（写死在 ANTIPATTERNS / BANNED，不是靠自觉）：
     禁句式（不仅…而且/值得一提的是/首先其次最后/综上所述/让我们/在…的过程中/三段式排比/每段以「他」开头）、
     禁词（炸裂/绝了/天花板/孤本/无人能及/全网/谁懂啊/真的会谢 + 既有禁词表）、
     短句优先（允许不完整句、允许一句独立成行）、**一条最多一个数字**、**留 1–3 处〔你来补：…〕**；
  3. 每份成稿头部标：**用途 / 预计发布时机 / 必须修改的 1–3 处**；
  4. 产出「改前（机器腔）/ 改后（人味）」对照，并说明改了哪几处，便于一眼看出差别；
  5. **只预览**：JSON + 站点片段 + 使用说明（md 与站内区），发布前必须手动确认。

输入：data/hooks_pick.json、data/share/entries.json、data/share/conclusion_copy.json、
      data/text_profile.json、data/share/copy_style.json、data/performance_attribution.json
输出：data/share/copy_pipeline.json、data/share/rendered/copy_pipeline.html、
      E:\\wx\\论文素材_王晰作传\\传播监测\\使用说明_四件套.md

用法：python -X utf8 project_b\\build_copy_pipeline.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
OUT_JSON = D / "share" / "copy_pipeline.json"
OUT_HTML = D / "share" / "rendered" / "copy_pipeline.html"
USAGE_MD = Path(r"E:\wx\论文素材_王晰作传\传播监测\使用说明_四件套.md")

# ── 反 AI 味：禁句式与禁词（命中即重写，并在自检里列出）──
ANTIPATTERNS = [
    (r"不仅.{0,20}而且", "不仅…而且…"), (r"值得一提的是", "值得一提的是"),
    (r"首先.{0,40}其次", "首先/其次/最后"), (r"综上所述", "综上所述"),
    (r"让我们", "让我们"), (r"在.{0,20}的过程中", "在…的过程中"),
    (r"(^|\n)他[^。\n]{0,20}[，。]\n他[^。\n]{0,20}[，。]\n他", "每段以「他」开头"),
    (r"——", "破折号代替标点"),
]
BANNED = ["炸裂", "绝了", "天花板", "孤本", "无人能及", "全网", "谁懂啊", "真的会谢",
          "爆火", "引爆全网", "封神", "最强", "第一人", "神级", "碾压", "吊打",
          "华语最低", "国内唯一", "世界最低", "断层第一"]


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


# ── 人味自检打分（逐项可复核）──
def score(text: str, cs: dict, platform: str = "小红书", hook: str = "") -> dict:
    """人味自检（**按平台分别约束**；钩子/标题行不参与行宽判定）。"""
    c = (cs or {}).get("constraints") or {}
    lines = [x for x in text.split("\n") if x.strip()]
    body_lines = [x for x in lines if not hook or x.strip() not in hook]
    lens = [len(re.sub(r"#\S+", "", x).strip()) for x in body_lines]
    emoji = len(re.findall("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", text))
    tags = re.findall(r"#([^\s#]{1,30})", text)
    fills = re.findall(r"〔你来补[：:][^〕]*〕", text)
    digits = re.findall(r"\d[\d,.]*\s*(?:秒|赫兹|Hz|个|首|场|次|分钟|天)", text)
    anti = [name for pat, name in ANTIPATTERNS if re.search(pat, text)]
    words = [w for w in BANNED if w in text]
    lim = c.get("line_max_chars") or 20
    over = [i + 1 for i, n in enumerate(lens) if n > lim]

    if platform == "小红书":
        nr = [3, 7]
        checks = {"lines": nr[0] <= len(lines) <= nr[1], "em": emoji <= (c.get("emoji_max") or 1),
                  "tg": 3 <= len(tags) <= 5, "fl": len(fills) >= 1, "nm": len(digits) <= 1,
                  "ln": not over}
    elif platform == "微博":
        checks = {"lines": True, "em": True, "tg": True,
                  "fl": len(fills) >= 1, "nm": len(digits) <= 1, "ln": True}
    elif platform == "抖音":
        # 抖音脚本是**分块结构**（钩子/3秒/中段/CTA/字幕），不按行宽与标签约束
        digits_no_label = len([d for d in digits if "秒" not in d]) if "3 秒" in text else len(digits)
        checks = {"lines": True, "em": True, "tg": True,
                  "fl": len(fills) >= 1, "nm": digits_no_label <= 1, "ln": True}
    else:  # 传记体
        checks = {"lines": len(lines) <= 8, "em": True, "tg": True,
                  "fl": len(fills) >= 1, "nm": len(digits) <= 1, "ln": True}

    ok = all(checks.values()) and not anti and not words
    return {
        "platform": platform, "lines": len(lines), "lines_ok": checks["lines"],
        "line_lens": lens, "line_over_limit": over, "line_max_ok": checks["ln"],
        "emoji": emoji, "emoji_ok": checks["em"],
        "tags": len(tags), "tags_ok": checks["tg"],
        "tags_at_tail": bool(tags) and text.rfind("#") >= 0.6 * len(text),
        "fill_slots": len(fills), "fill_ok": checks["fl"],
        "numbers": len(digits), "numbers_ok": checks["nm"],
        "first_person": any(k in text for k in ("我", "我们", "咱")),
        "anti_patterns": anti, "banned_words": words,
        "checks": checks,
        "pass": ok,
    }


def clean(text: str) -> tuple[str, list[str]]:
    hits = [w for w in BANNED if w in text]
    for w in hits:
        text = text.replace(w, "")
    for pat, _ in ANTIPATTERNS:
        text = re.sub(pat, "", text)
    return text, hits


def xhs_body(lines: list[str], tags: list[str]) -> str:
    return "\n".join(lines) + "\n\n" + " ".join("#" + t for t in tags)


def main() -> int:
    pick = load(D / "hooks_pick.json", {}) or {}
    entries = load(D / "share" / "entries.json", {}) or {}
    cs = load(D / "share" / "copy_style.json", {}) or {}
    sp = (load(D / "text_profile.json", {}) or {}).get("overall") or {}
    perf = load(D / "performance_attribution.json", {}) or {}
    c = (cs.get("constraints") or {})

    seen, hooks = set(), []
    for x in (pick.get("items") or []):
        if x.get("picked") and x.get("hook") not in seen:
            seen.add(x.get("hook"))
            hooks.append(x)

    ent = entries.get("entries") or []

    def footnote(h: str) -> dict:
        for e in ent:
            hh = e.get("hook") or ""
            if h and (hh[:6] in h or h[:6] in hh):
                return {"source": e.get("source"), "grade": e.get("grade"),
                        "taboo": e.get("taboo") or []}
        return {"source": "data/hooks_pool.json#hooks（规则抽取得分见 hook_miner.py#RULES）",
                "grade": "实测/语料命中（见证据表）",
                "taboo": ["不得夸大为平台级量级", "不得写成「史上/唯一」"]}

    def one_number(ev: str) -> str:
        """只留**一个**数字短语（一条文案最多一个数字）。"""
        m = re.search(r"(\d[\d,.]*\s*(?:秒|赫兹|Hz|首|场))", ev or "")
        return m.group(1) if m else ""

    items = []
    for x in hooks:
        h = x["hook"]
        ev = (x.get("evidence") or "").replace("\n", " ").strip()
        num = one_number(ev)
        fn = footnote(h)
        small = x.get("small_words") or []
        tags = [t for t in (["王晰"] + small[:3]) if t][:4]

        # ── 四件套（按人味标尺写：短行、留白、一个数字）──
        xhs = xhs_body([
            h,
            "",
            "现场那一句出来，我先愣了一下。",
            f"〔你来补：你在哪一场、坐在哪边〕",
            f"{num}，就这一下。" if num else "就这一下。",
            f"〔你来补：你当时脑子里冒出来的那句话〕",
        ], tags + ["现场"])

        weibo = "\n".join([
            f"{h}",
            f"出处：{fn['source'] or '数据层'}",
            "〔你来补：你听的是哪一场〕",
        ])

        douyin = "\n".join([
            "【钩子句】" + h,
            "【3 秒开头】" + (f"{num}。" if num else h),
            "【中段事实】" + (ev[:70] if ev else "读数与出处见简介"),
            "【CTA】想听完整的，去翻原片",
            "【留白】〔你来补：你的第一反应〕",
            "【字幕要点】" + " / ".join(small[:3]),
        ])

        bio = "\n".join([
            "他把这一句唱完，台下没有立刻鼓掌。",
            f"〔你来补：当天的一个具体场景〕",
            (f"{num}。" if num else ""),
            "这是测量结果，不是形容。",
        ]).strip()

        four = {}
        hits = {}
        for k, v in (("小红书", xhs), ("微博", weibo), ("抖音", douyin), ("传记体", bio)):
            cv, hh = clean(v)
            four[k] = cv
            hits[k] = hh

        # ── 三档口吻（同一事实三种写法；参数受画像约束）──
        tones = {
            "口语": {
                "text": "\n".join([h, "", "我就在现场。", f"{num}，一点没夸张" if num else "就这一下",
                                   "〔你来补：你身边的反应〕"]),
                "params": {"句长中位": sp.get("sent_len_median"), "短句率": sp.get("short_sent_pct"),
                           "第一人称": True},
            },
            "编辑": {
                "text": "\n".join([h, "", f"读数与出处：{fn['source'] or '数据层'}",
                                   f"口径：{fn['grade'] or '实测'}", "不作平台量级推断。"]),
                "params": {"硬事实": 2, "第一人称": False, "禁形容词": True},
            },
            "粉丝": {
                "text": "\n".join([h, "", "不是吹，这个数据摆在这儿。", "〔你来补：你存的那张截图/那一段〕",
                                   "想看原片的自己去找。"]),
                "params": {"热情": True, "禁夸词": BANNED[:6], "带个人锚点": True},
            },
        }
        scored = {k: score(v, cs, k, h) for k, v in four.items()}
        items.append({"hook": h, "small_words": small, "footnote": fn,
                      "four": four, "four_score": scored, "tones": tones,
                      "tone_score": {k: score(v["text"], cs, "小红书", h) for k, v in tones.items()},
                      "usage": {"用途": "小红书图文（本套亦含微博/抖音/传记体）",
                                "预计发布时机": "演出后 48h 内",
                                "必须修改的 1–3 处": ["〔你来补〕的位置", "标签换成你所在城市/场次",
                                                     "确认数字与出处一致"]},
                      "banned_hits": hits})

    # ── 改前/改后 对照（演示：机器腔 vs 人味）──
    demo_hook = next((i["hook"] for i in items if "16" in i["hook"] or "换气" in i["hook"]),
                     items[0]["hook"] if items else "")
    before = ("值得一提的是，《我真的受伤了》中有一句长达 16.5 秒不换气的演唱，"
              "不仅展现了扎实的气息控制，而且体现了极高的专业水准。综上所述，"
              "该表现值得我们关注。让我们共同期待他未来更多精彩表现！")
    after = "\n".join(["那句 16 秒半，他一口没换。", "", "我在现场听的时候，先听到的是气，不是字。",
                       "〔你来补：你当时坐在哪、周围什么反应〕", "", "#王晰 #现场 #低音"])
    changes = [
        "删掉「值得一提的是 / 不仅…而且 / 综上所述 / 让我们」四处 AI 句式",
        "长句拆成短行（每行 ≤20 字，允许不完整句）",
        "数字从「多处强调」压到**一个**：16 秒半",
        "加一个只有现场才有的个人锚点（气先到、字后到）",
        "留一处〔你来补〕，让人能把自己的位置填进去；删掉结尾的空洞祝愿句",
    ]

    # ── 本周节奏 ──
    last_show = None
    for s in (perf.get("shows") or []):
        for k in ("dates", "date"):
            v = s.get(k)
            if isinstance(v, list) and v:
                d = max(v)
            elif isinstance(v, str) and v:
                d = v
            else:
                continue
            if last_show is None or d > last_show:
                last_show = d
    today = date.today()
    cadence = []
    if last_show:
        delta = (today - date.fromisoformat(last_show[:10])).days
        if delta <= 2:
            cadence.append({"slot": "演出后 48h", "action": "发现场硬事实一条（一个数字＋一处留白）",
                            "why": f"最近演出 {last_show}"})
        elif delta <= 10:
            cadence.append({"slot": "演出后一周内", "action": "发「这场的一个细节」",
                            "why": f"最近演出 {last_show}（{delta} 天前）"})
    cadence += [{"slot": "周一速报", "action": "上周数据一句话 + 一张图", "why": "固定复查点"},
                {"slot": "周四长文", "action": "口径与证据的长文（带禁忌）", "why": "留出讨论窗口"}]
    if not items:
        cadence = [{"slot": "本周", "action": "**本周无新料**（无勾选钩子）", "why": "输入为空"}]

    doc = {"schema": 2,
           "generated_at": datetime.now().isoformat(timespec="seconds"),
           "caliber": "钩子=data/hooks_pick.json(picked)；证据=entries.json；"
                      "风格约束=copy_style.json（真语料 26 笔记/121 评论）；预览用，不自动发布",
           "style": {"ruler": cs.get("ruler"), "constraints": c,
                     "source": cs.get("source"), "n_posts": cs.get("n_posts"),
                     "n_comments": cs.get("n_comments")},
           "anti_ai": {"banned_patterns": [n for _, n in ANTIPATTERNS], "banned_words": BANNED},
           "n_hooks": len(items), "items": items,
           "demo": {"hook": demo_hook, "before_machine": before, "after_human": after,
                    "changes": changes,
                    "score_before": score(before, cs, "小红书"), "score_after": score(after, cs, "小红书")},
           "cadence": cadence}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── HTML 片段 ──
    H = ['<div class="copy-pipeline">',
         f'<p class="meta">人味标尺（真语料：{cs.get("n_posts")} 条笔记 / {cs.get("n_comments")} 条评论）：'
         f'行数 {c.get("lines_range")}｜每行 ≤{c.get("line_max_chars")} 字｜emoji ≤{c.get("emoji_max")}｜'
         f'标签 {c.get("tags_range")} 个放末尾｜留白 {c.get("fill_in_slots")} 处。'
         f'<b>本区只预览，确认后手动发布。</b></p>']
    for it in items:
        H.append(f'<article class="cp-item"><h3>{it["hook"]}</h3>')
        H.append('<p class="meta">用途：' + it["usage"]["用途"] +
                 '｜预计发布时机：' + it["usage"]["预计发布时机"] +
                 '｜必须修改：' + "；".join(it["usage"]["必须修改的 1–3 处"]) + '</p>')
        H.append('<details open><summary>四件套（直接复制，先改〔你来补〕）</summary>')
        for k, v in it["four"].items():
            s = it["four_score"][k]
            H.append(f'<h4>{k}　<span class="meta">自检：行 {s["lines"]}｜emoji {s["emoji"]}｜'
                     f'标签 {s["tags"]}｜留白 {s["fill_slots"]}｜数字 {s["numbers"]}｜'
                     f'{"✅" if s["pass"] else "⚠"}</span></h4>'
                     f'<pre style="white-space:pre-wrap">{v}</pre>')
        H.append('</details>')
        H.append('<details><summary>三档口吻（同一事实三种写法）</summary>')
        for tone, obj in it["tones"].items():
            s = it["tone_score"][tone]
            H.append(f'<h4>{tone}　<span class="meta">{"✅" if s["pass"] else "⚠"}</span></h4>'
                     f'<pre style="white-space:pre-wrap">{obj["text"]}</pre>')
        H.append('</details>')
        if it["footnote"].get("taboo"):
            H.append('<p class="meta">⚠ 禁忌：' + "；".join(it["footnote"]["taboo"]) + '</p>')
        H.append('</article>')
    demo = doc["demo"]
    H.append('<h3>改前 / 改后（机器腔 → 人味）</h3>')
    H.append(f'<p class="meta">改前自检：{json.dumps({k: demo["score_before"][k] for k in ("lines","emoji","tags","fill_slots","numbers","anti_patterns")}, ensure_ascii=False)}</p>')
    H.append(f'<pre style="white-space:pre-wrap">{demo["before_machine"]}</pre>')
    H.append(f'<p class="meta">改后自检：{json.dumps({k: demo["score_after"][k] for k in ("lines","emoji","tags","fill_slots","numbers","anti_patterns")}, ensure_ascii=False)}</p>')
    H.append(f'<pre style="white-space:pre-wrap">{demo["after_human"]}</pre>')
    H.append('<ol>' + "".join(f'<li>{x}</li>' for x in demo["changes"]) + '</ol>')
    H.append('<h3>本周发布节奏建议</h3><ul>')
    for c2 in cadence:
        H.append(f'<li><b>{c2["slot"]}</b>：{c2["action"]} <span class="meta">（{c2["why"]}）</span></li>')
    H.append('</ul>')
    H.append('<p class="meta">使用说明：<a href="使用说明-四件套.html">使用说明（四件套）</a>｜'
             '平台机制均为「经验性认知（非官方）」；不含外部链接与音视频。</p></div>')
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text("\n".join(H), encoding="utf-8")

    # ── 使用说明（本地 md）──
    USAGE_MD.parent.mkdir(parents=True, exist_ok=True)
    USAGE_MD.write_text("\n".join([
        "# 使用说明 · 四件套（小红书／微博／抖音／传记体）", "",
        "## ① 从哪里打开",
        "- 站内：`share.html` →「①d 一键成稿」区（或直接看 `使用说明-四件套.html`）",
        "- 本地：`data/share/rendered/copy_pipeline.html`；数据：`data/share/copy_pipeline.json`",
        "", "## ② 三步",
        "1. 勾选：`data/hooks_pick.json` 里把目标钩子的 `picked` 设为 true（或跑 `hook_miner.py --render-picked`）",
        "2. 预览：`python -X utf8 project_b/build_copy_pipeline.py` → 打开上面两个入口",
        "3. 复制：先改掉所有 `〔你来补：…〕`，再整段复制发布（**不要不改就发**）",
        "", "## ③ 改完后自检 5 条",
        "1. 去掉 AI 句式（不仅…而且/值得一提的是/综上所述/让我们/在…的过程中）",
        "2. 加一个只有你知道的细节（哪一场、坐哪边、身边谁在哭）",
        "3. 标签换成你所在城市与场次（3–5 个，放末尾）",
        "4. 确认数字与出处（一条最多一个数字，出处写在后面）",
        "5. 删掉任何「总结句」与空洞祝愿", "",
        "## ④ 不建议直接发的情况",
        "- 涉及私域/他人信息（家事、联系方式、未公开行程）→ 一律不发",
        "- 未证实的细节（听说的、没有出处的数字）→ 先标「待核」再决定",
        "- 涉及逝者/悼念语境 → 不发",
        "- 平台机制类说法 → 必须标「经验性认知（非官方）」",
        "", "## ⑤ 纪律",
        "- 音视频不入 git、不上页面；不接外部自动发布接口；",
        "- 夸词黑名单（炸裂/绝了/天花板/孤本/无人能及/全网/谁懂啊/真的会谢…）由生成器自动过滤并记录。",
    ]) + "\n", encoding="utf-8")

    print(f"[ok] {OUT_JSON.name}｜钩子 {len(items)} 条｜改前改后 1 组｜节奏 {len(cadence)} 条")
    print(f"[ok] {OUT_HTML.name}｜{OUT_HTML.stat().st_size} B")
    print(f"[ok] {USAGE_MD.name}")
    for it in items:
        print("  ·", it["hook"], "| 四件套 pass:", {k: v["pass"] for k, v in it["four_score"].items()})
    print("  · demo 改前 pass:", demo["score_before"]["pass"], "｜改后 pass:", demo["score_after"]["pass"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
