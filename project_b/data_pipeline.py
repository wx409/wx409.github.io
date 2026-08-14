#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / '01_原始数据'
CLEAN_DIR = BASE_DIR / '02_清洗数据'
REPORT_DIR = BASE_DIR / '03_周报输出'
WEBSITE_DIR = BASE_DIR.parent
for d in [RAW_DIR, CLEAN_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_song_metadata():
    meta_path = RAW_DIR / '歌曲信息汇总表.xlsx'
    if not meta_path.exists():
        print('[!] 未找到歌曲信息汇总表，将使用歌名模糊匹配')
        return {}

    meta = {}

    # Sheet: ost和单曲 — 列：序号, ID2, 歌名, 发行时间, 内容
    df_songs = pd.read_excel(meta_path, sheet_name='ost和单曲', header=0)
    for _, r in df_songs.iterrows():
        name = str(r.get('歌名', '')).strip()
        if not name or name == 'nan':
            continue
        content = str(r.get('内容', '')).strip()
        song_type = _classify_from_content(content)
        meta[name] = {
            'type': song_type,
            'album': '无',
            'platform': '',
            'vip': '',
            'source': 'ost和单曲',
        }

    # Sheet: 专辑、EP — 列：序号, 歌名, 属性, 专辑名称, 平台, 入V时间 ...
    df_albums = pd.read_excel(meta_path, sheet_name='专辑、EP', header=0)
    for _, r in df_albums.iterrows():
        name = str(r.get('歌名', '')).strip()
        if not name or name == 'nan':
            continue
        album_id = str(r.get('序号', '')).strip()
        attr = str(r.get('属性', '')).strip()
        album_raw = str(r.get('专辑名称', '')).strip()
        if album_raw == 'nan':
            album_raw = ''
        platform = str(r.get('平台', '')).strip()
        if platform == 'nan':
            platform = ''
        vip = str(r.get('入V时间', '')).strip()
        if vip == 'nan' or vip == '-':
            vip = ''
        album_name = _album_display(album_id, attr, album_raw)

        if name in meta:
            meta[name]['album'] = album_name
            meta[name]['type'] = '专辑曲'
            if platform:
                meta[name]['platform'] = platform
            if vip:
                meta[name]['vip'] = vip
        else:
            meta[name] = {
                'type': '专辑曲',
                'album': album_name,
                'platform': platform,
                'vip': vip,
                'source': '专辑、EP',
            }

    print(f'[OK] 加载元数据: {len(meta)} 首')
    return meta


def _classify_from_content(content):
    if any(x in content for x in ['电视剧', '网剧', '电影', '动画', '纪录片', '综艺', '游戏', '漫改']):
        return '影视OST'
    if '品牌' in content:
        return '推广曲'
    if '个人单曲' in content:
        return '个人单曲'
    if any(x in content for x in ['演唱会', '巡回', '现场']):
        return '现场/演唱会'
    if any(x in content for x in ['企划', '返场', '网易']):
        return '企划曲'
    return '散曲'


def _album_display(album_id, attr, album_raw):
    mapping = {
        '七专': f'七专《{album_raw or "不说"}》',
        '六专': f'六专《{album_raw or "X自选集"}》',
        '五专': f'五专《{album_raw or "B面图景"}》',
        'EP': f'EP《{album_raw or "回望"}》',
    }
    if attr in mapping:
        return mapping[attr]
    if str(album_id).startswith('ZJ7'):
        return f'七专《{album_raw or "不说"}》'
    if str(album_id).startswith('ZJ6'):
        return f'六专《{album_raw or "X自选集"}》'
    if str(album_id).startswith('ZJ5'):
        return f'五专《{album_raw or "B面图景"}》'
    if str(album_id).startswith('EP'):
        return f'EP《{album_raw or "回望"}》'
    return album_raw or '其他'


def classify_by_name(song_name, meta):
    if not meta:
        return {'type': '未分类', 'album': '无', 'platform': '', 'vip': ''}

    if song_name in meta:
        return meta[song_name]

    clean = re.sub(r'[《》]', '', song_name)
    clean = re.sub(r'\s*\(.*?\)|\s*（.*?）', '', clean)

    for key, val in meta.items():
        if clean == key or clean in key or key in clean:
            return val

    if any(c in song_name for c in ['&', '、', '•']):
        return {'type': '合作曲', 'album': '无', 'platform': '', 'vip': ''}

    return {'type': '未分类', 'album': '无', 'platform': '', 'vip': ''}


class WeeklyPipeline:
    def __init__(self):
        self.today = datetime.now().strftime('%Y%m%d')
        self.today_fmt = datetime.now().strftime('%Y.%m.%d')
        self.meta = load_song_metadata()

    def find_latest_excel(self):
        files = list(RAW_DIR.glob('*.xlsx')) + list(RAW_DIR.glob('*.csv'))
        files = [f for f in files if '歌曲信息汇总表' not in f.name]
        if not files:
            print(f'未找到QQ音乐数据Excel，请放入: {RAW_DIR}')
            return None
        return max(files, key=lambda f: f.stat().st_mtime)

    def clean(self, input_file=None):
        f = input_file or self.find_latest_excel()
        if not f:
            existing = CLEAN_DIR / 'wangxi_music_clean.csv'
            if existing.exists():
                print(f'[1/4] 无新QQ音乐Excel，复用已有清洗数据: {existing.name}')
                return existing
            return False
        f = Path(f)
        print(f'[1/4] 清洗: {f.name}')

        try:
            df = pd.read_excel(f, header=0)
            if '歌曲名称' not in [str(c).strip() for c in df.columns]:
                df = pd.read_excel(f, header=1)
        except Exception:
            df = pd.read_excel(f)

        df.columns = [str(c).strip() for c in df.columns]
        df['歌曲名称'] = df.iloc[:, 0].astype(str)
        df['演唱者'] = df.iloc[:, 1].astype(str)
        df['音乐指数'] = pd.to_numeric(
            df.iloc[:, 8] if len(df.columns) > 8 else df.iloc[:, -3],
            errors='coerce',
        ).fillna(0)
        df['全站排名'] = pd.to_numeric(
            df.iloc[:, 7] if len(df.columns) > 7 else df.iloc[:, -4],
            errors='coerce',
        ).fillna(0)
        change_col = df.iloc[:, 3].astype(str)
        df['变化幅度'] = pd.to_numeric(
            change_col.str.replace(r'[%]', '', regex=True), errors='coerce'
        ).fillna(0)

        df['专辑'] = '无'
        df['歌曲类型'] = '未分类'
        df['平台'] = ''
        df['入V状态'] = ''

        for idx, row in df.iterrows():
            info = classify_by_name(row['歌曲名称'], self.meta)
            df.at[idx, '专辑'] = info['album']
            df.at[idx, '歌曲类型'] = info['type']
            df.at[idx, '平台'] = info['platform']
            df.at[idx, '入V状态'] = info['vip']

        matched = (df['歌曲类型'] != '未分类').sum()
        out = CLEAN_DIR / 'wangxi_music_clean.csv'
        df.to_csv(out, index=False, encoding='utf-8-sig')
        print(f'   清洗完成: {out} | {len(df)}首 | 元数据匹配: {matched}首')
        return out

    def generate(self, csv_file=None):
        f = csv_file or (CLEAN_DIR / 'wangxi_music_clean.csv')
        if not f.exists():
            print('未找到CSV')
            return False
        print('[2/4] 生成脱敏周报...')

        df = pd.read_csv(f)
        total = len(df)
        df_active = df[df['音乐指数'] > 0].copy()
        active_count = len(df_active)

        rising = len(df_active[df_active['变化幅度'] > 0])
        falling = len(df_active[df_active['变化幅度'] < 0])
        flat = len(df_active[df_active['变化幅度'] == 0])

        album_groups = (
            df_active[df_active['专辑'] != '无']
            .groupby('专辑')['变化幅度']
            .mean()
            .sort_values(ascending=False)
        )
        type_groups = (
            df_active.groupby('歌曲类型')['变化幅度'].mean().sort_values(ascending=False)
        )

        top_rising = df_active[df_active['变化幅度'] > 0].nlargest(
            10, '变化幅度'
        )[['歌曲名称', '演唱者', '变化幅度', '专辑', '歌曲类型']]

        top_falling = df_active[df_active['变化幅度'] < 0].nsmallest(
            10, '变化幅度'
        )[['歌曲名称', '演唱者', '变化幅度', '专辑', '歌曲类型']]

        md = f"""# 王晰音乐趋势周报 · {self.today_fmt}
> 基于 QQ 音乐数据趋势分析 | 监测 {total} 首歌曲 | 星厂 B 项目自动生成

## 本周概览
| 指标 | 数值 |
|------|------|
| 监测歌曲总数 | {total} 首 |
| 有活跃数据 | {active_count} 首 |
| 趋势上涨 | {rising} 首 |
| 趋势下跌 | {falling} 首 |
| 趋势持平 | {flat} 首 |

## 专辑趋势（平均变化幅度）
| 专辑 | 活跃曲目数 | 平均变化幅度 |
|------|-----------|-------------|
"""
        for album, avg in album_groups.head(5).items():
            cnt = len(df_active[df_active['专辑'] == album])
            trend = '↑' if avg > 0 else '↓' if avg < 0 else '→'
            md += f'| {album} | {cnt} | {trend} {avg:+.2f}% |\n'

        md += """
## 歌曲类型趋势（平均变化幅度）
| 类型 | 活跃曲目数 | 平均变化幅度 |
|------|-----------|-------------|
"""
        for stype, avg in type_groups.items():
            cnt = len(df_active[df_active['歌曲类型'] == stype])
            trend = '↑' if avg > 0 else '↓' if avg < 0 else '→'
            md += f'| {stype} | {cnt} | {trend} {avg:+.2f}% |\n'

        md += """
## 本周涨幅 TOP10
| 歌曲 | 演唱者 | 变化幅度 | 专辑/类型 |
|------|--------|----------|-----------|
"""
        for _, r in top_rising.iterrows():
            tag = r['专辑'] if r['专辑'] != '无' else r['歌曲类型']
            md += f"| {r['歌曲名称']} | {r['演唱者']} | +{r['变化幅度']:.2f}% | {tag} |\n"

        if len(top_falling) > 0:
            md += """
## 本周跌幅 TOP10
| 歌曲 | 演唱者 | 变化幅度 | 专辑/类型 |
|------|--------|----------|-----------|
"""
            for _, r in top_falling.iterrows():
                tag = r['专辑'] if r['专辑'] != '无' else r['歌曲类型']
                md += f"| {r['歌曲名称']} | {r['演唱者']} | {r['变化幅度']:.2f}% | {tag} |\n"

        md += """
## 趋势洞察
"""
        if len(album_groups) > 0:
            top_album = album_groups.index[0]
            top_album_avg = album_groups.iloc[0]
            md += f'- **{top_album}** 本周变化最活跃，平均变化幅度 {top_album_avg:+.2f}%\n'
        if len(type_groups) > 0:
            top_type = type_groups.index[0]
            top_type_avg = type_groups.iloc[0]
            direction = '上涨' if top_type_avg > 0 else '下跌' if top_type_avg < 0 else '持平'
            md += f'- **{top_type}** 类型整体呈{direction}趋势\n'
        md += f'- 本周共有 {rising} 首歌曲趋势向上，{falling} 首趋势向下\n'

        md += f"""
> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 历史周报存档: [data/weekly/](data/weekly/)
> 注：本报告仅展示相对变化趋势，不含平台原始绝对数值
"""

        out = REPORT_DIR / f'{self.today}.md'
        out.write_text(md, encoding='utf-8')
        print(f'   脱敏周报: {out}')
        return out

    @staticmethod
    def _inline(s):
        return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)

    def _md_to_html_body(self, md_text):
        lines = md_text.splitlines()
        html = []
        in_table = False
        for line in lines:
            if line.startswith('# '):
                continue
            if line.startswith('## '):
                if in_table:
                    html.append('</table>')
                    in_table = False
                html.append(f'<h2>{self._inline(line[3:])}</h2>')
            elif line.startswith('> '):
                html.append(f'<blockquote>{self._inline(line[2:])}</blockquote>')
            elif line.startswith('- '):
                if in_table:
                    html.append('</table>')
                    in_table = False
                html.append(f'<p>{self._inline(line[2:])}</p>')
            elif line.startswith('|') and '---' not in line:
                cells = [c.strip() for c in line.strip('|').split('|')]
                if not in_table:
                    html.append('<table><tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
                    in_table = True
                else:
                    html.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            elif line.startswith('|') and '---' in line:
                continue
            elif not line.strip() and in_table:
                html.append('</table>')
                in_table = False
        if in_table:
            html.append('</table>')
        return '\n        '.join(html)

    def _update_music_index_html(self, md_path):
        md_text = Path(md_path).read_text(encoding='utf-8')
        body = self._md_to_html_body(md_text)
        m = re.search(r'·\s*(\d{4}\.\d{2}\.\d{2})', md_text)
        date_str = m.group(1) if m else self.today_fmt
        iso_date = date_str.replace('.', '-')
        jsonld = json.dumps({
            '@context': 'https://schema.org',
            '@type': 'Report',
            'name': '王晰音乐趋势周报',
            'datePublished': iso_date,
            'about': {'@type': 'MusicGroup', 'name': '王晰'},
            'description': '基于QQ音乐数据趋势分析的王晰音乐周报，含监测歌曲数、涨幅TOP10与专辑/歌曲类型趋势洞察。',
            'publisher': {'@type': 'Organization', 'name': '王晰GEO资料站', 'url': 'https://wx409.github.io/'},
        }, ensure_ascii=False)
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王晰音乐趋势周报 | QQ音乐趋势监测</title>
    <meta name="description" content="王晰音乐趋势周报 · {date_str}。基于QQ音乐数据趋势分析，含监测歌曲总数、涨幅TOP10与专辑/歌曲类型趋势洞察。">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #c41e3a; padding-bottom: 10px; }}
        h2 {{ color: #2c2c2c; margin-top: 30px; border-left: 4px solid #c41e3a; padding-left: 12px; }}
        .nav {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .nav a {{ color: #c41e3a; margin-right: 20px; text-decoration: none; font-weight: 500; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 14px; }}
        th, td {{ border: 1px solid #e0e0e0; padding: 8px 10px; text-align: left; }}
        th {{ background: #f8f9fa; }}
        blockquote {{ color: #666; border-left: 4px solid #c41e3a; padding-left: 15px; margin: 20px 0; }}
        a {{ color: #c41e3a; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ color: #888; font-size: 13px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 15px; }}
    </style>
    <script type="application/ld+json">{jsonld}</script>
    <link rel="canonical" href="https://wx409.github.io/data/music-index.html">
</head>
<body>
    <div class="nav">
        <a href="../index.html">首页</a>
        <a href="../live-reviews.html">现场实录</a>
        <a href="../discography.html">作品百科</a>
        <a href="../academic.html">学术研究</a>
        <a href="../gallery.html">视觉记录</a>
        <a href="../city-guides.html">城市攻略</a>
        <a href="music-index.html">音乐数据</a>
        <a href="../culture/index.html">文化足迹</a>
    </div>

    <h1>王晰音乐趋势周报</h1>

    <div id="content">
        {body}
    </div>

    <div class="footer">
        最后更新：{date_str} · 历史周报存档：<a href="weekly/">data/weekly/</a> · 本报告仅展示相对变化趋势，不含平台原始绝对数值
    </div>
</body>
</html>'''
        (WEBSITE_DIR / 'data' / 'music-index.html').write_text(html, encoding='utf-8')
        print('   已生成 HTML')

    def deploy(self, report_file=None):
        f = report_file or (REPORT_DIR / f'{self.today}.md')
        if not f.exists():
            print('未找到周报')
            return False
        print('[3/4] 部署到网站...')
        web_data = WEBSITE_DIR / 'data' / 'weekly'
        web_data.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, web_data / f'{self.today}.md')
        shutil.copy(f, WEBSITE_DIR / 'data' / 'music-index.md')
        self._update_music_index_html(f)
        print('   已部署')
        return True

    def git_push(self):
        print('[4/4] Git提交...')
        try:
            subprocess.run(
                ['git', '-C', str(WEBSITE_DIR), 'add', 'data/'],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ['git', '-C', str(WEBSITE_DIR), 'commit', '-m', f'{self.today}: 更新音乐趋势周报'],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ['git', '-C', str(WEBSITE_DIR), 'push', 'origin', 'main'],
                check=True,
                capture_output=True,
            )
            print('   已推送: https://wx409.github.io')
            return True
        except subprocess.CalledProcessError:
            print('   Git推送失败，请手动执行')
            return False

    def run_full(self):
        print(f"\n{'='*50}\n B项目趋势周报产线 | {self.today_fmt}\n{'='*50}")
        if not self.clean():
            return
        if not self.generate():
            return
        if not self.deploy():
            return
        self.git_push()
        print(f"{'='*50}\n 产线完成\n{'='*50}\n")


if __name__ == '__main__':
    WeeklyPipeline().run_full()
