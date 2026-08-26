# -*- coding: utf-8 -*-
"""手动精选微博正文入库：解析「wb链接（复制正文文字）.txt」→ 匿名化 → 并入 weibo_feedback.json + all_feedback.json

用法：
  python project_b/import_wb_manual.py --date 2026-08-23 --city 广州 \
      --file "E:\\wx\\六巡\\20260823广州站\\wb链接（复制正文文字）.txt"
  python project_b/import_wb_manual.py --date 2026-08-23 --city 广州 --file ... --with-links

匿名与链接（GEO 第一性原理）：
  - 默认不放链接：微博链接含用户 UID（weibo.com/<uid>/<mid>），放链接即泄露 ID；
    且微博对 AI 爬虫有登录墙/风控，链接对生成式引擎无可引用的增量价值。
  - --with-links 时用 m.weibo.cn/status/<mid>（不含 UID）作为干净回源链接。
  - @观众昵称 一律匿名（"观众"），@王晰 本人保留。
  - 与 collect_show_feedback.py 同源写 weibo_feedback.json，重跑收集不会冲掉手动精选。
"""
import argparse, json, re, sys, io
from pathlib import Path

FB = Path(r'E:\wx\私有工具\show_feedback')


def parse_file(text):
    """按 'N)日期' 分段，返回 [{date, time, text, mid}]"""
    items = []
    # 以行首 "数字)" 分段
    blocks = re.split(r'(?m)^\d+\)', text)
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        # 首行日期时间：2026年08月25日 10:10
        dt = re.match(r'^(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})', lines[0])
        date_s = ''
        if dt:
            date_s = '%s-%s-%s %s:%s' % (dt.group(1), dt.group(2).zfill(2), dt.group(3).zfill(2),
                                         dt.group(4).zfill(2), dt.group(5))
            lines = lines[1:]
        body = '\n'.join(lines)
        m = re.search(r'https?://weibo\.com/(?:u/)?\d+/(\d{10,})', body)
        mid = m.group(1) if m else ''
        items.append({'date': date_s, 'text': body, 'mid': mid})
    return items


def anonymize(text):
    """匿名化正文：删链接/标记/@观众昵称；保留 @王晰 本人与话题标签。"""
    t = str(text or '')
    t = re.sub(r'\[?链接\]?', '', t)                       # [链接] 标记
    t = re.sub(r'https?://\S+', '', t)                     # 所有 URL
    t = re.sub(r'\[cp\]@[^：:]+[：:]\s*', '（观众评论）', t)  # [cp]@昵称: 内容[/cp]
    t = re.sub(r'\[/cp\]', '', t)
    t = re.sub(r'@王晰', '王晰', t)                         # 歌手本人不匿名
    t = re.sub(r'@([^：:\s，。！？、；;]{1,20})[：:]', '观众：', t)  # @昵称：→ 观众：
    t = re.sub(r'@([^：:\s，。！？、；;]{1,20})', '', t)     # 裸 @昵称 删除
    # 清理装饰行（孤立 - / 空格行）与多余空白
    t = re.sub(r'(?m)^-\s*$', '', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return t.strip()


def main():
    if sys.stdout and getattr(sys.stdout, 'buffer', None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='手动精选微博正文入库（匿名化）')
    ap.add_argument('--date', required=True, help='演出日期 YYYY-MM-DD')
    ap.add_argument('--city', required=True)
    ap.add_argument('--file', required=True, help='wb链接（复制正文文字）.txt 路径')
    ap.add_argument('--with-links', action='store_true',
                    help='用 m.weibo.cn/status/<mid>（不含UID）作为回源链接；默认不放链接')
    args = ap.parse_args()

    src = Path(args.file)
    if not src.exists():
        print('!! 文件不存在: %s' % src); return
    raw = src.read_text(encoding='utf-8', errors='ignore')

    parsed = parse_file(raw)
    print('解析到 %d 段' % len(parsed))

    out_dir = FB / ('%s_%s' % (args.date.replace('-', ''), args.city))
    out_dir.mkdir(parents=True, exist_ok=True)

    # 现有微博反馈（与 collect 同源）
    wb_path = out_dir / 'weibo_feedback.json'
    existing = []
    if wb_path.exists():
        try:
            existing = json.loads(wb_path.read_text(encoding='utf-8'))
        except Exception:
            existing = []
    seen_mid = {p.get('mid') for p in existing if p.get('mid')}

    added = 0
    for it in parsed:
        cleaned = anonymize(it['text'])
        if len(cleaned) < 10:
            if it['mid']:
                print('  [跳过] 正文过短（%s）: %s' % (it['mid'], it['text'][:40].replace('\n', ' ')))
            continue
        if it['mid'] and it['mid'] in seen_mid:
            print('  [跳过] 已存在 mid=%s' % it['mid'])
            continue
        url = ('https://m.weibo.cn/status/' + it['mid']) if (args.with_links and it['mid']) else ''
        existing.append({
            'mid': it['mid'], 'user': '', 'uid': '',
            'text': cleaned, 'created_at': it['date'], 'url': url,
            'keyword': '手动精选', 'official': '', 'manual': True,
        })
        seen_mid.add(it['mid'])
        added += 1

    wb_path.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding='utf-8')

    # 同步 all_feedback.json 的 weibo 数组（build_show_repo / analyze 都读它）
    ap_path = out_dir / 'all_feedback.json'
    blob = {}
    if ap_path.exists():
        try:
            blob = json.loads(ap_path.read_text(encoding='utf-8'))
        except Exception:
            blob = {}
    blob['weibo'] = existing
    ap_path.write_text(json.dumps(blob, ensure_ascii=False, indent=1), encoding='utf-8')

    print('新增 %d 条手动微博正文（共 %d 条）→ %s' % (added, len(existing), out_dir))
    if added:
        print('--- 匿名化后首条预览 ---')
        print(existing[-added]['text'][:120])


if __name__ == '__main__':
    main()
