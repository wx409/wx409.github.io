# -*- coding: utf-8 -*-
"""Phase 0：声音素材库 —— 目录 + 媒体清单 + 出处元数据（先核验，不下载）。

- 建统一目录 E:\wx\声音素材库\{manifest,media,transcripts,meta}
- 用各平台公开 API 核验 URL、取标题/时长/日期（B站 view API、ximalaya/netease 尽量）
- 产出 manifest/media_manifest.json（机读，带出处/授权/状态），供后续下载与转写

用法：python -X utf8 project_b\build_media_manifest.py [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = r'E:\wx\声音素材库'
DIRS = ['manifest', 'media', 'transcripts', 'meta']

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')


def get_json(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://www.bilibili.com/'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8', 'replace'))
    except Exception as e:
        return {'_err': str(e)[:120]}


# ---------------------------------------------------------------- 素材清单
# 每项：id / title / platform / url / kind / series / 出处说明
ITEMS = [
    # ---- B站（可自动下载）----
    dict(id='yytsg_bili', title='王晰的音乐图书馆（合集 8P）', platform='bilibili',
         url='https://www.bilibili.com/video/BV1nt411D7FQ', kind='video',
         series='王晰的音乐图书馆', note='B站饭制合集（原喜马拉雅已下架）；UP 多艾红；av37228161'),
    dict(id='xwntj_bili', title='王晰｜晰望你听见（深夜晚安电台，合集）', platform='bilibili',
         url='https://www.bilibili.com/video/BV1KB4y1v7Au', kind='video',
         series='晰望你听见', note='快手原节目；B站饭制合集（b23.tv/CW8PsxD → BV1KB4y1v7Au 已解析核验）'),
    # ---- 喜马拉雅（单条读诗/读信）----
    dict(id='xmly_544193351', title='想念雪', platform='ximalaya',
         url='https://www.ximalaya.com/sound/544193351', kind='audio',
         series='散落读诗', note='2022-06-18 用户提供'),
    dict(id='xmly_283181641', title='王晰：世间万物千景，一生恍惚而过', platform='ximalaya',
         url='https://www.ximalaya.com/sound/283181641', kind='audio',
         series='散落读诗', note='2020-04-14 用户提供'),
    dict(id='xmly_382124733', title='《三体·黑暗森林》第四季第16集 对决（片尾人物曲《罗辑》）', platform='ximalaya',
         url='https://www.ximalaya.com/sound/382124733', kind='audio',
         series='散落读诗', note='2021-02-03 用户提供'),
    dict(id='xmly_623231068', title='歌手王晰低音炮朗读《从前慢》《哪有你这样你》', platform='ximalaya',
         url='https://www.ximalaya.com/sound/623231068', kind='audio',
         series='散落读诗', note='2023-04-03 用户提供'),
    # ---- 网易云 DJ 电台（30 集，JSON-LD 可直读）----
    dict(id='netease_dj_792978415', title='王晰的低音时间（DJ 电台存档 30 集）', platform='netease',
         url='https://music.163.com/djradio?id=792978415', kind='audio',
         series='王晰的低音时间', note='饭制存档（账号「王晰的小电台」）；内容与「音乐图书馆」有对应'),
    # ---- 需用户 console / 特殊处理 ----
    dict(id='xmly_haomeng11', title='我们的好梦时刻 第11期：白落梅《不败于岁月，不输于山河》', platform='ximalaya',
         url='', kind='audio', series='我们的好梦时刻',
         note='2020-04-14；节目页 URL 未获得（仅微博宣传帖可读全文），需在喜马拉雅 App 内搜索'),
    dict(id='weibo_kangyi_jiashu', title='抗疫家书（朗读）', platform='weibo',
         url='https://weibo.com/6315203766/4480190744624874', kind='video',
         series='散落读诗', note='2020-03-08；微博需登录（cookie 已在 wb.txt）'),
    dict(id='weibo_520_shencongwen', title='520 沈从文情书片段朗读（「我行过许多地方的桥…」）', platform='weibo',
         url='https://video.weibo.com/show?fid=1034:4506697763586114', kind='video',
         series='散落读诗', note='2020-05-20 工作室微博'),
    dict(id='lizhi_diyin', title='王晰的低音时间（荔枝FM 63 集）', platform='lizhi',
         url='https://www.lizhi.fm/user/2519182403760091180', kind='audio',
         series='王晰的低音时间', note='需浏览器 console 取接口（Next.js + 签名）；纯 HTTP 不可得'),
    dict(id='qq_citywalk', title='城市漫行（QQ音乐电台 25 周）', platform='qqmusic',
         url='https://y.qq.com/n/ryqq/albumDetail/003tbIDl16Y0XE', kind='audio',
         series='城市漫行', note='2021-02；专辑页 302，需用户 console 或 QQ音乐客户端接口'),
    dict(id='elle_wanan', title='ELLE007 王晰的晚安图书馆（7 期）', platform='weibo',
         url='https://weibo.com/2827620084/4693045729824142', kind='audio',
         series='ELLE007 晚安图书馆',
         note='发刊词+第1~7期共 8 条微博；需登录（cookie 已在 wb.txt）'),
    # ELLE 逐期（yt-dlp 对微博有效，已验证发刊词 8.3MB）
    dict(id='elle_p1', title='ELLE007 晚安图书馆 第1期', platform='weibo',
         url='https://weibo.com/2827620084/4695935270257911', kind='audio',
         series='ELLE007 晚安图书馆', note='第1期'),
    dict(id='elle_p2', title='ELLE007 晚安图书馆 第2期', platform='weibo',
         url='https://weibo.com/2827620084/4708598360051220', kind='audio',
         series='ELLE007 晚安图书馆', note='第2期'),
    dict(id='elle_p3', title='ELLE007 晚安图书馆 第3期', platform='weibo',
         url='https://weibo.com/2827620084/4722751702567391', kind='audio',
         series='ELLE007 晚安图书馆', note='第3期'),
    dict(id='elle_p4', title='ELLE007 晚安图书馆 第4期', platform='weibo',
         url='https://weibo.com/2827620084/4746303512512402', kind='audio',
         series='ELLE007 晚安图书馆', note='第4期'),
    dict(id='elle_p5', title='ELLE007 晚安图书馆 第5期', platform='weibo',
         url='https://weibo.com/2827620084/5258305620151102', kind='audio',
         series='ELLE007 晚安图书馆', note='第5期'),
    dict(id='elle_p6', title='ELLE007 晚安图书馆 第6期', platform='weibo',
         url='https://weibo.com/2827620084/5266261169672160', kind='audio',
         series='ELLE007 晚安图书馆', note='第6期'),
    dict(id='elle_p7', title='ELLE007 晚安图书馆 第7期', platform='weibo',
         url='https://weibo.com/2827620084/5287004691764499', kind='audio',
         series='ELLE007 晚安图书馆', note='第7期')
]


def verify_bilibili(url):
    """用 public view API 取标题/时长/分P。"""
    import re
    m = re.search(r'(BV[0-9A-Za-z]+)', url)
    if not m:
        return {}
    bv = m.group(1)
    d = get_json('https://api.bilibili.com/x/web-interface/view?bvid=%s' % bv)
    if d.get('code') != 0:
        return {'error': str(d.get('message'))[:80]}
    data = d.get('data') or {}
    pages = [{'index': p.get('page'), 'title': p.get('part'),
              'duration_s': p.get('duration')} for p in (data.get('pages') or [])]
    return {'bvid': bv, 'title': data.get('title'), 'owner': (data.get('owner') or {}).get('name'),
            'pubdate': datetime.fromtimestamp(data.get('pubdate') or 0).strftime('%Y-%m-%d'),
            'duration_s': data.get('duration'), 'pages': pages, 'n_pages': len(pages)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    for d in DIRS:
        os.makedirs(os.path.join(LIB, d), exist_ok=True)

    # 保留上一轮已有的下载记录（local_files/status/blocked_reason）——
    # 2026-09-14 踩坑：重建 manifest 会把下载记录抹掉，导致"下过了却显示未下载"。
    old_doc = {}
    _p = os.path.join(LIB, 'manifest', 'media_manifest.json')
    if os.path.exists(_p):
        try:
            old_doc = json.loads(io.open(_p, encoding='utf-8').read())
        except Exception:
            old_doc = {}
    old_by_id = {x.get('id'): x for x in (old_doc.get('items') or []) if isinstance(x, dict)}

    media_dir = os.path.join(LIB, 'media')
    out = []
    for it in ITEMS:
        rec = dict(it)
        rec.setdefault('status', 'pending')
        rec['verified'] = {}
        prev = old_by_id.get(it['id']) or {}
        for k in ('local_files', 'downloaded_at', 'status', 'blocked_reason'):
            if prev.get(k):
                rec[k] = prev[k]
        # 从磁盘回扫（目录名 = item id），确保 manifest 与磁盘一致
        d = os.path.join(media_dir, it['id'])
        if os.path.isdir(d):
            files = []
            for root, _dirs, fs in os.walk(d):
                for f in fs:
                    p2 = os.path.join(root, f)
                    files.append({'file': os.path.relpath(p2, LIB).replace('\\', '/'),
                                  'size_mb': round(os.path.getsize(p2) / 1e6, 1)})
            if files:
                rec['local_files'] = sorted(files, key=lambda z: z['file'])
                if rec.get('status') in (None, 'pending', 'verified'):
                    rec['status'] = 'downloaded'
        if it['platform'] == 'bilibili' and it['url']:
            v = verify_bilibili(it['url'])
            rec['verified'] = v
            if v.get('title'):
                rec['title_official'] = v['title']
                if not rec.get('local_files'):
                    rec['status'] = 'verified'
                rec['subitems'] = [
                    dict(id='%s_p%02d' % (it['id'], p['index']),
                         title=p['title'], page=p['index'], duration_s=p['duration_s'])
                    for p in v.get('pages') or []]
        out.append(rec)

    doc = {
        'schema': 'media_manifest v1',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'library_root': LIB,
        'note': ('王晰声音素材库清册：视频/音频/电台节目的出处与核验状态。'
                 '媒体文件仅本地留存，不入 git、不上线、不二次分发。'),
        'discipline': [
            '每条必须带 source_url 与出处说明；核验不到的标 status=pending 并写明原因。',
            '下载后转写为文字全文，字幕/转写稿可入库；媒体原件只留本地。',
            '官方声称的期数（荔枝 63 / 城市漫行 25 / ELLE 7）未核验前不得当既成事实。',
        ],
        'counts': {
            'items': len(out),
            'verified': sum(1 for x in out if x['status'] == 'verified'),
            'pending': sum(1 for x in out if x['status'] != 'verified'),
            'subitems': sum(len(x.get('subitems') or []) for x in out),
        },
        'items': out,
    }
    p = os.path.join(LIB, 'manifest', 'media_manifest.json')
    old = io.open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    new = json.dumps(doc, ensure_ascii=False, indent=1)
    if old == new:
        print('[OK] manifest 已一致')
        return 0
    if a.check:
        print('[FAIL] manifest 需更新')
        return 1
    io.open(p, 'w', encoding='utf-8').write(new)
    print('=' * 70)
    print('声音素材库 manifest')
    print('=' * 70)
    print('  目录:', LIB)
    print('  条目 %d（已核验 %d / 待核 %d）| 分P 子项 %d'
          % (doc['counts']['items'], doc['counts']['verified'],
             doc['counts']['pending'], doc['counts']['subitems']))
    for x in out:
        v = x.get('verified') or {}
        print('  %-24s %-10s %-8s %s' % (
            x['id'], x['platform'], x['status'],
            (v.get('title') or x['title'])[:44]))
        if v.get('error'):
            print('        ⚠️', v['error'])
        if v.get('n_pages'):
            print('        %d P / %s 秒 / UP %s / %s'
                  % (v['n_pages'], v.get('duration_s'), v.get('owner'), v.get('pubdate')))
    print('\n[写]', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
