# -*- coding: utf-8 -*-
"""模板卡 4 张 + 每周《可用 5 条》规则（数据派生；渲染进 share.html「模板卡」区）。

产物：
  data/share/cut_templates.json     4 张卡（含事实边界/素材边界五行/成熟度）
  data/share/weekly5.json           本周 3 常青 + 2 时效（无时效则 3+1 方法，允许 4 条）
  data/share/corrections.json       最近更正
  data/share/rendered/cut_templates.html   渲染片段（build_share_page 插入）
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data" / "share"
ISSUE = "https://github.com/wx409/wx409.github.io/issues"
VERSION = "v1"
TODAY = date.today().isoformat()


def boundary(facts_ok: str, facts_no: str, screenshot="可（注明出处）", remake="可（非商用、注明）",
             credit="署名：王晰 GEO 数字档案站（wx409.github.io）", share="不可打包外传"):
    return {"可站内阅读": "可", "可截图": screenshot, "可二创": remake,
            "需署名": credit, "不可打包外传": share,
            "事实边界": {"能说": facts_ok, "不能外推": facts_no}}


CARDS = [
 {"id": "dry-vocal", "name": "干声版", "use": "抽掉伴奏，只听人声怎么收",
  "source": "工作室中控台 4 段：5353988652270759（南屏晚钟）/ 5353266315265746（亲密爱人、哭砂、一生中最爱）；"
            "对应音频在 `音域分析\\场次音频\\wav_工作室中控台_分离\\`",
  "steps": ["剪映：原版与分离人声轨同时间线，切换点选同一个字起音前的静音谷底",
            "Premiere：切换处加恒定功率 5ms 交叉淡化，防“咔”",
            "字幕写「伴奏已移除」，不写“清唱”"],
  "spec": "29 秒｜1080×1920｜30fps｜AAC 192k",
  "subs": ["伴奏已移除", "只剩他的声音", "同一段，有伴奏"],
  "platform": "抖音／小红书：前 3 秒即有反差，完播率高",
  "fact": boundary("可写：把伴奏拿掉后，字的收法更清楚；低音位置以实测为准",
                   "不可写“唱到 E2”——南屏晚钟那句 HNR 3.8dB，未过 5dB 门槛，只是干声演示素材"),
  "maturity": "已验证（素材与流程均已跑通）"},
 {"id": "compare", "name": "对比版", "use": "同一句，录音室 vs 现场",
  "source": "`data/archive_stage_tour.json#live_vs_studio_pairs`（69 组；54 组为完整同曲）",
  "steps": ["剪映：按曲目取同一句，各 4 秒（录音室版在前）",
            "Premiere：两声部对齐到同一歌词起音，音量拉平（−1dB 差内）",
            "字幕打「现场 +1.8 半音」并标 n=69"],
  "spec": "20–30 秒｜1080×1920｜30fps",
  "subs": ["录音室", "现场", "他现场反而更高"],
  "platform": "B站／小红书：对比结构天然有讨论点",
  "fact": boundary("可写：69 组同曲配对，现场高出中位 1.8 半音，81% 场次偏高",
                   "不可跨窗口比单点——同曲跨源可差到 9 个半音（片段 vs 整曲），只能比区间"),
  "maturity": "已验证（配对数据在库）"},
 {"id": "timeline", "name": "时间线版", "use": "同一首歌，隔几年再唱",
  "source": "定番曲：Besame Mucho（跨 4 巡 13 场）／让她降落（3 巡 20 场）／心动（3 巡 20 场）；"
            "素材见 `data/setlists.json` 与现场层对应场次",
  "steps": ["剪映：按年份切 3 段、各 4 秒，同位置对齐",
            "Premiere：加年份字幕条，不做变速",
            "导出前核对每段确实是该年份（别用同名不同场）"],
  "spec": "12–15 秒｜1080×1920｜30fps",
  "subs": ["2019", "2021", "2024"],
  "platform": "小红书／视频号：时间跨度是情绪点",
  "fact": boundary("可写：同一首定番在不同巡次都唱，位置有移动（跨巡中位差 1.70 半音）",
                   "不可写“越唱越好”——没有质量评分，只有读数差"),
  "maturity": "待验证（需确认每段年份与音源）"},
 {"id": "long-tone", "name": "长音版", "use": "一口气 16 秒半",
  "source": "《我真的受伤了》现场 D2，16.5 秒（`data/archive_long_notes.json#top[0]`）",
  "steps": ["剪映：原速不加速，保留换气声",
            "Premiere：加计时器字幕，从 0 走到 16.5",
            "导出前确认没有拼贴（一次连续发声）"],
  "spec": "20 秒｜1080×1920｜30fps",
  "subs": ["0 秒", "8 秒", "16.5 秒"],
  "platform": "抖音／B站：计时器结构自带悬念",
  "fact": boundary("可写：现场连续发声 16.5 秒，D2，音高不移动",
                   "不可写“无人能及”；也不得把多段拼成一条"),
  "maturity": "已验证（长音榜已落库）"},
]

for c in CARDS:
    c["boundary"] = c.pop("fact")
    c["correction_line"] = f"版本 {VERSION} ｜ 更新 {TODAY} ｜ 纠错：{ISSUE}"

WEEKLY = {
 "generated_at": TODAY, "rule": "默认 3 常青 + 2 时效；无时效料时 3 常青 + 1 方法（共 4 条），不凑数",
 "items": [
   {"kind": "常青", "hook": "他的低音不是偶尔为之：72 首里 44 首低于 E2",
    "asset": "低音线卡片（card_low_baseline）", "platform": "小红书",
    "fact_boundary": "可写 44/72；不可写“华语最低”", "material_boundary": "可截图可二创，需署名",
    "risk": "低"},
   {"kind": "常青", "hook": "一口气 16.5 秒，音高不移动",
    "asset": "长音卡片（card_long_tone）", "platform": "抖音",
    "fact_boundary": "可写 16.5s/D2；不可写“无人能及”", "material_boundary": "可截图，需署名", "risk": "低"},
   {"kind": "常青", "hook": "现场他反而比唱片高一点",
    "asset": "配对卡片（card_pair_54）", "platform": "B站",
    "fact_boundary": "可写 +1.8 半音/81%；不可跨窗口比单点", "material_boundary": "可二创非商用", "risk": "中"},
   {"kind": "方法", "hook": "怎么核一个数：从 CSV 到能引用的一句",
    "asset": "share.html 口径段", "platform": "小红书",
    "fact_boundary": "只讲方法，不涉结论", "material_boundary": "可截图，需署名", "risk": "低"},
 ]}
CORR = {"items": [
   {"date": "2026-10-24", "what": "把“八年”更正为“十年”",
    "detail": "颤音跨度按 8 张录音室作品计（2014–2024），原文写“八年”，已改为“十年”。",
    "status": "已更正"}],
   "issue": ISSUE}


def card_html(c: dict) -> str:
    b = c["boundary"]
    mb = b
    rows = "".join(f"<li>{html.escape(k)}：{html.escape(str(v))}</li>" for k, v in
                   ((x, mb[x]) for x in ("可站内阅读", "可截图", "可二创", "需署名", "不可打包外传")))
    steps = "".join(f"<li>{html.escape(s)}</li>" for s in c["steps"])
    subs = "".join(f"<code>{html.escape(s)}</code> " for s in c["subs"])
    return f"""<section class="tpl-card" id="tpl-{c['id']}">
<h3>{html.escape(c['name'])}（{html.escape(c['maturity'])}）</h3>
<p><b>用途：</b>{html.escape(c['use'])}</p>
<p><b>素材从哪拿：</b>{html.escape(c['source'])}</p>
<p><b>怎么剪：</b></p><ol>{steps}</ol>
<p><b>时长与比例：</b>{html.escape(c['spec'])}</p>
<p><b>字幕可照抄：</b>{subs}</p>
<p><b>发哪个平台：</b>{html.escape(c['platform'])}</p>
<p><b>事实边界：</b>{html.escape(b['事实边界']['能说'])}；<b>不能外推：</b>{html.escape(b['事实边界']['不能外推'])}</p>
<p><b>素材边界：</b><ul>{rows}</ul></p>
<p class="meta">{html.escape(c['correction_line'])}</p>
</section>"""


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    (D / "cut_templates.json").write_text(json.dumps({"version": VERSION, "updated": TODAY,
                                                     "issue": ISSUE, "cards": CARDS},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    (D / "weekly5.json").write_text(json.dumps(WEEKLY, ensure_ascii=False, indent=1), encoding="utf-8")
    (D / "corrections.json").write_text(json.dumps(CORR, ensure_ascii=False, indent=1), encoding="utf-8")
    frag = ("<div class='tpl-wrap'><h2>模板卡</h2>"
            "<p class='meta'>四张卡都写明“能说什么、不能外推什么”。素材与流程均已在本机跑通，"
            f"缺的会标“待验证”。纠错入口：<a href='{ISSUE}'>{ISSUE}</a></p>"
            + "".join(card_html(c) for c in CARDS) + "</div>")
    (D / "rendered").mkdir(exist_ok=True)
    (D / "rendered" / "cut_templates.html").write_text(frag, encoding="utf-8")
    print("[ok] cut_templates.json / weekly5.json / corrections.json / rendered/cut_templates.html")
    print("    卡：", "、".join(c["name"] for c in CARDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
