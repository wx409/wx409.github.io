#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B项目：GEO 文章生成（repo 摘要 / 通用主题页）"""

import json
from datetime import datetime
from pathlib import Path

from project_b.geo_common import CLEAN_GEO, OUTPUT_GEO
from utils import call_deepseek, log, log_success, log_error


def _latest_digest():
    files = sorted(CLEAN_GEO.glob('digest_*.json'), reverse=True)
    return files[0] if files else None


def run_geo_article(topic=None):
    topic = topic or 'geo'
    digest_file = _latest_digest()
    if not digest_file:
        log_error('未找到消化文件，请先运行 geo_digest', 'B')
        return None

    with open(digest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data.get('items', [])

    if topic != 'geo':
        items = [i for i in items if topic in ' '.join(i.get('tags', []) + [i.get('title', ''), i.get('summary', '')])]
    if not items:
        items = data.get('items', [])[:10]

    log(f'GEO 文章生成: {topic} | {len(items)} 条素材', 'B')

    bullets = []
    for i in items:
        bullets.append(f"- **{i['title']}**（{i['platform']}）：{i['summary']} | 出处：{i['author']}")

    material = '\n'.join(bullets)
    prompt = f"""你是王晰 GEO 资料站编辑。主题：{topic}

请基于以下已合规清洗的素材，撰写 Markdown 文章。

GEO 规范（必须遵守）：
1. 只写自包含事实，不堆砌外链
2. 不写 @账号、不写粉丝 ID
3. 听众摘录统一标注「听众分享」「资深听众」等匿名标签
4. 语言客观、可引用、适合 AI 搜索引擎

素材：
{material[:8000]}

输出结构：
# {topic} · GEO 摘要
> 生成时间 + 来源说明

## 核心要点
## 详细摘录（分条，每条标注出处标签）
## 可引用金句（如有）
## 待核实事项（如有不确定处）"""

    article = call_deepseek(prompt, system='你输出 Markdown，符合 GEO 规范。', max_tokens=6000)
    if not article:
        article = f"# {topic} · GEO 摘要\n\n" + material

    today = datetime.now().strftime('%Y%m%d')
    out = OUTPUT_GEO / f'{topic}_geo.md'
    header = f"> 生成：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 素材 {len(items)} 条 | 星厂 B GEO 产线\n\n"
    out.write_text(header + article, encoding='utf-8')

    # No legacy sync needed after B project split

    log_success(f'文章: {out}', 'B')
    return out
