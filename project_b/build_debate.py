# -*- coding: utf-8 -*-
"""专家辩论模块生成器（瘦身 2.0 · 7.3）

议题：《向着太阳》最低音之争 —— 本站严格口径 G2（97.8Hz） vs 《乐器》杂志出版物读数。

第一性原理：两个数字不矛盾，矛盾只在**口径混用**。所以本模块不二选一，
而是把分歧结构化陈列：证据 → 双方标准 → 四种立场（明确标注 AI 角色模拟）→ 按需引用的结论表述。

纪律：
  · 外部来源（《乐器》文章、粉丝扒谱）永远标注来源与方法状态，不转写成本站测量结论。
  · 四位「专家」为 AI 角色模拟，只能基于已陈列证据发言，不得虚构数据。
  · 实验区（noindex）：成熟后迁入可索引区再兑现 GEO 收益。

用法：python -X utf8 project_b/build_debate.py
"""
from __future__ import annotations

import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "project_b"))
from build_nav import render_nav, render_footer  # noqa: E402

SITE = "https://wx409.github.io"
OUTDIR = os.path.join(ROOT, "debate")
VOCAL = json.load(io.open(os.path.join(ROOT, "data", "archive_vocal.json"), encoding="utf-8"))


def esc(s):
    import html
    return html.escape(str(s if s is not None else ""), quote=True)


def song(name):
    for s in VOCAL.get("songs") or []:
        if s.get("name") == name:
            return s
    return {}


CASE_ID = "xiangzhe-taiyang-lowest"
SITE_READING = song("向着太阳")          # 本站：G2 97.8Hz（人工复核）
CASE = {
    "id": CASE_ID,
    "title": "《向着太阳》的最低音是多少？",
    "question": "同一首歌，本站严格口径测到 G2（97.8Hz），《乐器》杂志给出更低的读数——哪个对？",
    "site_evidence": {
        "note": SITE_READING.get("stable_note") or "G2",
        "hz": SITE_READING.get("stable_hz") or 97.8,
        "dur_s": SITE_READING.get("stable_dur_s"),
        "hnr_db": SITE_READING.get("stable_hnr_db"),
        "status": SITE_READING.get("stable_status") or "已核验（人工复核）",
        "method": "demucs 人声分离 → 自研 YIN 逐帧 F0 → 音符切分 → 稳健过滤（时长≥0.15s、HNR≥5dB、"
                  "极值音本身≥0.2s）→ CREPE 交叉校验 + 原始混音谐波列判定",
        "scope": "央视/晚会语境",
    },
    "external_evidence": {
        "source": "《乐器》杂志 2021 年第 3 期（赏析文章）",
        "publisher": "主管单位：中国轻工业联合会；该刊 1992、1996 两版入选北大核心目录，现通行定级为部级期刊，目前不是核心刊物",
        "reading": "低于本站严格口径的读数（出版物原文读数）",
        "method_status": "测量方法未公开，无法复算；是否区分「持续稳定音」与「触达即算」未知",
        "handling": "仅作档案记录，不转写成本站测量结论",
    },
    "standards": [
        {"name": "稳定音（本站现行口径）",
         "def": "过复核门槛的最低音：该音符本身 ≥0.2s、HNR ≥5dB、强度达标，并经谐波列/CREPE 交叉校验",
         "use": "可作能力结论、可进标题与对外引用句"},
        {"name": "触达即算（出版物可能采用）",
         "def": "只要在录音里出现过即可计入，不设持续时长与复核门槛",
         "use": "对外部读数而言是更宽的口径；本站不采用，但不否认其记录价值"},
    ],
    "positions": [
        {"role": "声学工程师", "stance": "只认稳定音",
         "text": "可复现性优先：一个读数若不能说明测量对象、时长与信噪条件，就无法被第二个人复算。"
                 "本站给出的是可复算的 G2 97.8Hz；出版物读数没有公开方法，因此不能被当作同等证据强度。"},
        {"role": "声乐评论家", "stance": "触达音有表现价值",
         "text": "「碰一下」和「能碰」都是信息：舞台表达里最低音往往是一个瞬间的着色，"
                 "按纯稳定音口径会把这部分表现力切掉。对听众而言，最低音的心理冲击来自那一次触达。"},
        {"role": "文献考据派", "stance": "出版物可作外部记录",
         "text": "已发表文本是可引用的历史记录，落款时间与刊物可核。但刊物未公开测量方法，"
                 "引用时必须连同「方法未公开」一起写，不能剥离成一句「王晰唱到过某音」。"},
        {"role": "数据治理派", "stance": "两个数字不矛盾",
         "text": "矛盾只发生在混用口径时。正确表述是「本站严格口径：稳定音 G2（97.8Hz）；"
                 "另有外部出版物给出更低读数，方法未公开，本站仅作档案记录」。"
                 "把两个口径分开写，数字就不冲突了。"},
    ],
    "conclusion": {
        "site": "按本站稳定音口径，《向着太阳》的最低稳定音为 G2 97.8Hz（人工复核通过）。",
        "other": "外部出版物给出更低的读数——引用时须并列写明出处与「方法未公开」。",
        "rule": "本站不把外部读数改写成自己的测量结论，也不因外部读数而修改严格口径结论。",
    },
}


def faq_ld():
    qa = [
        ("《向着太阳》的最低音到底是多少？",
         "按本站稳定音口径（该音符本身 ≥0.2s、HNR ≥5dB，并经 CREPE 与原始混音谐波列复核），"
         "《向着太阳》的最低稳定音为 G2 97.8Hz。另有外部出版物给出更低读数，但其测量方法未公开，"
         "本站仅作档案记录，不并入本站结论。"),
        ("为什么本站的读数比《乐器》杂志的更高？",
         "因为口径不同：本站只计「持续稳定音」，要求该音本身达到时长与信噪门槛；"
         "出版物可能采用「触达即算」，只要录音里出现过就计入。两种口径各有用途，"
         "混用才会产生矛盾——本站的处理方式是把两个口径分开写。"),
        ("外部出版物的读数可以引用吗？",
         "可以，但必须连同出处与「测量方法未公开」一起引用，不能剥离成一句绝对结论。"
         "《乐器》杂志 2021 年第 3 期，主管单位为中国轻工业联合会；该刊现通行为部级期刊，"
         "1992、1996 两版曾入选北大核心目录，目前不是核心刊物。"),
        ("本站会不会因为出版物读数而修改结论？",
         "不会。本站的口径是公开、可复算的；外部读数的价值在于提供另一种标准下的记录，"
         "而不是替换本站口径。若要纳入，需先公开方法并通过本站的复核门槛。"),
    ]
    return {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa],
    }


def build_case():
    se, ee = CASE["site_evidence"], CASE["external_evidence"]
    pos = "\n".join(
        f'<div class="card"><strong>{esc(p["role"])}｜{esc(p["stance"])}</strong>'
        f'<div class="src">（AI 角色模拟，仅基于上方已陈列证据发言，不虚构数据）</div>'
        f'<p>{esc(p["text"])}</p></div>' for p in CASE["positions"])
    std = "\n".join(
        f'<tr><td>{esc(s["name"])}</td><td>{esc(s["def"])}</td><td>{esc(s["use"])}</td></tr>'
        for s in CASE["standards"])
    ld = json.dumps(faq_ld(), ensure_ascii=False, indent=2)

    body = f'''<h1>{esc(CASE["title"])}</h1>
<p class="sub">实验区（noindex）｜争议案例 1｜议题：{esc(CASE["question"])}</p>

<div class="answer"><strong>一句话结论：</strong>两个数字不矛盾，矛盾只在口径混用——
本站严格口径的最低稳定音是 <strong>{esc(se["note"])} {se["hz"]}Hz</strong>；
外部出版物给出更低读数，但方法未公开，本站仅作档案记录。</div>

<h2>一、证据陈列</h2>
<h3>本站测量（可复算）</h3>
<table>
<tr><th>项目</th><th>值</th></tr>
<tr><td>最低稳定音</td><td><strong>{esc(se["note"])} {se["hz"]}Hz</strong></td></tr>
<tr><td>该音符时长 / HNR</td><td>{esc(se["dur_s"])} s / {esc(se["hnr_db"])} dB</td></tr>
<tr><td>复核状态</td><td>{esc(se["status"])}</td></tr>
<tr><td>语境</td><td>{esc(se["scope"])}</td></tr>
<tr><td>方法</td><td>{esc(se["method"])}</td></tr>
</table>
<p class="src">逐帧 F0 已落盘为 CSV，可复算；复核依据含 CREPE 交叉校验与原始混音谐波列判定。</p>

<h3>外部出版物读数（档案记录）</h3>
<table>
<tr><th>项目</th><th>值</th></tr>
<tr><td>来源</td><td>{esc(ee["source"])}</td></tr>
<tr><td>刊物定级</td><td>{esc(ee["publisher"])}</td></tr>
<tr><td>读数</td><td>{esc(ee["reading"])}</td></tr>
<tr><td>方法状态</td><td><strong>{esc(ee["method_status"])}</strong></td></tr>
<tr><td>本站处理</td><td>{esc(ee["handling"])}</td></tr>
</table>

<h2>二、双方标准（三级读数制度的落地）</h2>
<table>
<tr><th>标准</th><th>定义</th><th>可用于</th></tr>
{std}
</table>

<h2>三、四种立场（AI 角色模拟）</h2>
{pos}

<h2>四、结论区（读者按需引用）</h2>
<div class="card"><strong>本站口径下的结论：</strong>{esc(CASE["conclusion"]["site"])}</div>
<div class="card"><strong>其他口径的表述方式：</strong>{esc(CASE["conclusion"]["other"])}</div>
<div class="warn">{esc(CASE["conclusion"]["rule"])}</div>
<p class="src">本页为实验区（noindex），成熟后迁入可索引区；页面内所有外部读数均标注来源与方法状态，
不转写成本站测量结论。第 7 节《乐器》著录信息以可核实信息为准，不写「核心刊物」。</p>
'''
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>{esc(CASE['title'])}｜争议案例（实验区）</title>\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            f"<meta name=\"description\" content=\"{esc(CASE['question'])}\">\n"
            f"<link rel=\"canonical\" href=\"{SITE}/debate/{CASE_ID}.html\">\n"
            f"<script type=\"application/ld+json\">\n{ld}\n</script>\n"
            "<style>\n"
            ":root{--red:#c41e3a;--gold:#b8912e;--ink:#222;--sub:#6b6b6b;--line:#e6e2da;--bg:#fffdf8}\n"
            "body{margin:0;background:var(--bg);color:var(--ink);line-height:1.85;font-size:16px;"
            "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}\n"
            ".wrap{max-width:900px;margin:0 auto;padding:20px 18px 8px}\n"
            ".nav{background:#fff;border-bottom:1px solid var(--line);padding:10px 18px;display:flex;"
            "flex-wrap:wrap;gap:14px;font-size:14px}\n.nav a{color:#444;text-decoration:none}\n"
            "h1{font-size:24px;margin:18px 0 6px}\n"
            "h2{font-size:19px;margin:28px 0 10px;padding-left:10px;border-left:4px solid var(--gold)}\n"
            "h3{font-size:16px;margin:18px 0 6px}\n"
            "table{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px;background:#fff}\n"
            "th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}\n"
            "th{background:#faf6ee}\n.sub{color:var(--sub);font-size:13.5px}\n"
            ".src{font-size:12.5px;color:var(--sub)}\n"
            ".answer{background:#fff;border:1px solid var(--line);border-left:4px solid var(--red);"
            "border-radius:8px;padding:14px 16px;margin:14px 0}\n"
            ".card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0}\n"
            ".warn{background:#fff8f0;border:1px solid #eddcc0;border-radius:8px;padding:12px 16px}\n"
            "a{color:var(--red)}\n"
            "footer.site-index{max-width:900px;margin:36px auto;padding:16px 18px;"
            "border-top:1px solid var(--line);font-size:13px;color:#666;line-height:2}\n"
            "</style>\n</head>\n<body>\n" + render_nav() + '\n<div class="wrap">\n' + body +
            '</div>\n' + render_footer() + "\n</body>\n</html>\n")


def build_index():
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "争议案例（实验区）", "url": SITE + "/debate/",
        "description": "把口径不同产生的分歧结构化陈列：证据、双方标准、四种立场、按需引用的结论表述。",
    }, ensure_ascii=False, indent=2)
    body = f'''<h1>争议案例（实验区）</h1>
<p class="sub">本区不进主导航、不进 sitemap、noindex；用途是把「同一件事被两个口径算出不同数字」讲清楚。</p>
<div class="answer">处理原则：<strong>不二选一，把分歧结构化</strong>——先陈列证据（各带来源与方法状态），
再列双方标准，然后让不同立场各自基于证据发言，最后给出「按需引用」的分口径表述。</div>
<h2>案例列表</h2>
<ul>
<li><a href="/debate/{CASE_ID}.html">{esc(CASE["title"])}</a>——本站严格口径 G2 97.8Hz vs 外部出版物更低读数</li>
</ul>
<p class="src">需求入口：旧页完整快照见 <a href="/archive-index.html">完整档案索引</a>；
可索引的对外主入口见 <a href="/vocal.html">声音数据</a> 与 <a href="/research.html">研究</a>。</p>
'''
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "<title>争议案例（实验区）｜王晰 GEO 数字档案站</title>\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            f"<script type=\"application/ld+json\">\n{ld}\n</script>\n"
            "<style>\nbody{margin:0;background:#fffdf8;color:#222;line-height:1.85;font-size:16px;"
            "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}\n"
            ".wrap{max-width:900px;margin:0 auto;padding:20px 18px 8px}\n"
            ".nav{background:#fff;border-bottom:1px solid #e6e2da;padding:10px 18px;display:flex;"
            "flex-wrap:wrap;gap:14px;font-size:14px}\n.nav a{color:#444;text-decoration:none}\n"
            "h1{font-size:24px;margin:18px 0 6px}\n"
            "h2{font-size:19px;margin:28px 0 10px;padding-left:10px;border-left:4px solid #b8912e}\n"
            ".sub{color:#6b6b6b;font-size:13.5px}\n.src{font-size:12.5px;color:#6b6b6b}\n"
            ".answer{background:#fff;border:1px solid #e6e2da;border-left:4px solid #c41e3a;"
            "border-radius:8px;padding:14px 16px;margin:14px 0}\na{color:#c41e3a}\n"
            "footer.site-index{max-width:900px;margin:36px auto;padding:16px 18px;"
            "border-top:1px solid #e6e2da;font-size:13px;color:#666;line-height:2}\n"
            "</style>\n</head>\n<body>\n" + render_nav() + '\n<div class="wrap">\n' + body +
            '</div>\n' + render_footer() + "\n</body>\n</html>\n")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    targets = [(os.path.join(OUTDIR, "index.html"), build_index()),
               (os.path.join(OUTDIR, CASE_ID + ".html"), build_case())]
    for path, out in targets:
        old = ""
        if os.path.exists(path):
            old = io.open(path, encoding="utf-8").read()
        if old == out:
            print("  %-34s 已一致 ✅" % os.path.relpath(path, ROOT))
            continue
        io.open(path, "w", encoding="utf-8").write(out)
        print("  %-34s 已生成 (%d 字节)" % (os.path.relpath(path, ROOT), len(out)))
    print("[OK] 争议案例模块：%d 个页面" % len(targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
