# -*- coding: utf-8 -*-
"""渲染「现场金句（talk 录音转写）」区块到 live 演出页（audience-repo 之后）

数据源：data/quotes.json（transcript_pipeline --merge 写入的金句数据层）
结构：语义化 section + blockquote + 场景标签 + 来源视频链接；幂等（先删旧区块再写）
诚实披露：verified=false 的条目标注「转写原文，待人工核对」，不伪造。
用法：
  python project_b/render_quotes_wall.py --page live/hui-回-广州-2026.html [--no-push]
"""
import argparse, json, re, sys, io, datetime, subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = Path(r'D:\wx409.github.io')
QUOTES = ROOT / 'data' / 'quotes.json'


def esc(s):
    return (str(s or '')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', required=True, help='live 页相对路径，如 live/hui-回-广州-2026.html')
    ap.add_argument('--no-push', action='store_true')
    args = ap.parse_args()

    if not QUOTES.exists():
        print('无 data/quotes.json，跳过'); return
    quotes = json.loads(QUOTES.read_text(encoding='utf-8')).get('quotes', [])
    if not quotes:
        print('quotes.json 为空'); return

    lis = []
    for q in quotes:
        scene = q.get('scene') or '现场'
        text = q.get('text') or ''
        if len(text.strip()) < 5:
            continue
        date = q.get('date') or ''
        url = q.get('source_url') or ''
        verified = q.get('verified')
        mark = '' if verified else ' <em style="color:#b8860b;font-size:12px;">（转写原文，待人工核对）</em>'
        link = ''
        if url:
            link = f' <a href="{esc(url)}" target="_blank" rel="noopener nofollow" style="font-size:12px;color:#1a56c4;">视频→</a>'
        meta = f'<span class="tag">{esc(scene)}</span> {esc(date)}{link}{mark}'
        lis.append(f'        <li><blockquote style="margin:0;">"{esc(text)}"</blockquote><p style="font-size:12px;color:#777;margin:2px 0 0;">{meta}</p></li>')

    section = (
        '\n    <section id="quotes-wall" style="margin-top:36px;">\n'
        '        <h2>🎙 现场金句（演出 talk 转写）</h2>\n'
        '        <p style="font-size:13px;color:#777;">'
        '广州站演出间隙 talk 的转写金句（来源：B站现场 talk 视频），按场景归类；'
        '转写为机器初稿，标注「待人工核对」的条目未经人工校对。</p>\n'
        '        <ul class="repo-list">\n' + '\n'.join(lis) + '\n        </ul>\n'
        '    </section>'
    )

    page = ROOT / args.page
    html = page.read_text(encoding='utf-8')
    # 幂等：删旧金句墙区
    html, n_del = re.subn(r'<section id="quotes-wall"[^>]*>.*?</section>', '', html, flags=re.S)
    # 插入到 audience-repo 区之后（若存在），否则 notice 之后
    m = re.search(r'</section>\s*(?=<section id="gz-|$)', html, re.S)
    anchor = '</section>'
    if 'audience-repo' in html:
        i = html.find('</section>', html.find('audience-repo'))
        j = i + len('</section>')
        html = html[:j] + '\n' + section + html[j:]
    else:
        # 兜底：notice 后
        np = re.compile(r'<div class="notice"[^>]*>.*?</div>', re.S)
        mm = np.search(html)
        if mm:
            j = mm.end()
            html = html[:j] + section + html[j:]
        else:
            print('!! 定位插入点失败'); return

    html = re.sub(r'最后更新：[^<]*', '最后更新：' + datetime.date.today().strftime('%Y-%m-%d'), html, count=1)
    page.write_text(html, encoding='utf-8')
    print('金句墙已写入 %d 条 -> %s（删旧 %d）' % (len(lis), args.page, n_del))

    if not args.no_push:
        subprocess.run(['git', '-C', str(ROOT), 'add', args.page])
        subprocess.run(['git', '-C', str(ROOT), 'commit', '-m', '金句墙：现场talk转写金句渲染到演出页(%d条)' % len(lis)])
        r = subprocess.run(['git', '-C', str(ROOT), 'push', 'origin', 'main'])
        print('已 commit + push（退出码 %d）' % r.returncode)
    else:
        print('--no-push 模式，未提交。')


if __name__ == '__main__':
    main()
