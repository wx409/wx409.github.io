# -*- coding: utf-8 -*-
import json
d = json.load(open(r'E:\wx\私有工具\weibo_merged\_event_candidates.json', encoding='utf-8'))
pd = [i for i in d['items'] if i['cat'] == '待定']
print(f'待定 {len(pd)} 条，抽样15条:')
for i in pd[:15]:
    print(f"  [{i['source']}] {i['date']} {i['text'][:45]}")
