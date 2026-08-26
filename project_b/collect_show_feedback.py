# -*- coding: utf-8 -*-
"""演出观众反馈收集：微博搜索 + 小红书 + B站（晚些）+ Bing 托底 + 抖音指引
用法：
  python project_b/collect_show_feedback.py --date 2026-08-23 --city 广州
  python project_b/collect_show_feedback.py --date 2026-08-23 --city 广州 --bili-only   # 只跑B站（晚些补收）
  python project_b/collect_show_feedback.py --date 2026-08-23 --city 广州 --skip-bili   # 跳过B站（首次收集）
流程：
  1. 微博 m.weibo.cn 搜索多关键词组（观众 UGC，按 mid 去重，时间过滤演出当日起）
  2. 小红书 xhs_crawler.py 多关键词搜索（复用，归档到 xhs_archive）
  3. B站 api.bilibili.com 视频搜索 + Top 视频评论（规则筛选，零 LLM）
  4. Bing 搜索托底（覆盖抖音网页/知乎/豆瓣等，复用 watch_web 抓取模式）
  5. 抖音无自动工具 -> 打印手动收集指引
  6. 结果归档 E:\wx\私有工具\show_feedback\<日期>_<城市>\（私有，不进 git）
"""
import argparse, json, re, sys, io, time, datetime, subprocess, os
from pathlib import Path

COOKIE_FILE = Path(r'E:\wx\私有工具\weibo_cookies.txt')
SETLIST_LONG = Path(r'E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx')
EVENT_WORDS = ['巡演', '演出', '音乐会', '演唱会', '现场', 'repo', '低音']
OUT_ROOT = Path(r'E:\wx\私有工具\show_feedback')
XHS_CRAWLER = Path(r'E:\wx\私有工具\xhs_proxy\xhs_crawler.py')
HDRS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://m.weibo.cn/',
}
UA_PC = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'}
# 官方号（排除或标注）
OFFICIAL_UIDS = {'1292815744': '王晰本人', '7215995153': '王晰工作室'}

def log(*a):
    print('[%s]' % datetime.datetime.now().strftime('%H:%M:%S'), *a, flush=True)

def weibo_search(keyword, since=None, pages=2):
    """搜索微博，返回 [(mid, user, text, created_at, url)]"""
    import urllib.request, urllib.parse
    out = []
    for pg in range(1, pages + 1):
        params = {'containerid': '100103type=1&q=' + keyword, 'page_type': 'searchall'}
        if since: params['since_id'] = since
        url = 'https://m.weibo.cn/api/container/getIndex?' + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers=HDRS)
            d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
            cards = d.get('data', {}).get('cards', [])
            since = (d.get('data', {}).get('cardlistInfo') or {}).get('since_id')
        except Exception as e:
            log('微博搜索失败 %s: %s' % (keyword, repr(e)[:60]))
            break
        added = 0
        for c in cards:
            mb = c.get('mblog') or {}
            mid = mb.get('mid')
            if not mid: continue
            out.append({
                'mid': mid,
                'user': (mb.get('user') or {}).get('screen_name', ''),
                'uid': str((mb.get('user') or {}).get('id', '')),
                'text': re.sub(r'<[^>]+>', '', mb.get('text') or ''),
                'created_at': mb.get('created_at', ''),
                'url': 'https://m.weibo.cn/status/' + mid,
                'keyword': keyword,
            })
            added += 1
        log('  关键词[%s] page%d: +%d' % (keyword, pg, added))
        if not since or added == 0:
            break
        time.sleep(1.2)
    return out

def parse_date(s):
    try:
        t = datetime.datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y')
        return t.date()
    except Exception:
        return None

def load_setlist_songs(date_str):
    """从长表读该场次歌单（曲目+数据层归一名），供二次筛选；城市/歌单随场次动态。"""
    try:
        import pandas as pd
        df = pd.read_excel(SETLIST_LONG, sheet_name='合并长表')
        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        sub = df[df['日期'] == date_str]
        songs = set()
        for col in ('曲目', '数据层归一名'):
            for v in sub[col].dropna().astype(str):
                v = v.strip()
                if v and v != 'nan':
                    songs.add(v)
        return songs
    except Exception as e:
        log('!! 长表读取失败（歌单筛选降级为城市+活动词）: %s' % e)
        return set()


def build_filter(city, setlist_songs):
    """二次筛选：命中 任一歌单歌曲（高级）或 城市 或 活动词 即保留。
    演出后 7 日内内容多围绕音乐会，营销号/纯分享旧歌会被此筛掉。"""
    def keep(text):
        t = str(text or '')
        if any(s and s in t for s in setlist_songs):
            return True
        if city and city in t:
            return True
        return any(k in t for k in EVENT_WORDS)
    return keep


# ---- B站（晚些收集；零 LLM，规则筛选）----
_bili_opener = None
def bili_opener():
    """带 cookie jar 的 opener：先访问主页拿 buvid3，规避 412 风控"""
    global _bili_opener
    if _bili_opener is None:
        import http.cookiejar, urllib.request
        cj = http.cookiejar.CookieJar()
        _bili_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        try:
            _bili_opener.open(urllib.request.Request('https://www.bilibili.com/', headers=UA_PC), timeout=15)
        except Exception:
            pass
    return _bili_opener

def bili_search(keyword, pages=2):
    """B站视频搜索，返回 [{bvid,title,author,play,pubdate,desc,url}]"""
    import urllib.request, urllib.parse
    out = []
    op = bili_opener()
    for pg in range(1, pages + 1):
        params = urllib.parse.urlencode({
            'search_type': 'video', 'keyword': keyword, 'page': pg,
            'order': 'click',  # 按播放排序（click）更容易命中真实观众视频
        })
        url = 'https://api.bilibili.com/x/web-interface/search/type?' + params
        try:
            req = urllib.request.Request(url, headers=UA_PC)
            req.add_header('Referer', 'https://www.bilibili.com/')
            d = json.loads(op.open(req, timeout=20).read().decode('utf-8'))
            if d.get('code') != 0:
                log('B站搜索 code=%s（可能风控）' % d.get('code'))
                break
            res = (d.get('data') or {}).get('result') or []
            if not isinstance(res, list): break
            for v in res:
                title = re.sub(r'<[^>]+>', '', v.get('title', ''))
                out.append({
                    'bvid': v.get('bvid', ''),
                    'title': title,
                    'author': v.get('author', ''),
                    'play': v.get('play', 0),
                    'pubdate': v.get('pubdate', 0),
                    'desc': re.sub(r'<[^>]+>', '', v.get('description', ''))[:200],
                    'url': v.get('arcurl', ''),
                })
        except Exception as e:
            log('B站搜索失败 %s: %s' % (keyword, repr(e)[:60]))
            break
        time.sleep(1.0)
    return out

def bili_comments(bvid, topn=3):
    """Top 视频的热门评论（零 LLM，只取前几条评论文本）"""
    import urllib.request
    out = []
    try:
        op = bili_opener()
        req = urllib.request.Request('https://api.bilibili.com/x/web-interface/view?bvid=' + bvid, headers=UA_PC)
        req.add_header('Referer', 'https://www.bilibili.com/')
        vd = json.loads(op.open(req, timeout=15).read().decode('utf-8'))
        aid = (vd.get('data') or {}).get('aid')
        if not aid: return out
        url = 'https://api.bilibili.com/x/v2/reply/main?type=1&oid=%s&mode=3' % aid
        req2 = urllib.request.Request(url, headers=UA_PC)
        req2.add_header('Referer', 'https://www.bilibili.com/')
        rd = json.loads(op.open(req2, timeout=15).read().decode('utf-8'))
        replies = ((rd.get('data') or {}).get('replies')) or []
        for r in replies[:topn]:
            out.append({
                'user': (r.get('member') or {}).get('uname', ''),
                'text': re.sub(r'<[^>]+>', '', r.get('content', {}).get('message', ''))[:120],
                'like': r.get('like', 0),
            })
    except Exception as e:
        log('B站评论失败 %s: %s' % (bvid, repr(e)[:60]))
    return out

# ---- Bing 托底（复用 watch_web 抓取模式）----
def bing_search(q):
    import urllib.request, urllib.parse
    url = 'https://www.bing.com/search?q=' + urllib.parse.quote(q)
    try:
        req = urllib.request.Request(url, headers=UA_PC)
        d = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
        hits = re.findall(r'<li class="b_algo".*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>', d, re.S)
        return [{
            'url': h[0],
            'title': re.sub(r'<[^>]+>', '', h[1]),
            'snippet': re.sub(r'<[^>]+>', '', h[2])[:200],
        } for h in hits]
    except Exception as e:
        log('Bing 失败 %s: %s' % (q, repr(e)[:60]))
        return []

def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True, help='演出日期 YYYY-MM-DD')
    ap.add_argument('--city', required=True, help='城市')
    ap.add_argument('--venue', default='', help='场馆（可选）')
    ap.add_argument('--pages', type=int, default=2, help='每关键词微博翻页数')
    ap.add_argument('--skip-bili', action='store_true', help='跳过 B站（首次收集用）')
    ap.add_argument('--bili-only', action='store_true', help='只跑 B站（晚些补收用）')
    args = ap.parse_args()

    show_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    out_dir = OUT_ROOT / ('%s_%s' % (args.date.replace('-', ''), args.city))
    out_dir.mkdir(parents=True, exist_ok=True)

    # cookie
    if COOKIE_FILE.exists():
        HDRS['Cookie'] = COOKIE_FILE.read_text(encoding='utf-8', errors='ignore').strip()
    else:
        log('!! 微博 cookie 缺失: %s' % COOKIE_FILE)

    # 场次歌单 + 二次筛选器（城市/活动词/歌单歌曲，随场次动态）
    setlist_songs = load_setlist_songs(args.date)
    keep = build_filter(args.city, setlist_songs)
    log('场次歌单 %d 首（长表），筛选: 城市[%s] + 活动词 + 歌单歌曲' % (len(setlist_songs), args.city))

    # ===== B站（晚些收集，独立可跑）=====
    if args.bili_only:
        run_bili(args, show_date, out_dir, keep)
        return

    # ===== 微博 =====
    keywords = [
        '王晰',
        '王晰 %s 演唱会' % args.city,
        '王晰 %s站' % args.city,
        '王晰 巡演 repo',
        '王晰 %s 现场' % args.city,
        '王晰低音 %s' % args.city,
    ]
    log('=== 微博搜索（%d 组关键词）===' % len(keywords))
    all_posts = []
    seen = set()
    for kw in keywords:
        for p in weibo_search(kw, pages=args.pages):
            if p['mid'] in seen: continue
            seen.add(p['mid'])
            d = parse_date(p['created_at'])
            if d and d < show_date:  # 只要演出当天及以后的反馈
                continue
            p['official'] = OFFICIAL_UIDS.get(p['uid'], '')
            # 二次筛选：命中歌单歌曲/城市/活动词才保留（滤营销号旧内容）
            if not keep(p['text']):
                continue
            all_posts.append(p)
    log('微博去重后: %d 条（演出当日及以后）' % len(all_posts))
    (out_dir / 'weibo_feedback.json').write_text(
        json.dumps(all_posts, ensure_ascii=False, indent=1), encoding='utf-8')
    if all_posts:
        summary = ['【微博观众反馈 %s %s站】共 %d 条' % (args.date, args.city, len(all_posts))]
        for p in all_posts[:40]:
            tag = ('[官方:%s]' % p['official']) if p['official'] else '[观众]'
            summary.append('%s @%s | %s | %s' % (tag, p['user'], p['created_at'], p['text'][:80]))
        (out_dir / 'weibo_summary.txt').write_text('\n'.join(summary), encoding='utf-8')
        log('已存: %s\\weibo_feedback.json + weibo_summary.txt' % out_dir)

    # ===== 小红书 =====
    log('=== 小红书搜索（xhs_crawler）===')
    xhs_kw = '王晰 %s 巡演repo,王晰 %s 演唱会,王晰 %s 现场' % (args.city, args.city, args.city)
    try:
        env = dict(os.environ)
        env['PYTHONIOENCODING'] = 'utf-8'  # 避免 xhs_crawler 打印 ✓ 等字符 GBK 崩
        r = subprocess.run([sys.executable, str(XHS_CRAWLER), '--keywords', xhs_kw, '--pages', '2', '--no-media'],
                           capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300, env=env)
        log('xhs_crawler 退出码: %d' % r.returncode)
        (out_dir / 'xhs_log.txt').write_text((r.stdout or '')[-4000:] + '\n---STDERR---\n' + (r.stderr or '')[-2000:], encoding='utf-8')
    except Exception as e:
        log('小红书抓取失败: %s（需检查 xhs cookie）' % repr(e)[:100])

    # ===== B站（首次可跳过，8/25 补收）=====
    if not args.skip_bili:
        run_bili(args, show_date, out_dir, keep)

    # ===== Bing 托底 =====
    run_bing(args, out_dir, keep)

    # ===== 汇总 =====
    merge_all(out_dir)

    # 抖音指引
    log('=== 抖音：无自动工具，手动收集指引 ===')
    guide = (
        '抖音收集指引（%s %s站）：\n'
        '1. 抖音搜索「王晰 广州 演唱会」「王晰 回 巡演」，按「最新」排序\n'
        '2. 收集高赞观众视频/图文：复制分享链接（含观众昵称+视频描述+评论区高赞）\n'
        '3. 关注点：现场低音质感、选曲、返场、观众repo、直拍\n'
        '4. 链接清单存到: %s\\douyin_links.txt' % (args.date, args.city, out_dir)
    )
    (out_dir / 'douyin_guide.txt').write_text(guide, encoding='utf-8')
    log('完成。结果目录: %s' % out_dir)

def run_bili(args, show_date, out_dir, keep):
    """B站视频搜索 + Top 视频评论（规则筛选，零 LLM）"""
    log('=== B站搜索（api.bilibili.com）===')
    bili_kws = ['王晰', '王晰 %s 演唱会' % args.city, '王晰 %s 巡演' % args.city, '王晰 回 巡演 %s' % args.city]
    bili_all = []
    seen_bv = set()
    for kw in bili_kws:
        for v in bili_search(kw, pages=2):
            if v['bvid'] in seen_bv: continue
            seen_bv.add(v['bvid'])
            pub = datetime.datetime.fromtimestamp(v.get('pubdate') or 0).date() if v.get('pubdate') else None
            if pub and pub < show_date:
                continue  # 只要演出后的视频
            # 二次筛选：标题/简介命中歌单歌曲/城市/活动词才拉评论
            if not keep(v.get('title', '') + ' ' + (v.get('desc') or '')):
                continue
            v['comments'] = bili_comments(v['bvid'], topn=3)
            bili_all.append(v)
        time.sleep(1.0)
    log('B站去重后: %d 个视频（演出后发布）' % len(bili_all))
    (out_dir / 'bili_feedback.json').write_text(json.dumps(bili_all, ensure_ascii=False, indent=1), encoding='utf-8')
    if bili_all:
        (out_dir / 'bili_summary.txt').write_text('\n'.join(
            ['【B站反馈 %s %s站】%d 个视频' % (args.date, args.city, len(bili_all))] +
            ['%s | UP:%s | 播放:%s | %s | %s' % (v['title'][:40], v['author'], v['play'], v['url'], '评论:' + '；'.join(c['text'][:30] for c in v['comments'][:2])) for v in bili_all[:30]]
        ), encoding='utf-8')
        log('已存: %s\\bili_feedback.json' % out_dir)

def run_bing(args, out_dir, keep):
    """Bing 托底搜索（覆盖抖音网页/知乎/豆瓣/百家号等）"""
    log('=== Bing 托底搜索 ===')
    bing_qs = [
        '王晰 %s 演出' % args.city,
        '王晰 %s 演唱会 评价' % args.city,
        '王晰 %s站 repo' % args.city,
        '王晰 %s 演唱会 观后感' % args.city,
        'site:weibo.com 王晰 %s 演唱会' % args.city,
        'site:xiaohongshu.com 王晰 %s' % args.city,
        'site:bilibili.com 王晰 %s 演唱会' % args.city,
    ]
    bing_all = []
    seen_u = set()
    for q in bing_qs:
        for h in bing_search(q):
            if h['url'] in seen_u: continue
            seen_u.add(h['url'])
            # 二次筛选：标题/摘要命中歌单歌曲/城市/活动词才保留
            if not keep(h.get('title', '') + ' ' + (h.get('snippet') or '')):
                continue
            h['query'] = q
            bing_all.append(h)
        time.sleep(1.0)
    log('Bing 去重后: %d 条网页结果' % len(bing_all))
    (out_dir / 'bing_feedback.json').write_text(json.dumps(bing_all, ensure_ascii=False, indent=1), encoding='utf-8')
    if bing_all:
        (out_dir / 'bing_summary.txt').write_text('\n'.join(
            ['【Bing 托底 %s %s站】%d 条' % (args.date, args.city, len(bing_all))] +
            ['%s | %s | %s' % (h['title'][:40], h['url'], h['snippet'][:60]) for h in bing_all[:30]]
        ), encoding='utf-8')

def merge_all(out_dir):
    """把各平台结果合并为 all_feedback.json（供 build_show_repo.py 自动入库）"""
    merged = {'weibo': [], 'bili': [], 'bing': []}
    for fn, key in [('weibo_feedback.json', 'weibo'), ('bili_feedback.json', 'bili'), ('bing_feedback.json', 'bing')]:
        p = out_dir / fn
        if p.exists():
            try:
                merged[key] = json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                pass
    # 小红书归档在 xhs_archive 下（由 xhs_crawler 管理），此处从 _summary 拿统计
    merged['xhs_note'] = 'xhs_archive 目录（E:\\wx\\私有工具\\xhs_archive），正文见各 note 文件夹'
    (out_dir / 'all_feedback.json').write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding='utf-8')
    log('已汇总: all_feedback.json')

if __name__ == '__main__':
    main()
