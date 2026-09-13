# -*- coding: utf-8 -*-
"""第五阶段（金句档案）：在 data/quotes.json 增加 golden_quotes 图层（幂等）。

设计（第一性原理）：
  · quotes.json 原有字段（现场 Talk 原话，带时间戳/素材来源/verified）**保持不变**，
    它同时是 build_kb_graph.py 的金句实体来源、render_quotes_wall.py 的金句墙数据源。
  · 新增 golden_quotes 段承载"跨来源金句档案"：本人微博/论坛/媒体/权威点评/现场 Talk，
    每条带 id / text / date / source / source_url / context / theme / related_page / evidence_level。
  · 纪律：可核实来源写明确出处；不可核实的标 evidence_level="待核实" 并单独列出，不混入引用。

用法：python -X utf8 project_b/build_golden_quotes.py [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "quotes.json")

SCHEMA = ("golden_quotes v1：id/text/date/source/source_url/context/theme/related_page/evidence_level。"
          "evidence_level ∈ {本人, 权威点评, 媒体, 第三方, 现场Talk, 待核实}。"
          "「权威点评」为外部原话档案记录，不构成本站结论；「待核实」条目不得用于对外引用句。")

GOLDEN = [
    {
        "id": "gq-2015-11-30-lowc",
        "text": "这次不仅 Low C 几乎到了自己极限，最低音低过 Low C，不说全球，在亚洲这张专辑可以说是最低音的一张。",
        "date": "2015-11-30",
        "source": "王晰本人微博（录制第二张专辑期间）",
        "source_url": "",
        "context": "录制《Low C的诱惑Ⅱ》期间自述；与本站全量实测方向一致——72 首录音室曲目中 4 首最低稳定音达 B1（61.5–61.9Hz），低于 Low C（C2 65.4Hz）。",
        "theme": "低音自述",
        "related_page": "vocal.html",
        "evidence_level": "本人",
    },
    {
        "id": "gq-2014-09-28-forum-lowc",
        "text": "王晰唱得最低；王晰常徘徊在 85Hz 附近起步，赵鹏 100Hz 点到为止。",
        "date": "2014-09-28",
        "source": "家电论坛 Hi-Fi 版帖《王晰、赵鹏、Lee Lessack with Ken page，谈谈〈Low C的诱惑〉》（作者 青岛子弹）",
        "source_url": "https://www.jdbbs.com/forum.php?mobile=2&mod=viewthread&tid=5126499",
        "context": "三张唱片对比（王晰《鸿雁》/赵鹏《外婆的澎湖湾》/Lee Lessack《Vincent》）。属第三方听感/频谱估计，非本站口径；本站已复测《鸿雁》人声最低稳定音 F2 86.5Hz，与当年听感吻合。",
        "theme": "同台对比（第三方）",
        "related_page": "vocal.html",
        "evidence_level": "第三方",
    },
    {
        "id": "gq-2015-09-03-cctv4",
        "text": "谁终将用最低音挑战你的耳朵。",
        "date": "2015-09-03",
        "source": "央视四套《中国文艺·低音更疯狂》节目宣发",
        "source_url": "",
        "context": "低音王子王晰与人声低音炮赵鹏等同台；宣发语为媒体表述，非测量结论。",
        "theme": "媒体表述",
        "related_page": "vocal.html",
        "evidence_level": "媒体",
    },
    {
        "id": "gq-yaofeng-guben",
        "text": "作为 Bass-baritone 的话，在中国本身就不多，这是流行圈内的，恐怕就是孤本了。",
        "date": "",
        "source": "姚峰（深圳音协主席）",
        "source_url": "",
        "context": "外部权威定性原话，本站作档案记录并直接引用，不据此做排名或唯一性断言。",
        "theme": "权威定性",
        "related_page": "vocal.html",
        "evidence_level": "权威点评",
    },
    {
        "id": "gq-liaochangyong-gaoshan",
        "text": "男生就像一座高山一样，稳稳地……这个用男低音是特别好的。",
        "date": "",
        "source": "廖昌永（上海音乐学院院长）",
        "source_url": "",
        "context": "外部权威点评原话，作档案记录。",
        "theme": "权威定性",
        "related_page": "vocal.html",
        "evidence_level": "权威点评",
    },
    {
        "id": "gq-caution-2half-octave",
        "text": "（撒贝宁语）两个半八度。",
        "date": "",
        "source": "节目主持人撒贝宁口语表述",
        "source_url": "",
        "context": "⚠️ 已核实为口语、不准确：实测男女声叠加约 3.3 个八度。收录此条是为了防止二次传播误引——引用音域跨度请以实测口径为准。",
        "theme": "防误引",
        "related_page": "vocal.html",
        "evidence_level": "媒体",
    },
    {
        "id": "gq-2015-11-30-alt",
        "text": "正式作品最低《葬心》B1、正式现场最低《月光》开口 B1。",
        "date": "",
        "source": "豆瓣「晰晰音域整理帖」（粉丝扒谱）",
        "source_url": "",
        "context": "粉丝整理，方法未公开、未标明时间；site 实测未把《葬心》纳入已核验低音口径。列此仅作互证线索。",
        "theme": "公开资料互证",
        "related_page": "vocal.html",
        "evidence_level": "待核实",
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    data = json.load(io.open(PATH, encoding="utf-8"))
    data["golden_quotes_schema"] = SCHEMA
    data["golden_quotes"] = GOLDEN
    data["golden_quotes_count"] = len(GOLDEN)
    out = json.dumps(data, ensure_ascii=False, indent=1)

    old = io.open(PATH, encoding="utf-8").read()
    if old.strip() == out.strip():
        print("[OK] quotes.json golden_quotes 已一致（%d 条）" % len(GOLDEN))
        return 0
    if args.check:
        print("[FAIL] quotes.json 需更新")
        return 1
    io.open(PATH, "w", encoding="utf-8").write(out)
    print("[OK] 已写入 data/quotes.json：golden_quotes %d 条（原有现场 Talk %d 条保持不变）"
          % (len(GOLDEN), len(data.get("quotes") or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
