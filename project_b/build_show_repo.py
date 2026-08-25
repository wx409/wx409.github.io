# -*- coding: utf-8 -*-
"""观众反馈自动入库：读收集结果 → 规则筛选/分类（零LLM）→ 生成 repo HTML → 插入 live 页 → git commit+push
用法：
  python project_b/build_show_repo.py --date 2026-08-23 --city 广州 --page live/hui-回-广州-2026.html
  python project_b/build_show_repo.py --date 2026-08-23 --city 广州 --page ... --no-push
规则（省 token）：关键词分类 + 长度过滤 + 去重；只引用短句（≤60字）+ 外链 + 平台标签，不公开昵称。
"""
import argparse, json, re, sys, io, datetime, subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = Path(r'D:\wx409.github.io')
FB_ROOT = Path(r'E:\wx\私有工具\show_feedback')
XHS_ARCHIVE = Path(r'E:\wx\私有工具\xhs_archive')

POS = re.compile(r'好听|震撼|值|绝|封神|感动|完美|牛|沉浸|惊喜|精彩|安可|返场|低音|声压|氛围|浪漫|治愈|值回|难忘|上头')
NEG = re.compile(r'差|失望|一般|不值|翻车|拉胯|后悔|退票|糟糕|敷衍')
WEB_DOMAIN_OK = re.compile(r'weibo\.com|xiaohongshu\.com|bilibili\.com|douyin\.com|zhihu\.com|douban\.com|baijiahao|toutiao\.com')

def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def cut(s, n=60):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s[:n] + ('…' if len(s) > n else '')

def classify(t):
    if POS.search(t): return 'pos'
    if NEG.search(t): return 'neg'
    return 'neu'

def xhs_notes(show_date, city):
    """从 xhs_archive 扫演出日及以后、含城市的笔记（正文短句）"""
    out = []
    if not XHS_ARCHIVE.exists(): return out
    d0 = show_date.strftime('%Y%m%d')
    for kd in XHS_ARCHIVE.iterdir():
        if not kd.is_dir(): continue
        name = kd.name
        m = re.match(r'^(\d{8})_', name)
        if not m or m.group(1) < d0: continue
        if city not in name: continue
        ct = kd / 'content.txt'
        if not ct.exists(): continue
        txt = ct.read_text(encoding='utf-8', errors='ignore').strip().replace('\n', ' ')[:80]
        if len(txt) < 10: continue
        out.append({'platform': '小红书', 'text': txt,
                    'url': 'https://www.xiaohongshu.com/explore/' + (kd.name.split('_')[-1] if '_' in kd.name else ''),
                    'tag': classify(txt)})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--city', required=True)
    ap.add_argument('--page', required=True, help='live 页相对路径，如 live/hui-回-广州-2026.html')
    ap.add_argument('--max', type=int, default=15, help='最多入库条数')
    ap.add_argument('--no-push', action='store_true')
    args = ap.parse_args()

    show_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    out_dir = FB_ROOT / ('%s_%s' % (args.date.replace('-', ''), args.city))
    fb = {}
    if (out_dir / 'all_feedback.json').exists():
        fb = json.loads((out_dir / 'all_feedback.json').read_text(encoding='utf-8'))

    rows = []
    # 微博（观众，非官方）
    for p in fb.get('weibo') or []:
        if p.get('official'): continue
        t = p.get('text', '')
        if len(t.strip()) < 10: continue
        rows.append({'platform': '微博', 'text': cut(t), 'url': p.get('url', ''), 'tag': classify(t)})
    # B站（视频标题 + Top 评论）
    for v in fb.get('bili') or []:
        t = v.get('title', '')
        if len(t.strip()) < 6: continue
        rows.append({'platform': 'B站', 'text': cut(t, 50), 'url': v.get('url', ''), 'tag': classify(t), 'extra': ('UP:' + v['author']) if v.get('author') else ''})
        for c in (v.get('comments') or [])[:1]:
            ct = c.get('text', '')
            if len(ct.strip()) >= 8:
                rows.append({'platform': 'B站评论', 'text': cut(ct, 50), 'url': v.get('url', ''), 'tag': classify(ct)})
    # Bing 托底（域名白名单 + 摘要含反馈词）
    for h in fb.get('bing') or []:
        u = h.get('url', '')
        sn = h.get('snippet', '') + h.get('title', '')
        if not WEB_DOMAIN_OK.search(u): continue
        if not re.search(r'王晰', sn): continue
        rows.append({'platform': '网页', 'text': cut(h.get('snippet') or h.get('title'), 60), 'url': u, 'tag': classify(sn)})
    # 小红书（xhs_archive 正文）
    rows += xhs_notes(show_date, args.city)

    # 去重 + 排序（正面优先，限量）
    seen, uniq = set(), []
    for r in rows:
        k = (r['platform'], r['text'][:20], r['url'])
        if k in seen: continue
        seen.add(k)
        uniq.append(r)
    order = {'pos': 0, 'neu': 1, 'neg': 2}
    uniq.sort(key=lambda r: order.get(r['tag'], 1))
    picked = uniq[:args.max]

    if not picked:
        print('无有效反馈（可能演出刚结束或未收集），跳过入库。')
        return

    # 生成 HTML
    li = []
    for r in picked:
        label = {'pos': '👍', 'neu': '·', 'neg': '⚠'}.get(r['tag'], '·')
        extra = r.get('extra', '')
        if r['url']:
            li.append(f'<li><span class="tag">{esc(r["platform"])}</span> <a href="{esc(r["url"])}" target="_blank" rel="noopener nofollow">"{esc(r["text"])}"</a> {label} {("(" + esc(extra) + ")") if extra else ""}</li>')
        else:
            li.append(f'<li><span class="tag">{esc(r["platform"])}</span> "{esc(r["text"])}" {label}</li>')
    repo_html = (
        '\n    <section id="audience-repo" style="margin-top:36px;">\n'
        '        <h2>👥 观众反馈（自动收集 · 多平台）</h2>\n'
        '        <p style="font-size:13px;color:#777;">以下为演出后微博/B站/小红书/网页等平台观众公开发布的短评，自动汇总并附外链可复核（不公开昵称，仅保留短句）。</p>\n'
        '        <ul class="repo-list">\n' + '\n'.join(li) + '\n        </ul>\n'
        '    </section>'
    )

    # 插入 live 页（幂等：先删旧 repo 区，再替换 notice + 插入新 repo 区）
    page = ROOT / args.page
    html = page.read_text(encoding='utf-8')
    # 兼容带内联样式的旧标记（此前插入会改写 notice/section 为带 style 版本，导致正则失配的自锁 bug）
    html = re.sub(r'<section id="audience-repo"[^>]*>.*?</section>', '', html, flags=re.S)  # 删旧 repo 区
    notice_pat = re.compile(r'<div class="notice"[^>]*>.*?</div>', re.S)
    if not notice_pat.search(html):
        print('!! 未找到 notice 区，插入失败（检查页面结构）')
        return
    new_notice = ('<div class="notice" style="background:#eef9ee;">'
                  '<strong>演出已完成。</strong>以下为观众反馈汇总（自动收集，链接可复核）；完整歌单与现场实录持续补充中。</div>')
    html2 = notice_pat.sub(new_notice + repo_html, html, count=1)
    # 更新页脚"最后更新"
    html2 = re.sub(r'最后更新：[^<]*', '最后更新：' + datetime.date.today().strftime('%Y-%m-%d'), html2, count=1)
    page.write_text(html2, encoding='utf-8')
    print('已插入 %d 条反馈 -> %s' % (len(picked), args.page))

    if not args.no_push:
        r = subprocess.run(['git', '-C', str(ROOT), 'add', args.page])
        r = subprocess.run(['git', '-C', str(ROOT), 'commit', '-m',
                            '自动收录观众反馈(%s %s站, %d条, 微博/B站/小红书/网页)' % (args.date, args.city, len(picked))])
        r = subprocess.run(['git', '-C', str(ROOT), 'push', 'origin', 'main'])
        print('已 commit + push（退出码 %d）' % r.returncode)
    else:
        print('--no-push 模式，未提交。')

if __name__ == '__main__':
    main()
