# -*- coding: utf-8 -*-
"""微博 → 知识库 自动更新流水线（一键跑完整流程，增量、省 token）。
流程：
  1. 增量抓取本人/工作室微博（只抓归档里没有的新 mid）
  2. 对新增内容用 DeepSeek 提取事件（LLM 只处理新增）
  3. 更新 causality_kb.json（新事件并入）
  4. rebuild 大屏 + push（SSH）

用法：python project_b/pipeline_weibo_update.py [--studio|--self|--both] [--no-push]
"""
import os, re, json, sys, time, datetime
from pathlib import Path

BASE = Path(r'E:\wx\私有工具\weibo_merged')
STUDIO_UID = '7215995153'
SELF_UID = '1292815744'
COOKIE_FILE = Path(r'E:\wx\私有工具\weibo_cookies.txt')
DASH_GEN = Path(r'E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py')
KB = Path(r'E:\wx\私有工具\weibo_merged\causality_kb.json')
HDRS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15', 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://m.weibo.cn/'}


def log(*a):
    print('[%s]' % datetime.datetime.now().strftime('%H:%M:%S'), *a, flush=True)


def get_cookie():
    c = open(COOKIE_FILE, encoding='utf-8', errors='ignore').read().strip()
    HDRS['Cookie'] = c
    return c


def fetch_list(uid, since=None):
    """翻一页列表，返回 (cards, since_id)"""
    import urllib.request, urllib.parse, urllib.error
    base = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=%s&containerid=107603%s' % (uid, uid)
    url = base + ('&since_id=%s' % since if since else '')
    req = urllib.request.Request(url, headers=HDRS)
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 432:
            raise RuntimeError(
                '微博风控(HTTP 432)：m.weibo.cn 已标记当前 IP/账号（多为近期高频抓取触发，'
                '如 weibo_proxy 全量抓取）。请停止一切微博请求 24-48 小时后重试，'
                '期间勿跑 weibo_proxy / collect_show_feedback / 本管线')
        raise
    info = d.get('data', {}).get('cardlistInfo', {})
    cards = [c for c in d.get('data', {}).get('cards', []) if c.get('card_type') == 9]
    return cards, info.get('since_id')


def existing_mids(archive_dir):
    """从归档文件夹名收集已有 mid 集合（16位数字 mid）。"""
    mids = set()
    d = Path(archive_dir)
    if d.exists():
        for name in os.listdir(d):
            # 文件夹名格式: YYYYMMDD_<16位mid>_<摘要>
            m = re.match(r'\d{8}_(\d{16})_', name)
            if m:
                mids.add(m.group(1))
    return mids


def crawl_incremental(uid, archive_dir, max_pages=30):
    """增量抓取：翻页，只保留归档里没有的 mid。"""
    existing = existing_mids(archive_dir)
    log('已有归档 mid 数: %d (%s)' % (len(existing), archive_dir))
    new_items = []
    seen = set()
    since = None
    for page in range(1, max_pages + 1):
        try:
            cards, since = fetch_list(uid, since)
        except Exception as e:
            log('翻页失败 page%d: %s' % (page, repr(e)[:60]))
            break
        added = 0
        for c in cards:
            mb = c.get('mblog', {})
            mid = mb.get('mid')
            if not mid or mid in existing or mid in seen:
                continue
            seen.add(mid)
            new_items.append({
                'mid': mid,
                'uid': uid,
                'created_at': mb.get('created_at', ''),
                'text': re.sub(r'<[^>]+>', '', mb.get('text') or ''),
                'url': 'https://m.weibo.cn/status/' + mid,
            })
            added += 1
        log('page%d: 新增 %d, 累计新 %d' % (page, added, len(new_items)))
        if not since or added == 0:
            break
        time.sleep(1.0)
    return new_items


def save_items(items, uid, archive_dir):
    """把新微博存为 日期_mid_摘要/content.txt，返回创建的文件夹名列表。"""
    import datetime as dt
    saved_folders = []
    for it in items:
        # created_at: Mon Dec 16 12:00:21 +0800 2024
        try:
            t = dt.datetime.strptime(it['created_at'], '%a %b %d %H:%M:%S %z %Y')
            ymd = t.strftime('%Y%m%d')
        except Exception:
            ymd = '00000000'
        # 摘要（去非法字符，限长；空则用 mid 兜底）
        summary = re.sub(r'[\\/:*?"<>|\s#\[\]#@]', '', it['text'])[:25]
        if not summary:
            summary = '微博'
        folder = '%s_%s_%s' % (ymd, it['mid'], summary)
        d = Path(archive_dir) / folder
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / 'content.txt').write_text(it['text'], encoding='utf-8')
            (d / 'meta.json').write_text(json.dumps({
                'mid': it['mid'], 'date': ymd, 'text': it['text'],
                'source': '微博', 'url': it['url'], 'uid': uid,
            }, ensure_ascii=False, indent=1), encoding='utf-8')
            saved_folders.append(folder)
        except Exception as e:
            log('存文件夹失败 %s: %s' % (folder, repr(e)[:50]))
    return saved_folders


def extract_new_events(archive_dir, new_folders):
    """对【本轮新增的】微博做 LLM 事件提取（只处理新增，省 token），追加进 _events_extracted.json。"""
    import urllib.request
    events_out = BASE / '_events_extracted.json'
    existing = {}
    if events_out.exists():
        try:
            existing = json.loads(events_out.read_text(encoding='utf-8'))
        except Exception:
            existing = {}

    new_texts = []
    d = Path(archive_dir)
    for folder in new_folders:
        ct = d / folder / 'content.txt'
        if not ct.exists():
            continue
        m = re.match(r'(\d{8})_\d{16}_', folder)
        ymd = m.group(1) if m else '00000000'
        txt = ct.read_text(encoding='utf-8', errors='ignore').strip()
        if txt:
            new_texts.append({'date': '%s-%s-%s' % (ymd[:4], ymd[4:6], ymd[6:8]), 'text': txt, 'folder': folder})

    if not new_texts:
        log('事件提取：无新增文本')
        return 0

    # 取 DeepSeek key：优先环境变量 DEEPSEEK_API_KEY（由 secret_vault run 注入），
    # 其次 gitignored 私有配置 temp/deepseek_key.json（兼容旧路径）
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        kp = Path(r'D:\wx409.github.io\temp\deepseek_key.json')
        if kp.exists():
            try:
                key = json.loads(kp.read_text(encoding='utf-8')).get('api_key', '').strip()
            except Exception:
                pass
    if not key:
        log('事件提取：无 DeepSeek key，跳过（仅归档）')
        return 0

    # 逐条调用（每条约1次 LLM，只处理新增）
    added = 0
    for it in new_texts:
        key_ev = '%s_%s' % (it['date'], it['text'][:8])
        if key_ev in existing:
            continue
        prompt = (
            "你是档案结构化提取器。下面是一条歌手王晰的微博，请提取其中「事件」信息，输出 JSON（只输出JSON）：\n"
            '{"date":"事件日期YYYY-MM-DD","category":"巡演|演出|新歌|其他","title":"事件标题≤20字",'
            '"city":"城市(无则空)","venue":"场馆(无则空)","song":"相关歌曲(无则空)",'
            '"tour":"巡演名(无则空)","summary":"一句话要点≤40字"}\n'
            "不要臆造，只依据微博。若无有效事件返回空字段。\n微博内容：\n" + it['text'][:1200]
        )
        try:
            body = json.dumps({
                'model': 'deepseek-v4-flash',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.2,
                'response_format': {'type': 'json_object'},
            }).encode('utf-8')
            req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions', data=body, headers={
                'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode('utf-8'))
            content = r['choices'][0]['message']['content'].strip()
            import re as _re
            content = _re.sub(r'^```(?:json)?\s*|\s*```$', '', content)
            parsed = json.loads(content)
            existing[key_ev] = {
                'event_key': key_ev, 'date': parsed.get('date') or it['date'],
                'category': parsed.get('category') or '其他',
                'title': parsed.get('title') or '', 'city': parsed.get('city') or '',
                'venue': parsed.get('venue') or '', 'song': parsed.get('song') or '',
                'tour': parsed.get('tour') or '', 'summary': parsed.get('summary') or '',
                'source': '微博流水线', 'folders': [it['folder']], 'raw_texts': [it['text']],
            }
            added += 1
        except Exception as e:
            log('单条提取失败 %s: %s' % (it['folder'][:30], repr(e)[:60]))
        time.sleep(0.5)

    try:
        events_out.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding='utf-8')
    except Exception as e:
        log('写 events_out 失败: %s' % e)
    log('事件提取：新增 %d 条事件' % added)
    return added


def update_kb(added_events_file=BASE / '_events_extracted.json'):
    """把新增事件并入 causality_kb.json（events 实体）。"""
    if not KB.exists():
        log('因果库不存在，跳过 kb 更新')
        return
    kb = json.loads(KB.read_text(encoding='utf-8'))
    evs = json.loads(added_events_file.read_text(encoding='utf-8')) if added_events_file.exists() else {}
    exist_ids = set()
    for e in kb.get('entities', {}).get('events', []):
        exist_ids.add(e.get('id'))
    added = 0
    for k, v in evs.items():
        eid = 'ev_' + k
        if eid in exist_ids:
            continue
        kb.setdefault('entities', {}).setdefault('events', []).append({
            'id': eid, 'date': v.get('date'), 'category': v.get('category'),
            'title': v.get('title'), 'city': v.get('city'), 'venue': v.get('venue'),
            'song': v.get('song'), 'tour': v.get('tour'), 'summary': v.get('summary'),
            'source': v.get('source'),
        })
        exist_ids.add(eid)
        added += 1
    kb['meta']['counts'] = kb.get('meta', {}).get('counts', {})
    kb['meta']['counts']['事件'] = len(kb['entities']['events'])
    KB.write_text(json.dumps(kb, ensure_ascii=False, indent=1), encoding='utf-8')
    log('因果库事件实体：新增 %d' % added)
    return added


def main():
    mode = 'both'
    no_push = False
    if '--studio' in sys.argv:
        mode = 'studio'
    elif '--self' in sys.argv:
        mode = 'self'
    if '--no-push' in sys.argv:
        no_push = True

    get_cookie()
    total_new = 0
    new_folders_by_archive = {}  # archive_dir -> [folder名]

    if mode in ('studio', 'both'):
        log('=== 抓工作室微博 ===')
        items = crawl_incremental(STUDIO_UID, r'E:\wx\私有工具\weibo_merged\工作室微博_完整')
        if items:
            folders = save_items(items, STUDIO_UID, r'E:\wx\私有工具\weibo_merged\工作室微博_完整')
            total_new += len(folders)
            new_folders_by_archive[r'E:\wx\私有工具\weibo_merged\工作室微博_完整'] = folders
            log('工作室新增保存: %d' % len(folders))
        else:
            log('工作室无新增')

    if mode in ('self', 'both'):
        log('=== 抓本人微博 ===')
        items = crawl_incremental(SELF_UID, r'E:\wx\私有工具\weibo_merged\微博')
        if items:
            folders = save_items(items, SELF_UID, r'E:\wx\私有工具\weibo_merged\微博')
            total_new += len(folders)
            new_folders_by_archive[r'E:\wx\私有工具\weibo_merged\微博'] = folders
            log('本人新增保存: %d' % len(folders))
        else:
            log('本人无新增')

    log('=== 本轮新增微博总数: %d ===' % total_new)

    if total_new == 0:
        log('无新内容，跳过后续（不提取 / 不 rebuild）')
        return

    # 2. 事件提取（LLM，只处理本轮新增）
    log('=== 事件提取（LLM，增量）===')
    for ad, folders in new_folders_by_archive.items():
        extract_new_events(ad, folders)

    # 3. 更新因果库
    log('=== 因果库更新 ===')
    update_kb()

    # 4. rebuild + push
    if not no_push:
        log('=== rebuild 大屏 ===')
        import subprocess
        r = subprocess.run([sys.executable, str(DASH_GEN), '--rebuild'])
        log('rebuild 退出码: %d' % r.returncode)
        if r.returncode == 0:
            log('=== git push（SSH）===')
            r2 = subprocess.run(['git', '-C', r'D:\wx409.github.io', 'push', 'origin', 'main'])
            log('push 退出码: %d' % r2.returncode)
    else:
        log('--no-push 模式，跳过 rebuild/push')


if __name__ == '__main__':
    main()
