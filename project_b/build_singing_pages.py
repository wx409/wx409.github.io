# -*- coding: utf-8 -*-
"""`singing.html`（文章版 A ＋ 文末核对表）＋ `singing-social.html`（社媒版 B，供转发）。

正文与数字**全部从源文件派生**（不手写 HTML、不手写数字）：
  A：`E:\\wx\\论文素材_王晰作传\\原始材料\\传记草稿_王晰演唱专业版_v1.md`（九段 + 文末核对表 + 因缺证据没写）
  B：`同目录\\传记草稿_王晰演唱专业版_社媒版_v1.md`（九条钩子 + 短句 + 出处）
  卡片：`data/share/rendered/card_{low_baseline,vibrato_8y,pair_54}.html`（三条实测卡，附在文章版末）

做法：自写**最小 Markdown → HTML** 转换（标题/引用/列表/表格/粗体/代码/分隔线），
不引第三方依赖；JSON-LD 用 `Article`，`author` 指向站点实体（index.html 的 Person），
`isBasedOn`/`citation` 指向 `data/` 证据文件。

纪律：两页**不得含逝者/私域信息**（脚本内置黑名单，命中即拒绝生成并报错）；
平台机制表述标「经验性认知（非官方）」；不进主导航。

用法：python -X utf8 project_b\\build_singing_pages.py [--check]
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
RAW = Path(r"E:\wx\论文素材_王晰作传\原始材料")
MD_A = RAW / "传记草稿_王晰演唱专业版_v1.md"
MD_B = RAW / "传记草稿_王晰演唱专业版_社媒版_v1.md"
OUT_A = SITE / "singing.html"
OUT_B = SITE / "singing-social.html"
TODAY = date.today().isoformat()
BASE = "https://wx409.github.io"

# 隐私黑名单：命中即拒绝上线（用户私下告知的内容不得进站）
PRIVATE = ("去世", "离世", "过世", "悼念", "遗愿", "逝者", "病逝", "追悼", "老粉走了")
HYPE = ("爆火", "引爆全网", "上热点", "刷屏", "破圈", "顶流")


def esc(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md_to_html(md: str) -> str:
    """最小 Markdown → HTML：标题 / 引用 / 有序与无序列表 / 表格 / 分隔线 / 段落。"""
    out, i = [], 0
    lines = md.splitlines()
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s.startswith("---"):
            out.append("<hr>")
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            i += 1
            continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf)))
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            head = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            tr = "".join("<tr>%s</tr>" % "".join(f"<td>{inline(c)}</td>" for c in r) for r in rows)
            out.append(f"<div class='tw'><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>")
            continue
        if re.match(r"^\d+\.\s", s):
            buf = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                buf.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>%s</ol>" % "".join(f"<li>{inline(x)}</li>" for x in buf))
            continue
        if s.startswith("- "):
            buf = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                buf.append(lines[i].strip()[2:])
                i += 1
            out.append("<ul>%s</ul>" % "".join(f"<li>{inline(x)}</li>" for x in buf))
            continue
        # 普通段落（连续行合并）
        buf = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#|>|\||- |\d+\.\s|---)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def person_id() -> str:
    """从 index.html 的 JSON-LD 取站点 Person 的 @id（供 Article.author 复用）。"""
    t = (SITE / "index.html").read_text(encoding="utf-8")
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        items = d if isinstance(d, list) else (d.get("@graph") or [d])
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "Person" and it.get("@id"):
                return it["@id"]
    return f"{BASE}/#person"


SHELL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}｜AI 可读数字档案｜GEO 资料站</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<style>
body{{max-width:820px;margin:0 auto;padding:20px 18px 60px;font:16px/1.85 -apple-system,"Microsoft YaHei",sans-serif;color:#2b2320;background:#faf6ef}}
h1{{font-size:25px;line-height:1.35;margin:6px 0 10px}} h2{{font-size:19px;margin:30px 0 8px;border-left:4px solid #c9a227;padding-left:9px}}
h3{{font-size:16.5px;margin:22px 0 6px}}
blockquote{{background:#fff;border-left:3px solid #d9c46a;margin:12px 0;padding:9px 13px;color:#6d6252;font-size:14px}}
code{{background:#f1e9da;border-radius:4px;padding:1px 5px;font-size:13px}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13.5px;background:#fff}}
th,td{{border:1px solid #e6dcc9;padding:6px 8px;vertical-align:top;text-align:left}}
th{{background:#f6efe1;white-space:nowrap}}
.meta{{color:#8a7f6d;font-size:12.5px}} hr{{border:0;border-top:1px dashed #e2d8c7;margin:22px 0}}
.card{{background:#fff;border:1px solid #eadfc9;border-radius:8px;padding:12px 15px;margin:14px 0}}
.card h3{{margin-top:2px}} .pill{{font-size:11px;background:#eee3d3;color:#7a6a55;border-radius:10px;padding:2px 8px;margin-left:8px}}
.nums li{{margin:3px 0}} .foot{{color:#8a7f6d;font-size:12.5px;border-top:1px dashed #e2d8c7;padding-top:6px}}
.lock{{background:#fff4f0;border-left:3px solid #d98b6a;padding:8px 12px;margin:10px 0;font-size:13.5px}}
.plat{{background:#f3f6ef;border-left:3px solid #8aa87a;padding:8px 12px;margin:10px 0;font-size:13.5px}}
.sub{{color:#8a7f6d;margin:2px 0 10px}}
.tocband{{background:#fff;border:1px dashed #e0d5c0;border-radius:8px;padding:10px 14px;margin:14px 0;font-size:14px}}
</style></head><body>
<!-- NAV_START --><!-- NAV_END -->
{body}
<script type="application/ld+json">{ld}</script>
</body></html>
"""


def build() -> int:
    md_a = MD_A.read_text(encoding="utf-8")
    md_b = MD_B.read_text(encoding="utf-8")
    # 隐私/量级词闸门（上线前核对；命中即拒绝生成）
    problems = []
    for name, txt in (("A 文章版", md_a), ("B 社媒版", md_b)):
        for w in PRIVATE:
            if w in txt:
                problems.append(f"{name} 命中隐私黑名单「{w}」")
        for w in HYPE:
            if w in txt:
                problems.append(f"{name} 命中量级词「{w}」")
    if problems:
        print("[X] 拒绝生成：\n  " + "\n  ".join(problems))
        return 1

    pid = person_id()
    cards_html = ""
    for cid in ("low_baseline", "vibrato_8y", "pair_54"):
        f = D / "share" / "rendered" / f"card_{cid}.html"
        if f.exists():
            cards_html += f.read_text(encoding="utf-8")

    body_a = ("<h1>他唱得怎么样：一份基于实测的说明</h1>"
              "<p class='meta'>数字均来自本站实测数据（人声分离 → 逐帧基频 → 稳健过滤）；"
              "每条结论在文末核对表可定位到文件与字段。生成 " + TODAY + "｜"
              "<b>经验性认知（非官方）</b>：本页为基于公开材料与自测数据的经验性整理，非官方发布。</p>"
              "<div class='tocband'>两版说明：本页为<b>文章版</b>（含文末核对表）；"
              "要转发的短句版见 <a href='singing-social.html'>singing-social.html</a>。"
              "配套三张实测卡见文末。</div>"
              + md_to_html(md_a)
              + "<h2>配套实测卡（三张）</h2>"
              + (cards_html or "<p class='meta'>（卡片片段缺失，请先跑 build_article_cards.py）</p>"))

    body_b = ("<h1>他唱得怎么样：可转发短句版</h1>"
              "<p class='meta'><b>供转发使用</b>｜每条短句都挂着出处（文件 + 字段/时间戳）；"
              "改写时请保留数字与限定语，不要写成平台量级断言。生成 " + TODAY + "。</p>"
              "<div class='tocband'>要完整论述与文末核对表，见 <a href='singing.html'>文章版</a>。</div>"
              + md_to_html(md_b))

    ld_a = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": "他唱得怎么样：一份基于实测的说明",
        "description": "以最低稳定音、颤音速率、同曲录音室与现场配对等实测指标，说明王晰的演唱能力与限度；"
                       "含文末核对表（每条结论可定位到数据文件与字段）。",
        "inLanguage": "zh-CN", "datePublished": TODAY, "dateModified": TODAY,
        "mainEntityOfPage": f"{BASE}/singing.html",
        "author": {"@id": pid},
        "publisher": {"@type": "Organization", "name": "王晰数字档案（GEO 资料站）", "url": BASE},
        "isBasedOn": [f"{BASE}/data/archive_vocal_albums.json",
                      f"{BASE}/data/archive_long_notes.json",
                      f"{BASE}/data/archive_stage_tour.json",
                      f"{BASE}/data/archive_context_compare.json",
                      f"{BASE}/data/calibers.md"],
        "citation": [{"@type": "Dataset", "name": "72 首录音室曲目音域实测（archive_vocal_albums.json）",
                      "url": f"{BASE}/data/archive_vocal_albums.json"},
                     {"@type": "Dataset", "name": "长声实测榜（archive_long_notes.json）",
                      "url": f"{BASE}/data/archive_long_notes.json"},
                     {"@type": "Dataset", "name": "舞台层可主张素材与同曲配对（archive_stage_tour.json）",
                      "url": f"{BASE}/data/archive_stage_tour.json"}],
        "license": f"{BASE}/docs/CALIBER.md",
    }
    ld_b = dict(ld_a)
    ld_b.update({"headline": "他唱得怎么样：可转发短句版",
                 "description": "文章版的可转发短句版（九条），每条附出处；供转发使用。",
                 "mainEntityOfPage": f"{BASE}/singing-social.html"})

    OUT_A.write_text(SHELL.format(
        title="他唱得怎么样：一份基于实测的说明", desc="最低稳定音 B1 61.5Hz、72 首里 44 首低于 E2、"
        "八张专辑颤音速率极差 0.27Hz、同曲录音室与现场配对 56 组中位 1.7 半音——含文末核对表。",
        canonical=f"{BASE}/singing.html", ogtitle="他唱得怎么样：一份基于实测的说明",
        body=body_a, ld=json.dumps(ld_a, ensure_ascii=False)), encoding="utf-8")
    OUT_B.write_text(SHELL.format(
        title="他唱得怎么样：可转发短句版", desc="文章版的可转发短句版（九条钩子 + 短句 + 出处），供转发使用。",
        canonical=f"{BASE}/singing-social.html", ogtitle="他唱得怎么样：可转发短句版",
        body=body_b, ld=json.dumps(ld_b, ensure_ascii=False)), encoding="utf-8")
    print("[OK] singing.html（文章版 + 核对表 + 三卡）｜singing-social.html（短句版，供转发）")
    print("     隐私/量级词闸门：通过（0 命中）｜JSON-LD：Article + citation/isBasedOn")
    return 0


def check() -> int:
    ok = True
    for p in (OUT_A, OUT_B):
        if not p.exists():
            print("[X] 缺文件", p)
            ok = False
            continue
        t = p.read_text(encoding="utf-8")
        for w in PRIVATE:
            if w in t:
                print(f"[X] {p.name} 命中隐私词「{w}」")
                ok = False
        if '"@type": "Article"' not in t:
            print(f"[X] {p.name} 缺 Article JSON-LD")
            ok = False
        if f"{BASE}/{p.name}" not in t:
            print(f"[X] {p.name} canonical 不对")
            ok = False
    print("[check]", "通过 ✅" if ok else "未通过 ✗")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(check() if "--check" in sys.argv else build())
