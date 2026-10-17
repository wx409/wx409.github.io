# -*- coding: utf-8 -*-
"""build_copy_pipeline.py —— 「一键成稿」v3（**选项式留白**，预览用，不自动发布）

v3 变更（2026-10-17 用户反馈「留白太抽象、没头绪」）：
  1. 留白改为**选项式填空**：给可选项 + 示例句，不用从零构思；
  2. 每套顶部加「**填写示例（填好的样子）**」折叠块（已填满的成品）；
  3. 每份成稿留白 **≤3 处**，按重要性：① 哪一场/哪个位置 ② 你当时的反应 ③ 一句你自己的话；
  4. 每处留白下加提示：`不填也能发（删掉方括号直发），但填了才像你`；
  5. 每套另给「**零填版**」（删掉方括号，可直接复制），标注「信息量低、可能平淡」；
  6. 人味标尺 / 反 AI 味 / 三档口吻 / 证据脚注 / 禁忌 沿用 v2。

输入：hooks_pick.json、entries.json、copy_style.json、text_profile.json、performance_attribution.json
输出：data/share/copy_pipeline.json、data/share/rendered/copy_pipeline.html、
      E:\\wx\\论文素材_王晰作传\\传播监测\\使用说明_四件套.md
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

SLOTS = [
    {"id": "night_seat", "priority": 1,
     "text": "〔选一个场次＋位置：10-09 首场 / 10-10 第二场 ｜ 左边 / 中间 / 右边 / 前排〕",
     "hint": "不填也能发（删掉方括号直发），但填了才像你"},
    {"id": "reaction", "priority": 2,
     "text": ("〔从这三句里挑一句，或改成你自己的：① 我以为低音会糊，结果每个字都清楚 "
              "② 他一开口，前排有人小声「哇」 ③ 那句尾音落下去，我下意识屏住呼吸〕"),
     "hint": "不填也能发（删掉方括号直发），但填了才像你"},
    {"id": "own_line", "priority": 3,
     "text": "〔填当天的天气／排队／邻座的一句吐槽，一句就够〕",
     "hint": "不填也能发（删掉方括号直发），但填了才像你"},
]
FILLED = {"night_seat": "10-09 首场，坐左边靠过道",
          "reaction": "那句尾音落下去，我下意识屏住呼吸",
          "own_line": "散场时外面在下小雨，排队等车的人都在哼那句"}

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


def strip_slots(text: str) -> str:
    t = re.sub(r"〔[^〕]*〕", "", text)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return "\n".join(x.rstrip() for x in t.splitlines() if x.strip())


def fill_slots(text: str) -> str:
    out = text
    for i, s in enumerate(SLOTS):
        v = FILLED.get(s["id"])
        if v and i < 2:
            out = out.replace(s["text"], v, 1)
    return out


def score(text: str, cs: dict, platform: str = "小红书", hook: str = "") -> dict:
    c = (cs or {}).get("constraints") or {}
    lines = [x for x in text.split("\n") if x.strip()]
    # 行宽/数字只算**正文行**：排除钩子行与〔…〕留白提示行（那些是给人改的选项，不是成稿正文）
    body = [x for x in lines
            if (not hook or x.strip() not in hook) and "〔" not in x]
    lens = [len(re.sub(r"#\S+", "", x).strip()) for x in body]
    emoji = len(re.findall("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", text))
    tags = re.findall(r"#([^\s#]{1,30})", text)
    fills = re.findall(r"〔[^〕]*〕", text)
    digits = re.findall(r"\d[\d,.]*\s*(?:秒|赫兹|Hz|个|首|场|次|分钟|天)", "\n".join(body))
    anti = [n for p, n in ANTIPATTERNS if re.search(p, text)]
    words = [w for w in BANNED if w in text]
    lim = c.get("line_max_chars") or 20
    over = [i + 1 for i, n in enumerate(lens) if n > lim]
    if platform == "小红书":
        chk = {"lines": 3 <= len(lines) <= 9, "em": emoji <= 1, "tg": 3 <= len(tags) <= 5,
               "fl": 1 <= len(fills) <= 3, "nm": len(digits) <= 1, "ln": not over}
    elif platform == "微博":
        chk = {"lines": True, "em": True, "tg": True, "fl": 1 <= len(fills) <= 3,
               "nm": len(digits) <= 1, "ln": True}
    elif platform == "抖音":
        chk = {"lines": True, "em": True, "tg": True, "fl": 1 <= len(fills) <= 3,
               "nm": True, "ln": True}
    else:
        chk = {"lines": len(lines) <= 9, "em": True, "tg": True, "fl": 1 <= len(fills) <= 3,
               "nm": len(digits) <= 1, "ln": True}
    return {"platform": platform, "lines": len(lines), "lines_ok": chk["lines"],
            "line_lens": lens, "line_over_limit": over, "line_max_ok": chk["ln"],
            "emoji": emoji, "emoji_ok": chk["em"], "tags": len(tags), "tags_ok": chk["tg"],
            "fill_slots": len(fills), "fill_ok": chk["fl"], "fill_le3": len(fills) <= 3,
            "numbers": len(digits), "numbers_ok": chk["nm"],
            "anti_patterns": anti, "banned_words": words, "checks": chk,
            "pass": all(chk.values()) and not anti and not words}


def main() -> int:
    pick = load(D / "hooks_pick.json", {}) or {}
    entries = load(D / "share" / "entries.json", {}) or {}
    cs = load(D / "share" / "copy_style.json", {}) or {}
    sp = (load(D / "text_profile.json", {}) or {}).get("overall") or {}
    perf = load(D / "performance_attribution.json", {}) or {}
    c = cs.get("constraints") or {}

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
        return {"source": "data/hooks_pool.json#hooks", "grade": "实测/语料命中（见证据表）",
                "taboo": ["不得夸大为平台级量级", "不得写成「史上/唯一」"]}

    items = []
    for x in hooks:
        h = x["hook"]
        ev = (x.get("evidence") or "").replace("\n", " ").strip()
        m = re.search(r"(\d[\d,.]*\s*(?:秒|赫兹|Hz|首|场))", ev) if ev else None
        num = m.group(1) if m else ""
        fn = footnote(h)
        small = x.get("small_words") or []
        tags = [t for t in (["王晰"] + small[:3]) if t][:4]
        S1, S2, S3 = (s["text"] for s in SLOTS)

        xhs = "\n".join([h, "", "现场那一句出来，我先愣了一下。", S1, "", S2, "",
                         (f"{num}，就这一下。" if num else "就这一下。"), S3, "",
                         " ".join("#" + t for t in tags + ["现场"])])
        weibo = "\n".join([h, (f"{num}。" if num else ""), "出处：" + (fn["source"] or "数据层"), S1, S3])
        douyin = "\n".join(["【钩子句】" + h, "【3 秒开头】" + (f"{num}。" if num else h),
                            "【中段事实】" + (ev[:70] if ev else "读数与出处见简介"),
                            "【CTA】想听完整的，去翻原片", "【留白】" + S2,
                            "【字幕要点】" + " / ".join(small[:3])])
        bio = "\n".join(["他把这一句唱完，台下没有立刻鼓掌。", S1, S2,
                         (f"{num}。" if num else ""), "这是测量结果，不是形容。"])
        FOUR = {"小红书": xhs, "微博": weibo, "抖音": douyin, "传记体": bio}

        items.append({
            "hook": h, "small_words": small, "footnote": fn,
            "four": FOUR,
            "zero_fill": {k: strip_slots(v) for k, v in FOUR.items()},
            "filled_example": {k: fill_slots(v) for k, v in FOUR.items()},
            "slots": SLOTS,
            "fill_count": {k: len(re.findall(r"〔[^〕]*〕", v)) for k, v in FOUR.items()},
            "four_score": {k: score(v, cs, k, h) for k, v in FOUR.items()},
            "zero_score": {k: score(strip_slots(v), cs, k, h) for k, v in FOUR.items()},
            "tones": {
                "口语": {"text": "\n".join([h, "", "我就在现场。", S2, "就这一下。"]),
                         "params": {"句长中位": sp.get("sent_len_median"), "第一人称": True}},
                "编辑": {"text": "\n".join([h, "", "读数与出处：" + (fn["source"] or "数据层"),
                                            "口径：" + (fn["grade"] or "实测"), "不作平台量级推断。"]),
                         "params": {"硬事实": 2, "第一人称": False}},
                "粉丝": {"text": "\n".join([h, "", "不是吹，这个数据摆在这儿。", S3, "想看原片的自己去找。"]),
                         "params": {"热情": True, "禁夸词": BANNED[:6], "带个人锚点": True}},
            },
            "usage": {"用途": "小红书图文（本套亦含微博/抖音/传记体）",
                      "预计发布时机": "演出后 48h 内",
                      "必须修改的 1–3 处": ["〔选一个：哪一场 / 哪个位置〕",
                                          "〔从三句里挑一句，或改成你自己的〕",
                                          "〔填一句当天的小细节〕"],
                      "提示": "不填也能发（删掉方括号直发），但填了才像你；零填版见每套下方"},
        })

    demo_hook = next((i["hook"] for i in items if "16" in i["hook"] or "换气" in i["hook"]),
                     items[0]["hook"] if items else "")
    before = ("值得一提的是，《我真的受伤了》中有一句长达 16.5 秒不换气的演唱，"
              "不仅展现了扎实的气息控制，而且体现了极高的专业水准。综上所述，该表现值得我们关注。"
              "让我们共同期待他未来更多精彩表现！")
    after = "\n".join(["那句 16 秒半，他一口没换。", "", "我在现场听的时候，先听到的是气，不是字。",
                       SLOTS[0]["text"], SLOTS[1]["text"], "", "#王晰 #现场 #低音"])
    changes = ["删掉「值得一提的是／不仅…而且／综上所述／让我们」四处 AI 句式",
               "长句拆成短行（每行 ≤20 字，允许不完整句）",
               "数字压到**一个**（16 秒半）",
               "留白改成**选项式**：场次/位置给选项、反应给三句备选",
               "留白下加提示「不填也能发，但填了才像你」；另给零填版"]

    last_show = None
    for s in (perf.get("shows") or []):
        for k in ("dates", "date"):
            v = s.get(k)
            d = max(v) if isinstance(v, list) and v else (v if isinstance(v, str) and v else None)
            if d and (last_show is None or d > last_show):
                last_show = d
    today = date.today()
    cadence = []
    if last_show:
        delta = (today - date.fromisoformat(last_show[:10])).days
        if delta <= 2:
            cadence.append({"slot": "演出后 48h", "action": "发现场硬事实一条", "why": f"最近演出 {last_show}"})
        elif delta <= 10:
            cadence.append({"slot": "演出后一周内", "action": "发「这场的一个细节」",
                            "why": f"最近演出 {last_show}（{delta} 天前）"})
    cadence += [{"slot": "周一速报", "action": "上周数据一句话 + 一张图", "why": "固定复查点"},
                {"slot": "周四长文", "action": "口径与证据的长文（带禁忌）", "why": "留出讨论窗口"}]
    if not items:
        cadence = [{"slot": "本周", "action": "**本周无新料**", "why": "输入为空"}]

    doc = {"schema": 3, "generated_at": datetime.now().isoformat(timespec="seconds"),
           "caliber": "钩子=hooks_pick；证据=entries；风格=copy_style（真语料）；留白≤3 且为选项式；预览用",
           "style": {"ruler": cs.get("ruler"), "constraints": c, "source": cs.get("source"),
                     "n_posts": cs.get("n_posts"), "n_comments": cs.get("n_comments")},
           "anti_ai": {"banned_patterns": [n for _, n in ANTIPATTERNS], "banned_words": BANNED},
           "slots": SLOTS, "n_hooks": len(items), "items": items,
           "demo": {"hook": demo_hook, "before_machine": before, "after_human": after,
                    "changes": changes, "score_before": score(before, cs),
                    "score_after": score(after, cs)},
           "cadence": cadence}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    H = ['<div class="copy-pipeline">',
         f'<p class="meta">人味标尺（真语料 {cs.get("n_posts")} 笔记 / {cs.get("n_comments")} 评论）：'
         f'行数 {c.get("lines_range")}｜每行 ≤{c.get("line_max_chars")} 字｜emoji ≤{c.get("emoji_max")}｜'
         f'标签 {c.get("tags_range")} 个放末尾｜<b>留白 ≤3 处，且都是选项式</b>。'
         f'<b>只预览，确认后手动发布。</b></p>']
    for it in items:
        H.append(f'<article class="cp-item"><h3>{it["hook"]}</h3>')
        H.append('<p class="meta">用途：' + it["usage"]["用途"] + '｜发布时机：' + it["usage"]["预计发布时机"]
                 + '｜必须修改：' + "；".join(it["usage"]["必须修改的 1–3 处"]) + '</p>')
        H.append('<details open><summary><b>填写示例（填好的样子）</b>——先看这个，照着改成你自己的</summary>')
        for k, v in it["filled_example"].items():
            H.append(f'<h4>{k}</h4><pre style="white-space:pre-wrap">{v}</pre>')
        H.append('</details>')
        H.append('<details open><summary>四件套（选项式留白，≤3 处）</summary>')
        for k, v in it["four"].items():
            s = it["four_score"][k]
            H.append(f'<h4>{k}　<span class="meta">留白 {it["fill_count"][k]} 处｜行 {s["lines"]}｜'
                     f'标签 {s["tags"]}｜数字 {s["numbers"]}｜{"✅" if s["pass"] else "⚠"}</span></h4>'
                     f'<pre style="white-space:pre-wrap">{v}</pre>')
            H.append('<p class="meta">提示：不填也能发（删掉方括号直发），但填了才像你。</p>')
        H.append('</details>')
        H.append('<details><summary>零填版（可直接复制，信息量低、可能平淡）</summary>')
        for k, v in it["zero_fill"].items():
            H.append(f'<h4>{k}</h4><pre style="white-space:pre-wrap">{v}</pre>')
        H.append('</details>')
        H.append('<details><summary>三档口吻（同一事实三种写法）</summary>')
        for tone, obj in it["tones"].items():
            H.append(f'<h4>{tone}</h4><pre style="white-space:pre-wrap">{obj["text"]}</pre>')
        H.append('</details>')
        if it["footnote"].get("taboo"):
            H.append('<p class="meta">⚠ 禁忌：' + "；".join(it["footnote"]["taboo"]) + '</p>')
        H.append('</article>')
    demo = doc["demo"]
    H.append('<h3>改前 / 改后（机器腔 → 人味）</h3>')
    H.append('<p class="meta">改前自检：' + json.dumps(
        {k: demo["score_before"][k] for k in ("lines", "tags", "fill_slots", "numbers", "anti_patterns")},
        ensure_ascii=False) + '</p>')
    H.append(f'<pre style="white-space:pre-wrap">{demo["before_machine"]}</pre>')
    H.append('<p class="meta">改后自检：' + json.dumps(
        {k: demo["score_after"][k] for k in ("lines", "tags", "fill_slots", "numbers", "anti_patterns")},
        ensure_ascii=False) + '</p>')
    H.append(f'<pre style="white-space:pre-wrap">{demo["after_human"]}</pre>')
    H.append('<ol>' + "".join(f'<li>{x}</li>' for x in demo["changes"]) + '</ol>')
    H.append('<h3>本周发布节奏建议</h3><ul>')
    for c2 in cadence:
        H.append(f'<li><b>{c2["slot"]}</b>：{c2["action"]} <span class="meta">（{c2["why"]}）</span></li>')
    H.append('</ul><p class="meta">使用说明：<a href="使用说明-四件套.html">使用说明（四件套）</a>｜'
             '平台机制为「经验性认知（非官方）」；无外部链接与音视频。</p></div>')
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text("\n".join(H), encoding="utf-8")

    USAGE_MD.parent.mkdir(parents=True, exist_ok=True)
    USAGE_MD.write_text("\n".join([
        "# 使用说明 · 四件套", "",
        "**① 打开哪**：站内 `share.html` →「①d 一键成稿」；或本地 `data/share/rendered/copy_pipeline.html`。",
        "**② 三处怎么填**：留白都是**选项式**——① 〔选一个：10-09 首场 / 10-10 第二场〕"
        "② 〔从三句里挑一句，或改成你自己的〕③ 〔填一句当天的小细节〕；不想填就删掉方括号。",
        "**③ 不想填**：直接复制每套的「**零填版**」（已删掉方括号），能发但信息量低、可能平淡。", "",
        "## 详细步骤",
        "1. 勾选：`data/hooks_pick.json` 把 `picked` 设 true（或跑 `hook_miner.py --render-picked`）",
        "2. 预览：`python -X utf8 project_b/build_copy_pipeline.py` → 打开上面入口",
        "3. 复制：先按选项改掉 `〔…〕`（≤3 处），再整段复制发布", "",
        "## 每处留白下方都有提示",
        "「不填也能发（删掉方括号直发），但填了才像你。」", "",
        "## 改完后自检 5 条",
        "1. 去掉 AI 句式（不仅…而且／值得一提的是／综上所述／让我们／在…的过程中）",
        "2. 三处留白至少填一处（场次/位置最好填）",
        "3. 标签换成你所在城市与场次（3–5 个，放末尾）",
        "4. 确认数字与出处（一条最多一个数字）",
        "5. 删掉任何「总结句」与空洞祝愿", "",
        "## 不建议直接发",
        "- 私域/他人信息、未证实细节、逝者/悼念语境 → 一律不发",
        "- 平台机制说法 → 标「经验性认知（非官方）」", "",
        "## 纪律",
        "音视频不入 git、不上页面；不接外部自动发布接口；夸词黑名单由生成器自动过滤并记账。",
    ]) + "\n", encoding="utf-8")

    print(f"[ok] {OUT_JSON.name}｜钩子 {len(items)}｜留白上限 3 生效")
    for it in items:
        print("  ·", it["hook"][:20], "| 留白数:", it["fill_count"],
              "| pass:", {k: v["pass"] for k, v in it["four_score"].items()})
    print(f"[ok] {OUT_HTML.name}｜{OUT_HTML.stat().st_size} B｜{USAGE_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
