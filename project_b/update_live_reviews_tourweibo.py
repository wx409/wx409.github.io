# -*- coding: utf-8 -*-
"""更新 live-reviews.html：巡演微博插入对应场次（正确处理 pending 场次）"""
import json, re
from pathlib import Path

HTML = Path(r'D:\wx409.github.io\live-reviews.html')
TOUR_JSON = Path(r'D:\wx409.github.io\data\tour_weibo_posts.json')

def build_li(rec):
    text = rec.get('text', '').strip()
    text_short = re.sub(r'\s+', ' ', text)
    url = rec.get('url', '')
    platform = rec.get('platform', '微博')
    disp_text = text_short[:50] + ('…' if len(text_short) > 50 else '')
    # 用 sourceType 区分：studio_weibo=工作室，其余=王晰本人
    src_type = rec.get('sourceType', '')
    is_studio = src_type == 'studio_weibo' or '工作室' in platform or '晰息相关' in platform
    tag = '王晰工作室' if is_studio else '王晰本人'
    if url:
        return (f'<li><a href="{url}" target="_blank" rel="noopener nofollow" title="{text_short}">'
                f'王晰微博：{disp_text}</a> <span class="tag">{tag}</span> '
                f'<span class="src-badge official">官方</span></li>')
    return (f'<li><span title="{text_short}">王晰微博：{disp_text}</span> '
            f'<span class="tag">{tag}</span> <span class="src-badge official">官方</span></li>')


def insert_for_event(html, show_date, records):
    """在 show_date 对应场次的 article 里插入微博条目"""
    # 定位 time datetime
    m = re.search(rf'<time datetime="{re.escape(show_date)}"[^>]*>', html)
    if not m:
        return html, False
    # 定位该 time 所在的 article 起始
    article_start = html.rfind('<article', 0, m.start())
    if article_start < 0:
        return html, False
    # 定位该 article 的结束 </article>
    article_end = html.find('</article>', m.start())
    if article_end < 0:
        return html, False

    segment = html[article_start:article_end]
    insert_html = '\n'.join(build_li(r) for r in records)

    if '<ul class="repo-list">' in segment:
        # 已有 repo-list，在 </ul> 前插入
        ul_end_rel = segment.rfind('</ul>')
        if ul_end_rel < 0:
            return html, False
        insert_pos = article_start + ul_end_rel
        new_html = html[:insert_pos] + '\n' + insert_html + html[insert_pos:]
    else:
        # pending 场次（无 ul），把 pending-note 替换为 ul + 微博 + 保留 pending 提示
        # 找到 pending-note 段落
        pn_rel = segment.find('pending-note')
        if pn_rel >= 0:
            # 在 pending-note <p> 之前插入 ul
            p_start_rel = segment.rfind('<p', 0, pn_rel)
            insert_pos = article_start + p_start_rel
            ul = '<ul class="repo-list">\n' + insert_html + '\n</ul>\n'
            new_html = html[:insert_pos] + ul + html[insert_pos:]
        else:
            # 无 pending-note 也无 ul，直接在 </article> 前插入
            insert_pos = article_end
            ul = '<ul class="repo-list">\n' + insert_html + '\n</ul>\n'
            new_html = html[:insert_pos] + ul + html[insert_pos:]
    return new_html, True


def main():
    html = HTML.read_text(encoding='utf-8')
    tour = json.loads(TOUR_JSON.read_text(encoding='utf-8'))
    matched = tour.get('matched_to_shows', [])

    by_show = {}
    for rec in matched:
        show_date = rec.get('show_date') or rec.get('date', '')[:10]
        if show_date:
            by_show.setdefault(show_date, []).append(rec)

    inserted = 0
    skipped = 0
    failed = []
    for show_date, recs in by_show.items():
        # 去重：跳过 url 已在页面中的记录
        new_recs = []
        for r in recs:
            url = r.get('url', '')
            if url and url in html:
                skipped += 1
                continue
            new_recs.append(r)
        if not new_recs:
            continue
        html, ok = insert_for_event(html, show_date, new_recs)
        if ok:
            inserted += len(new_recs)
        else:
            failed.append(show_date)

    HTML.write_text(html, encoding='utf-8')
    print(f'插入 {inserted} 条微博（跳过重复 {skipped} 条）')
    if failed:
        print(f'失败场次: {failed}')

if __name__ == '__main__':
    main()
