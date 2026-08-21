# -*- coding: utf-8 -*-
"""qa_bank.json 定期更新检测：对比 dashboard 数据指纹，找出因数据变化而过期的问答。
省 token：只检测变化、只标记需更新的条目，不盲目重跑 LLM。
用法：python update_qa_bank.py  （或接 auto_update 定时跑）
"""
import json, os, hashlib
from datetime import datetime

DASH = r'D:\wx409.github.io\dashboard\dashboard_data.json'
QABANK = r'D:\wx409.github.io\data\qa_bank.json'

def fingerprint(dash):
    """从 dashboard 提取影响问答答案的数据指纹。"""
    tse = dash.get('tour_song_effects', [])
    # 每场演出：date + content_type + 三口径（这些是答案引用的核心数值）
    sig = []
    for e in sorted(tse, key=lambda x: x.get('date') or ''):
        sig.append('%s|%s|%s|%s|%s' % (
            e.get('date'), e.get('content_type'),
            e.get('total_uplift'), e.get('setlist_uplift'), e.get('radiance_uplift')))
    # 全站概览关键值
    ov = dash.get('daily_listen_overview', {})
    sig.append('active=%s' % ov.get('active_count'))
    raw = '||'.join(sig)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def main():
    if not os.path.exists(DASH):
        print('未找到 dashboard_data.json，跳过。')
        return
    dash = json.load(open(DASH, encoding='utf-8'))
    fp = fingerprint(dash)

    qa = json.load(open(QABANK, encoding='utf-8')) if os.path.exists(QABANK) else {'meta': {}, 'items': []}
    old_fp = qa.get('meta', {}).get('data_fingerprint', '')

    if old_fp == fp:
        print('数据指纹无变化，问答库无需更新。')
        return

    print('数据已变化，需要复核问答库。')
    print('旧指纹:', old_fp[:12], '→ 新指纹:', fp[:12])
    print('影响的问答条目（引用演出三口径/内容形态的）：')
    # 简单提示：所有引用 content_type 或三口径的问答都可能过期
    affected = []
    for it in qa.get('items', []):
        txt = (it.get('answer', '') + ' '.join(it.get('keywords', [])))
        if any(k in txt for k in ['个人巡回', '歌舞剧', '音乐节', '演唱会', '晚会', '辐射带动', '溢出', '衰减', 'content_type', '三口径']):
            affected.append(it.get('id', ''))
    print('  疑似需更新:', affected if affected else '（无明确引用，但建议整体复核）')
    print()
    print('提示：把 data_fingerprint 更新后，再针对 affected 条目重新调 DeepSeek 生成答案。')

if __name__ == '__main__':
    main()
