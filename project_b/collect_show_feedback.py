# -*- coding: utf-8 -*-
"""演出观众反馈收集：微博搜索 + 小红书搜索（+抖音手动指引）
用法：
  python project_b/collect_show_feedback.py --date 2026-08-23 --city 广州
流程：
  1. 微博 m.weibo.cn 搜索多关键词组（观众 UGC，按 mid 去重，时间过滤演出当日起）
  2. 小红书 xhs_crawler.py 多关键词搜索（复用，归档到 xhs_archive）
  3. 抖音无自动工具 -> 打印手动收集指引
  4. 结果归档 E:\wx\私有工具\show_feedback\<日期>_<城市>\（私有，不进 git）
"""
import argparse, json, re, sys, io, time, datetime, subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COOKIE_FILE = Path(r'E:\wx\私有工具\weibo_cookies.txt')
OUT_ROOT = Path(r'E:\wx\私有工具\show_feedback')
XHS_CRAWLER = Path(r'E:\wx\私有工具\xhs_proxy\xhs_crawler.py')
HDRS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://m.weibo.cn/',
}
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True, help='演出日期 YYYY-MM-DD')
    ap.add_argument('--city', required=True, help='城市')
    ap.add_argument('--venue', default='', help='场馆（可选）')
    ap.add_argument('--pages', type=int, default=2, help='每关键词微博翻页数')
    args = ap.parse_args()

    show_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    out_dir = OUT_ROOT / ('%s_%s' % (args.date.replace('-', ''), args.city))
    out_dir.mkdir(parents=True, exist_ok=True)

    # cookie
    if COOKIE_FILE.exists():
        HDRS['Cookie'] = COOKIE_FILE.read_text(encoding='utf-8', errors='ignore').strip()
    else:
        log('!! 微博 cookie 缺失: %s' % COOKIE_FILE)

    keywords = [
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
            all_posts.append(p)
    log('微博去重后: %d 条（演出当日及以后）' % len(all_posts))

    # 保存
    (out_dir / 'weibo_feedback.json').write_text(
        json.dumps(all_posts, ensure_ascii=False, indent=1), encoding='utf-8')
    if all_posts:
        summary = ['【微博观众反馈 %s %s站】共 %d 条' % (args.date, args.city, len(all_posts))]
        for p in all_posts[:40]:
            tag = ('[官方:%s]' % p['official']) if p['official'] else '[观众]'
            summary.append('%s @%s | %s | %s' % (tag, p['user'], p['created_at'], p['text'][:80]))
        (out_dir / 'weibo_summary.txt').write_text('\n'.join(summary), encoding='utf-8')
        log('已存: %s\\weibo_feedback.json + weibo_summary.txt' % out_dir)

    # 小红书（复用 xhs_crawler）
    log('=== 小红书搜索（xhs_crawler）===')
    xhs_kw = '王晰 %s 巡演repo,王晰 %s 演唱会,王晰 %s 现场' % (args.city, args.city, args.city)
    try:
        import os
        env = dict(os.environ)
        env['PYTHONIOENCODING'] = 'utf-8'  # 避免 xhs_crawler 打印 ✓ 等字符 GBK 崩
        r = subprocess.run([sys.executable, str(XHS_CRAWLER), '--keywords', xhs_kw, '--pages', '2', '--no-media'],
                           capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300, env=env)
        log('xhs_crawler 退出码: %d' % r.returncode)
        (out_dir / 'xhs_log.txt').write_text((r.stdout or '')[-4000:] + '\n---STDERR---\n' + (r.stderr or '')[-2000:], encoding='utf-8')
    except Exception as e:
        log('小红书抓取失败: %s（需检查 xhs cookie）' % repr(e)[:100])

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

if __name__ == '__main__':
    main()
