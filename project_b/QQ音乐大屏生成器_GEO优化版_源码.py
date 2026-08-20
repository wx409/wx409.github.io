# -*- coding: utf-8 -*-
"""
QQ音乐数据采集 + 历史合并 + 大屏趋势看板生成器（v3 维度增强版）

功能：
  1. 双模式定时采集（quick 极速 / full 全量），结果存 Excel
  2. 每批次采集后自动合并【历史归档目录】+【采集输出目录】的全部 Excel
  3. 重新生成自包含大屏网页（真实数据，无编造；ECharts 多 CDN 备用 / 可内嵌离线）

用法：
  python qqmusic_dashboard_整合修复版.py                 # 定时调度模式（按 SCHEDULE 采集+更新网页）
  python qqmusic_dashboard_整合修复版.py --once --full   # 立刻跑一次全量采集并更新网页
  python qqmusic_dashboard_整合修复版.py --once --quick  # 立刻跑一次极速采集并更新网页
  python qqmusic_dashboard_整合修复版.py --rebuild       # 不采集，只用已有 Excel 重建网页

可选参数（覆盖默认路径）：
  --excel <链接表.xlsx>  --records <采集输出目录>  --history <历史归档目录>  --dashboard <网页输出目录>

离线网页（可选）：把 echarts.min.js 放到本脚本同目录，生成的网页将内嵌图表库，断网也能打开。
"""
import os
import re
import sys
import time
import random
import logging
import queue
import threading
import tempfile
import json
import pickle
import argparse
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# DrissionPage 只在采集时需要；--rebuild 模式没装也能跑
try:
    from DrissionPage import ChromiumPage, ChromiumOptions
    HAS_DRISSION = True
except ImportError:
    HAS_DRISSION = False

# ==================== 用户配置 ====================
EXCEL_INPUT = r"收听人数（2026.7.24）.xlsx"      # 链接清单
OUTPUT_DIR = r"E:\wx\index_records"              # 采集 Excel 输出目录
HISTORY_DIR = r"E:\wx\指数\分年指数数据"          # 历史归档目录
DASHBOARD_DIR = os.path.join(OUTPUT_DIR, "dashboard")  # 网页输出目录
SONG_INFO_XLSX = os.path.join(OUTPUT_DIR, "王晰歌曲信息汇总.xlsx")  # 歌曲信息表（3个工作表，可选）
SETLIST_LONG_XLSX = os.path.join(OUTPUT_DIR, "历次巡演歌单", "王晰巡演歌单长表_单一事实源.xlsx")  # 巡演歌单长表（歌曲级效应唯一输入）
PERFORMANCE_EVENTS_XLSX = os.path.join(OUTPUT_DIR, "王晰演出活动.xlsx")  # 演出活动表（音乐剧/综艺等非巡演演出，辐射带动分析输入）

# ---- 网站发布配置（GEO：面向搜索引擎与 AI 引用的公开信息）----
SITE_URL = "https://wx409.github.io/dashboard"   # 大屏实际部署子目录（不带结尾 /）
ROOT_URL = "https://wx409.github.io"              # 站点根（Schema 实体关联用）
ARTIST_NAME = "王晰"                    # 追踪对象
AUTHOR_NAME = "wx409"                   # 署名（建议改为真实姓名或常用ID，增强 E-E-A-T 可信度）
UPDATE_FREQ_DESC = "每日多批次自动监测更新"

# 批次 Excel 归档路径（index_records 不再堆积每日表格）
DOWNLOAD_MAIN = r"E:\wx\download"                        # 23:51 终批 -> 保存位置①
DB_INCREMENT = r"E:\wx\指数数据库\增补数据库2025.2.22-"    # 23:51 终批 -> 保存位置②
QUICK_DIR = r"E:\wx\指数vs"                              # 其他所有批次 -> 保存位置
EDGE_EXE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WEBSITE_REPO = r"D:\wx409.github.io"                      # GitHub Pages 本地仓库路径（自动推送目标）

# 增量合并缓存：把 1600+ 个历史 Excel 的合并结果缓存为单文件，
# 每批次只读取新增/变更的 2-4 个 Excel 增量合并，rebuild 从 ~19 分钟降到 ~1 分钟
MERGE_CACHE_PATH = os.path.join(OUTPUT_DIR, "merge_cache.pkl")
MERGE_CACHE_VERSION = 2  # v2：缓存从「原始 concat 1439万行」改为「过滤后 ~43万行」，旧 v1 缓存（2GB）自动失效

TAB_COUNT_QUICK = 20
TAB_COUNT_FULL = 15
PAGE_TIMEOUT = 10

# 双模式调度
SCHEDULE = [
    ("8:05", "quick"), ("8:15", "quick"), ("8:25", "quick"),
    ("11:49", "quick"), ("11:59", "quick"), ("12:18", "quick"),
    ("13:09", "quick"),
    ("18:05", "quick"), ("18:15", "quick"), ("18:25", "quick"),
    ("18:39", "quick"), ("18:45", "quick"), ("18:55", "quick"),
    ("19:21", "quick"), ("20:30", "quick"),
    ("21:00", "quick"), ("21:30", "quick"),
    ("23:15", "full"), ("23:55", "full"),
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("qqmusic_dp_edge.log", encoding="utf-8", mode="a"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 数据谱系统计（lineage）：rebuild 全程收集清洗统计，写入 payload 供大屏「数据谱系」面板展示
LINEAGE = {}

# ==================== 自动查找 Edge ====================
def find_edge_exe():
    if EDGE_EXE_PATH and os.path.exists(EDGE_EXE_PATH) and EDGE_EXE_PATH.endswith("msedge.exe"):
        return EDGE_EXE_PATH
    candidates = [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        for base in [r"C:\Program Files\Microsoft\Edge\Application", r"C:\Program Files (x86)\Microsoft\Edge\Application"]:
            p = os.path.join(base, version, "msedge.exe")
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return ""

# ==================== 浏览器初始化 ====================
def init_browser():
    co = ChromiumOptions()
    edge_path = find_edge_exe()
    if edge_path:
        co.set_browser_path(edge_path)
        logger.info(f"使用 Edge: {edge_path}")
    else:
        logger.warning("未找到 Edge，尝试使用系统默认 Chromium")

    user_data_dir = os.path.join(tempfile.gettempdir(), f"dp_user_data_{int(time.time())}")
    co.set_user_data_path(user_data_dir)
    port = random.randint(19222, 19999)
    co.set_address(f"127.0.0.1:{port}")

    co.headless(True)
    co.set_argument('--disable-gpu')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-extensions')
    co.set_argument('--disable-images')
    co.set_argument('--blink-settings=imagesEnabled=false')
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--disable-background-networking')
    co.set_argument('--disable-default-apps')
    co.set_argument('--disable-sync')
    co.set_argument('--no-first-run')
    co.set_argument('--disable-features=TranslateUI')
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0')

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            browser = ChromiumPage(addr_or_opts=co)
            return browser
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"浏览器启动失败（第{attempt}/{max_retries}次），换端口重试: {e}")
                time.sleep(3)
                # 换端口 + 换用户目录，避免残留占用
                co.set_address(f"127.0.0.1:{random.randint(19222, 19999)}")
                co.set_user_data_path(os.path.join(tempfile.gettempdir(), f"dp_user_data_{int(time.time())}"))
            else:
                logger.error(f"浏览器启动失败，已重试{max_retries}次")
                raise

# ==================== JS 提取器 ====================
JS_FULL = r"""
try {
    var r = {};
    var n1 = document.querySelector('.info_album_tit');
    r.song = n1 ? n1.innerText.trim() : document.title.replace(/[-–—]\s*QQ音乐.*$/,'').trim();
    var n2 = document.querySelector('.info_album_txt');
    r.singer = n2 ? n2.innerText.trim() : '';
    var n3 = document.querySelector('.info_album__listen');
    r.listen = n3 ? n3.getAttribute('aria-label').replace('人正在听','').trim() : '';
    var n4 = document.querySelector('.base_tit__desc');
    r.time = n4 ? n4.innerText.replace('最近更新','').trim() : '';
    var x1 = document.evaluate("//div[contains(@aria-label, '实时音乐指数')]//div[@class='base_data__num']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    r.idx = x1 ? x1.innerText.trim() : '';
    var x2 = document.evaluate("//div[contains(@aria-label, '全站排名')]//div[@class='base_data__num']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    r.rank = x2 ? x2.innerText.trim() : '';
    var y1 = document.evaluate("//div[contains(@aria-label, '昨日指数')]//div[@class='base_mini_data__num']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    r.yIdx = y1 ? y1.innerText.trim() : '';
    var y2 = document.evaluate("//div[contains(@aria-label, '较前一天')]//div[@class='base_mini_data__num']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    r.yChange = y2 ? y2.innerText.trim() : '';
    var y3 = document.evaluate("//div[contains(@aria-label, '昨日排名')]//div[@class='base_mini_data__num']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    r.yRank = y3 ? y3.innerText.trim() : '';
    var y4 = document.evaluate("//div[contains(@aria-label, '较前一天')]/following-sibling::div[contains(@class, 'base_mini_data__item')][2]//div[@class='base_mini_data__num']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    r.yRankChange = y4 ? y4.innerText.trim() : '';
    var achs = document.querySelectorAll('.history_item');
    var aList = [];
    for(var i=0;i<achs.length;i++){
        var lbl = achs[i].getAttribute('aria-label');
        if(lbl) aList.push(lbl);
    }
    r.ach = aList.join('\n');
    return JSON.stringify(r);
} catch(e) {
    return JSON.stringify({error: e.message});
}
"""

JS_QUICK = r"""
try {
    var r = {};
    var n1 = document.querySelector('.info_album_tit');
    r.song = n1 ? n1.innerText.trim() : document.title.replace(/[-–—]\s*QQ音乐.*$/,'').trim();
    var n2 = document.querySelector('.info_album_txt');
    r.singer = n2 ? n2.innerText.trim() : '';
    var n3 = document.querySelector('.info_album__listen');
    r.listen = n3 ? n3.getAttribute('aria-label').replace('人正在听','').trim() : '';
    var n4 = document.querySelector('.base_tit__desc');
    r.time = n4 ? n4.innerText.replace('最近更新','').trim() : '';
    return JSON.stringify(r);
} catch(e) {
    return JSON.stringify({error: e.message});
}
"""

# ==================== 单条采集 ====================
def wait_song_ready(tab, timeout=3.5, interval=0.35):
    """等待歌曲页 SPA 渲染出歌名元素 .info_album_tit。

    tab.wait.doc_loaded() 只保证 HTML 壳加载完成，QQ音乐页面由 JS 动态渲染，
    过早提取会拿到空壳（title 为空、无歌名元素），导致"识别不到歌曲名称"。
    """
    end = time.time() + timeout
    while time.time() < end:
        try:
            if str(tab.run_js("return document.querySelector('.info_album_tit') ? 1 : 0;")).strip() == "1":
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def fetch_song_by_mid(mid):
    """mid 兜底：调 QQ音乐公开接口获取歌曲名/歌手（页面渲染失败时补名）。

    链接本身带 songmid，直接用官方老版单曲接口（稳定、无需登录）取歌名，
    绕开页面渲染。返回 (name, singer)；失败返回 ("", "")。
    仅作兜底，不影响正常采集。
    """
    import urllib.request, urllib.parse
    api = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
    try:
        url = api + "?" + urllib.parse.urlencode(
            {"songmid": mid, "format": "json", "outCharset": "utf-8"})
        req = urllib.request.Request(url, headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0 Safari/537.36"),
            "Referer": "https://y.qq.com/",
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
        arr = j.get("data") or []
        if not arr:
            return "", ""
        s = arr[0]
        name = (s.get("name") or s.get("songname") or "").strip()
        singers = ",".join(a.get("name", "") for a in (s.get("singer") or []) if a.get("name"))
        return name, singers
    except Exception:
        return "", ""


def scrape_one(tab, url, idx, debug_dir, mode="full", max_retry=1):
    is_quick = (mode == "quick")
    js_code = JS_QUICK if is_quick else JS_FULL
    base_sleep = 0.05 if is_quick else 0.2
    retry_sleep = 0.3 if is_quick else 0.5

    for attempt in range(max_retry + 1):
        data = {
            "序号": idx, "歌曲名称": "", "演唱者": "",
            "昨日音乐指数": "", "较前一日": "", "昨日全站排名": "", "较前一日1": "",
            "当前时间": "", "全站排名": "", "音乐指数": "",
            "当前收听人数": "", "历史成绩": "",
            "链接": url, "状态": "成功"
        }
        try:
            tab.get(url, timeout=PAGE_TIMEOUT)
            tab.wait.doc_loaded()
            time.sleep(random.uniform(base_sleep, base_sleep + 0.15))
            # 等待 SPA 渲染出歌名元素，避免拿到空壳页面
            wait_song_ready(tab)

            js_res_raw = tab.run_js(js_code)
            js_res = json.loads(js_res_raw) if js_res_raw and isinstance(js_res_raw, str) else {}

            if js_res.get("error"):
                if attempt < max_retry:
                    time.sleep(retry_sleep)
                    continue
                data["状态"] = f"失败: {js_res['error'][:50]}"
                return data

            data["歌曲名称"] = js_res.get("song", "")
            data["演唱者"] = js_res.get("singer", "")
            data["当前收听人数"] = js_res.get("listen", "")
            data["当前时间"] = js_res.get("time", "")

            if not is_quick:
                data["音乐指数"] = js_res.get("idx", "")
                data["全站排名"] = js_res.get("rank", "")
                data["昨日音乐指数"] = js_res.get("yIdx", "")
                data["较前一日"] = js_res.get("yChange", "")
                data["昨日全站排名"] = js_res.get("yRank", "")
                data["较前一日1"] = js_res.get("yRankChange", "")
                data["历史成绩"] = js_res.get("ach", "")

            if not data["歌曲名称"] and attempt < max_retry:
                continue

            if not data["歌曲名称"]:
                # 页面渲染失败兜底：用链接中的 mid 调官方接口补歌名
                mid = extract_mid(url)
                if mid:
                    api_name, api_singer = fetch_song_by_mid(mid)
                    if api_name:
                        data["歌曲名称"] = api_name
                        if not data["演唱者"]:
                            data["演唱者"] = api_singer
                        data["状态"] = "成功"
                        return data
                data["状态"] = "警告: 歌曲名为空"
                try:
                    with open(os.path.join(debug_dir, f"debug_page_{idx}.html"), "w", encoding="utf-8") as f:
                        f.write(tab.html)
                except Exception:
                    pass
            return data

        except Exception as e:
            if attempt < max_retry:
                time.sleep(retry_sleep)
                continue
            data["状态"] = f"失败: {str(e)}"
            return data

# ==================== 多线程工作器 ====================
def worker(tab, q, results, lock, debug_dir, total, mode):
    is_quick = (mode == "quick")
    while True:
        try:
            idx, url = q.get_nowait()
        except queue.Empty:
            break

        res = scrape_one(tab, url, idx, debug_dir, mode=mode)
        with lock:
            results.append(res)
            done = len(results)
            if done % 50 == 0 or done == total:
                logger.info(f"进度: {done}/{total} ({done*100//total}%)")

        mark = "OK" if res["状态"] == "成功" else ("!" if "警告" in res["状态"] else "X")
        logger.info(f"{mark} 第 {idx} 条 | {res['歌曲名称'][:20]} | {res['状态']}")
        # 修复：原代码 full 模式给 sleep 传了元组 (0.1, 0.3)，会直接 TypeError 崩溃
        time.sleep(random.uniform(0.05, 0.15) if is_quick else random.uniform(0.1, 0.3))

# ==================== Excel读写 ====================
def read_links(excel_path):
    if not os.path.exists(excel_path):
        logger.error(f"文件不存在: {excel_path}")
        return []
    df = pd.read_excel(excel_path, header=0)
    links = []
    for i, row in df.iterrows():
        val0 = str(row.iloc[0]).strip()
        if val0 in ("2026-7 序号", "序号", "nan"):
            continue
        if len(row) < 4:
            continue
        url = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
        if not url.startswith("http"):
            continue
        if str(row.iloc[1]).strip() == "歌曲名称":
            continue
        links.append((i + 1, url))
    logger.info(f"从Excel读取到 {len(links)} 条有效链接")
    return links

# ==================== 文件名生成 ====================
def get_output_filename(mode, run_time_str):
    now = datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    if mode == "quick":
        return f"{date_str}_{now.strftime('%H%M')}_quick.xlsx"
    else:
        if run_time_str == "23:55":
            return f"{date_str}.xlsx"
        else:
            return f"{date_str}_{now.strftime('%H%M')}.xlsx"

# ============================================================
# 第二部分：历史数据读取 + 统一身份识别（链接为准）
# ============================================================
def parse_date_from_filename(filename):
    m = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", filename)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", filename)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None

def clean_numeric(val):
    if pd.isna(val):
        return np.nan
    s = str(val).replace(",", "").replace(" ", "").replace("人正在听", "").replace("最近更新", "").strip()
    if s in ("", "-", "NaN", "nan", "10w+"):
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

def clean_pct(val):
    if pd.isna(val):
        return np.nan
    s = str(val).replace("%", "").replace(" ", "").strip()
    if s in ("", "-", "NaN", "nan"):
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

def norm_name(s):
    """名称规范化：全半角统一 + 去空白（仅用于匹配，不改变展示名）"""
    import unicodedata
    s = unicodedata.normalize("NFKC", str(s)).strip()
    return re.sub(r"\s+", "", s)

def extract_mid(link):
    """从 QQ 音乐链接提取稳定的 mid 作为唯一身份"""
    if pd.isna(link):
        return None
    m = re.search(r"[?&](?:mid|type)=([A-Za-z0-9]+)", str(link))
    return m.group(1) if m else None

# 非歌曲内容（播客/综艺/电台条目），不计入歌曲统计
NONSONG_PATTERN = (
    "期|睡前故事|王晰，请回答|漫步|漫行|逛逛|走进|寻觅|夜游|雨天行舟|滨江|从暂停|品一杯|喝一杯|"
    "听雨赏雨|品晚冬|品飞行|念一场|花见酒|四季春|心动的感觉|一杯白朗姆|一杯青梅酒|与骑行|爱的温度|"
    "穿过漫长|迎接|用温热|雪落|初雪|愿你有|寒冬|人与梅|在葡萄|与利柏特|热薄荷|一杯深情|星星藏进|四月|晚风轻吹"
)

def detect_header_row(fpath, max_rows=8):
    try:
        raw = pd.read_excel(fpath, header=None, nrows=max_rows)
    except Exception:
        return 0
    for i in range(len(raw)):
        joined = "|".join(str(v) for v in raw.iloc[i].tolist())
        if ("歌" in joined and ("曲" in joined or "名" in joined)) or "song" in joined.lower():
            return i
    return 0

def match_song_col(c):
    c2 = re.sub(r"\s", "", str(c))
    if c2 in ("歌曲名称", "歌曲名", "歌名", "曲名", "歌曲", "名称"):
        return True
    if "歌" in c2 and ("曲" in c2 or "名" in c2 or "称" in c2):
        return True
    if "" in c2 and ("歌" in c2 or "曲" in c2):
        return True
    if c2.lower() in ("song", "songname", "song_name", "title", "name"):
        return True
    return False

def fuzzy_match_column(col_name):
    c = re.sub(r"\s", "", str(col_name))
    exact_map = {
        "歌曲名称": "song_name", "演唱者": "singer", "歌手": "singer", "艺人": "singer",
        "昨日音乐指数": "yesterday_index", "较前一日": "day_change_pct",
        "昨日全站排名": "yesterday_rank", "较前一日1": "rank_change",
        "更新日期": "update_date", "当前时间": "current_time",
        "全站排名": "current_rank", "音乐指数": "current_index", "指数": "current_index",
        "当前收听人数": "listeners", "收听人数": "listeners", "收听": "listeners",
        "指数日期": "index_date", "历史成绩": "history", "变化幅度": "change_amplitude",
        "序号": "seq", "链接": "link", "状态": "status", "排名": "current_rank",
    }
    if c in exact_map:
        return exact_map[c]
    if match_song_col(c):
        return "song_name"
    if "演唱" in c or "歌手" in c:
        return "singer"
    if "昨日" in c and "指数" in c:
        return "yesterday_index"
    if "昨日" in c and "排" in c:
        return "yesterday_rank"
    if "指数" in c:
        return "current_index"
    if "收听" in c or "在听" in c:
        return "listeners"
    if "排" in c and "名" in c:
        return "current_rank"
    if "链" in c and "接" in c:
        return "link"
    if len(c) > 10 and ("更" in c or "新" in c or "时" in c or "间" in c):
        return "current_time"
    return None

def guess_song_col_by_content(df, used_cols):
    for c in df.columns:
        if c in used_cols:
            continue
        vals = df[c].dropna().astype(str).head(20).tolist()
        if not vals:
            continue
        if any(v.startswith("http") for v in vals):
            continue
        chinese = sum(1 for v in vals if re.search(r"[一-鿿]", v))
        numeric = sum(1 for v in vals if re.fullmatch(r"[\d.,%+-]+", v.strip()))
        if chinese >= max(3, len(vals) // 2) and numeric <= len(vals) // 4:
            return c
    return None

def standardize_df(df, filename):
    date_str = parse_date_from_filename(filename)
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all")

    rename_map = {}
    for c in df.columns:
        if "全站排" in c and "昨日" in c:
            rename_map[c] = "昨日全站排名"
    if rename_map:
        df = df.rename(columns=rename_map)

    df_std = pd.DataFrame()
    used_cols = set()
    for c in df.columns:
        std = fuzzy_match_column(c)
        if std and std not in df_std.columns:
            df_std[std] = df[c]
            used_cols.add(c)

    if "song_name" not in df_std.columns:
        guess = guess_song_col_by_content(df, used_cols)
        if guess is not None:
            df_std["song_name"] = df[guess]
            logger.info(f"    [{filename}] 按内容推断歌曲名列为: {guess}")

    if "song_name" not in df_std.columns:
        logger.warning(f"    [{filename}] 无法识别歌曲名列，实际表头: {list(df.columns)[:10]}")
        return pd.DataFrame()

    if "singer" not in df_std.columns:
        df_std["singer"] = ""
    if "link" not in df_std.columns:
        df_std["link"] = np.nan
    for col in ["yesterday_index", "current_index", "yesterday_rank", "rank_change", "listeners", "current_rank"]:
        if col in df_std.columns:
            df_std[col] = df_std[col].apply(clean_numeric)
    if "day_change_pct" in df_std.columns:
        df_std["day_change_pct"] = df_std["day_change_pct"].apply(clean_pct)

    df_std["data_date"] = date_str
    df_std["song_name"] = df_std["song_name"].astype(str).str.strip()
    bad_names = {"歌曲名称", "歌曲名", "歌名", "曲名", "nan", "None", ""}
    df_std = df_std[df_std["song_name"].notna()]
    df_std = df_std[~df_std["song_name"].isin(bad_names)]
    df_std = df_std[~df_std["song_name"].str.contains("名称|歌名", na=False) & (df_std["song_name"].str.len() <= 40)]
    return df_std

def read_one_excel(fpath):
    fname = os.path.basename(fpath)
    try:
        header_row = detect_header_row(fpath)
        df_raw = pd.read_excel(fpath, header=header_row)
        if df_raw.empty:
            return None, "空文件"
        df_std = standardize_df(df_raw, fname)
        if df_std.empty:
            return None, "标准化后无数据"
        return df_std, None
    except Exception as e:
        return None, str(e)

def build_link_registry(df_all):
    """从数据中所有带链接的行建立 链接mid <-> 歌名 注册表"""
    reg = df_all[df_all["mid"].notna()][["song_name", "mid"]].drop_duplicates()
    # 同时读取链接清单 Excel 补充注册表
    if EXCEL_INPUT and os.path.exists(EXCEL_INPUT):
        try:
            df_in = pd.read_excel(EXCEL_INPUT, header=0)
            for _, row in df_in.iterrows():
                if len(row) < 4:
                    continue
                url = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                mid = extract_mid(url)
                if mid and name and name not in ("歌曲名称", "nan"):
                    reg = pd.concat([reg, pd.DataFrame([{"song_name": name, "mid": mid}])], ignore_index=True)
        except Exception as e:
            logger.warning(f"读取链接清单补充注册表失败: {e}")
    reg = reg.drop_duplicates(subset=["mid"])
    reg["norm"] = reg["song_name"].map(norm_name)
    mid2name = dict(zip(reg["mid"], reg["song_name"]))
    name2mids = reg.groupby("norm")["mid"].apply(set).to_dict()
    logger.info(f"链接注册表: {len(mid2name)} 个唯一链接(mid)")
    LINEAGE["link_registry"] = int(len(mid2name))
    return mid2name, name2mids

def assign_uids(df_all, mid2name, name2mids):
    """统一身份：有链接用链接mid；无链接但歌名唯一对应一个链接的归入该链接；其余按规范化歌名"""
    _t0 = time.time()
    df_all = df_all.copy()
    df_all["norm"] = df_all["song_name"].map(norm_name)

    # 向量化 uid 分配（与逐行 apply 语义完全一致；43 万行由分钟级降到秒级）
    has_mid = df_all["mid"].notna() & (df_all["mid"].astype(str).str != "")
    mid_vals = df_all["mid"].where(has_mid)
    name_mids = df_all["norm"].map(lambda n: name2mids.get(n) or set())
    solo_mid = name_mids.map(lambda s: next(iter(s)) if len(s) == 1 else None)

    uid = np.empty(len(df_all), dtype=object)
    uid[has_mid.values] = ("L:" + mid_vals[has_mid].astype(str)).values
    no_mid = ~has_mid.values
    solo = no_mid & solo_mid.notna().values
    uid[solo] = ("L:" + solo_mid[solo].astype(str)).values
    uid[no_mid & ~solo] = ("N:" + df_all.loc[no_mid & ~solo, "norm"].astype(str)).values
    df_all["uid"] = uid
    logger.info(f"uid 身份分配(向量化): {time.time()-_t0:.1f}s")

    # 展示名：链接身份用注册表名，名称身份用出现最多的原始名
    def display_name(uid, grp):
        if uid.startswith("L:"):
            n = mid2name.get(uid[2:])
            if n:
                return n
        return grp["song_name"].mode().iloc[0]

    name_map = {}
    for uid, grp in df_all.groupby("uid"):
        name_map[uid] = display_name(uid, grp)
    df_all["display_name"] = df_all["uid"].map(name_map)
    logger.info(f"uid 展示名归并: {len(name_map)} 个身份, 共耗时 {time.time()-_t0:.1f}s")
    return df_all, name_map

def load_all_history(dirs, use_cache=True):
    # ---- 增量合并缓存：只读取新增/变更的 Excel，历史结果从缓存载入 ----
    cache_key = lambda p: f"{os.path.getsize(p)}:{os.path.getmtime(p)}"
    cache_payload = None
    if use_cache and os.path.exists(MERGE_CACHE_PATH):
        try:
            with open(MERGE_CACHE_PATH, "rb") as f:
                cache_payload = pickle.load(f)
            if cache_payload.get("version") != MERGE_CACHE_VERSION:
                cache_payload = None
        except Exception:
            cache_payload = None

    cached_files = (cache_payload or {}).get("files", {})     # path -> key
    cached_raw = (cache_payload or {}).get("raw")             # DataFrame（已 data_date 过滤 + 剔除非歌曲，未 uid 归并）

    # 扫描当前全部源文件
    all_files = []
    for base_dir in dirs:
        if not base_dir or not os.path.isdir(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            if any(k in root.lower() for k in ("dashboard", "debug", "raw_archive", "历次巡演歌单")):
                continue
            for f in files:
                if f.endswith((".xlsx", ".xls")) and not f.startswith("~$"):
                    all_files.append(os.path.join(root, f))
    all_files = sorted(set(all_files))
    logger.info(f"发现 {len(all_files)} 个Excel文件")

    # 找出需要重读的文件：新增的 + 内容变化的 + 缓存中已删除的
    need_read = []
    for p in all_files:
        k = cache_key(p)
        if cached_files.get(p) != k:
            need_read.append(p)
    removed_paths = [p for p in cached_files if p not in set(all_files)]

    fail_list = []
    frames = []
    use_base = use_cache and cache_payload and cached_raw is not None
    if use_base:
        base = cached_raw
        if removed_paths:
            src_col = [c for c in base.columns if c.startswith("_src_")]
            if src_col:
                base = base[~base[src_col[0]].isin(removed_paths)]
                logger.info(f"缓存剔除已删除文件")
        frames.append(base)
        if need_read:
            logger.info(f"增量读取 {len(need_read)} 个文件（历史缓存复用 {len(cached_files)} 个）")
        else:
            logger.info("缓存命中：无新增/变更文件，直接复用历史合并结果")
    else:
        if need_read or not all_files:
            logger.info(f"首次构建缓存（或缓存失效），全量读取 {len(all_files)} 个文件")

    for fpath in need_read:
        fname = os.path.basename(fpath)
        df_std, err = read_one_excel(fpath)
        if df_std is not None:
            _mseq = re.search(r"_(\d{4})", fname)
            df_std["_seq"] = int(_mseq.group(1)) if _mseq else 2400
            df_std["_src_path"] = fpath
            frames.append(df_std)
        else:
            fail_list.append(fname)
            logger.warning(f"  FAIL {fname}: {err}")

    # 统一清洗：data_date 解析 + 剔除非歌曲（对增量帧与缓存帧幂等）
    if frames:
        df_all = pd.concat(frames, ignore_index=True)
        df_all["data_date"] = pd.to_datetime(df_all["data_date"], errors="coerce")
        df_all = df_all[df_all["data_date"].notna()]
        before = len(df_all)
        nonsong = df_all["song_name"].map(norm_name).str.contains(NONSONG_PATTERN, na=False)
        df_all = df_all[~nonsong]
        logger.info(f"剔除非歌曲内容 {before - len(df_all)} 行（{nonsong.sum() / max(before,1) * 100:.1f}%），保留歌曲记录 {len(df_all)} 行")
        LINEAGE["nonsong_filtered"] = {"rows": int(before - len(df_all)), "pct": round(nonsong.sum() / max(before,1) * 100, 1)}
    else:
        df_all = pd.DataFrame()

    # 缓存只对「过滤后 concat」做持久化（约 40 万行），供下次增量复用；
    # 仅在有新增/变更/删除文件时才重写缓存；纯命中时直接复用
    if use_cache and frames and (need_read or removed_paths):
        new_files = {p: cache_key(p) for p in all_files}
        try:
            with open(MERGE_CACHE_PATH + ".tmp", "wb") as f:
                pickle.dump({"version": MERGE_CACHE_VERSION, "files": new_files, "raw": df_all}, f)
            os.replace(MERGE_CACHE_PATH + ".tmp", MERGE_CACHE_PATH)
            logger.info(f"增量缓存已更新: {len(new_files)} 个文件指纹 | {len(df_all)} 行数据")
        except Exception as e:
            logger.warning(f"增量缓存写入失败（不影响本次构建）: {e}")

    LINEAGE["excel_files"] = {"total": len(all_files), "success": len(all_files) - len(fail_list), "failed": list(fail_list)}
    if fail_list:
        logger.info(f"失败文件 {len(fail_list)} 个: {fail_list[:10]}{'...' if len(fail_list) > 10 else ''}")
    if df_all.empty:
        return pd.DataFrame(), {}

    df_all["mid"] = df_all["link"].map(extract_mid)
    mid2name, name2mids = build_link_registry(df_all)
    df_all, name_map = assign_uids(df_all, mid2name, name2mids)

    # 同一首歌同一天：日内多批次按字段取最新有效值（解决 23:39/23:55 取舍，互相补全）
    # 向量化：按 _seq 排序后，每列取组内（uid, data_date）_seq 最大的有效值（原 groupby.agg 逐组 Python 调用，由分钟级降到秒级）
    before = len(df_all)
    df_all = df_all.sort_values(["uid", "data_date", "_seq"])
    group_cols = ["uid", "data_date"]
    merge_cols = [c for c in df_all.columns if c not in (set(group_cols) | {"_seq"})]
    base = df_all.drop_duplicates(subset=group_cols).set_index(group_cols)
    _uid_re = re.compile(r"^[LN]:[A-Za-z0-9]+$")
    for col in merge_cols:
        valid = df_all[col].notna()
        if df_all[col].dtype == object:
            sstr = df_all[col].astype(str)
            valid &= sstr.str.strip().ne("") & ~sstr.str.match(_uid_re, na=False)
        if not valid.any():
            base[col] = np.nan
            continue
        sub = df_all[valid]
        # 组内行序即排序序（df 已按 uid/data_date/_seq 稳定处理），取组内最后一个有效行
        sub = sub.assign(_rnk=sub.groupby(group_cols).cumcount())
        idx = sub.groupby(group_cols)["_rnk"].idxmax()
        rows = sub.loc[idx, [*group_cols, col]].copy()
        rows.index = pd.MultiIndex.from_frame(rows[group_cols])
        base[col] = rows[col]
    df_all = base.reset_index()
    after = len(df_all)
    logger.info(f"日内多批次合并: {before} -> {after} 行（按字段取最新有效值，前批次补全后批次缺失）")
    LINEAGE["intraday_merged"] = {"before": int(before), "after": int(after)}

    # 校验：display_name 不应泄漏 uid 格式（L:/N:）
    leak = int(df_all["display_name"].astype(str).str.match(r"^[LN]:[A-Za-z0-9]+$").sum())
    if leak > 0:
        logger.warning(f"检测到 {leak} 行 display_name 仍为 uid 格式（L:/N:），存在 uid 泄漏风险")
    df_all = df_all.drop(columns=["_seq", "_src_path"], errors="ignore").reset_index(drop=True)

    # 指数口径校准：某日的官方指数 = 次日抓到的「昨日音乐指数」；
    # 无次日数据时退回当日「音乐指数」（同日去重后已是 23:51 终批值）
    if "yesterday_index" in df_all.columns:
        y = df_all[df_all["yesterday_index"].notna()][["uid", "data_date", "yesterday_index"]].copy()
        y["data_date"] = y["data_date"] - pd.Timedelta(days=1)
        y = y.drop_duplicates(subset=["uid", "data_date"], keep="last")
        y = y.rename(columns={"yesterday_index": "_yidx"})
        df_all = df_all.merge(y, on=["uid", "data_date"], how="left")
        calibrated = int(df_all["_yidx"].notna().sum())
        df_all["current_index"] = df_all["_yidx"].combine_first(df_all["current_index"])
        df_all = df_all.drop(columns=["_yidx"])
        logger.info(f"指数口径校准: {calibrated}/{len(df_all)} 行采用『昨日音乐指数』官方值（{calibrated / max(len(df_all),1) * 100:.1f}%），其余为当日终批音乐指数")
        LINEAGE["index_calibration"] = {"rows": int(calibrated), "total": int(len(df_all)),
                                        "pct": round(calibrated / max(len(df_all),1) * 100, 1)}
    return df_all, {"mid2name": mid2name, "name_map": name_map}

# ============================================================
def extract_listener_from_dirs(scan_dirs, use_cache=True):
    """扫描指定目录中所有 Excel 文件，提取当前收听人数（仅 listeners 列），
    以同一链接(mid)身份归并，同歌同日取最大值。返回 peak_listeners DataFrame 或 None。"""
    if not scan_dirs:
        return None
    # 优先复用增量合并缓存（load_all_history 刚更新），避免二次全量读取 1600+ Excel
    raw = None
    if use_cache and os.path.exists(MERGE_CACHE_PATH):
        try:
            with open(MERGE_CACHE_PATH, "rb") as f:
                _payload = pickle.load(f)
            if _payload.get("version") == MERGE_CACHE_VERSION:
                raw = _payload.get("raw")
        except Exception:
            raw = None
    all_data = []
    if raw is not None:
        src_col = [c for c in raw.columns if c.startswith("_src_")]
        if src_col and "listeners" in raw.columns:
            src = raw[src_col[0]]
            keep = src.map(lambda p: any(str(p).startswith(str(d)) for d in scan_dirs))
            sub = raw[keep]
            if not sub.empty:
                need = ["data_date", "song_name", "singer", "link", "listeners"]
                exist = [c for c in need if c in sub.columns]
                sub = sub[sub["listeners"].notna()][exist]
                all_data.append(sub)
                logger.info(f"收听人数提取：缓存复用 {len(sub)} 行")
        else:
            raw = None
    if raw is None and not all_data:
        for base_dir in scan_dirs:
            if not base_dir or not os.path.isdir(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                if any(k in root.lower() for k in ("dashboard", "debug", "raw_archive")):
                    continue
                for f in files:
                    if f.endswith((".xlsx", ".xls")) and not f.startswith("~$"):
                        fpath = os.path.join(root, f)
                        df_std, _ = read_one_excel(fpath)
                        if df_std is not None and "listeners" in df_std.columns:
                            df_std = df_std[df_std["listeners"].notna()]
                            if not df_std.empty:
                                all_data.append(df_std[["data_date", "song_name", "singer", "link", "listeners"]])
    if not all_data:
        return None
    ls_all = pd.concat(all_data, ignore_index=True)
    ls_all["data_date"] = pd.to_datetime(ls_all["data_date"], errors="coerce")
    ls_all = ls_all[ls_all["data_date"].notna()]
    # 剔除临时公式污染行
    bad_names = {"歌曲名称", "歌曲名", "歌名", "曲名", "nan", "None", ""}
    ls_all = ls_all[~ls_all["song_name"].isin(bad_names)]
    ls_all = ls_all[~ls_all["song_name"].str.contains("名称|歌名", na=False) & (ls_all["song_name"].str.len() <= 40)]
    ls_all["mid"] = ls_all["link"].map(extract_mid)
    ls_all["norm"] = ls_all["song_name"].map(norm_name)

    # 用已有的 name2mids 注册表做身份归并
    name2mids = {}
    if os.path.exists(EXCEL_INPUT):
        try:
            reg = pd.read_excel(EXCEL_INPUT, header=0)
            for _, row in reg.iterrows():
                if len(row) < 4: continue
                url = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                mid = extract_mid(url)
                if mid and name and name not in bad_names:
                    n = norm_name(name)
                    name2mids.setdefault(n, set()).add(mid)
        except Exception:
            pass

    def to_uid(row):
        if pd.notna(row["mid"]) and row["mid"]:
            return "L:" + row["mid"]
        mids = name2mids.get(row["norm"])
        if mids and len(mids) == 1:
            return "L:" + next(iter(mids))
        return "N:" + row["norm"]
    ls_all["uid"] = ls_all.apply(to_uid, axis=1)

    peak = ls_all.groupby(["uid", "data_date"])["listeners"].max().reset_index()
    peak = peak.rename(columns={"listeners": "peak_listeners"})
    n_dirs = len([d for d in scan_dirs if d])
    logger.info(f"收听人数峰值: {len(peak)} 条 (uid×日期)，仅扫描 {n_dirs} 个指定目录（同歌同日取最大值）")
    return peak


# ============================================================
# 第二部分B：维度分析（参考 2.0 文档，按 uid 计算）
# ============================================================
def analyze_trends(df_all):
    """异常活跃分析（按 uid）"""
    song_stats = []
    for uid, group in df_all.groupby("uid"):
        group = group.sort_values("data_date")
        if len(group) < 2:
            continue
        idx_values = group["current_index"].dropna()
        rank_values = group["current_rank"].dropna()
        if len(idx_values) < 2:
            continue
        latest = group.iloc[-1]
        idx_change = ((idx_values.iloc[-1] - idx_values.iloc[0]) / max(idx_values.iloc[0], 1)) * 100
        rank_change = (float(rank_values.iloc[-1]) - float(rank_values.iloc[0])) if len(rank_values) >= 2 else 0
        if "day_change_pct" in group.columns:
            avg_growth = group["day_change_pct"].mean()
            max_growth = group["day_change_pct"].max()
        else:
            avg_growth = np.nan
            max_growth = np.nan
        latest_idx = float(latest["current_index"]) if pd.notna(latest.get("current_index")) else 0
        latest_listeners = float(latest["listeners"]) if pd.notna(latest.get("listeners")) else 0
        score = 0
        if pd.notna(avg_growth) and avg_growth > 10: score += 30
        if pd.notna(max_growth) and max_growth > 50: score += 25
        if idx_change > 50: score += 25
        if rank_change < -10000: score += 20
        if latest_idx > 1000: score += 15
        if latest_listeners > 100: score += 10
        song_stats.append({
            "uid": uid, "song_name": latest["display_name"],
            "idx_change_pct": round(idx_change, 1),
            "avg_growth": round(float(avg_growth), 1) if pd.notna(avg_growth) else 0,
            "max_growth": round(float(max_growth), 1) if pd.notna(max_growth) else 0,
            "anomaly_score": score,
        })
    df_stats = pd.DataFrame(song_stats)
    if df_stats.empty:
        return df_stats
    return df_stats.sort_values("anomaly_score", ascending=False)

def analyze_recent_anomaly(df_all, days=30):
    """近30日异常活跃分析：环比增长 + 近期斜率 + 单日暴涨 + 新歌加成"""
    max_date = df_all["data_date"].max()
    r_start = max_date - pd.Timedelta(days=days)
    p_start = max_date - pd.Timedelta(days=days * 2)
    recent = df_all[df_all["data_date"] >= r_start]
    prior = df_all[(df_all["data_date"] >= p_start) & (df_all["data_date"] < r_start)]
    prior_mean = prior.groupby("uid")["current_index"].mean()
    first_date = df_all.groupby("uid")["data_date"].min()

    rows = []
    for uid, g in recent.groupby("uid"):
        g = g.sort_values("data_date")
        idx = g["current_index"].dropna()
        if len(idx) < 3:
            continue
        r_mean = idx.mean()
        p_mean = prior_mean.get(uid, np.nan)
        growth = ((r_mean - p_mean) / p_mean * 100) if pd.notna(p_mean) and p_mean > 0 else np.nan
        slope = _slope(idx.tail(7))
        chg = (idx.pct_change() * 100).replace([np.inf, -np.inf], np.nan).dropna()
        max_up = float(chg.max()) if len(chg) > 0 else 0.0
        is_new = first_date.get(uid, max_date) >= r_start

        score = 0
        if pd.notna(growth):
            if growth > 50: score += 40
            elif growth > 20: score += 25
            elif growth > 5: score += 10
        if slope > 1: score += 20
        elif slope > 0.3: score += 10
        if max_up > 30: score += 15
        if r_mean > 1000: score += 15
        elif r_mean > 500: score += 8
        if is_new: score += 10
        tag = "飙升" if (pd.notna(growth) and growth > 20) or is_new else ("上涨" if slope > 0.3 else "活跃")
        rows.append({
            "uid": uid, "song_name": g.iloc[-1]["display_name"],
            "trend": round(float(growth), 1) if pd.notna(growth) else 0.0,
            "anomaly_score": int(score), "tag": tag,
        })
    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return df_out
    return df_out.sort_values("anomaly_score", ascending=False)

def _slope(series):
    s = series.dropna()
    if len(s) < 3:
        return 0.0
    return float(np.polyfit(range(len(s)), s.values, 1)[0])

def _max_streak(series):
    s = series.dropna().astype(float)
    if len(s) < 2:
        return 0
    best = cur = 0
    vals = s.values
    for i in range(1, len(vals)):
        if vals[i] > vals[i - 1]:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best

def compute_dimensions(df_all, window_days=90):
    """维度指标（默认近90日窗口）：趋势斜率/波动率/上涨天数占比/最长连涨/生命周期/综合得分/周末工作日"""
    if window_days:
        cutoff = df_all["data_date"].max() - pd.Timedelta(days=window_days)
        df_all = df_all[df_all["data_date"] >= cutoff]
    rows = []
    for uid, g in df_all.groupby("uid"):
        g = g.sort_values("data_date")
        idx = g["current_index"].dropna()
        if len(idx) < 5:
            continue
        mean_v = idx.mean()
        median_v = idx.median()  # 中位数（抗单日异常，比均值稳健）
        vol = float(idx.std() / mean_v * 100) if mean_v > 0 else 0.0
        chg = idx.pct_change() * 100
        chg = chg.replace([np.inf, -np.inf], np.nan).dropna()
        up_ratio = float((chg > 0).sum() / len(chg) * 100) if len(chg) > 0 else 0.0
        slope30 = _slope(idx.tail(30))
        slope7 = _slope(idx.tail(7))
        streak = _max_streak(idx)
        lifecycle = "上升期" if slope7 > 0.5 else ("经典沉淀期" if slope7 < -0.5 else "稳定期")
        weekend = g[g["data_date"].dt.dayofweek >= 5]["current_index"].mean()
        workday = g[g["data_date"].dt.dayofweek < 5]["current_index"].mean()
        rows.append({
            "uid": uid, "song_name": g.iloc[-1]["display_name"],
            "mean_index": round(float(mean_v), 0),
            "median_index": round(float(median_v), 0),
            "latest_index": round(float(idx.iloc[-1]), 0),
            "volatility": round(vol, 1),
            "up_ratio": round(up_ratio, 1),
            "slope30": round(slope30, 2),
            "max_streak": int(streak),
            "lifecycle": lifecycle,
            "weekend_avg": round(float(weekend), 0) if pd.notna(weekend) else 0,
            "workday_avg": round(float(workday), 0) if pd.notna(workday) else 0,
        })
    dims = pd.DataFrame(rows)
    if dims.empty:
        return dims
    # 综合得分 v3：中位数体量(0~55) + 相对趋势(±15) + 上涨占比(0~12) + 连涨(0~8) − 波动罚(0~10)
    # 说明：①体量用「中位数」而非均值，抗单日异常；②趋势用「相对斜率」(slope30÷中位数×100，日均变化率%)
    #   使其跨量级可比，避免绝对斜率天然偏向高体量歌；③趋势分以 |相对斜率| 最大值为锚缩放并封顶 ±15，
    #   避免低体量新歌（如仅 1~2 个数据点的歌）仅凭短期上升就拿高分——体量仍是主导项。
    s = dims
    max_med = max(s["median_index"].max(), 1)
    rel_slope = s["slope30"] / s["median_index"].clip(lower=1) * 100
    max_abs_rs = float(abs(rel_slope).max()) if len(rel_slope) else 0
    momentum = (rel_slope / max_abs_rs * 15).clip(-15, 15) if max_abs_rs > 0 else 0.0
    dims["score"] = (
        s["median_index"] / max_med * 55 +
        momentum +
        s["up_ratio"] / 100 * 12 +
        s["max_streak"] / max(s["max_streak"].max(), 1) * 8 -
        s["volatility"] / max(s["volatility"].max(), 1) * 10
    ).round(1)
    return dims.sort_values("score", ascending=False).reset_index(drop=True)

# ============================================================
# 高级分析维度（指令4）：生命周期迁移 / 衰减曲线 / 周末溢价 / 第二春 / 排名跃迁
# ============================================================
def compute_lifecycle_migration(df_all, window=30):
    """歌曲生命周期月度迁移（桑基图）：上月→本月 上升期/稳定期/经典沉淀期 流动数量"""
    if df_all is None or df_all.empty:
        return {"nodes": [], "links": []}
    d_max = df_all["data_date"].max()
    cur_lo = d_max - pd.Timedelta(days=window)
    prev_lo = d_max - pd.Timedelta(days=2 * window)
    cur = df_all[df_all["data_date"] > cur_lo]
    prev = df_all[(df_all["data_date"] > prev_lo) & (df_all["data_date"] <= cur_lo)]

    def tag_frame(sub):
        tags = {}
        for uid, g in sub.groupby("uid"):
            g = g.sort_values("data_date")
            idx = g["current_index"].dropna()
            if len(idx) < 5:
                continue
            sl = _slope(idx.tail(7))
            tags[uid] = "上升期" if sl > 0.5 else ("经典沉淀期" if sl < -0.5 else "稳定期")
        return tags

    t_cur, t_prev = tag_frame(cur), tag_frame(prev)
    states = ["上升期", "稳定期", "经典沉淀期"]
    links = []
    for k in states:
        for v in states:
            n = sum(1 for u in t_prev if t_prev.get(u) == k and t_cur.get(u) == v)
            if n > 0:
                links.append({"source": f"上月·{k}", "target": f"本月·{v}", "value": n})
    cur_count = {s: sum(1 for u in t_cur.values() if u == s) for s in states}
    nodes = [{"name": f"上月·{k}"} for k in states] + [{"name": f"本月·{k}", "value": cur_count[k]} for k in states]
    return {"nodes": nodes, "links": links}


def compute_release_decay(df_all, song_info, max_days=90):
    """新歌发行后衰减曲线族：发行日起收听归一化（发行日=100%），按属性分组平均 + 半衰期天数"""
    meta = (song_info or {}).get("name2meta", {})
    if not meta:
        return {"labels": [], "series": {}, "halflife": {}}
    norm2uids = {}
    for u, disp in df_all.groupby("uid")["display_name"].last().items():
        norm2uids.setdefault(norm_name(disp), []).append(u)
    curves = {}
    for nm, info in meta.items():
        rel = pd.to_datetime(info["date"], errors="coerce")
        uids = norm2uids.get(nm)
        if not uids or pd.isna(rel):
            continue
        sub = df_all[(df_all["uid"].isin(uids)) & (df_all["data_date"] >= rel)].sort_values("data_date")
        base = None
        curve = {}
        for _, r in sub.iterrows():
            lv = r["listeners"]
            if pd.isna(lv):
                continue
            days = (r["data_date"] - rel).days
            if days < 1 or days > max_days:
                continue
            if base is None and lv > 0:
                base = float(lv)
            if base and base > 0:
                curve[days] = float(lv) / base * 100
        if len(curve) >= 3:
            attr = info.get("attr", "专辑")
            curves.setdefault(attr, {})[nm] = curve
    labels = list(range(1, max_days + 1))
    series, halflife = {}, {}
    for attr, umap in curves.items():
        avg = []
        for d in labels:
            vals = [c[d] for c in umap.values() if d in c]
            avg.append(round(float(np.mean(vals)), 1) if vals else None)
        hl = next((d for d in labels if avg[d - 1] is not None and avg[d - 1] <= 50), None)
        series[attr] = avg
        halflife[attr] = hl
    return {"labels": labels, "series": series, "halflife": halflife}


def compute_weekend_premium(df_all, song_info=None, max_months=6):
    """周末溢价热力矩阵：按属性分组（专辑 vs OST/单曲）并排对比
    每首歌 周末均值/工作日均值 比率；X=月份（最近 max_months），Y=各自 Top12 歌曲。
    输出：{album, ost, months, album_songs, ost_songs, attr_premium}"""
    if df_all is None or df_all.empty:
        return {"album": [], "ost": [], "months": [], "album_songs": [], "ost_songs": [], "attr_premium": []}
    df = df_all.copy()
    df["ym"] = df["data_date"].dt.to_period("M")
    df["is_weekend"] = df["data_date"].dt.dayofweek >= 5

    meta = {}
    if isinstance(song_info, dict):
        meta = song_info.get("name2meta", {}) or {}
    uid2attr = {}
    for u, disp in df.groupby("uid")["display_name"].last().items():
        m = meta.get(norm_name(disp), {})
        uid2attr[u] = m.get("attr", "其他追踪") if m else "其他追踪"

    df["attr"] = df["uid"].map(uid2attr)
    df["attr"] = df["attr"].apply(lambda a: a if a in ("专辑", "OST/单曲") else "其他")

    # 最近 max_months 个月（原实现取全部月份会导致 X 轴 40+ 标签挤压）
    months = sorted(df["ym"].dropna().unique(), key=lambda x: x.start_time)[-max_months:]
    month_labels = [str(m) for m in months]

    def build_matrix(attr_name, top_n=12):
        sub = df[(df["attr"] == attr_name) & (df["ym"].isin(months))]
        if sub.empty:
            return [], []
        # 选歌逻辑：按"近窗口内有效月份数"优先（而非总数据点数）。
        # 原因：QQ音乐指数仅对近期活跃歌曲返回数据，按数据点计数会选出
        # 大量"仅在个别月份零散冒泡"的歌，导致热力矩阵大片空白。
        # 这里先逐曲统计其在 months 内能满足样本门槛(周末≥2/工作日≥3)的月份数，
        # 有效月份越多越靠前，且只保留至少 1 个有效月份的歌曲。
        scored = []
        for u, g in sub.groupby("uid"):
            valid_months = 0
            row = []
            for m in months:
                mm = g[g["ym"] == m]
                wk = mm[mm["is_weekend"]]["current_index"].dropna()
                wd = mm[~mm["is_weekend"]]["current_index"].dropna()
                if len(wk) >= 2 and len(wd) >= 3 and wd.mean() > 0:
                    valid_months += 1
                    row.append(round(float(wk.mean() / wd.mean()), 2))
                else:
                    row.append(None)
            if valid_months >= 1:
                disp = g["display_name"].dropna()
                name = str(disp.iloc[-1]) if len(disp) > 0 else str(u)
                scored.append((valid_months, row, name))
        # 有效月份多者优先；同月份数时按最近月份是否有值微调（稳定排序即可）
        scored.sort(key=lambda x: (x[0], x[1][-1] if x[1][-1] is not None else -1), reverse=True)
        scored = scored[:top_n]
        matrix = [s[1] for s in scored]
        names = [s[2] for s in scored]
        return matrix, names

    album_mat, album_names = build_matrix("专辑")
    ost_mat, ost_names = build_matrix("OST/单曲")

    # 按属性平均溢价率（全部 uid，预分组避免全表扫描）
    attr_premium = []
    prem = {}
    uid_groups = {u: g for u, g in df.groupby("uid")}
    for u, g in uid_groups.items():
        a = uid2attr.get(u, "其他追踪")
        wk = g[g["is_weekend"]]["current_index"].dropna()
        wd = g[~g["is_weekend"]]["current_index"].dropna()
        if len(wk) >= 2 and len(wd) >= 3 and wd.mean() > 0:
            prem.setdefault(a, []).append(float(wk.mean() / wd.mean()))
    attr_premium = [{"attr": a, "ratio": round(float(np.mean(v)), 2)} for a, v in prem.items()]
    attr_premium.sort(key=lambda x: x["ratio"], reverse=True)

    return {
        "album": album_mat, "ost": ost_mat,
        "months": month_labels,
        "album_songs": album_names, "ost_songs": ost_names,
        "attr_premium": attr_premium,
    }


def compute_second_spring(df_all, days=30, song_info=None):
    """老歌复活雷达：发行>180天的老歌，近期30日均值 vs 近90日基线均值偏离度（100%=基线），显著回升标记「第二春」"""
    meta = (song_info or {}).get("name2meta", {})
    if not meta:
        return {"names": [], "values": [], "spring": [], "max": 100}
    norm2uids = {}
    for u, disp in df_all.groupby("uid")["display_name"].last().items():
        norm2uids.setdefault(norm_name(disp), []).append(u)
    uid2disp = df_all.groupby("uid")["display_name"].last().to_dict()
    d_max = df_all["data_date"].max()
    recent_lo = d_max - pd.Timedelta(days=days)
    base_lo = d_max - pd.Timedelta(days=90)
    rows = []
    for nm, info in meta.items():
        rel = pd.to_datetime(info["date"], errors="coerce")
        uids = norm2uids.get(nm)
        if not uids or pd.isna(rel):
            continue
        if (d_max - rel).days < 180:
            continue
        sub = df_all[df_all["uid"].isin(uids)]
        recent = sub[sub["data_date"] > recent_lo]["listeners"].dropna()
        baseline = sub[(sub["data_date"] <= recent_lo) & (sub["data_date"] > base_lo)]["listeners"].dropna()
        if len(recent) < 3 or len(baseline) < 5:
            continue
        br = float(baseline.mean())
        if br <= 0:
            continue
        dev = float(recent.mean()) / br * 100
        if dev > 110:  # 近期高于基线10%以上（回升中）即入选；>150 标记「第二春」（巡演/综艺带动复活）
            disp = uid2disp.get(uids[0], nm)
            rows.append({"name": disp, "dev": round(dev, 1), "spring": dev > 150})
    rows.sort(key=lambda x: x["dev"], reverse=True)
    rows = rows[:8]
    return {"names": [r["name"] for r in rows], "values": [r["dev"] for r in rows],
            "spring": [r["spring"] for r in rows], "max": 100}


def compute_rank_waterfall(df_all, top_n=20):
    """排名跃迁瀑布：今日 vs 昨日 全站排名变化量（正=上升），取 |变化量| 最大 TopN"""
    if df_all is None or df_all.empty or "current_rank" not in df_all.columns:
        return {"names": [], "changes": [], "labels": []}
    df = df_all.copy()
    df["rank"] = pd.to_numeric(df["current_rank"], errors="coerce")

    def rank_map(d):
        sub = df[df["data_date"] == d]
        return {u: r for u, r in zip(sub["uid"], sub["rank"]) if pd.notna(r)}

    # 只取最后两个有排名数据的日期（末批可能无排名列）
    dates = sorted(df["data_date"].dropna().unique())
    rank_dates = [d for d in dates if len(rank_map(d)) >= 3]
    if len(rank_dates) < 2:
        return {"names": [], "changes": [], "labels": []}
    d_today, d_yday = rank_dates[-1], rank_dates[-2]

    rt, ry = rank_map(d_today), rank_map(d_yday)
    name_of = df.groupby("uid")["display_name"].last().to_dict()
    changes = []
    for u in set(rt) & set(ry):
        c = ry[u] - rt[u]  # 正=排名数字变小=上升
        if c == 0:
            continue
        changes.append({"name": name_of.get(u, u), "change": int(c)})
    changes.sort(key=lambda x: abs(x["change"]), reverse=True)
    changes = changes[:top_n]
    changes.sort(key=lambda x: x["change"], reverse=True)  # 上升在前
    return {
        "names": [c["name"] for c in changes],
        "changes": [c["change"] for c in changes],
        "labels": ["↑ 上升" if c["change"] > 0 else "↓ 下降" for c in changes],
    }


def compute_timeline_narrative(df_all, song_info, top_n=15, max_months=48):
    """时间轴叙事数据：每月 Top 歌曲竞争格局（份额% + 排名变化位/月 + 生命周期 + 相对峰值%）
    输出 ECharts timeline 月度帧。优化：预构建「月度分组」与「uid 分组」索引，避免逐月全表扫描。
    口径全部为比率/变化量，无绝对指数展示。"""
    if df_all is None or df_all.empty:
        return []
    df = df_all.copy()
    df["year_month"] = df["data_date"].dt.to_period("M")
    months = sorted(df["year_month"].dropna().unique(), key=lambda x: x.start_time)[-max_months:]

    # 关键事件映射（月份 -> 事件），标题栏自动标记
    events = {}
    for e in (song_info or {}).get("tour_events", []):
        dt = pd.to_datetime(e.get("date", ""), errors="coerce")
        if pd.notna(dt):
            events.setdefault(dt.strftime("%Y-%m"), []).append({"type": "tour", "name": e.get("name", e.get("city", ""))})
    for e in (song_info or {}).get("release_events", []):
        dt = pd.to_datetime(e.get("date", ""), errors="coerce")
        if pd.notna(dt):
            events.setdefault(dt.strftime("%Y-%m"), []).append({"type": "release", "name": e.get("name", "")})

    # 预构建索引（一次 groupby，后续 O(1) 取用）
    month_groups = {m: g for m, g in df.groupby("year_month")}
    uid_groups = {u: g.sort_values("data_date") for u, g in df.groupby("uid")}
    name_of = df.groupby("uid")["display_name"].last().to_dict()
    month_means = {}
    month_ranks = {}
    for m, g in month_groups.items():
        month_means[m] = g.groupby("uid")["current_index"].mean().dropna()
        month_ranks[m] = g.groupby("uid")["current_rank"].mean().dropna()

    frames = []
    for i, month in enumerate(months):
        means = month_means.get(month)
        if means is None or means.empty:
            continue
        total = float(means.sum())
        if total <= 0:
            continue
        top = means.sort_values(ascending=False).head(top_n)
        prev_ranks = month_ranks.get(months[i - 1], pd.Series(dtype=float))
        cur_ranks = month_ranks.get(month, pd.Series(dtype=float))

        points = []
        for u, mv in top.items():
            g = uid_groups.get(u)
            if g is None:
                continue
            # 生命周期：截止当月末的近期斜率（复用 _slope）
            recent = g[g["data_date"] <= month.end_time]["current_index"].dropna()
            sl = _slope(recent.tail(7))
            lc = "上升期" if sl > 0.5 else ("经典沉淀期" if sl < -0.5 else "稳定期")
            # 当月份额（index 均值占比）
            share = round(float(mv) / total * 100, 2)
            # 排名变化速度（位/月）：上月均值 - 本月均值，正=上升
            prev_r, cur_r = prev_ranks.get(u, np.nan), cur_ranks.get(u, np.nan)
            delta = round(float(prev_r - cur_r), 1) if pd.notna(prev_r) and pd.notna(cur_r) else 0
            # 相对自身峰值（截至上月末的历史最高指数均值）。封顶 100%：
            # 新歌/低体量歌无历史峰值时会出现 >100%（如 117.4%），气泡虚大误导「一家独大」，故封顶
            hist = g[g["data_date"] < month.start_time]["current_index"]
            hmax = float(hist.max()) if len(hist) > 0 else 0
            peak_ratio = round(min(float(mv) / hmax * 100, 100), 1) if hmax > 0 else 100
            points.append({
                "name": str(name_of.get(u, u)),
                "value": [delta, share, peak_ratio, lc],
                "uid": u,
            })

        mk = str(month)
        evs = events.get(mk, [])
        ev_str = "  ".join(["🎤 " + e["name"] + "站" if e["type"] == "tour" else "🎵 《" + e["name"] + "》发行" for e in evs])
        frames.append({"month": mk, "points": points, "events": evs, "event_str": ev_str})
    return frames


def compute_daily_listen(df_all, total_songs, min_active=5, top_n=20, min_display=10):
    """今日收听态势：活跃歌曲池份额集中度 + 环比趋势（全部为比率/计数，无绝对收听人数）。
    口径：活跃池 = 当日 max(listeners) > 0 的歌曲；份额分母 = 当日活跃池峰值总和。
    数据完整日回退：最新采集日活跃 < min_active（采集未完成，如凌晨批次仅 2 首）时，
    自动回退到最近一个活跃 >= min_active 的日期，并在 as_of 标注实际数据日期，避免份额失真。
    min_display：当日活跃歌曲数低于该阈值时视为"样本过小"，trend 返回空、
    overview.too_small=True，前端隐藏份额列表（避免 8 首这种小样本误导）。
    top_n：份额列表最多列出的歌曲数（默认 20，覆盖当日有指数的多数歌曲）。
    另输出 new_today：昨日无指数而今日出现指数的歌曲（首次活跃/恢复活跃）。"""
    empty = {
        "overview": {"active_count": 0, "total_tracked": int(total_songs),
                     "concentration_top3": None, "as_of": None, "too_small": False},
        "trend": [],
        "new_today": [],
    }
    if df_all is None or df_all.empty or "listeners" not in df_all.columns:
        return empty
    df = df_all.copy()
    df["data_date"] = pd.to_datetime(df["data_date"], errors="coerce")
    df = df.dropna(subset=["data_date"])
    if df.empty:
        return empty
    # 每首歌每日峰值收听
    daily = df.groupby(["uid", "data_date"])["listeners"].max().reset_index()
    dates = sorted(daily["data_date"].unique())

    # 选择数据完整日（最新日活跃不足则回退）
    cur_date = None
    for d in reversed(dates):
        g = daily[daily["data_date"] == d]
        n = int((g["listeners"].notna() & (g["listeners"] > 0)).sum())
        if n >= min_active:
            cur_date = d
            break
    if cur_date is None:
        cur_date = dates[-1]

    t = daily[daily["data_date"] == cur_date].copy()
    active = t[t["listeners"].notna() & (t["listeners"] > 0)].copy()
    if active.empty:
        return empty
    active["peak"] = active["listeners"]

    total_peak = float(active["peak"].sum())
    if total_peak <= 0:
        return empty
    active = active.sort_values("peak", ascending=False)
    top3 = active.head(3)
    concentration = round(float(top3["peak"].sum()) / total_peak * 100, 1)

    # 基准日（自然日前一天）全天峰值
    yesterday = cur_date - pd.Timedelta(days=1)
    y_peak = daily[daily["data_date"] == yesterday].set_index("uid")["listeners"]
    uid2disp = df.groupby("uid")["display_name"].last().to_dict()

    trend = []
    for rank, (_, r) in enumerate(active.head(top_n).iterrows(), 1):
        prev = y_peak.get(r["uid"])
        if prev is not None and pd.notna(prev) and prev > 0:
            trend_pct = round(float((r["peak"] - prev) / prev * 100), 1)
            if abs(trend_pct) <= 5:
                label = "flat"
            elif trend_pct > 0:
                label = "up"
            else:
                label = "down"
        else:
            trend_pct = None
            label = "new"
        trend.append({
            "rank": rank,
            "song": str(uid2disp.get(r["uid"], r["uid"])),
            "share_pct": round(float(r["peak"]) / total_peak * 100, 1),
            "trend_pct": trend_pct,
            "trend_label": label,
        })

    # 昨日无指数、今日出现指数的歌曲（首次活跃/恢复活跃，不限于 TopN）
    new_today = []
    for uid, r in active.sort_values("peak", ascending=False).iterrows():
        prev = y_peak.get(uid)
        if prev is None or pd.isna(prev) or prev <= 0:
            new_today.append({
                "song": str(uid2disp.get(uid, uid)),
                "share_pct": round(float(r["peak"]) / total_peak * 100, 1),
            })
    new_today = new_today[:20]

    too_small = int(len(active)) < min_display
    return {
        "overview": {
            "active_count": int(len(active)),
            "total_tracked": int(total_songs),
            "concentration_top3": concentration,
            "as_of": cur_date.strftime("%Y-%m-%d"),
            "too_small": too_small,
        },
        "trend": [] if too_small else trend,
        "new_today": new_today,
    }


def compute_daily_freshness(df_all, min_active=5, idx_pct_thr=0.30, rank_up_thr=3000, top_n=3):
    """日报层数据新鲜度：新增歌曲数 + 最近7日全站均值 + 今日异动检测。
    异动口径（与全站一致用 current_index / current_rank）：
      - 指数突增：当日指数较前7日均值涨幅 >= +30%
      - 排名飙升：当日排名较昨日上升 >= 3000 位（排名数字变小 = 靠前）
    基准日沿用「数据完整日回退」（最新日活跃 < min_active 视为采集未完成）。
    全部输出为比率/计数/名称，不含绝对收听人数。"""
    empty = {
        "daily_new_records": None,
        "recent_7days": [],
        "latest_anomaly": None,
        "daily_anomalies": [],
    }
    if df_all is None or df_all.empty:
        return empty
    df = df_all.copy()
    df["data_date"] = pd.to_datetime(df["data_date"], errors="coerce")
    df = df.dropna(subset=["data_date"])
    if df.empty:
        return empty
    dates = sorted(df["data_date"].unique())

    # 数据完整日回退（与 compute_daily_listen 同口径）
    cur_date = None
    for d in reversed(dates):
        g = df[df["data_date"] == d]
        n = int((g["listeners"].notna() & (g["listeners"] > 0)).sum()) if "listeners" in g.columns else int(g["uid"].nunique())
        if n >= min_active:
            cur_date = d
            break
    if cur_date is None:
        cur_date = dates[-1]

    # 1) 新增歌曲数：as_of 日有、前一日无的 uid 数
    uid2disp = df.groupby("uid")["display_name"].last().to_dict()
    prev_uids = set(df[df["data_date"] == cur_date - pd.Timedelta(days=1)]["uid"])
    cur_uids = set(df[df["data_date"] == cur_date]["uid"])
    daily_new_records = int(len(cur_uids - prev_uids)) if cur_uids else 0

    # 2) 最近7日（含 as_of）全站平均指数
    recent_7days = []
    for i in range(6, -1, -1):
        d = cur_date - pd.Timedelta(days=i)
        g = df[df["data_date"] == d]
        avg = g["current_index"].mean() if "current_index" in g.columns and not g["current_index"].isna().all() else None
        recent_7days.append({
            "date": d.strftime("%Y-%m-%d"),
            "avg_index": round(float(avg), 1) if pd.notna(avg) else None,
            "total_songs": int(g["uid"].nunique()) if len(g) else 0,
            "complete": int(g["uid"].nunique()) >= min_active,
        })

    # 3) 异动检测（as_of 日）
    cur = df[df["data_date"] == cur_date].copy()
    anomalies = []
    if not cur.empty:
        base = df[(df["data_date"] >= cur_date - pd.Timedelta(days=7)) &
                  (df["data_date"] < cur_date)].groupby("uid")["current_index"].mean()
        y_rank = df[df["data_date"] == cur_date - pd.Timedelta(days=1)].groupby("uid")["current_rank"].max() \
            if "current_rank" in df.columns else None
        for _, r in cur.iterrows():
            u = r["uid"]
            disp = str(uid2disp.get(u, u))
            change_pct = None
            if u in base.index and pd.notna(base[u]) and base[u] > 0 and pd.notna(r.get("current_index")):
                change_pct = (r["current_index"] / base[u] - 1)
            rank_up = None
            if y_rank is not None and u in y_rank.index and pd.notna(y_rank[u]) and pd.notna(r.get("current_rank")):
                rank_up = int(y_rank[u] - r["current_rank"])  # 正 = 上升
            if change_pct is not None and change_pct >= idx_pct_thr:
                anomalies.append({
                    "song": disp, "type": "🔥 指数突增", "metric": "指数",
                    "change_pct": round(float(change_pct), 3),
                    "desc": f"指数较7日均值 +{round(float(change_pct)*100, 1)}%",
                })
            elif rank_up is not None and rank_up >= rank_up_thr:
                anomalies.append({
                    "song": disp, "type": "📈 排名飙升", "metric": "排名",
                    "change_pct": None,
                    "desc": f"排名较昨日上升 {rank_up:,} 位",
                })
        # 显著度排序：指数突增按涨幅、排名飙升按位次
        anomalies.sort(key=lambda a: (a["change_pct"] or 0, 0) if a["type"] == "🔥 指数突增"
                       else (0, int(a["desc"].split("上升 ")[1].replace(",", "").split(" ")[0]))
                       if "排名" in a["desc"] else (0, 0), reverse=True)
        anomalies = anomalies[:top_n]

    return {
        "daily_new_records": daily_new_records,
        "recent_7days": recent_7days,
        "latest_anomaly": anomalies[0] if anomalies else None,
        "daily_anomalies": anomalies,
    }


# ============================================================
# 第二部分C：事件效应量化（巡演带动 / 新歌发行）
# ============================================================
def tour_uplift(df_all, tour_events, topn=10):
    """巡演带动效应：每场巡演后 7 日的全站日均指数 vs 前 21~7 日基线的涨幅%"""
    daily = df_all.groupby("data_date")["current_index"].mean().dropna().sort_index()
    rows = []
    for e in tour_events:
        d = pd.to_datetime(e["date"], errors="coerce")
        if pd.isna(d):
            continue
        pre = daily[(daily.index >= d - pd.Timedelta(days=21)) & (daily.index < d - pd.Timedelta(days=7))]
        post = daily[(daily.index >= d) & (daily.index <= d + pd.Timedelta(days=7))]
        if len(pre) < 3 or len(post) < 2 or pre.mean() <= 0:
            continue
        uplift = (post.mean() / pre.mean() - 1) * 100
        rows.append({"label": f"{e['date'][5:]} {e['name']}", "uplift": round(float(uplift), 1)})
    rows.sort(key=lambda x: x["uplift"], reverse=True)
    return rows[:topn]

def load_setlist(path):
    """读取巡演歌单长表（单一事实源）：场次键(日期+场次名) → {tour, songs(数据层归一名)}。
    长表列：巡次 | 日期 | 场次 | 场次内序号 | 曲目 | 备注 | 数据层归一名 | 来源
    组合曲目（如"女人花+水中花"）拆分为单曲加入匹配集，供歌单内效应匹配。
    文件缺失时返回空 dict（歌曲级效应自动留白，不影响主流程）。
    """
    setlists = {}
    if not path or not os.path.exists(path):
        logger.warning(f"巡演歌单长表不存在（歌曲级效应留白）: {path}")
        return setlists
    try:
        df = pd.read_excel(path, sheet_name="合并长表")
        df = df[df["曲目"].notna() & (df["曲目"].astype(str).str.strip() != "")]
        for date, g in df.groupby("日期"):
            d = str(date)[:10]
            for scene, gg in g.groupby("场次"):
                tour = str(gg["巡次"].iloc[0]).strip()
                songs = set()
                for v in gg["数据层归一名"].fillna(gg["曲目"]):
                    n = norm_name(str(v).strip())
                    if not n or n == "None":
                        continue
                    songs.add(n)
                    if "+" in n:  # 组合曲目拆分（仅用于匹配，不改变展示）
                        for part in n.split("+"):
                            part = part.strip()
                            if len(part) >= 2:
                                songs.add(part)
                setlists[(d, str(scene).strip())] = {"tour": tour, "songs": songs}
        logger.info(f"巡演歌单长表: {len(setlists)} 场次已加载（歌曲级效应输入）")
    except Exception as e:
        logger.warning(f"巡演歌单长表读取失败（歌曲级效应留白）: {e}")
    return setlists


def load_performance_events(path):
    """读取演出活动表（音乐剧/综艺等非巡演演出），输出与 load_setlist 同构的 dict：
    (日期, 场次名) → {tour, songs(数据层归一名集合)}，复用 tour_song_effects 做辐射带动分析。

    演出活动表列：序号 | 演出名称 | 时间 | 地点 | 备注 | 演唱曲目
    与巡演长表区别：单一曲目演出（如音乐剧王晰仅唱《埋下记忆》），歌单内仅 1 首，
    其余全部歌曲为"歌单外"，故辐射带动（radiance_uplift）能反映"该演出是否带动王晰整体关注度"。
    文件缺失时返回空 dict（不影响主流程）。
    """
    events = {}
    if not path or not os.path.exists(path):
        logger.info(f"演出活动表不存在（辐射带动分析不含音乐剧演出）: {path}")
        return events
    try:
        df = pd.read_excel(path, sheet_name=0)
        for _, row in df.iterrows():
            name = str(row.get("演出名称", "") or "").strip()
            date = row.get("时间", None)
            city = str(row.get("地点", "") or "").strip()
            song = str(row.get("演唱曲目", "") or "").strip()
            if not name or pd.isna(date) or not song:
                continue
            d = pd.to_datetime(date).strftime("%Y-%m-%d")
            # 场次键用"演出名·城市"避免与巡演长表的 (日期, 城市) 键冲突
            scene = f"{name}·{city}" if city else name
            nsong = norm_name(song)
            songs = {nsong}
            # 组合曲目拆分（仅用于匹配）
            if "+" in nsong:
                songs.update(p.strip() for p in nsong.split("+") if len(p.strip()) >= 2)
            events[(d, scene)] = {"tour": name, "songs": songs}
        logger.info(f"演出活动表: {len(events)} 场演出已加载（辐射带动分析输入）")
    except Exception as e:
        logger.warning(f"演出活动表读取失败（辐射带动分析跳过演出活动）: {e}")
    return events


def _city_of(scene):
    """从演出活动场次名（'演出名·城市'）中提取城市部分，供节点展示去重。"""
    if not scene:
        return ""
    return scene.split("·")[-1].strip() if "·" in scene else scene


def tour_song_effects(df_all, setlists, topn=5):
    """场次后歌曲级效应（以长表为唯一输入）：
    - 直接效应：该场歌单内歌曲 演出后7日 日均指数 vs 前21~7日基线 的涨幅
    - 辐射带动：歌单外歌曲同期涨幅——巡演让路人关注王晰，去平台收听非巡演歌曲，同样算积极影响
    - 无数据不输出：仅统计数据层真实追踪到、且前后窗口均有有效数据的歌曲
    返回按日期升序的场次效应列表。
    """
    if not setlists or df_all is None or df_all.empty:
        return []
    d_min, d_max = df_all["data_date"].min(), df_all["data_date"].max()
    # 每首歌的时序（uid → (归一名, 时间序列)）
    series = {}
    for uid, g in df_all.groupby("uid"):
        s = g.set_index("data_date")["current_index"].sort_index().dropna()
        if len(s) < 5:
            continue
        name = str(g["display_name"].iloc[-1]).strip()
        if not name or name == "nan":
            continue
        series[uid] = (name, norm_name(name), s)  # (原始显示名, 数据层归一名, 时序)
    if not series:
        return []
    rows = []
    for (date, scene), info in setlists.items():
        d = pd.to_datetime(date, errors="coerce")
        if pd.isna(d) or d < d_min or d > d_max:
            continue
        pre_lo, pre_hi = d - pd.Timedelta(days=21), d - pd.Timedelta(days=7)
        post_lo, post_hi = d, d + pd.Timedelta(days=7)
        on_norms = set(info["songs"])
        effects = []  # (显示名, uplift, on_setlist)
        total_pre, total_post = [], []
        for disp, nrm, s in series.values():
            pre = s[(s.index >= pre_lo) & (s.index < pre_hi)]
            post = s[(s.index >= post_lo) & (s.index <= post_hi)]
            if len(pre) < 3 or len(post) < 2 or pre.mean() <= 0:
                continue
            up = (post.mean() / pre.mean() - 1) * 100
            effects.append((disp, float(up), nrm in on_norms))
            total_pre.append(pre.mean())
            total_post.append(post.mean())
        if not effects:
            continue
        total_uplift = ((sum(total_post) / len(total_post)) / (sum(total_pre) / len(total_pre)) - 1) * 100
        on_list = [e for e in effects if e[2]]
        off_list = [e for e in effects if not e[2]]
        setlist_uplift = (sum(e[1] for e in on_list) / len(on_list)) if on_list else None
        radiance_uplift = (sum(e[1] for e in off_list) / len(off_list)) if off_list else None
        candidates = sorted(effects, key=lambda e: e[1], reverse=True)[:topn]
        rows.append({
            "date": date,
            "scene": scene,
            "city": re.split(r"[（(]", scene)[0].strip(),
            "tour": info["tour"],
            "total_uplift": round(float(total_uplift), 1),
            "setlist_uplift": round(float(setlist_uplift), 1) if setlist_uplift is not None else None,
            "radiance_uplift": round(float(radiance_uplift), 1) if radiance_uplift is not None else None,
            "top_songs": [{"name": n, "uplift": round(u, 1), "on_setlist": o} for n, u, o in candidates],
            # 全量歌曲涨幅（不限 top5）：供 live 页「完整歌单」逐曲标注场后涨幅
            "songs": [{"name": n, "uplift": round(u, 1), "on_setlist": o} for n, u, o in effects],
        })
    rows.sort(key=lambda r: r["date"])
    return rows

def release_performance(df_all, release_events, topn=10):
    """新歌发行后 14 日表现：该曲发行起 14 日内的平均指数与峰值（仅统计已有数据的发行）"""
    norm2uids = {}
    for u, disp in df_all.groupby("uid")["display_name"].last().items():
        norm2uids.setdefault(norm_name(disp), []).append(u)
    d_min, d_max = df_all["data_date"].min(), df_all["data_date"].max()
    rows = []
    for e in release_events:
        d = pd.to_datetime(e["date"], errors="coerce")
        if pd.isna(d) or d < d_min or d > d_max:
            continue
        uids = norm2uids.get(norm_name(e["name"]))
        if not uids:
            continue
        sub = df_all[(df_all["uid"].isin(uids)) &
                     (df_all["data_date"] >= d) & (df_all["data_date"] <= d + pd.Timedelta(days=14))]
        idx = sub["current_index"].dropna()
        if len(idx) < 3:
            continue
        rows.append({"label": f"《{e['name']}》{e['date'][5:]}", "avg": round(float(idx.mean()), 0),
                     "peak": round(float(idx.max()), 0)})
    rows.sort(key=lambda x: x["avg"], reverse=True)
    return rows[:topn]

# ============================================================
# 第二部分D：歌曲信息汇总表（3 个工作表，可选接入）
# ============================================================
def load_song_info(path):
    """读取 王晰歌曲信息汇总.xlsx：OST&单曲 / 专辑 / 巡演重要时间节点"""
    info = {"release_events": [], "tour_events": [], "attr_rows": [], "name2meta": {}}
    if not path or not os.path.exists(path):
        logger.warning(f"歌曲信息表不存在（跳过维度增强）: {path}")
        return info
    try:
        xl = pd.ExcelFile(path)
        # --- OST&单曲 ---
        if "OST&单曲" in xl.sheet_names:
            d = pd.read_excel(xl, sheet_name="OST&单曲")
            for _, r in d.iterrows():
                name = str(r.get("歌名", "")).strip()
                dt = pd.to_datetime(r.get("发行时间"), errors="coerce")
                desc = str(r.get("内容", "")).strip()
                if not name or name == "nan" or pd.isna(dt):
                    continue
                info["release_events"].append({"date": dt.strftime("%Y-%m-%d"), "name": name, "desc": desc, "kind": "OST/单曲"})
                info["attr_rows"].append({"name": name, "attr": "OST/单曲", "date": dt.strftime("%Y-%m-%d"), "desc": desc})
                info["name2meta"][norm_name(name)] = {"date": dt.strftime("%Y-%m-%d"), "attr": "OST/单曲"}
        # --- 专辑 ---
        if "专辑" in xl.sheet_names:
            d = pd.read_excel(xl, sheet_name="专辑")
            for _, r in d.iterrows():
                name = str(r.get("歌曲名称", "")).strip()
                dt = pd.to_datetime(r.get("发行日期"), errors="coerce")
                attr = str(r.get("属性", "专辑")).strip() or "专辑"
                if not name or name == "nan" or pd.isna(dt):
                    continue
                info["release_events"].append({"date": dt.strftime("%Y-%m-%d"), "name": name, "desc": attr, "kind": "专辑"})
                info["attr_rows"].append({"name": name, "attr": attr, "date": dt.strftime("%Y-%m-%d"), "desc": attr})
                info["name2meta"][norm_name(name)] = {"date": dt.strftime("%Y-%m-%d"), "attr": attr}
        # --- 巡演重要时间节点 ---
        if "巡演重要时间节点" in xl.sheet_names:
            d = pd.read_excel(xl, sheet_name="巡演重要时间节点")
            for _, r in d.iterrows():
                raw_t = r.get("时间")
                if pd.isna(raw_t):
                    continue
                if isinstance(raw_t, (int, float)):  # Excel 序列日期
                    dt = pd.to_datetime("1899-12-30") + pd.to_timedelta(float(raw_t), unit="D")
                else:
                    dt = pd.to_datetime(raw_t, errors="coerce")
                if pd.isna(dt):
                    continue
                tour = str(r.get("巡次", "")).strip()
                city = str(r.get("场次", "")).strip()
                info["tour_events"].append({"date": dt.strftime("%Y-%m-%d"), "name": city, "desc": tour, "kind": "巡演"})
        logger.info(f"歌曲信息表: 发行事件 {len(info['release_events'])} 条, 巡演节点 {len(info['tour_events'])} 条, 属性条目 {len(info['attr_rows'])} 条")
    except Exception as e:
        logger.warning(f"歌曲信息表读取失败（跳过）: {e}")
    return info

# ============================================================
# 第三部分：大屏看板生成（v3 维度增强版）
# ============================================================
CDN_LOADER = """<script>
(function(){
  var cdns=[
    "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js",
    "https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js",
    "https://unpkg.com/echarts@5.4.3/dist/echarts.min.js"
  ];
  var i=0;
  function loadNext(){
    if(i>=cdns.length){document.dispatchEvent(new Event("echarts-fail"));return;}
    var s=document.createElement("script");
    s.src=cdns[i++];
    s.onload=function(){document.dispatchEvent(new Event("echarts-ready"));};
    s.onerror=loadNext;
    document.head.appendChild(s);
  }
  loadNext();
})();
</script>"""

def build_echarts_tag():
    """ECharts 加载策略：CDN 优先（jsdelivr→npmmirror→unpkg）+ 本地 fallback。
    本地 echarts.min.js 复制到 dashboard 目录供回退使用（不内联进 HTML，控制体积）；
    网络可用时走 CDN 加速，断网/CDN 失效时回退同目录本地文件，保证离线可看。"""
    local_lib = None
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "echarts.min.js"),
        os.path.join(DASHBOARD_DIR, "echarts.min.js"),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 100000:
            local_lib = p
            break
    if local_lib:
        try:
            dst = os.path.join(DASHBOARD_DIR, "echarts.min.js")
            if os.path.abspath(local_lib) != os.path.abspath(dst):
                shutil.copy2(local_lib, dst)
            logger.info(f"本地图表库就绪（fallback）: {dst}")
        except Exception as e:
            logger.warning(f"复制本地图表库失败: {e}")
        return """<script>
(function(){
  var cdns=[
    "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js",
    "https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js",
    "https://unpkg.com/echarts@5.4.3/dist/echarts.min.js",
    "./echarts.min.js"
  ];
  var i=0;
  function loadNext(){
    if(i>=cdns.length){document.dispatchEvent(new Event("echarts-fail"));return;}
    var s=document.createElement("script");
    s.src=cdns[i++];
    s.onload=function(){document.dispatchEvent(new Event("echarts-ready"));};
    s.onerror=loadNext;
    document.head.appendChild(s);
  }
  loadNext();
})();
</script>"""
    return CDN_LOADER

def calc_next_run():
    now = datetime.now()
    for t_str, mode in SCHEDULE:
        t = datetime.strptime(t_str, "%H:%M").time()
        if datetime.combine(now.date(), t) > now:
            return t_str + (" 全量" if mode == "full" else " 极速")
    return SCHEDULE[0][0] + "（明日）"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>__PAGE_TITLE__</title>
__META_TAGS__
__JSON_LD__
__ECHARTS_TAG__
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei','PingFang SC',sans-serif;background:radial-gradient(ellipse at center,#0f1535 0%,#080c24 100%),radial-gradient(circle at 18% 28%,rgba(0,210,255,0.07) 0,transparent 32%),radial-gradient(circle at 82% 72%,rgba(0,255,157,0.05) 0,transparent 32%);color:#fff;overflow-x:hidden;min-height:100vh;}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background-image:radial-gradient(rgba(0,210,255,0.10) 1px,transparent 1px);background-size:26px 26px;opacity:.16;animation:floatGrid 20s linear infinite;}
@keyframes floatGrid{0%{background-position:0 0}100%{background-position:26px 26px}}
.container{width:100%;padding:20px;max-width:1920px;margin:0 auto;position:relative;z-index:1}
.header{text-align:center;padding:25px 0;position:relative;border-bottom:1px solid rgba(0,210,255,0.15);margin-bottom:25px;}
.header h1{font-size:38px;font-weight:700;letter-spacing:6px;background:linear-gradient(90deg,#00d2ff,#3a7bd5,#00d2ff);background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shine 3s linear infinite;}
@keyframes shine{to{background-position:200% center}}
.header .subtitle{color:#5a6b8c;font-size:14px;margin-top:8px;letter-spacing:2px}
.header .time{color:#00d2ff;font-size:20px;margin-top:12px;font-family:'Courier New',monospace;letter-spacing:2px;}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin:25px 0}
.kpi-card{background:rgba(0,210,255,0.06);border:1px solid rgba(0,210,255,0.12);border-radius:14px;padding:28px 22px;position:relative;overflow:hidden;transition:all .4s;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);box-shadow:0 8px 32px rgba(0,0,0,0.25);}
.kpi-card:hover{border-color:rgba(0,210,255,0.35);box-shadow:0 0 30px rgba(0,210,255,0.08);transform:translateY(-3px);}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#00d2ff,transparent);opacity:.6;}
.kpi-label{color:#5a6b8c;font-size:13px;margin-bottom:10px;letter-spacing:1px}
.kpi-value{font-size:44px;font-weight:700;color:#00d2ff;font-family:'DIN Alternate','Arial Black',sans-serif;letter-spacing:1px;text-shadow:0 0 20px rgba(0,210,255,0.2);}
.kpi-value.up{color:#00ff9d;text-shadow:0 0 20px rgba(0,255,157,0.2)}
.kpi-trend{font-size:13px;margin-top:10px;display:flex;align-items:center;gap:6px}
.trend-up{color:#00ff9d}.trend-flat{color:#ffd700}
.chart-row{display:grid;grid-template-columns:1fr;gap:20px;margin:25px 0}
.chart-box{background:rgba(0,210,255,0.02);border:1px solid rgba(0,210,255,0.08);border-radius:14px;padding:22px;position:relative;overflow:hidden;box-shadow:0 6px 28px rgba(0,0,0,0.22);}
.chart-box::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:linear-gradient(180deg,#00d2ff,transparent);opacity:.5;}
.chart-title{font-size:15px;color:#00d2ff;margin-bottom:18px;padding-left:14px;border-left:3px solid #00d2ff;font-weight:600;letter-spacing:1px;}
.chart-container{width:100%;height:300px}
.chart-container.tall{height:360px}
/* 巡演歌曲级效应面板 */
.tse-scene{background:rgba(0,210,255,0.03);border:1px solid rgba(0,210,255,0.12);border-radius:10px;margin:10px 0;padding:0;}
.tse-scene summary{cursor:pointer;padding:12px 16px;display:flex;align-items:center;flex-wrap:wrap;gap:8px 16px;list-style:none;font-size:13px;}
.tse-scene summary::-webkit-details-marker{display:none}
.tse-scene summary::before{content:'▸';color:#00d2ff;font-size:11px;transition:transform .2s;margin-right:2px}
.tse-scene[open] summary::before{transform:rotate(90deg)}
.tse-scene[open]{border-color:rgba(0,210,255,0.3)}
.tse-date{color:#00d2ff;font-weight:600;min-width:92px}
.tse-city{color:#fff;font-weight:600}
.tse-m{color:#8896b3;font-size:12px}
.tse-m b{font-size:13px;margin-left:2px}
.tse-up{color:#00ff9d}.tse-down{color:#ff5e62}.tse-flat{color:#ffd700}
.tse-body{padding:12px 16px 16px;border-top:1px solid rgba(0,210,255,0.1)}
.tse-tops{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:12px;font-size:12px;color:#5a6b8c}
.tse-chip{font-size:11px;padding:3px 10px;border-radius:20px;background:rgba(0,210,255,0.08);border:1px solid rgba(0,210,255,0.15);color:#8896b3;white-space:nowrap}
.tse-chip.on{border-color:rgba(0,255,157,0.35);color:#00ff9d}
.tse-table{width:100%;border-collapse:collapse;font-size:12px}
.tse-table th{color:#00d2ff;padding:6px 8px;text-align:left;border-bottom:1px solid rgba(0,210,255,0.2);font-weight:600}
.tse-table td{padding:5px 8px;color:#8896b3;border-bottom:1px solid rgba(255,255,255,0.04)}
.tse-table td.name{color:#fff}
.tse-tag{font-size:10px;padding:1px 8px;border-radius:4px;background:rgba(0,210,255,0.12);color:#00d2ff;white-space:nowrap}
.tse-tag-on{font-size:10px;padding:1px 8px;border-radius:4px;background:rgba(0,255,157,0.15);color:#00ff9d;white-space:nowrap}
/* 双向链接：城市名可点击跳转 live 详情页（hover 显示 ↗）；深链定位高亮 */
.tse-link{color:#00d2ff;text-decoration:none;border-bottom:1px dashed rgba(0,210,255,0.55);cursor:pointer;transition:color .15s,border-color .15s}
.tse-link:hover{color:#7fe9ff;border-bottom-style:solid;text-shadow:0 0 10px rgba(0,210,255,0.35)}
.tse-link::after{content:'↗';margin-left:3px;font-size:11px;opacity:0;transition:opacity .15s}
.tse-link:hover::after{opacity:1}
.tse-scene.tse-flash{border-color:#00d2ff;box-shadow:0 0 0 2px rgba(0,210,255,0.28),0 6px 28px rgba(0,0,0,0.3)}
.bottom-row{display:grid;grid-template-columns:1.1fr 1.4fr 1fr;gap:20px;margin:25px 0}
.dim-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin:25px 0}
.status-panel{padding:20px;max-height:340px;overflow-y:auto}
.status-item{display:flex;align-items:center;justify-content:space-between;padding:11px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:13px;color:#8896b3;}
.status-item:last-child{border-bottom:none}
.status-value{color:#00d2ff;font-weight:600}
.status-dot{width:8px;height:8px;border-radius:50%;background:#00ff9d;box-shadow:0 0 12px #00ff9d;animation:pulse 2s infinite;display:inline-block;margin-right:8px;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.anomaly-card{background:rgba(255,94,98,0.04);border:1px solid rgba(255,94,98,0.15);border-radius:10px;padding:12px 16px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;}
.anomaly-card .tag{font-size:11px;padding:3px 10px;border-radius:20px;background:rgba(255,94,98,0.15);color:#ff5e62;white-space:nowrap;margin-left:10px;}
.anomaly-card .tag.hot{background:rgba(0,255,157,0.15);color:#00ff9d}
.anomaly-card .tag.up{background:rgba(0,210,255,0.15);color:#00d2ff}
.anomaly-name{font-size:14px;color:#fff;font-weight:600}
.anomaly-meta{font-size:12px;color:#5a6b8c;margin-top:3px}
.rank-table{width:100%;border-collapse:collapse;font-size:12px}
.rank-table th{color:#00d2ff;padding:8px 6px;text-align:left;border-bottom:1px solid rgba(0,210,255,0.2);font-weight:600;white-space:nowrap}
.rank-table td{padding:7px 6px;color:#8896b3;border-bottom:1px solid rgba(255,255,255,0.04);white-space:nowrap}
.rank-table td.name{color:#fff;font-weight:600;max-width:130px;overflow:hidden;text-overflow:ellipsis}
.rank-table tr:hover td{background:rgba(0,210,255,0.04)}
.lc-up{color:#00ff9d}.lc-down{color:#ff5e62}.lc-flat{color:#ffd700}
.rank-tabs{display:flex;gap:8px;margin-bottom:10px}
.rank-tabs button,.mini-toggle button{background:rgba(0,210,255,0.06);border:1px solid rgba(0,210,255,0.2);color:#8896b3;padding:5px 14px;border-radius:16px;font-size:12px;cursor:pointer;transition:all .25s}
.rank-tabs button.active,.mini-toggle button.active{background:rgba(0,210,255,0.18);color:#00d2ff;border-color:#00d2ff}
.mini-toggle{display:flex;gap:8px;margin:-6px 0 10px 0}
.detail-bar{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.detail-bar select{background:#0f1535;border:1px solid rgba(0,210,255,0.3);color:#fff;padding:8px 12px;border-radius:8px;font-size:13px;min-width:220px;outline:none}
.stats-strip{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.stat-chip{background:rgba(0,210,255,0.05);border:1px solid rgba(0,210,255,0.15);border-radius:8px;padding:8px 14px;font-size:12px;color:#8896b3}
.stat-chip b{color:#00d2ff;font-size:15px;margin-left:6px}
.geo-summary{background:rgba(0,210,255,0.03);border:1px solid rgba(0,210,255,0.12);border-radius:14px;padding:26px 30px;margin:25px 0}
.geo-summary h2{font-size:20px;color:#00d2ff;letter-spacing:2px;margin-bottom:14px;padding-left:14px;border-left:3px solid #00d2ff}
.geo-summary h3{font-size:15px;color:#3a7bd5;margin:18px 0 8px;letter-spacing:1px}
.geo-summary p{color:#8896b3;line-height:2;font-size:14px;margin:8px 0}
.geo-summary strong{color:#00d2ff;font-weight:600}
.geo-summary ul{color:#8896b3;font-size:13px;line-height:2.1;padding-left:22px;columns:2;margin:6px 0}
.geo-summary ul b{color:#fff;font-weight:600}
.geo-summary a{color:#00d2ff;text-decoration:none}
.data-snapshot-badge{display:inline-block;background:rgba(255,255,255,0.06);border-radius:4px;padding:4px 10px;font-size:12px;color:#8b92b9;font-weight:400;margin-left:12px;vertical-align:middle;}
h2.chart-title{font-size:15px;font-weight:600}
.trend-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;}
.trend-badge.up{color:#00ff9d;background:rgba(0,255,157,0.12)}
.trend-badge.down{color:#ff5e62;background:rgba(255,94,98,0.12)}
.trend-badge.flat{color:#ffd700;background:rgba(255,215,0,0.12)}
.sankey-note,.premium-note{font-size:11px;color:#3a4a6c;margin-top:8px;letter-spacing:.5px;}
.story-nav{display:flex;gap:8px;flex-wrap:nowrap;overflow-x:auto;padding:10px 14px;margin:0 0 22px 0;background:rgba(16,20,40,0.8);border:1px solid rgba(0,210,255,0.10);border-radius:12px;position:sticky;top:8px;z-index:20;scrollbar-width:thin;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);}
.story-nav a{color:#8b92b9;font-size:13px;text-decoration:none;padding:6px 12px;border-radius:8px;white-space:nowrap;transition:all .25s;letter-spacing:.5px;}
.story-nav a:hover{color:#00d2ff;background:rgba(0,210,255,0.08);}
.story-nav a.active{color:#00d2ff;font-weight:600;background:rgba(0,210,255,0.12);box-shadow:inset 0 -2px 0 #00d2ff;}
.chart-insight{color:#8b92b9;font-size:13px;margin:-8px 0 14px 16px;font-weight:400;letter-spacing:.3px;line-height:1.6;}
[id]{scroll-margin-top:64px}
.insight-card{background:rgba(255,255,255,0.03);border:1px solid rgba(0,210,255,0.10);border-left:3px solid #00d2ff;border-radius:10px;padding:12px 14px;font-size:14px;line-height:1.6;color:#8b92b9;margin-top:12px;}
.insight-card b{color:#fff;font-weight:600;}
.insight-card .insight-num{color:#00d2ff;font-weight:700;font-size:15px;}
.insight-meta{font-size:11px;color:#5a6078;margin-top:8px;font-style:italic;line-height:1.5;}
.insight-card.ost{border-left:3px solid #ff9f7f;}
.insight-card.ost .insight-num{color:#ff9f7f;}
.listen-pulse-bar{display:flex;justify-content:space-between;gap:20px;align-items:center;flex-wrap:wrap;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:14px 20px;margin-bottom:16px;}
.pulse-title{font-size:14px;color:#c8cce0;font-weight:600;margin-right:10px;}
.pulse-meta{font-size:12px;color:#5a6078;}
.pulse-meta strong{color:#8b92b9;font-weight:700;}
.pulse-trend-list{display:flex;flex-wrap:wrap;gap:8px 18px;}
.trend-item{display:flex;align-items:center;gap:8px;height:28px;}
.trend-rank{width:16px;color:#00d2ff;font-weight:700;font-size:12px;}
.trend-song{max-width:100px;color:#c8cce0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px;}
.trend-share-bar{width:120px;height:8px;background:rgba(255,255,255,0.08);border-radius:4px;flex-shrink:0;}
.trend-share-fill{height:100%;background:#00d2ff;border-radius:4px;transition:width .6s ease;min-width:2px;}
.trend-share-label{font-size:11px;color:#8b92b9;width:42px;text-align:right;font-variant-numeric:tabular-nums;}
.daily-trend-card{background:rgba(0,210,255,0.03);border:1px solid rgba(0,210,255,0.10);border-radius:10px;padding:14px 18px;margin-bottom:16px;}
.daily-trend-header{font-size:13px;color:#00d2ff;font-weight:600;margin-bottom:10px;}
.daily-trend-list{display:flex;flex-wrap:wrap;gap:10px 24px;}
.trend-badge{font-size:11px;padding:2px 6px;border-radius:4px;font-variant-numeric:tabular-nums;}
.pulse-badge{font-size:11px;padding:2px 6px;border-radius:4px;font-variant-numeric:tabular-nums;}
.pulse-badge.up{background:rgba(255,159,127,0.12);color:#ff9f7f;}
.pulse-badge.down{background:rgba(0,210,255,0.12);color:#00d2ff;}
.pulse-badge.flat{background:rgba(90,96,120,0.15);color:#8b92b9;}
.pulse-badge.new{background:rgba(103,224,227,0.12);color:#67e0e3;}
.pulse-empty{font-size:13px;color:#5a6078;}
.data-freshness-bar{display:flex;flex-wrap:wrap;gap:24px;align-items:center;background:rgba(0,210,255,0.05);border-left:3px solid #00d2ff;padding:12px 20px;margin-bottom:16px;font-size:13px;color:#8b92b9;border-radius:8px;overflow-x:auto;}
.data-freshness-bar strong{color:#00d2ff;font-weight:600;}
.open-data-link{color:#00d2ff;text-decoration:underline;white-space:nowrap;}
.lineage-panel{background:rgba(90,96,120,0.06);border:1px solid rgba(90,96,120,0.18);border-radius:8px;padding:10px 16px;margin-bottom:16px;font-size:12px;color:#8b92b9;}
.lineage-panel summary{cursor:pointer;font-size:13px;color:#c8cce0;font-weight:600;}
.lineage-body{margin-top:10px;overflow-x:auto;}
.lineage-table{width:100%;border-collapse:collapse;font-size:12px;}
.lineage-table th,.lineage-table td{border:1px solid rgba(255,255,255,0.07);padding:6px 9px;text-align:left;vertical-align:top;}
.lineage-table th{color:#8b92b9;background:rgba(255,255,255,0.03);white-space:nowrap;}
.lineage-table td{color:#c8cce0;}
/* ===== 数据知识库搜索（DataSpeak）===== */
.search-zone{background:rgba(0,210,255,0.04);border:1px solid rgba(0,210,255,0.14);border-radius:12px;padding:14px 18px;margin-bottom:16px;}
.search-box{display:flex;gap:10px;align-items:stretch;}
.search-box input{flex:1;min-width:0;background:rgba(8,12,36,0.85);border:1px solid rgba(0,210,255,0.25);border-radius:8px;padding:11px 14px;color:#fff;font-size:14px;outline:none;transition:border-color .3s;}
.search-box input::placeholder{color:#5a6b8c;}
.search-box input:focus{border-color:#00d2ff;box-shadow:0 0 0 3px rgba(0,210,255,0.12);}
.search-box button{background:linear-gradient(90deg,#00d2ff,#3a7bd5);border:none;border-radius:8px;color:#04102b;font-weight:700;padding:0 22px;font-size:14px;cursor:pointer;white-space:nowrap;}
.search-box button:hover{filter:brightness(1.15);}
.search-chips{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;}
.chip-label{color:#5a6b8c;font-size:12px;margin-right:2px;}
.chip{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.10);color:#8b92b9;border-radius:20px;padding:4px 12px;font-size:12px;cursor:pointer;transition:all .25s;}
.chip:hover{border-color:#00d2ff;color:#00d2ff;background:rgba(0,210,255,0.08);}
.search-results{margin-top:12px;display:flex;flex-direction:column;gap:12px;}
.sr-block{display:flex;flex-direction:column;gap:8px;}
.sr-answer{background:rgba(0,210,255,0.06);border-left:3px solid #00d2ff;border-radius:8px;padding:10px 14px;font-size:13px;color:#c8cce0;line-height:1.7;}
.sr-hint{background:rgba(255,255,255,0.03);border-left:3px solid #ffd700;color:#8b92b9;}
.sr-head{font-size:13px;color:#00d2ff;font-weight:600;letter-spacing:.5px;margin-top:4px;}
.sr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;}
.song-card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.09);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:8px;transition:all .3s;}
.song-card:hover{border-color:rgba(0,210,255,0.35);transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,0.3);}
.sc-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.sc-name{font-size:15px;font-weight:700;color:#fff;}
.sc-attr{font-size:11px;color:#67e0e3;background:rgba(103,224,227,0.10);border:1px solid rgba(103,224,227,0.25);border-radius:4px;padding:1px 7px;}
.sc-life{font-size:11px;color:#ffd700;background:rgba(255,215,0,0.08);border:1px solid rgba(255,215,0,0.22);border-radius:4px;padding:1px 7px;}
.sc-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;}
.sc-m{display:flex;flex-direction:column;gap:1px;}
.sc-m span{font-size:10px;color:#5a6b8c;}
.sc-m b{font-size:13px;color:#c8cce0;font-variant-numeric:tabular-nums;}
.sc-extra{display:flex;flex-wrap:wrap;gap:4px 10px;}
.sc-extra-item{font-size:11px;color:#8b92b9;}
.sc-extra-item b{color:#67e0e3;font-weight:600;}
.sc-chart{width:100%;}
.sc-chart-text{font-size:11px;color:#5a6b8c;line-height:56px;text-align:center;}
.sc-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;}
.sc-rel{font-size:11px;color:#5a6b8c;}
.sc-open{background:rgba(0,210,255,0.10);border:1px solid rgba(0,210,255,0.30);color:#00d2ff;border-radius:6px;padding:3px 10px;font-size:11px;cursor:pointer;}
.sc-open:hover{background:rgba(0,210,255,0.20);}
.sr-rows{display:flex;flex-direction:column;gap:4px;}
.sr-row{display:flex;align-items:center;gap:12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:7px 12px;font-size:13px;}
.sr-rank{width:20px;color:#00d2ff;font-weight:700;font-size:12px;text-align:center;}
.sr-song{color:#c8cce0;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.sr-val{font-weight:700;font-variant-numeric:tabular-nums;}
.sr-val.up{color:#ff9f7f;}
.sr-tag{font-size:11px;color:#5a6b8c;background:rgba(90,96,120,0.15);border-radius:4px;padding:1px 7px;}
.sr-insight{background:rgba(255,215,0,0.04);border:1px solid rgba(255,215,0,0.12);border-left:3px solid #ffd700;border-radius:8px;padding:8px 12px;font-size:12px;color:#c8cce0;line-height:1.7;}
.sr-insight-jump{background:none;border:none;color:#00d2ff;font-size:12px;cursor:pointer;margin-left:6px;text-decoration:underline;}
.sr-jump{background:rgba(0,210,255,0.08);border:1px solid rgba(0,210,255,0.30);color:#00d2ff;border-radius:8px;padding:8px 14px;font-size:12px;cursor:pointer;align-self:flex-start;transition:all .25s;}
.sr-jump:hover{background:rgba(0,210,255,0.18);}
.sr-empty{color:#5a6b8c;font-size:13px;padding:10px 2px;}
.sr-flash{animation:srFlash 1.8s ease;}
@keyframes srFlash{0%,60%{box-shadow:0 0 0 3px rgba(0,210,255,0.55);border-color:#00d2ff;}100%{box-shadow:0 0 0 0 rgba(0,210,255,0);}}
.anomaly-mini-list{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto;}
.anomaly-item{background:rgba(255,159,127,0.1);color:#ff9f7f;border-radius:4px;padding:2px 8px;font-size:12px;white-space:nowrap;}
.anomaly-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:middle;}
.anomaly-dot.idx{background:#ff9f7f;}
.anomaly-dot.rank{background:#00d2ff;}
.micro-trend-box{background:rgba(0,210,255,0.03);border:1px solid rgba(0,210,255,0.10);border-radius:14px;padding:16px 20px 12px 20px;margin-bottom:20px;}
.micro-trend-box h2{margin-bottom:6px;}
.footer{text-align:center;padding:25px;color:#3a4a6c;font-size:12px;border-top:1px solid rgba(0,210,255,0.08);margin-top:20px;letter-spacing:1px;}
@media(max-width:1200px){.grid{grid-template-columns:repeat(2,1fr)}.bottom-row{grid-template-columns:1fr}.dim-row{grid-template-columns:1fr}.geo-summary ul{columns:1}.listen-pulse-bar{flex-direction:column;align-items:flex-start;}.daily-trend-list{flex-direction:column;}.data-freshness-bar{flex-direction:column;align-items:flex-start;gap:10px;}.anomaly-mini-list{margin-left:0;}}
</style>
</head>
<body>
<div class="container">
  <div class="data-freshness-bar" id="freshnessBar">
    <span class="fresh-item">📊 数据快照 <strong id="snapTime">--</strong></span>
    <span class="fresh-item">数据覆盖 <strong id="todayBatches">--</strong> 天</span>
    <span class="fresh-item">较昨日新增追踪 <strong id="dailyDelta">--</strong> 首</span>
    <span class="fresh-item" id="anomalyAlert">今日监测平稳</span>
    <div id="anomalyMiniList" class="anomaly-mini-list"></div>
    <a class="open-data-link" href="dashboard_data.json" download title="开放数据 JSON（Schema.org Dataset 分发）">开放数据 JSON ↗</a>
  </div>
  <details class="lineage-panel" id="lineagePanel">
    <summary>数据谱系 · 清洗日志 <span style="font-weight:400;color:#5a6b8c;font-size:11px">（点击展开 · 供 AI/研究者核验数据可信度）</span></summary>
    <div id="lineageBody" class="lineage-body"></div>
  </details>
  <div class="search-zone" id="searchZone" role="search">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="搜索歌曲 / 问数据：如「涨幅最大的歌」「周末听什么」「巡演影响」「最近异常」「在路上」" autocomplete="off" aria-label="数据知识库搜索：输入歌名或数据问题">
      <button type="button" id="searchBtn" aria-label="搜索">搜索</button>
    </div>
    <div class="search-chips">
      <span class="chip-label">试试问：</span>
      <button type="button" class="chip" data-q="涨幅最大的歌">📈 涨幅最大</button>
      <button type="button" class="chip" data-q="周末听什么">🌙 周末听什么</button>
      <button type="button" class="chip" data-q="巡演影响">🎤 巡演影响</button>
      <button type="button" class="chip" data-q="最近异常">⚠️ 最近异常</button>
      <button type="button" class="chip" data-q="经典沉淀期">🕰 经典沉淀期</button>
      <button type="button" class="chip" data-q="新歌发行">🎵 新歌发行</button>
    </div>
    <div id="searchResults" class="search-results" aria-live="polite"></div>
  </div>
  <div class="header">
    <h1>音乐数据趋势大屏</h1>
    <div class="subtitle">TREND ANALYSIS DASHBOARD</div>
    <div class="time" id="clock">--</div>
    __HEAD_INFO__
  </div>
  <div class="grid">
    <div class="kpi-card"><div class="kpi-label">数据完整度</div><div id="kpiCompleteGauge" style="height:92px"></div><div class="kpi-trend"><span class="trend-flat">有指数记录占比</span></div></div>
    <div class="kpi-card"><div class="kpi-label">指数覆盖率</div><div id="kpiIndexGauge" style="height:92px"></div><div class="kpi-trend"><span class="trend-flat">历史均值</span></div></div>
    <div class="kpi-card"><div class="kpi-label">活跃歌曲占比</div><div id="kpiActiveGauge" style="height:92px"></div><div class="kpi-trend"><span class="trend-flat">有收听数据</span></div></div>
    <div class="kpi-card"><div class="kpi-label">追踪歌曲总数</div><div class="kpi-value" id="kpi-total">__KPI_TOTAL__</div><div class="kpi-trend"><span class="trend-up" id="uid-split">__UID_SPLIT__</span></div><div style="font-size:10px;color:#5a6b8c;text-align:center">作品库规模 · 非实时指标</div><div id="kpiSparkline" style="height:42px;margin-top:6px"></div></div>
  </div>
  <nav class="story-nav" id="storyNav">
    <a href="#trendChart" data-target="trendChart">① 全景概览</a>
    <a href="#timelineChart" data-target="timelineChart">② 竞争格局演变</a>
    <a href="#sankeyChart" data-target="sankeyChart">③ 生命周期流转</a>
    <a href="#albumPremiumChart" data-target="albumPremiumChart">④ 时间偏好洞察</a>
    <a href="#tourFxChart" data-target="tourFxChart">⑤ 巡演与发行事件</a>
  </nav>
__GEO_SUMMARY__
  <div class="listen-pulse-bar" id="listenPulseBar">
    <div class="pulse-overview">
      <span class="pulse-title">📡 今日收听态势</span>
      <span class="pulse-meta">
        <strong id="activeCount">--</strong> / <span id="totalTracked">--</span> 首作品出现收听
        · 集中度 <strong id="concentration">--</strong>%
        · 截至 <span id="asOf">--</span>
      </span>
    </div>
  </div>
  <div class="daily-trend-card" id="dailyTrendCard">
    <div class="daily-trend-header">今日收听份额 TOP20</div>
    <div class="daily-trend-list" id="dailyTrendList"></div>
    <div class="daily-trend-empty" id="dailyTrendEmpty" style="display:none;color:#5a6b8c;padding:12px;font-size:12px;text-align:center;">今日活跃歌曲样本过小（&lt;10 首），份额结构无统计意义，暂不展示。</div>
  </div>
  <div class="daily-trend-card" id="dailyNewTodayCard" style="margin-top:12px;">
    <div class="daily-trend-header">🆕 昨日无指数 · 今日出现</div>
    <div class="daily-trend-list" id="dailyNewTodayList"></div>
    <div class="daily-trend-empty" id="dailyNewTodayEmpty" style="display:none;color:#5a6b8c;padding:12px;font-size:12px;text-align:center;">今日无"昨日空白、今日新增指数"的歌曲。</div>
  </div>
  <div class="micro-trend-box" id="microTrendBox">
    <h2 class="chart-title">最近7日全站热度微趋势</h2>
    <div id="microTrendChart" style="width:100%;height:140px"></div>
  </div>
  <div class="chart-row">
    <div class="chart-box"><h2 class="chart-title">历史指数趋势变化（含巡演 / 发行节点）</h2><p class="chart-insight"><span id="trendSongCount">--</span> 首作品日粒度追踪：2023-01 至今的完整热度考古</p><div class="chart-container tall" id="trendChart"></div></div>
    <div class="chart-box"><h2 class="chart-title">收听热度比例趋势（归一化至峰值月 = 100%）</h2><div class="chart-container" id="listenerChart" style="height:300px"></div></div>
  </div>
  <div class="chart-row">
    <div class="chart-box"><h2 class="chart-title">TOP 歌曲指数走势对比（近30日热度前10）</h2>
      <div class="mini-toggle"><button id="btnRaw">原始指数</button><button id="btnNorm" class="active">归一化对比（基期=100）</button></div>
      <div class="chart-container tall" id="linesChart"></div></div>
  </div>
  <div class="chart-row">
    <div class="chart-box"><h2 class="chart-title">单曲详情对比（日粒度，任选两首叠加）</h2>
      <div class="detail-bar">
        <select id="selSongA"></select>
        <select id="selSongB"></select>
      </div>
      <div class="stats-strip" id="statsStrip"></div>
      <div class="chart-container tall" id="detailChart"></div></div>
  </div>
  <div class="chart-row">
    <div class="chart-box"><h2 class="chart-title">作品属性走势对比（专辑 vs OST/单曲 vs 其他）</h2><div class="chart-container" id="catChart"></div></div>
  </div>
  <div class="bottom-row">
    <div class="chart-box"><h2 class="chart-title">近30日异常活跃歌曲</h2><div id="anomalyList" style="padding:10px;max-height:340px;overflow-y:auto;"></div></div>
    <div class="chart-box"><h2 class="chart-title">综合表现 TOP10（近90日·按属性）</h2>
      <div class="rank-tabs" id="rankTabs"><button data-attr="专辑" class="active">专辑</button><button data-attr="OST/单曲">OST/单曲</button><button data-attr="其他追踪">其他</button></div>
      <div style="max-height:300px;overflow-y:auto;padding:4px;">
      <table class="rank-table"><thead><tr><th>#</th><th>歌曲</th><th>综合得分</th><th>波动率</th><th>最长连涨</th><th>发行日期</th><th>属性</th></tr></thead><tbody id="rankBody"></tbody></table>
    </div></div>
    <div class="chart-box"><h2 class="chart-title">监测与归档状态</h2><div class="status-panel">
__STATUS_INFO__
    </div></div>
  </div>
  <div class="dim-row" style="grid-template-columns:1fr 1fr">
    <div class="chart-box"><h2 class="chart-title">收听历史对比 · 2022~2024 时代（归一化首月=100）</h2>
      <select id="histSongSelect" style="margin:4px 8px;padding:4px 8px;background:rgba(0,210,255,0.1);color:#b0c8f0;border:1px solid rgba(0,210,255,0.3);border-radius:4px;font-size:12px;max-width:95%;min-width:180px">
        <option value="top10">收听峰值 TOP10 歌曲</option>
      </select>
      <div class="chart-container" id="histTrendChart" style="height:300px"></div>
    </div>
    <div class="chart-box"><h2 class="chart-title">收听趋势对比 · 当前时代（同歌监听收比例归一化）</h2>
      <div class="chart-container" id="histCurrentChart" style="height:300px"></div>
    </div>
  </div>
  <div class="dim-row" style="grid-template-columns:1fr 1fr">
    <div class="chart-box"><h2 class="chart-title">同曲跨时代排名对比（Top 20）</h2><div class="chart-container" id="crossEraChart" style="height:280px"></div></div>
    <div class="chart-box"><h2 class="chart-title">头部集中度 &amp; 峰值半衰期</h2><div id="advancedMetrics" style="padding:12px 16px;color:#8896b3;font-size:13px;line-height:1.8"></div></div>
  </div>
  <div class="dim-row" style="grid-template-columns:1fr 1fr">
    <div class="chart-box"><h2 class="chart-title">巡演带动效应（事件后7日 vs 基线，全站日均指数涨幅%）</h2><div class="chart-container" id="tourFxChart" style="height:300px"></div></div>
    <div class="chart-box"><h2 class="chart-title">新歌发行14日表现（平均指数 / 峰值）</h2><div class="chart-container" id="releaseFxChart" style="height:300px"></div></div>
  </div>
  <div class="dim-row">
    <div class="chart-box"><h2 class="chart-title">热度-稳定性矩阵（体量 × 波动）</h2><div class="chart-container" id="matrixChart" style="height:260px"></div></div>
    <div class="chart-box"><h2 class="chart-title">周末 vs 工作日表现</h2><div class="chart-container" id="weekChart" style="height:260px"></div></div>
    <div class="chart-box"><h2 class="chart-title">作品属性维度（信息表比对）</h2><div class="chart-container" id="attrChart" style="height:260px"></div></div>
  </div>
  <div class="dim-row" style="grid-template-columns:1.2fr 1fr 1fr">
    <div class="chart-box"><h2 class="chart-title">作品成长生态流转 · 热度生命力分布</h2><p class="chart-insight">近 60 日窗口：作品在「上升期→稳定期→经典沉淀期」之间的流转生态</p><div class="chart-container" id="sankeyChart" style="height:300px" aria-describedby="ai-sankey"></div><div class="sankey-note">上月→本月：上升期/稳定期/经典沉淀期 流动数量（近60日窗口）</div><div class="ai-summary" id="ai-sankey" aria-label="图表文本摘要" data-summary="sankey" style="position:absolute;left:-9999px;"></div></div>
    <div class="chart-box"><h2 class="chart-title">作品生命力衰减带 · 发行后 D+1~D+90</h2><div class="chart-container" id="decayChart" style="height:300px"></div></div>
    <div class="chart-box"><h2 class="chart-title">听众时间偏好矩阵 · 专辑 vs OST/单曲</h2>
      <div style="display:flex;gap:20px;flex-wrap:wrap;">
        <div style="flex:1;min-width:260px;"><div style="font-size:13px;color:#00d2ff;margin-bottom:8px;font-weight:600;">🎵 专辑类</div><div class="chart-container" id="albumPremiumChart" style="height:300px" aria-describedby="ai-weekend"></div>
          <div class="insight-card">专辑类洞察：<span id="insightTextAlb">数据计算中…</span><p class="insight-meta">数据截止 <span id="insightDate">--</span>，覆盖 <span id="insightBatches">--</span> 天监测</p></div></div>
        <div style="flex:1;min-width:260px;"><div style="font-size:13px;color:#ffd700;margin-bottom:8px;font-weight:600;">🎬 OST/单曲</div><div class="chart-container" id="ostPremiumChart" style="height:300px" aria-describedby="ai-weekend"></div>
          <div class="insight-card ost">OST/单曲洞察：<span id="insightTextOst">数据计算中…</span><p class="insight-meta">数据截止 <span id="insightDate2">--</span>，覆盖 <span id="insightBatches2">--</span> 天监测</p></div></div>
      </div><div class="premium-note">周末/工作日收听比率：&gt;1 周末型（蓝）· &lt;1 通勤型（橙）· 各取数据最充分 Top12 歌曲</div><div class="ai-summary" id="ai-weekend" aria-label="图表文本摘要" data-summary="weekend_premium" style="position:absolute;left:-9999px;"></div></div>
  </div>
  <div class="dim-row" style="grid-template-columns:1fr 1fr 1fr">
    <div class="chart-box"><h2 class="chart-title">老歌复活雷达 · 近期 vs 历史均值</h2><div class="chart-container" id="radarSpringChart" style="height:300px"></div></div>
    <div class="chart-box"><h2 class="chart-title">排名战争瀑布 · 日粒度跃迁量</h2><div class="chart-container" id="waterfallChart" style="height:300px" aria-describedby="ai-waterfall"></div><div class="ai-summary" id="ai-waterfall" aria-label="图表文本摘要" data-summary="waterfall" style="position:absolute;left:-9999px;"></div></div>
    <div class="chart-box"><h2 class="chart-title">生命周期速览 · 当前分类占比</h2><div id="lifecycleSummary" style="padding:12px 16px;color:#8896b3;font-size:13px;line-height:2"></div></div>
  </div>
  <div class="chart-row">
    <div class="chart-box"><h2 class="chart-title">月度竞争格局时间轴 · 作品势力消长</h2>
      <p class="chart-insight"><span id="tlFrameCount">--</span> 个月竞争格局：自动播放展示每月 Top15 份额争夺与巡演/发行事件叠加</p>
      <div class="chart-container" id="timelineChart" style="height:430px" aria-describedby="ai-timeline"></div>
      <div style="font-size:11px;color:#5a6b8c;margin-top:6px">气泡大小 = 相对自身峰值 · X = 排名变化速度(位/月) · Y = 当月份额(%) · 绿=上升期 / 黄=稳定期 / 紫=经典沉淀期</div><div class="ai-summary" id="ai-timeline" aria-label="图表文本摘要" data-summary="timeline" style="position:absolute;left:-9999px;"></div></div>
  </div>
  <div class="chart-row">
    <div class="chart-box">
      <h2 class="chart-title">巡演歌曲级效应 · 每场全站/歌单内/辐射带动</h2>
      <p class="chart-insight"><span id="tourSongFxCount">--</span> 场演出已有歌曲级监测数据：演出后 7 日平台指数相对演出前（21~7 日）基线的变化，分全站 / 歌单内 / 辐射带动三口径；歌单内 = 直接效应，歌单外 = 巡演辐射带动</p>
      <div id="tourSongFx"></div>
      <div class="ai-summary" id="ai-tourSongFx" aria-label="图表文本摘要" style="position:absolute;left:-9999px;"></div>
    </div>
  </div>
__ABOUT_SECTION__
  <div class="footer">数据仅供个人研究使用 · 链接身份唯一识别 · 历史趋势分析面板 · 原始数据本地留存</div>
</div>
<script>
// 数据加载：改为从独立的 dashboard_data.json 加载（不再内嵌进 HTML）。
// 用带时间戳的 URL 绕过 CDN/浏览器缓存，确保每批次数据即时生效。
// 同步加载保证下方渲染代码（依赖 dashboardData）在就绪后才执行，改动最小、最可靠。
(function(){
  var url = 'dashboard_data.json?t=' + Date.now();
  var xhr = new XMLHttpRequest();
  xhr.open('GET', url, false);            // 同步：阻塞直到数据就绪
  try {
    xhr.send(null);
    if (xhr.status === 200) {
      window.dashboardData = JSON.parse(xhr.responseText);
    } else {
      window.dashboardData = null;
      console.error('数据加载失败 HTTP ' + xhr.status);
    }
  } catch (e) {
    window.dashboardData = null;
    console.error('数据加载异常: ' + e.message);
  }
})();
var dashboardData = window.dashboardData || {};
if (!window.dashboardData) {
  var _fb = document.getElementById('freshnessBar');
  if (_fb) _fb.insertAdjacentHTML('afterend', '<div style="color:#ff9f7f;padding:20px;text-align:center;background:rgba(255,159,127,0.08);border:1px solid rgba(255,159,127,0.3);border-radius:12px;margin:20px 0;">数据加载失败，请刷新重试；若持续失败请检查网络。</div>');
}
// 指令4：AI 可读摘要——从 payload 动态填充隐藏层（无数字写死，视觉不可见但可被爬虫/读屏提取）
document.querySelectorAll('.ai-summary').forEach(function(el){
  var k = el.getAttribute('data-summary');
  if (k && dashboardData.chart_summaries && dashboardData.chart_summaries[k]) {
    el.textContent = dashboardData.chart_summaries[k];
  }
});
// #5 数据谱系：渲染清洗日志折叠面板（供 AI/研究者核验可信度）
(function(){
  var lg = dashboardData.lineage;
  var body = document.getElementById('lineageBody');
  if (!lg || !body) return;
  var rows = [
    ['数据快照', (dashboardData.timestamp || '') + ' · 覆盖 ' + (dashboardData.batch_count || '-') + ' 天'],
    ['Excel 文件', lg.excel_files ? (lg.excel_files.success + '/' + lg.excel_files.total + ' 成功，失败 ' + lg.excel_files.failed.length + ' 个') : '-'],
    ['失败文件明细', lg.excel_files && lg.excel_files.failed.length ? lg.excel_files.failed.join('、') : '无（全部读取成功）'],
    ['非歌曲内容剔除', lg.nonsong_filtered ? (lg.nonsong_filtered.rows + ' 行（' + lg.nonsong_filtered.pct + '%），播客/综艺条目') : '-'],
    ['日内多批次合并', lg.intraday_merged ? (lg.intraday_merged.before + ' → ' + lg.intraday_merged.after + ' 行，按字段取最新有效值') : '-'],
    ['指数口径校准', lg.index_calibration ? (lg.index_calibration.rows + '/' + lg.index_calibration.total + ' 行采用「昨日音乐指数」官方值（' + lg.index_calibration.pct + '%）') : '-'],
    ['追踪数据集', lg.dataset ? (lg.dataset.records + ' 条记录 · ' + lg.dataset.date_range + ' · 追踪歌曲 ' + lg.dataset.tracked_uids + ' 首') : '-'],
    ['身份识别', lg.link_registry ? ('链接注册表 ' + lg.link_registry + ' 个唯一 mid；参考映射 ' + (lg.reference_map ? lg.reference_map.mid2name + ' mid→name（' + lg.reference_map.name2mid_1to1 + ' 组 1:1）' : '-')) : '-'],
    ['生命周期分布', lg.lifecycle_dist ? Object.keys(lg.lifecycle_dist).map(function(k){return k + ' ' + lg.lifecycle_dist[k] + ' 首';}).join(' · ') : '-'],
    ['历史收听归档', (lg.hist_cache_rows ? ('缓存 ' + lg.hist_cache_rows + ' 条；') : '') + (lg.hist_trend_songs ? lg.hist_trend_songs + ' 首歌曲有 3 月以上有效数据' : '-')]
  ];
  var html = '<table class="lineage-table"><tr><th>环节</th><th>口径与结果</th></tr>';
  rows.forEach(function(r){ html += '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td></tr>'; });
  html += '</table>';
  body.innerHTML = html;
})();
// #6 巡演歌曲级效应：渲染每场三口径 + Top5 带动 + 可展开全量歌曲列表（动态读取，不写死）
//   双向链接：有 live_url 的场次，summary 左侧日期+城市可点击跳转 live 详情页（新标签页）；
//   支持 #tour-scene-YYYY-MM-DD 深链定位（自动展开并滚动到视口，无匹配时静默）
(function(){
  var box = document.getElementById('tourSongFx');
  if (!box) return;
  var tse = dashboardData.tour_song_effects || [];
  var cnt = document.getElementById('tourSongFxCount');
  if (cnt) cnt.textContent = tse.length;
  if (!tse.length) {
    box.innerHTML = '<div style="color:#5a6b8c;padding:20px;text-align:center">暂无歌曲级效应数据</div>';
    return;
  }
  function fmt(v){ return (v===null||v===undefined)?'—':((v>0?'+':'')+v.toFixed(1)+'%'); }
  function cls(v){ return v>0?'tse-up':(v<0?'tse-down':'tse-flat'); }
  // 点击 live 链接：阻止 <summary> 默认展开/收起，改为新标签页打开详情页
  box.addEventListener('click', function(ev){
    var t = ev.target;
    var a = (t && t.closest) ? t.closest('a.tse-link') : null;
    if (!a) return;
    ev.preventDefault();
    window.open(a.getAttribute('href'), '_blank', 'noopener');
  });
  var html = '', aiLines = [];
  tse.slice().reverse().forEach(function(e){  // 最新场次在前
    var tops = e.top_songs || [];
    var songs = (e.songs || []).slice().sort(function(a,b){ return (b.uplift||0)-(a.uplift||0); });
    html += '<details class="tse-scene" id="tour-scene-' + (e.date||'') + '">';
    html += '<summary>';
    html += '<span class="tse-date">' + (e.date||'').replace(/-/g,'.') + '</span>';
    html += (e.live_url
      ? '<a class="tse-city tse-link" href="' + e.live_url + '" target="_blank" rel="noopener" title="打开该场次 live 详情页">' + (e.city||'') + '</a>'
      : '<span class="tse-city">' + (e.city||'') + '</span>');
    html += '<span class="tse-m">全站 <b class="'+cls(e.total_uplift)+'">'+fmt(e.total_uplift)+'</b></span>';
    html += (e.setlist_uplift!=null ? '<span class="tse-m">歌单内 <b class="'+cls(e.setlist_uplift)+'">'+fmt(e.setlist_uplift)+'</b></span>' : '');
    html += (e.radiance_uplift!=null ? '<span class="tse-m">辐射带动 <b class="'+cls(e.radiance_uplift)+'">'+fmt(e.radiance_uplift)+'</b></span>' : '');
    html += '</summary><div class="tse-body">';
    if (tops.length) {
      html += '<div class="tse-tops">带动最显著：' + tops.map(function(t){
        return '<span class="tse-chip'+(t.on_setlist?' on':'')+'">' + t.name + ' ' + fmt(t.uplift) + (t.on_setlist?' · 歌单内':'') + '</span>';
      }).join('') + '</div>';
    }
    if (songs.length) {
      html += '<table class="tse-table"><tr><th>曲目</th><th>涨幅</th><th>归属</th></tr>';
      songs.forEach(function(s){
        html += '<tr><td class="name">' + s.name + '</td><td class="'+cls(s.uplift)+'">' + fmt(s.uplift) + '</td><td>' + (s.on_setlist?'<span class="tse-tag-on">歌单内</span>':'<span class="tse-tag">辐射带动</span>') + '</td></tr>';
      });
      html += '</table>';
    }
    html += '</div></details>';
    aiLines.push((e.date||'') + ' ' + (e.city||'') + ' 全站' + fmt(e.total_uplift) + ' 歌单内' + fmt(e.setlist_uplift) + ' 辐射带动' + fmt(e.radiance_uplift) + '；');
  });
  box.innerHTML = html;
  var ais = document.getElementById('ai-tourSongFx');
  if (ais) ais.textContent = '巡演歌曲级效应：共' + tse.length + '场有监测数据。' + aiLines.join(' ');
  // 深链定位：#tour-scene-YYYY-MM-DD → 自动展开该场并滚动到视口（无匹配时正常加载不报错）
  function openFromHash(){
    var h = location.hash;
    if (!h || h.indexOf('#tour-scene-') !== 0) return;
    var el = document.getElementById(h.slice(1));
    if (!el) return;
    el.open = true;
    setTimeout(function(){
      el.scrollIntoView({behavior:'smooth', block:'start'});
      el.classList.add('tse-flash');
      setTimeout(function(){ el.classList.remove('tse-flash'); }, 2600);
    }, 120);
  }
  openFromHash();
  window.addEventListener('hashchange', openFromHash);
})();
</script>
<script>
// ===== 阅读指南导航（平滑滚动 + 滚动高亮）=====
(function(){
  var nav = document.getElementById('storyNav');
  if (!nav) return;
  var links = Array.prototype.slice.call(nav.querySelectorAll('a'));
  // 按文档位置排序 targets（导航序与文档序可能不一致，高亮须以文档序计算）
  var ordered = links.map(function(a){
    return { link: a, target: document.getElementById(a.getAttribute('data-target')) };
  }).filter(function(x){ return x.target; });
  ordered.sort(function(x, y){ return x.target.getBoundingClientRect().top - y.target.getBoundingClientRect().top; });
  function setActive(link){
    links.forEach(function(a){ a.classList.remove('active'); });
    if (link) link.classList.add('active');
  }
  // 点击：平滑滚动并立即高亮对应项
  links.forEach(function(a){
    a.addEventListener('click', function(e){
      e.preventDefault();
      setActive(a);
      var target = document.getElementById(a.getAttribute('data-target'));
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  // 手动滚动：以「距视口阈值线最近」的区块高亮（确定性，且同行区块也能正确区分）
  var ticking = false;
  function highlight(){
    ticking = false;
    var line = window.innerHeight * 0.35;
    var best = ordered[0], bestDist = Infinity;
    for (var i = 0; i < ordered.length; i++) {
      var d = Math.abs(ordered[i].target.getBoundingClientRect().top - line);
      if (d < bestDist) { bestDist = d; best = ordered[i]; }
    }
    setActive(best.link);
  }
  window.addEventListener('scroll', function(){
    if (!ticking) { ticking = true; requestAnimationFrame(highlight); }
  }, { passive: true });
  highlight();
})();
// ===== 洞察文案：周末溢价比率由数据驱动动态生成（不写死结论）=====
(function(){
  var ap = (dashboardData.weekend_premium || {}).attr_premium || [];
  var ratioOf = {};
  ap.forEach(function(x){ ratioOf[x.attr] = x.ratio; });
  var alb = ratioOf['专辑'], ost = ratioOf['OST/单曲'];
  var fmt = function(v){ return (v !== undefined && v !== null) ? v.toFixed(2) : '--'; };
  var has = function(v){ return v !== undefined && v !== null; };

  function descRatio(r){
    if (!has(r)) return '暂无数据';
    if (r >= 1.02) return '呈「周末型」特征（周末收听高于工作日）';
    if (r <= 0.98) return '呈「通勤型」特征（工作日收听更高）';
    return '接近持平（周末与工作日差异不大）';
  }

  var albText = '数据不足，暂无法生成洞察。';
  var ostText = '数据不足，暂无法生成洞察。';
  if (has(alb) && has(ost)) {
    var diff = alb - ost;
    if (diff > 0.02) {
      albText = '周末/工作日收听比率 ' + fmt(alb) + '，' + descRatio(alb) + '；周末溢价高于 OST/单曲（' + fmt(ost) + '），更具「周末沉浸式聆听」特质，而非背景音属性。';
      ostText = '周末/工作日收听比率 ' + fmt(ost) + '，' + descRatio(ost) + '；周末溢价低于专辑类作品（' + fmt(alb) + '），推测更多承担「通勤伴随」功能。';
    } else if (diff < -0.02) {
      albText = '周末/工作日收听比率 ' + fmt(alb) + '，' + descRatio(alb) + '；周末溢价低于 OST/单曲（' + fmt(ost) + '），日常收听分布更均匀。';
      ostText = '周末/工作日收听比率 ' + fmt(ost) + '，' + descRatio(ost) + '；周末溢价高于专辑类作品（' + fmt(alb) + '），推测与「周末追剧/观影场景」联动相关。';
    } else {
      albText = '周末/工作日收听比率 ' + fmt(alb) + '，' + descRatio(alb) + '；与 OST/单曲（' + fmt(ost) + '）基本持平，两类作品周末偏好趋同。';
      ostText = '周末/工作日收听比率 ' + fmt(ost) + '，' + descRatio(ost) + '；与专辑类作品（' + fmt(alb) + '）基本持平，听众时间偏好无显著差异。';
    }
  } else if (has(alb)) {
    albText = '周末/工作日收听比率 ' + fmt(alb) + '，' + descRatio(alb) + '；OST/单曲暂无足够数据对比。';
  } else if (has(ost)) {
    ostText = '周末/工作日收听比率 ' + fmt(ost) + '，' + descRatio(ost) + '；专辑类暂无足够数据对比。';
  }
  var t1 = document.getElementById('insightTextAlb');
  if (t1) t1.textContent = albText;
  var t2 = document.getElementById('insightTextOst');
  if (t2) t2.textContent = ostText;
})();
// ===== 副标题动态数据：时间轴帧数 / 追踪歌曲总数 =====
(function(){
  var tlFrames = (dashboardData.timeline_narrative || []).length;
  if (tlFrames > 0) {
    var el = document.getElementById('tlFrameCount');
    if (el) el.textContent = tlFrames;
  }
  var el2 = document.getElementById('trendSongCount');
  if (el2 && dashboardData.total_songs) el2.textContent = dashboardData.total_songs;
})();
// ===== 今日收听态势（只保留概览，Top5 移入独立卡片）=====
(function(){
  var bar = document.getElementById('listenPulseBar');
  if (!bar) return;
  var ov = dashboardData.daily_listen_overview || {};
  var trend = dashboardData.daily_listen_trend || [];
  if (!ov.active_count || ov.active_count === 0) {
    bar.innerHTML = '<div class="pulse-empty">📡 今日收听态势 · 暂无活跃收听数据 · 监测持续中</div>';
    return;
  }
  document.getElementById('activeCount').textContent = ov.active_count;
  document.getElementById('totalTracked').textContent = ov.total_tracked;
  var conc = document.getElementById('concentration');
  conc.textContent = (ov.concentration_top3 !== null && ov.concentration_top3 !== undefined) ? ov.concentration_top3 : '--';
  document.getElementById('asOf').textContent = ov.as_of || '--';
  // ===== 今日份额列表（dailyTrendCard）：小样本（too_small）时隐藏，避免误导 =====
  var card = document.getElementById('dailyTrendCard');
  var list = document.getElementById('dailyTrendList');
  var emptyTip = document.getElementById('dailyTrendEmpty');
  if (!card || !list) return;
  if (ov.too_small) {
    if (emptyTip) emptyTip.style.display = 'block';
    return;
  }
  if (trend.length === 0) {
    if (emptyTip) emptyTip.style.display = 'block';
    return;
  }
  list.innerHTML = '';
  trend.forEach(function(it){
    var badgeTxt = '', badgeCls = '';
    if (it.trend_label === 'up') { badgeTxt = '↑ ' + Math.round(Math.abs(it.trend_pct)) + '%'; badgeCls = 'up'; }
    else if (it.trend_label === 'down') { badgeTxt = '↓ ' + Math.round(Math.abs(it.trend_pct)) + '%'; badgeCls = 'down'; }
    else if (it.trend_label === 'flat') { badgeTxt = '→ 持平'; badgeCls = 'flat'; }
    else { badgeTxt = '● 新活跃'; badgeCls = 'new'; }
    var div = document.createElement('div');
    div.className = 'trend-item';
    div.innerHTML = '<span class="trend-rank">' + it.rank + '</span>' +
      '<span class="trend-song" title="' + it.song + '">' + it.song + '</span>' +
      '<div class="trend-share-bar"><div class="trend-share-fill" style="width:' + Math.min(it.share_pct, 100) + '%"></div></div>' +
      '<span class="trend-share-label">' + it.share_pct + '%</span>' +
      '<span class="pulse-badge ' + badgeCls + '">' + badgeTxt + '</span>';
    list.appendChild(div);
  });
  // ===== 昨日无指数 · 今日出现（dailyNewTodayCard）=====
  var ntCard = document.getElementById('dailyNewTodayCard');
  var ntList = document.getElementById('dailyNewTodayList');
  var ntEmpty = document.getElementById('dailyNewTodayEmpty');
  if (ntCard && ntList) {
    var nt = dashboardData.daily_new_today || [];
    if (nt.length === 0) {
      if (ntEmpty) ntEmpty.style.display = 'block';
    } else {
      ntList.innerHTML = '';
      nt.forEach(function(it){
        var div = document.createElement('div');
        div.className = 'trend-item';
        div.innerHTML = '<span class="trend-rank">🆕</span>' +
          '<span class="trend-song" title="' + it.song + '">' + it.song + '</span>' +
          '<div class="trend-share-bar"><div class="trend-share-fill" style="width:' + Math.min(it.share_pct, 100) + '%"></div></div>' +
          '<span class="trend-share-label">' + it.share_pct + '%</span>';
        ntList.appendChild(div);
      });
    }
  }
})();
// ===== 日报层：数据新鲜度条 + insight-meta + 微趋势图 + 异动警报 =====
(function(){
  var d = dashboardData;
  // freshness-bar
  var snap = document.getElementById('snapTime');
  if (snap && d.last_update) snap.textContent = d.last_update;
  var batches = document.getElementById('todayBatches');
  if (batches && d.today_batches !== undefined) batches.textContent = d.today_batches;
  var delta = document.getElementById('dailyDelta');
  if (delta && d.daily_new_records !== undefined && d.daily_new_records !== null) {
    var val = d.daily_new_records;
    delta.textContent = (val >= 0 ? '+' : '') + val;
    delta.style.color = val > 0 ? '#00ff9d' : '#00d2ff';
  }
  // anomaly alert
  var alertEl = document.getElementById('anomalyAlert');
  if (alertEl) {
    if (d.latest_anomaly) {
      var isIdx = d.latest_anomaly.type.indexOf('指数') >= 0;
      alertEl.innerHTML = '<span class="anomaly-dot ' + (isIdx ? 'idx' : 'rank') + '"></span>' + d.latest_anomaly.song + ' ' + d.latest_anomaly.desc;
      alertEl.style.color = '#ff9f7f';
      alertEl.style.fontWeight = '600';
    } else {
      alertEl.textContent = '今日监测平稳，无显著异动';
    }
  }
  // anomaly mini list (指令6, 合并到 freshness-bar 右侧)
  var miniList = document.getElementById('anomalyMiniList');
  if (miniList && d.daily_anomalies && d.daily_anomalies.length > 0) {
    d.daily_anomalies.forEach(function(a){
      var s = document.createElement('span');
      s.className = 'anomaly-item';
      var isIdx2 = a.type.indexOf('指数') >= 0;
      s.innerHTML = '<span class="anomaly-dot ' + (isIdx2 ? 'idx' : 'rank') + '"></span>' + a.song + ' ' + a.desc;
      miniList.appendChild(s);
    });
  }
  // insight-meta (指令4)
  var asOf = (d.daily_listen_overview && d.daily_listen_overview.as_of) || '--';
  var bc = d.today_batches || '--';
  var elD1 = document.getElementById('insightDate'), elD2 = document.getElementById('insightDate2');
  if (elD1) elD1.textContent = asOf;
  if (elD2) elD2.textContent = asOf;
  var elB1 = document.getElementById('insightBatches'), elB2 = document.getElementById('insightBatches2');
  if (elB1) elB1.textContent = bc;
  if (elB2) elB2.textContent = bc;
  // microTrendChart (指令5)
  var r7 = d.recent_7days;
  if (r7 && r7.length > 0) {
    var mc = document.getElementById('microTrendChart');
    if (mc && typeof echarts !== 'undefined') {
      var mtChart = echarts.init(mc);
      var dates = r7.map(function(x){return x.date ? x.date.slice(5) : '';});
      var vals = r7.map(function(x){return x.avg_index !== null ? x.avg_index : null;});
      var lastVal = vals.filter(function(v){return v!==null;});
      var last = lastVal.length > 0 ? lastVal[lastVal.length-1] : null;
      var prev = lastVal.length > 1 ? lastVal[lastVal.length-2] : null;
      var deltaPct = (last && prev && prev > 0) ? ((last/prev - 1)*100).toFixed(1) : null;
      var markData = [];
      if (deltaPct !== null) markData.push({
        name: deltaPct>=0 ? '↑'+Math.abs(deltaPct)+'%' : '↓'+Math.abs(deltaPct)+'%',
        coord: [dates[dates.length-1], last],
        symbol: 'pin', symbolSize: 36, symbolOffset: [0, -24],
        itemStyle: {color: deltaPct>=0 ? '#00ff9d' : '#ff5e62'},
        label: {show: true, fontSize: 11, fontWeight: 700}
      });
      mtChart.setOption({
        backgroundColor: 'transparent',
        grid: {left: '3%', right: '5%', top: '18%', bottom: '5%', containLabel: true},
        xAxis: {type: 'category', data: dates, axisLine: {lineStyle: {color: 'rgba(0,210,255,0.2)'}}, axisLabel: {color: '#5a6b8c', fontSize: 10}},
        yAxis: {type: 'value', axisLine: {lineStyle: {color: 'rgba(0,210,255,0.2)'}}, splitLine: {lineStyle: {color: 'rgba(0,210,255,0.04)'}}, axisLabel: {color: '#5a6b8c', fontSize: 10}},
        series: [{
          type: 'line', data: vals, smooth: true, lineStyle: {color: '#00d2ff', width: 2}, symbol: 'circle', symbolSize: 6,
          areaStyle: {color: {type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: 'rgba(0,210,255,0.08)'}, {offset: 1, color: 'rgba(0,210,255,0)'}]}},
          markPoint: {data: markData}
        }]
      });
      window.addEventListener('resize', function(){ mtChart.resize(); });
    }
  }
})();
</script>
<script>
function main(){
function updateClock(){
  const now=new Date();
  document.getElementById('clock').textContent=
    now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')+'-'+String(now.getDate()).padStart(2,'0')+' '+
    String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0')+':'+String(now.getSeconds()).padStart(2,'0');
}
setInterval(updateClock,1000);updateClock();

function animateValue(id,start,end,duration,suffix){
  suffix = suffix || "";
  const obj=document.getElementById(id);
  let startTimestamp=null;
  const step=function(timestamp){
    if(!startTimestamp)startTimestamp=timestamp;
    const progress=Math.min((timestamp-startTimestamp)/duration,1);
    const val=Math.floor(progress*(end-start)+start);
    obj.textContent=val+suffix;
    if(progress<1)window.requestAnimationFrame(step);
  };
  window.requestAnimationFrame(step);
}

setTimeout(function(){animateValue('kpi-total',0,dashboardData.total_songs,1500,'');},800);
document.getElementById('uid-split').textContent='链接身份 '+dashboardData.link_uids+' | 名称身份 '+dashboardData.name_uids;

// KPI 迷你 gauge 环形图（只展示百分比份额，不展示绝对数值）
function initKpiGauge(elId,value,color){
  var el=document.getElementById(elId);
  if(!el)return;
  var g=echarts.init(el);
  g.setOption({
    backgroundColor:'transparent',
    series:[{
      type:'gauge',startAngle:210,endAngle:-30,min:0,max:100,radius:'95%',center:['50%','60%'],
      progress:{show:true,width:8,itemStyle:{color:color}},
      axisLine:{lineStyle:{width:8,color:[[1,'rgba(0,210,255,0.10)']]}},
      pointer:{show:false},axisTick:{show:false},splitLine:{show:false},axisLabel:{show:false},
      detail:{valueAnimation:true,offsetCenter:[0,2],formatter:function(v){return Math.round(v)+'%';},color:'#b0c8f0',fontSize:17,fontWeight:'bold'},
      data:[{value:value}]
    }]
  });
  window.addEventListener('resize',function(){g.resize();});
}
setTimeout(function(){initKpiGauge('kpiCompleteGauge',dashboardData.complete_rate,'#00ff9d');},200);
setTimeout(function(){initKpiGauge('kpiIndexGauge',dashboardData.index_rate,'#00d2ff');},400);
setTimeout(function(){initKpiGauge('kpiActiveGauge',dashboardData.active_rate,'#ffd700');},600);

const anomalyList=document.getElementById('anomalyList');
(dashboardData.top_songs||[]).forEach(function(s){
  const div=document.createElement("div");
  div.className="anomaly-card";
  let tagClass="";
  if(s.tag==='飙升') tagClass='hot';
  else if(s.tag==='上涨') tagClass='up';
  div.innerHTML='<div><div class="anomaly-name">'+s.name+'</div><div class="anomaly-meta">近30日环比: '+s.trend+'% | 异常评分: '+s.score+'</div></div><div class="tag '+tagClass+'">'+s.tag+'</div>';
  anomalyList.appendChild(div);
});

const rankBody=document.getElementById('rankBody');
const rankGroups=dashboardData.rank_groups||{};
function renderRank(attr){
  rankBody.innerHTML='';
  (rankGroups[attr]||[]).forEach(function(r,i){
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+(i+1)+'</td><td class="name" title="'+r[1]+'">'+r[1]+'</td><td style="color:#00d2ff">'+r[2]+'</td><td>'+r[3]+'%</td><td>'+r[4]+'次</td><td>'+(r[6]||'-')+'</td><td>'+(r[7]||'-')+'</td>';
    rankBody.appendChild(tr);
  });
}
renderRank('专辑');
document.querySelectorAll('#rankTabs button').forEach(function(btn){
  btn.addEventListener('click',function(){
    document.querySelectorAll('#rankTabs button').forEach(function(b){b.classList.remove('active');});
    btn.classList.add('active');
    renderRank(btn.getAttribute('data-attr'));
  });
});

var labels=dashboardData.time_labels||[];
var maxIdx=Math.max.apply(null,(dashboardData.trend_raw||[1]))*1.12;

var trendChart=echarts.init(document.getElementById('trendChart'));
trendChart.setOption({
  backgroundColor:'transparent',
  tooltip:{trigger:'axis',axisPointer:{type:'cross'}},
  legend:{data:['平均指数','活跃歌曲数','巡演节点','新歌发行','演出活动'],textStyle:{color:'#5a6b8c'}},
  grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
  xAxis:{type:'category',data:labels,axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#5a6b8c',fontSize:11}},
  yAxis:[
    {type:'value',name:'指数',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
    {type:'value',name:'歌曲数',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{show:false},axisLabel:{color:'#5a6b8c'}}
  ],
  series:[
    {name:'平均指数',type:'line',smooth:true,symbol:'circle',symbolSize:8,data:dashboardData.trend_raw||[],lineStyle:{color:'#00d2ff',width:3},itemStyle:{color:'#00d2ff',borderColor:'#fff',borderWidth:2},areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,210,255,0.25)'},{offset:1,color:'rgba(0,210,255,0)'}])}},
    {name:'活跃歌曲数',type:'bar',yAxisIndex:1,data:dashboardData.song_count_trend||[],itemStyle:{color:'rgba(0,255,157,0.25)',borderRadius:[4,4,0,0]},barWidth:'30%'},
    {name:'巡演节点',type:'scatter',symbol:'pin',symbolSize:22,data:(dashboardData.tour_events||[]).map(function(e){return {value:[e[0],maxIdx],name:e[1]};}),itemStyle:{color:'#ffd700'},tooltip:{formatter:function(p){return p.name;}}},
    {name:'新歌发行',type:'scatter',symbol:'diamond',symbolSize:14,data:(dashboardData.release_events||[]).map(function(e){return {value:[e[0],maxIdx*0.96],name:e[1]};}),itemStyle:{color:'#ff9f7f'},tooltip:{formatter:function(p){return p.name;}}},
    {name:'演出活动',type:'scatter',symbol:'roundRect',symbolSize:12,data:(dashboardData.performance_events||[]).map(function(e){return {value:[e[0],maxIdx*0.88],name:e[1]};}),itemStyle:{color:'#00ff9d'},tooltip:{formatter:function(p){return p.name;}}}
  ]
});

var listenerChart=echarts.init(document.getElementById('listenerChart'));
var lrData=dashboardData.listener_ratio_trend||[];
var ltData=dashboardData.listener_trend||[];
var listenerLabels=dashboardData.listener_labels&&dashboardData.listener_labels.length>0?dashboardData.listener_labels:labels;
if(lrData.length>0){
  listenerChart.setOption({
    backgroundColor:'transparent',
    tooltip:{trigger:'axis',formatter:function(ps){return ps[0].name+'<br/>热度比例: '+ps[0].value+'%（峰值月=100%）';}},
    grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
    xAxis:{type:'category',data:listenerLabels,axisLine:{lineStyle:{color:'rgba(0,255,157,0.2)'}},axisLabel:{color:'#5a6b8c',fontSize:11}},
    yAxis:{type:'value',name:'%',axisLine:{lineStyle:{color:'rgba(0,255,157,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,255,157,0.04)'}},axisLabel:{color:'#5a6b8c'}},
    series:[
      {name:'收听热度比例',type:'bar',data:lrData,itemStyle:{color:'rgba(0,255,157,0.3)',borderRadius:[4,4,0,0]},barWidth:'50%',
        markLine:{silent:true,data:[{yAxis:100,name:'峰值月',label:{formatter:'峰值月 100%'}}],lineStyle:{color:'rgba(0,255,157,0.5)',type:'dashed'}}},
      {name:'热度趋势',type:'line',smooth:true,data:lrData,symbol:'circle',symbolSize:6,
        lineStyle:{color:'#00ff9d',width:2.5},itemStyle:{color:'#00ff9d',borderColor:'#000',borderWidth:2},
        areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,255,157,0.15)'},{offset:1,color:'rgba(0,255,157,0)'}])}}
    ]
  });
}

var linesChart=echarts.init(document.getElementById('linesChart'));
var tl=dashboardData.top_lines||{names:[],series:[]};
var palette=['#00d2ff','#00ff9d','#ffd700','#ff9f7f','#b78cff','#ff6b9d','#4ECDC4','#96CEB4','#e0e0e0','#7fb3ff'];
function normSeries(arr){
  var base=null;
  for(var i=0;i<arr.length;i++){if(arr[i]!=null){base=arr[i];break;}}
  if(base==null||base===0)return arr;
  return arr.map(function(v){return v==null?null:Math.round(v/base*1000)/10;});
}
function linesOption(normalized){
  return {
    backgroundColor:'transparent',
    tooltip:{trigger:'axis'},
    legend:{data:tl.names,textStyle:{color:'#5a6b8c',fontSize:11},type:'scroll'},
    grid:{left:'3%',right:'4%',bottom:'8%',containLabel:true},
    xAxis:{type:'category',data:labels,axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#5a6b8c',fontSize:11}},
    yAxis:{type:'value',name:normalized?'相对指数':'指数',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
    series:tl.names.map(function(n,i){
      return {name:n,type:'line',smooth:true,symbol:'none',connectNulls:true,
        data:normalized?normSeries(tl.series[i]):tl.series[i],
        lineStyle:{width:2,color:palette[i%palette.length]},itemStyle:{color:palette[i%palette.length]}};
    })
  };
}
linesChart.setOption(linesOption(true));
document.getElementById('btnRaw').addEventListener('click',function(){
  this.classList.add('active');document.getElementById('btnNorm').classList.remove('active');
  linesChart.setOption(linesOption(false),true);
});
document.getElementById('btnNorm').addEventListener('click',function(){
  this.classList.add('active');document.getElementById('btnRaw').classList.remove('active');
  linesChart.setOption(linesOption(true),true);
});

// ===== 单曲详情对比 =====
var detailSongs=dashboardData.detail_songs||[];
var selA=document.getElementById('selSongA'), selB=document.getElementById('selSongB');
detailSongs.forEach(function(s,i){
  var o1=document.createElement('option');o1.value=i;o1.textContent=s.name;selA.appendChild(o1);
  var o2=document.createElement('option');o2.value=i;o2.textContent=s.name;selB.appendChild(o2);
});
var oB0=document.createElement('option');oB0.value='-1';oB0.textContent='（不对比）';selB.insertBefore(oB0,selB.firstChild);selB.value='-1';
if(detailSongs.length>1){selA.value='0';}
var detailChart=echarts.init(document.getElementById('detailChart'));
function renderDetail(){
  var ia=parseInt(selA.value), ib=parseInt(selB.value);
  var series=[], names=[], strip=document.getElementById('statsStrip');
  strip.innerHTML='';
  [ia,ib].forEach(function(idx,k){
    if(idx<0||!detailSongs[idx])return;
    var s=detailSongs[idx];
    names.push(s.name);
    series.push({name:s.name,type:'line',smooth:true,symbol:'none',connectNulls:true,
      data:s.points.map(function(p){return [p[0],p[1]];}),
      lineStyle:{width:2.5,color:palette[k]},itemStyle:{color:palette[k]},
      areaStyle:k===0?{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,210,255,0.12)'},{offset:1,color:'rgba(0,210,255,0)'}])}:undefined});
    strip.innerHTML+='<div class="stat-chip">'+s.name+' | 最新<b>'+s.latest+'</b> 30日均值<b>'+s.mean30+'</b> 峰值<b>'+s.peak+'</b> 发行<b>'+(s.release||'-')+'</b> '+s.attr+'</div>';
  });
  detailChart.setOption({
    backgroundColor:'transparent',
    tooltip:{trigger:'axis'},
    legend:{data:names,textStyle:{color:'#5a6b8c'}},
    grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
    xAxis:{type:'time',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#5a6b8c',fontSize:11}},
    yAxis:{type:'value',name:'指数',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
    series:series
  },true);
}
selA.addEventListener('change',renderDetail);
selB.addEventListener('change',renderDetail);
if(detailSongs.length>0)renderDetail();

var catChart=echarts.init(document.getElementById('catChart'));
var cl=dashboardData.cat_lines||{names:[],series:[]};
var catColors={'专辑':'#00d2ff','OST/单曲':'#ffd700','其他追踪':'#5a6b8c'};
catChart.setOption({
  backgroundColor:'transparent',
  tooltip:{trigger:'axis'},
  legend:{data:cl.names,textStyle:{color:'#5a6b8c'}},
  grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
  xAxis:{type:'category',data:labels,axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#5a6b8c',fontSize:11}},
  yAxis:{type:'value',name:'平均指数',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  series:cl.names.map(function(n,i){
    return {name:n,type:'line',smooth:true,symbol:'circle',symbolSize:6,connectNulls:true,data:cl.series[i],
      lineStyle:{width:3,color:catColors[n]||palette[i%palette.length]},
      itemStyle:{color:catColors[n]||palette[i%palette.length]},
      areaStyle:n==='专辑'?{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,210,255,0.15)'},{offset:1,color:'rgba(0,210,255,0)'}])}:undefined};
  })
});

var tourFxChart=echarts.init(document.getElementById('tourFxChart'));
var tf=dashboardData.tour_fx||[];
tourFxChart.setOption({
  backgroundColor:'transparent',
  tooltip:{trigger:'axis',formatter:function(ps){var p=ps[0];return p.name+'<br/>带动效应: '+(p.value>0?'+':'')+p.value+'%';}},
  grid:{left:'3%',right:'8%',bottom:'3%',containLabel:true},
  xAxis:{type:'value',name:'涨幅%',nameTextStyle:{color:'#5a6b8c'},axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  yAxis:{type:'category',data:tf.map(function(e){return e.label;}).reverse(),axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#8896b3',fontSize:11}},
  series:[{type:'bar',barWidth:'55%',data:tf.map(function(e){return {value:e.uplift,itemStyle:{color:e.uplift>=0?'#00ff9d':'#ff5e62',borderRadius:[0,6,6,0]}};}).reverse(),
    label:{show:true,position:'right',color:'#fff',fontSize:11,formatter:function(p){return (p.value>0?'+':'')+p.value+'%';}}}]
});

var releaseFxChart=echarts.init(document.getElementById('releaseFxChart'));
var rf=dashboardData.release_fx||[];
releaseFxChart.setOption({
  backgroundColor:'transparent',
  tooltip:{trigger:'axis'},
  legend:{data:['14日均值','14日峰值'],textStyle:{color:'#5a6b8c'}},
  grid:{left:'3%',right:'8%',bottom:'3%',containLabel:true},
  xAxis:{type:'value',name:'指数',nameTextStyle:{color:'#5a6b8c'},axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  yAxis:{type:'category',data:rf.map(function(e){return e.label;}).reverse(),axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#8896b3',fontSize:11}},
  series:[
    {name:'14日均值',type:'bar',barWidth:'35%',data:rf.map(function(e){return e.avg;}).reverse(),itemStyle:{color:'#00d2ff',borderRadius:[0,6,6,0]}},
    {name:'14日峰值',type:'bar',barWidth:'35%',data:rf.map(function(e){return e.peak;}).reverse(),itemStyle:{color:'rgba(255,215,0,0.7)',borderRadius:[0,6,6,0]}}
  ]
});

var matrixChart=echarts.init(document.getElementById('matrixChart'));
var mp=dashboardData.matrix_points||[];
var attrColor={'专辑':'#00d2ff','OST/单曲':'#ffd700','其他追踪':'#8896b3'};
// 今日收听态势 Top5 映射（歌名->份额），用于热力矩阵高亮当前活跃歌曲
var todayTop={};
(dashboardData.daily_listen_trend||[]).forEach(function(d,i){todayTop[d.song]={rank:i+1,share:d.share_pct};});
var mpByAttr={};
mp.forEach(function(p){(mpByAttr[p[4]]=mpByAttr[p[4]]||[]).push(p);});
matrixChart.setOption({
  backgroundColor:'transparent',
  tooltip:{formatter:function(p){var t=todayTop[p.data[3]]||null;return '<b>'+p.data[3]+'</b><br/>平均指数: '+p.data[0]+'<br/>波动率: '+p.data[1]+'%<br/>近期指数: '+p.data[2]+(t?'<br/><span style="color:#ffd700">今日收听 Top'+t.rank+' · 份额 '+t.share+'%</span>':'');}},
  legend:{data:Object.keys(mpByAttr),textStyle:{color:'#5a6b8c'}},
  grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
  xAxis:{type:'log',name:'平均指数(对数)',nameTextStyle:{color:'#5a6b8c'},axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  yAxis:{type:'value',name:'波动率%',nameTextStyle:{color:'#5a6b8c'},axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  series:Object.keys(mpByAttr).map(function(a){
    return {name:a,type:'scatter',
      data:mpByAttr[a].map(function(p){return [Math.max(p[0],1),p[1],p[2],p[3]];}),
      // 气泡大小改用对数刻度，避免高体量老歌独占视觉；今日活跃歌曲放大 1.6 倍 + 金色描边 + 歌名标签
      symbolSize:function(d){var base=Math.max(6,Math.min(24,Math.log10(Math.max(d[0],1))*7));return todayTop[d[3]]?base*1.6:base;},
      itemStyle:{color:attrColor[a],opacity:0.75,borderColor:function(params){return todayTop[params.data[3]]?'#ffd700':'transparent';},borderWidth:2},
      label:{show:true,formatter:function(params){return todayTop[params.data[3]]?params.data[3]:'';},color:'#ffd700',fontSize:11,position:'right'},
      emphasis:{focus:'series'}};
  })
});

var weekChart=echarts.init(document.getElementById('weekChart'));
var ww=dashboardData.weekend_workday||[0,0];
weekChart.setOption({
  backgroundColor:'transparent',
  tooltip:{trigger:'axis'},
  grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
  xAxis:{type:'category',data:['周末均值','工作日均值'],axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#8896b3'}},
  yAxis:{type:'value',name:'平均指数',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  series:[{type:'bar',barWidth:'45%',data:[
    {value:ww[0],itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#00d2ff'},{offset:1,color:'#3a7bd5'}]),borderRadius:[6,6,0,0]}},
    {value:ww[1],itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#00ff9d'},{offset:1,color:'#0e9f6e'}]),borderRadius:[6,6,0,0]}}
  ],label:{show:true,position:'top',color:'#fff'}}]
});

var attrChart=echarts.init(document.getElementById('attrChart'));
var at=dashboardData.attr_stats||{labels:[],counts:[],tracked:[]};
attrChart.setOption({
  backgroundColor:'transparent',
  tooltip:{trigger:'axis'},
  legend:{data:['信息表收录','已被追踪'],textStyle:{color:'#5a6b8c'}},
  grid:{left:'3%',right:'4%',bottom:'3%',containLabel:true},
  xAxis:{type:'category',data:at.labels,axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},axisLabel:{color:'#8896b3'}},
  yAxis:{type:'value',name:'数量',axisLine:{lineStyle:{color:'rgba(0,210,255,0.2)'}},splitLine:{lineStyle:{color:'rgba(0,210,255,0.04)'}},axisLabel:{color:'#5a6b8c'}},
  series:[
    {name:'信息表收录',type:'bar',data:at.counts,itemStyle:{color:'rgba(58,123,213,0.7)',borderRadius:[6,6,0,0]},barWidth:'30%'},
    {name:'已被追踪',type:'bar',data:at.tracked,itemStyle:{color:'rgba(0,210,255,0.8)',borderRadius:[6,6,0,0]},barWidth:'30%',label:{show:true,position:'top',color:'#00d2ff'}}
  ]
});

// ===== 历史收听对比图表 =====
var histTrends = dashboardData.hist_trends || {};
var uidNameMap = dashboardData.hist_uid_names || {};
function uidToName(uid) {
  var name = uidNameMap[uid] || '';
  // fallback: 如果映射中没有，尝试去掉前缀
  if (!name) name = (uid||'').replace(/^[MN]:/, '');
  // 缩短过长歌名（去掉(Live)等后缀）
  return name.replace(/\(Live\)/g,'').replace(/\(live\)/g,'').replace(/\(伴奏\)/g,'').trim();
}
var histPalette = ['#00d2ff','#00ff9d','#ffd700','#ff9f7f','#b78cff','#ff6b9d','#4ECDC4','#96CEB4','#e0e0e0','#7fb3ff'];

// 计算每个uid的收听峰值，找出TOP10
var histPeaks = [];
Object.keys(histTrends).forEach(function(uid) {
  var raw = histTrends[uid].raw || [];
  if (raw.length > 0) {
    histPeaks.push({uid: uid, peak: Math.max.apply(null, raw)});
  }
});
histPeaks.sort(function(a,b){return b.peak - a.peak;});
var top10Uids = histPeaks.slice(0, 10).map(function(d){return d.uid;});

// 填充下拉框
var histSelect = document.getElementById('histSongSelect');
if (histSelect && top10Uids.length > 0) {
  top10Uids.forEach(function(uid, i) {
    var name = uidToName(uid);
    var opt = document.createElement('option');
    opt.value = uid;
    opt.textContent = (i+1) + '. ' + name;
    histSelect.appendChild(opt);
  });
}

function renderHistTrendChart(uids) {
  var allLabels = [];
  uids.forEach(function(uid) {
    if (histTrends[uid] && histTrends[uid].labels) {
      histTrends[uid].labels.forEach(function(l) {
        if (allLabels.indexOf(l) === -1) allLabels.push(l);
      });
    }
  });
  allLabels.sort();
  
  var series = uids.map(function(uid, i) {
    var ht = histTrends[uid];
    var name = uidToName(uid);
    if (!ht) return {name: name, type: 'line', data: [], lineStyle: {width: 2}};
    var data = allLabels.map(function(l) {
      var idx = ht.labels.indexOf(l);
      return idx >= 0 ? ht.values[idx] : null;
    });
    return {
      name: name, type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      connectNulls: true, data: data,
      lineStyle: {width: 2, color: histPalette[i % histPalette.length]},
      itemStyle: {color: histPalette[i % histPalette.length]}
    };
  });
  
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(function(s){return s.name;}), textStyle: {color: '#5a6b8c', fontSize: 11}, type: 'scroll', bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: { type: 'category', data: allLabels, axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#5a6b8c', fontSize: 10, rotate: 45 } },
    yAxis: { type: 'value', name: '归一化(首月=100)', axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, splitLine: { lineStyle: {color: 'rgba(0,210,255,0.04)'} }, axisLabel: { color: '#5a6b8c' } },
    series: series
  };
}

var histTrendChart = echarts.init(document.getElementById('histTrendChart'));
if (top10Uids.length > 0) {
  histTrendChart.setOption(renderHistTrendChart(top10Uids));
}

if (histSelect) {
  histSelect.addEventListener('change', function() {
    var val = this.value;
    if (val === 'top10') {
      histTrendChart.setOption(renderHistTrendChart(top10Uids), true);
    } else {
      histTrendChart.setOption(renderHistTrendChart([val]), true);
    }
  });
}

// 当前时代收听趋势
var histCurrentChart = echarts.init(document.getElementById('histCurrentChart'));
var lrData2 = dashboardData.listener_ratio_trend || [];
var listenerLabels2 = dashboardData.listener_labels || [];
if (lrData2.length > 0) {
  var hccLabels = listenerLabels2.length > 0 ? listenerLabels2 : 
    (dashboardData.time_labels ? dashboardData.time_labels.slice(-24) : []);
  histCurrentChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['收听比例趋势(%)'], textStyle: { color: '#5a6b8c' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: hccLabels, axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#5a6b8c', fontSize: 11 } },
    yAxis: { type: 'value', name: '收听比例%', axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, splitLine: { lineStyle: {color: 'rgba(0,210,255,0.04)'} }, axisLabel: { color: '#5a6b8c' } },
    series: [
      { name: '收听比例趋势(%)', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, data: lrData2, lineStyle: { color: '#00d2ff', width: 3 }, itemStyle: { color: '#00d2ff' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,210,255,0.2)'},{offset:1,color:'rgba(0,210,255,0)'}]) } }
    ]
  });
}

// 跨时代排名对比
var crossEraChart = echarts.init(document.getElementById('crossEraChart'));
var crossData = [];
Object.keys(histTrends).forEach(function(uid) {
  var raw = histTrends[uid].raw || [];
  if (raw.length > 0) {
    crossData.push({name: uidToName(uid), peak: Math.max.apply(null, raw), months: raw.length});
  }
});
crossData.sort(function(a,b){return b.peak - a.peak;});
var top20cross = crossData.slice(0, 20);

if (top20cross.length > 0) {
  crossEraChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '10%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', name: '收听峰值', nameTextStyle: {color: '#5a6b8c'}, axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, splitLine: { lineStyle: {color: 'rgba(0,210,255,0.04)'} }, axisLabel: { color: '#5a6b8c' } },
    yAxis: { type: 'category', data: top20cross.map(function(d){return d.name;}).reverse(), axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#8896b3', fontSize: 11, interval: 0, overflow: 'truncate', width: 120 } },
    series: [{
      type: 'bar', barWidth: '60%',
      data: top20cross.map(function(d, i) {
        var colors = ['#00d2ff', '#00ff9d', '#ffd700', '#ff9f7f', '#b78cff'];
        return { value: d.peak, itemStyle: { color: colors[Math.min(i, colors.length-1)], borderRadius: [0, 4, 4, 0] } };
      }).reverse(),
      label: { show: true, position: 'right', color: '#b0c8f0', fontSize: 10, formatter: function(p) { return p.value >= 10000 ? (p.value/10000).toFixed(1)+'w' : p.value; } }
    }]
  });
}

// 高级分析指标
var advDiv = document.getElementById('advancedMetrics');
if (advDiv && crossData.length > 0) {
  var totalPeak = crossData.reduce(function(s,d){return s + d.peak;}, 0);
  var top5Peak = crossData.slice(0, 5).reduce(function(s,d){return s + d.peak;}, 0);
  var cr5 = totalPeak > 0 ? (top5Peak / totalPeak * 100).toFixed(1) : 0;
  
  var hhi = 0;
  crossData.forEach(function(d) {
    var share = totalPeak > 0 ? d.peak / totalPeak * 100 : 0;
    hhi += share * share;
  });
  
  var halfLifeLines = [];
  top10Uids.slice(0, 5).forEach(function(uid, i) {
    var ht = histTrends[uid];
    if (!ht || !ht.raw || ht.raw.length < 3) return;
    var raw = ht.raw;
    var peak = Math.max.apply(null, raw);
    var peakIdx = raw.indexOf(peak);
    var half = peak / 2;
    var hlMonths = -1;
    for (var j = peakIdx + 1; j < raw.length; j++) {
      if (raw[j] <= half) { hlMonths = j - peakIdx; break; }
    }
    var name = uidToName(uid);
    if (hlMonths > 0) halfLifeLines.push('<span style="color:' + histPalette[i] + '">' + name + '</span>: ' + hlMonths + '月');
    else halfLifeLines.push('<span style="color:' + histPalette[i] + '">' + name + '</span>: 未衰减到半值');
  });
  
  advDiv.innerHTML = 
    '<div style="margin-bottom:8px"><b>CR5 头部集中度:</b> ' + cr5 + '% (前5首收听峰值占比)</div>' +
    '<div style="margin-bottom:8px"><b>HHI 指数:</b> ' + hhi.toFixed(0) + ' (>2500=高集中, <1500=分散)</div>' +
    '<div style="margin-bottom:6px"><b>峰值半衰期 (TOP5):</b></div>' +
    halfLifeLines.map(function(l) { return '<div style="margin-left:16px;font-size:12px;line-height:1.6">• ' + l + '</div>'; }).join('') +
    '<div style="margin-top:6px;font-size:11px;color:#5a6b8c">*半衰期 = 达收听峰值后衰减至一半所需月数</div>';
}

// ========== 指令4：高级分析维度图表 ==========

// 1. 生命周期桑基图
var stateColor = { '上升期': '#00ff9d', '稳定期': '#ffd700', '经典沉淀期': '#7b61ff' };
var sankeyChart = echarts.init(document.getElementById('sankeyChart'));
var lcm = dashboardData.lifecycle_migration || {nodes: [], links: []};
if (lcm.nodes.length > 0) {
  sankeyChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: [{
      type: 'sankey', left: '4%', right: '8%', top: '4%', bottom: '4%',
      data: lcm.nodes.map(function(n) {
        var st = n.name.replace('上月·','').replace('本月·','');
        return { name: n.name, itemStyle: { color: stateColor[st] || '#00d2ff' }, label: { color: '#8896b3', fontSize: 11 } };
      }),
      links: lcm.links.map(function(l) {
        var toState = l.target.replace('本月·','');
        return { source: l.source, target: l.target, value: l.value, lineStyle: { color: stateColor[toState] || '#00d2ff', opacity: 0.5 } };
      }),
      label: { color: '#8896b3', fontSize: 11 },
      lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.45 },
      emphasis: { focus: 'adjacency' }
    }]
  });
}
var lifeDiv = document.getElementById('lifecycleSummary');
if (lifeDiv && lcm.nodes.length > 0) {
  var curCounts = {};
  lcm.nodes.forEach(function(n) {
    if (n.name.indexOf('本月') === 0 && n.value) curCounts[n.name.replace('本月·','')] = n.value;
  });
  lifeDiv.innerHTML = ['上升期','稳定期','经典沉淀期'].map(function(s) {
    var c = curCounts[s] || 0;
    var color = stateColor[s];
    return '<div><span class="trend-badge" style="background:' + color + '22;color:' + color + '">' + s + '</span> &nbsp;' + c + ' 首</div>';
  }).join('') + '<div style="margin-top:8px;font-size:11px;color:#5a6b8c">*基于近7日指数斜率分类</div>';
}

// 2. 新歌衰减曲线族
var decayChart = echarts.init(document.getElementById('decayChart'));
var dec = dashboardData.release_decay || {labels: [], series: {}, halflife: {}};
var decayAttrs = Object.keys(dec.series || {});
var decColors = ['#00ff9d', '#00d2ff', '#b78cff'];
var decaySeries = decayAttrs.map(function(attr, i) {
  var hl = dec.halflife[attr];
  return {
    name: attr + (hl ? '（半衰期 D+' + hl + '）' : ''),
    type: 'line', smooth: true, connectNulls: true, symbol: 'none',
    data: dec.series[attr] || [], lineStyle: { width: 3, color: decColors[i % decColors.length] },
    itemStyle: { color: decColors[i % decColors.length] }, areaStyle: { color: 'rgba(0,210,255,0.06)' }
  };
});
if (decaySeries.length > 0) {
  decayChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', formatter: function(ps) {
      var s = ps[0].name + ' 天<br/>';
      ps.forEach(function(p) { s += p.marker + p.seriesName + ': ' + (p.value==null?'-':p.value) + '%<br/>'; });
      return s;
    } },
    legend: { data: decaySeries.map(function(s){return s.name;}), textStyle: { color: '#5a6b8c', fontSize: 11 }, type: 'scroll', bottom: 0 },
    grid: { left: '4%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', data: dec.labels, name: '发行后天数', axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#5a6b8c', fontSize: 10, interval: 14 } },
    yAxis: { type: 'value', name: '相对发行日 %', axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, splitLine: { lineStyle: {color: 'rgba(0,210,255,0.04)'} }, axisLabel: { color: '#5a6b8c' } },
    series: decaySeries.concat([{
      name: '半衰参考线(50%)', type: 'line', symbol: 'none', data: dec.labels.map(function(){ return 50; }),
      lineStyle: { color: '#ff5e62', width: 1, type: 'dashed' }, itemStyle: { color: '#ff5e62' }, silent: true
    }])
  });
}

// 3. 周末溢价热力矩阵：专辑 vs OST/单曲 并排
var prem = dashboardData.weekend_premium || {};
var premMonths = prem.months || [];
var premPalette = ['#ff9f7f', '#ffffff', '#00d2ff'];

function renderPremium(elId, matrix, songNames) {
  var el = document.getElementById(elId);
  if (!matrix || matrix.length === 0 || !songNames || songNames.length === 0) {
    if (el) el.innerHTML = '<div style="color:#5a6b8c;text-align:center;padding-top:120px">数据不足</div>';
    return null;
  }
  var chart = echarts.init(el);
  var data = [];
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[i].length; j++) {
      if (matrix[i][j] !== null && matrix[i][j] !== undefined) data.push([j, i, matrix[i][j]]);
    }
  }
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: function(p) {
      var v = p.value[2];
      var arrow = v > 1.02 ? '<span style="color:#00d2ff">↑ 周末型</span>' : (v < 0.98 ? '<span style="color:#ff9f7f">↓ 通勤型</span>' : '<span style="color:#ffd700">→ 持平</span>');
      return songNames[p.value[1]] + ' · ' + premMonths[p.value[0]] + '<br/>周末/工作日: ' + v + '<br/>' + arrow;
    } },
    grid: { left: '18%', right: '8%', top: '5%', bottom: '16%' },
    xAxis: { type: 'category', data: premMonths, splitArea: { show: true }, axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#5a6b8c', fontSize: 10, rotate: 40 } },
    yAxis: { type: 'category', data: songNames, splitArea: { show: true }, axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#8896b3', fontSize: 10, interval: 0, width: 100, overflow: 'truncate' } },
    visualMap: { min: 0.5, max: 1.5, calculable: false, orient: 'vertical', right: '1%', top: 'center', itemWidth: 10, itemHeight: 90, textStyle: { color: '#5a6b8c' }, inRange: { color: premPalette } },
    series: [{ type: 'heatmap', data: data, label: { show: false }, itemStyle: { borderColor: 'rgba(0,0,0,0.25)', borderWidth: 0.5 }, emphasis: { itemStyle: { borderColor: '#fff', borderWidth: 2, shadowBlur: 8, shadowColor: 'rgba(0,210,255,0.4)' } } }]
  });
  return chart;
}

var albumPremChart = renderPremium('albumPremiumChart', prem.album, prem.album_songs);
var ostPremChart = renderPremium('ostPremiumChart', prem.ost, prem.ost_songs);
var _resizePrem = function(){ if (albumPremChart) albumPremChart.resize(); if (ostPremChart) ostPremChart.resize(); };
window.addEventListener('resize', _resizePrem);

// 4. 老歌复活雷达
var radarSpringChart = echarts.init(document.getElementById('radarSpringChart'));
var ss = dashboardData.second_spring || {names: [], values: [], spring: []};
if (ss.names && ss.names.length > 0) {
  var ssMax = Math.max.apply(null, ss.values) || 200;
  radarSpringChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: function(ps) {
      var i = ps.dataIndex;
      var tag = (ss.spring && ss.spring[i]) ? ' <span style="color:#00ff9d">★ 第二春（巡演/事件带动复活）</span>' : '';
      return ss.names[i] + tag + '<br/>偏离度: ' + ss.values[i] + '%（100% = 自身历史均值）';
    } },
    radar: { indicator: ss.names.map(function(n) { return { name: n, max: Math.max(400, Math.ceil(ssMax/100)*100) }; }),
      radius: '62%', center: ['50%','52%'],
      axisName: { color: '#8896b3', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0,210,255,0.1)' } },
      splitArea: { areaStyle: { color: ['rgba(0,210,255,0.02)','rgba(0,210,255,0.06)'] } },
      axisLine: { lineStyle: { color: 'rgba(0,210,255,0.2)' } } },
    series: [{
      type: 'radar', data: [{ value: ss.values, name: '近期偏离%', symbol: 'circle', symbolSize: 5,
        itemStyle: { color: '#00ff9d' }, lineStyle: { color: '#00ff9d', width: 2 }, areaStyle: { color: 'rgba(0,255,157,0.18)' } }]
    }]
  });
}

// 5. 排名跃迁瀑布
var waterfallChart = echarts.init(document.getElementById('waterfallChart'));
var rw = dashboardData.rank_waterfall || {names: [], changes: [], labels: []};
if (rw.names && rw.names.length > 0) {
  waterfallChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: function(ps) {
      var i = ps[0].dataIndex;
      var c = rw.changes[i];
      var arrow = c > 0 ? '<span style="color:#00ff9d">↑ 上升</span>' : '<span style="color:#ff5e62">↓ 下降</span>';
      return rw.names[i] + '<br/>' + arrow + ' ' + Math.abs(c) + ' 位';
    } },
    grid: { left: '8%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: rw.names, axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, axisLabel: { color: '#8896b3', fontSize: 10, interval: 0, rotate: 30, width: 90, overflow: 'truncate' } },
    yAxis: { type: 'value', name: '排名变化(位)', axisLine: { lineStyle: {color: 'rgba(0,210,255,0.2)'} }, splitLine: { lineStyle: {color: 'rgba(0,210,255,0.04)'} }, axisLabel: { color: '#5a6b8c' } },
    series: [{
      type: 'bar', barWidth: '58%',
      data: rw.changes.map(function(c, i) {
        return { value: c, itemStyle: { color: c > 0 ? '#00ff9d' : '#ff5e62', borderRadius: c > 0 ? [4,4,0,0] : [0,0,4,4] } };
      }),
      label: { show: true, position: 'top', color: '#b0c8f0', fontSize: 10, formatter: function(p) { return (p.value > 0 ? '+' : '') + p.value; } }
    }]
  });
}

// 6. KPI 第4卡：近30日新增追踪数 sparkline
var kpiSparkEl = document.getElementById('kpiSparkline');
if (kpiSparkEl) {
  var ntt = dashboardData.new_track_trend || {labels: [], values: []};
  if (ntt.values && ntt.values.length > 0) {
    var sp = echarts.init(kpiSparkEl);
    sp.setOption({
      backgroundColor: 'transparent',
      grid: { left: 2, right: 2, top: 4, bottom: 2 },
      xAxis: { type: 'category', show: false, data: ntt.labels },
      yAxis: { type: 'value', show: false },
      tooltip: { formatter: function(ps) { return ps[0].name + '<br/>新增: ' + ps[0].value + ' 首'; } },
      series: [{ type: 'line', smooth: true, symbol: 'none', data: ntt.values, lineStyle: { color: '#00d2ff', width: 1.5 }, areaStyle: { color: 'rgba(0,210,255,0.15)' } }]
    });
    window.addEventListener('resize', function(){ sp.resize(); });
  }
}

// 7. 月度竞争格局时间轴（timeline 播放）
var tlData = dashboardData.timeline_narrative || [];
if (tlData.length > 0) {
  var timelineChart = echarts.init(document.getElementById('timelineChart'));
  var tlMonths = tlData.map(function(f){ return f.month; });
  var lcColor = { '上升期': '#00ff9d', '稳定期': '#ffd700', '经典沉淀期': '#7b61ff' };
  var tlOptions = tlData.map(function(frame){
    var pts = (frame.points || []).map(function(p){
      return { name: p.name, value: p.value, itemStyle: { color: lcColor[p.value[3]] || '#00d2ff' } };
    });
    return {
      title: { text: frame.month + (frame.event_str ? '  |  ' + frame.event_str : ''), textStyle: { color: '#5a6b8c', fontSize: 13, fontWeight: 'normal' } },
      series: [{ data: pts }]
    };
  });
  timelineChart.setOption({
    baseOption: {
      backgroundColor: 'transparent',
      timeline: {
        axisType: 'category', data: tlMonths, playInterval: 1200, autoPlay: true, symbolSize: 10,
        lineStyle: { color: 'rgba(0,210,255,0.3)' }, itemStyle: { color: '#00d2ff' },
        checkpointStyle: { color: '#00d2ff', borderColor: '#fff', borderWidth: 1 },
        controlStyle: { showNextBtn: true, showPrevBtn: true, itemSize: 18, color: '#00d2ff', borderColor: '#00d2ff' },
        label: { color: '#5a6b8c', fontSize: 11 }, emphasis: { label: { color: '#fff' } }
      },
      tooltip: {
        trigger: 'item',
        formatter: function(p){
          function abbr(v){ var av = Math.abs(v); if (av >= 1e8) return (v/1e8).toFixed(1)+'亿'; if (av >= 1e4) return (v/1e4).toFixed(1)+'万'; return v; }
          return '<b>' + p.name + '</b><br/>排名变化速度: ' + abbr(p.value[0]) + ' 位/月<br/>当月份额: ' + p.value[1] + '%<br/>相对自身峰值: ' + p.value[2] + '%<br/>状态: ' + (lcColor[p.value[3]] ? '<span style="color:' + lcColor[p.value[3]] + '">' + p.value[3] + '</span>' : p.value[3]);
        }
      },
      grid: { left: '8%', right: '12%', top: '18%', bottom: '12%', containLabel: true },
      xAxis: { type: 'value', scale: true, name: '排名变化速度（位/月）', nameTextStyle: { color: '#5a6b8c' }, axisLine: { lineStyle: { color: 'rgba(0,210,255,0.2)' } }, splitLine: { lineStyle: { color: 'rgba(0,210,255,0.04)' } }, axisLabel: { color: '#5a6b8c', formatter: function(v){ if (v >= 1e8) return (v/1e8).toFixed(1)+'亿'; if (v >= 1e4) return (v/1e4).toFixed(0)+'万'; return v; } } },
      yAxis: { type: 'value', name: '当月份额（%）', nameTextStyle: { color: '#5a6b8c' }, axisLine: { lineStyle: { color: 'rgba(0,210,255,0.2)' } }, splitLine: { lineStyle: { color: 'rgba(0,210,255,0.04)' } }, axisLabel: { color: '#5a6b8c' } },
      series: [{
        type: 'scatter',
        symbolSize: function(v){ return Math.max(8, Math.min(60, v[2] / 3)); },
        itemStyle: { opacity: 0.75, borderColor: '#fff', borderWidth: 1 },
        emphasis: {
          itemStyle: { opacity: 1, borderWidth: 2, shadowBlur: 10, shadowColor: 'rgba(0,210,255,0.5)' },
          label: { show: true, formatter: '{b}', color: '#fff', fontSize: 12 }
        }
      }]
    },
    options: tlOptions
  });
  window.addEventListener('resize', function(){ timelineChart.resize(); });
}

window.addEventListener('resize',function(){
  trendChart.resize();listenerChart.resize();linesChart.resize();detailChart.resize();catChart.resize();matrixChart.resize();weekChart.resize();attrChart.resize();tourFxChart.resize();releaseFxChart.resize();
  histTrendChart.resize();histCurrentChart.resize();crossEraChart.resize();
  sankeyChart.resize();decayChart.resize();radarSpringChart.resize();waterfallChart.resize();
});
}

if(typeof echarts!=="undefined"){main();}
else{
  document.addEventListener("echarts-ready",main);
  document.addEventListener("echarts-fail",function(){
    document.querySelectorAll(".chart-container").forEach(function(el){
      el.innerHTML='<div style="color:#5a6b8c;text-align:center;padding-top:120px">图表库加载失败，请检查网络后刷新（或将 echarts.min.js 放到脚本同目录重新生成）</div>';
    });
  });
}
</script>
<script src="search_engine.js"></script>
</body>
</html>
"""

# ============================================================
# 第三部分B：数据组装与网页生成
# ============================================================
def build_dashboard_payload(df_all, df_stats, dims, song_info, registry_info, hist_trends=None, hist_uid_names=None, setlists=None):
    """把全量数据组装成大屏 JSON（供生成网页使用，也可独立调用）"""
    now = datetime.now()
    total_records = len(df_all)
    success_records = int(df_all["current_index"].notna().sum()) if "current_index" in df_all.columns else 0
    active_songs = int(df_all[df_all["listeners"].notna() & (df_all["listeners"] > 0)]["uid"].nunique()) if "listeners" in df_all.columns else 0
    total_songs = int(df_all["uid"].nunique())
    link_uids = int(df_all[df_all["uid"].str.startswith("L:")]["uid"].nunique())
    name_uids = total_songs - link_uids
    complete_rate = round(success_records / total_records * 100, 1) if total_records > 0 else 0
    active_rate = round(active_songs / total_songs * 100, 1) if total_songs > 0 else 0

    df_all = df_all.copy()
    df_all["year_month"] = df_all["data_date"].dt.to_period("M")
    monthly = df_all.groupby("year_month").agg({"current_index": "mean", "uid": "nunique"}).reset_index()
    time_labels = [str(x) for x in monthly["year_month"]]
    label_set = set(time_labels)

    # 收听热度比例趋势：每月收听人数总和 / 追踪歌曲数 = 月均收听热度，归一化至峰值月 = 100%
    # 数据源仅来自三个指定目录（分年指数数据 / download / 指数vs），同歌同日取最大值
    listener_trend = []
    listener_ratio_trend = []
    listener_labels = []
    if "peak_listeners" in df_all.columns and df_all["peak_listeners"].notna().any():
        ls_monthly = df_all.groupby("year_month").agg({"peak_listeners": "sum", "uid": "nunique"}).reset_index()
        ls_monthly = ls_monthly.set_index("year_month").reindex([pd.Period(x, freq="M") for x in time_labels])
        ls_monthly["avg_listeners"] = ls_monthly["peak_listeners"] / ls_monthly["uid"].where(ls_monthly["uid"] > 0, np.nan)
        ls_max = ls_monthly["avg_listeners"].max()
        listener_avg_raw = [None if pd.isna(v) else round(float(v), 0) for v in ls_monthly["avg_listeners"]]
        listener_labels = time_labels[:]
        if ls_max and ls_max > 0:
            listener_ratio_trend = [None if pd.isna(v) else round(float(v) / ls_max * 100, 1) for v in ls_monthly["avg_listeners"]]
            listener_trend = listener_avg_raw
            # 超过24个月时只展示最近24个月，避免图表过于拥挤
            valid_count = len([x for x in listener_ratio_trend if x is not None])
            if valid_count > 24:
                start_valid = next(i for i, v in enumerate(listener_ratio_trend) if v is not None)
                tail_start = max(start_valid, len(listener_ratio_trend) - 24)
                listener_ratio_trend = listener_ratio_trend[tail_start:]
                listener_trend = listener_trend[tail_start:]
                listener_labels = time_labels[tail_start:]
            logger.info(f"收听热度趋势：{len([x for x in listener_ratio_trend if x is not None])} 个有效月份（展示最近{len(listener_labels)}个月），已归一化为比例趋势")

    # 异常活跃（近30日口径，完整歌名）
    top_trend = df_stats[df_stats["anomaly_score"] >= 20].head(10) if not df_stats.empty else pd.DataFrame()
    top_songs = []
    for _, row in top_trend.iterrows():
        top_songs.append({"name": row["song_name"], "trend": row["trend"], "score": int(row["anomaly_score"]), "tag": row["tag"]})

    # 歌曲信息表元数据（发行日期/属性）
    name2meta = song_info.get("name2meta", {})

    # TOP 歌曲走势（按近 30 天平均指数取前 10，反映近期热度）
    # 过滤：近30日【有效指数读数】< 5 天的歌曲不参与（按行数过滤无效——很多歌每日有行但 index 为 NaN，
    #   如「住口」29 行仅 1 个有效值 803，会以单点排到第 2，失真）
    top_lines = {"names": [], "series": []}
    max_date = df_all["data_date"].max()
    recent = df_all[df_all["data_date"] >= max_date - pd.Timedelta(days=30)]
    recent_idx = recent.dropna(subset=["current_index"])
    recent_cnt = recent_idx.groupby("uid").size()
    recent_mean = recent_idx.groupby("uid")["current_index"].mean().dropna()
    recent_mean = recent_mean[recent_cnt.reindex(recent_mean.index).fillna(0) >= 5]
    recent_mean = recent_mean.sort_values(ascending=False)
    top10_uids = list(recent_mean.head(10).index)
    if top10_uids:
        uid2disp = df_all.groupby("uid")["display_name"].last().to_dict()
        sub = df_all[df_all["uid"].isin(top10_uids)]
        pv = sub.groupby(["year_month", "uid"])["current_index"].mean().unstack()
        pv = pv.reindex([pd.Period(x, freq="M") for x in time_labels])
        seen_names = {}
        for u in top10_uids:
            if u in pv.columns:
                disp = str(uid2disp.get(u, u))
                # 同名不同版本（live/棚录）在图例中区分
                seen_names[disp] = seen_names.get(disp, 0) + 1
                if seen_names[disp] > 1:
                    disp = f"{disp}（版本{seen_names[disp]}）"
                top_lines["names"].append(disp)
                top_lines["series"].append([None if pd.isna(v) else round(float(v), 0) for v in pv[u]])

    # uid -> 属性 / 展示名（供多个模块使用）
    uid2disp = df_all.groupby("uid")["display_name"].last().to_dict()
    uid2attr = {}
    for u, disp in uid2disp.items():
        meta = name2meta.get(norm_name(disp))
        uid2attr[u] = meta["attr"] if meta else "其他追踪"

    # 作品属性走势对比（专辑 / OST&单曲 / 其他追踪 的月度平均指数）
    cat_lines = {"names": [], "series": []}
    if name2meta:
        df_cat = df_all.copy()
        df_cat["attr"] = df_cat["uid"].map(uid2attr)
        # 归并属性类别，避免过碎
        df_cat["attr"] = df_cat["attr"].apply(lambda a: a if a in ("专辑", "OST/单曲") else "其他追踪")
        pv2 = df_cat.groupby(["year_month", "attr"])["current_index"].mean().unstack()
        pv2 = pv2.reindex([pd.Period(x, freq="M") for x in time_labels])
        for a in ["专辑", "OST/单曲", "其他追踪"]:
            if a in pv2.columns:
                cat_lines["names"].append(a)
                cat_lines["series"].append([None if pd.isna(v) else round(float(v), 0) for v in pv2[a]])

    # 综合表现 TOP10：按 专辑 / OST·单曲 / 其他追踪 分组排名
    rank_groups = {"专辑": [], "OST/单曲": [], "其他追踪": []}
    if not dims.empty:
        dims2 = dims.copy()
        dims2["attr"] = dims2["uid"].map(uid2attr).fillna("其他追踪")
        dims2["attr"] = dims2["attr"].apply(lambda a: a if a in rank_groups else "其他追踪")
        for attr, grp in dims2.groupby("attr"):
            for _, r in grp.sort_values("score", ascending=False).head(10).iterrows():
                meta = name2meta.get(norm_name(r["song_name"]), {})
                rank_groups[attr].append([None, r["song_name"], r["score"], r["volatility"], r["max_streak"],
                                          r["lifecycle"], meta.get("date", "-"), meta.get("attr", "-")])

    # 热度-稳定性矩阵：X=平均指数(体量) Y=波动率(风险) 点大小=近期水平 颜色=属性
    matrix_points = []
    if not dims.empty:
        for _, r in dims.iterrows():
            a = uid2attr.get(r["uid"], "其他追踪")
            a = a if a in ("专辑", "OST/单曲") else "其他追踪"
            matrix_points.append([round(float(r["mean_index"]), 0), r["volatility"],
                                  round(float(r["latest_index"]), 0), r["song_name"], a])

    # 单曲详情对比候选集：近30日前40 + 综合得分前15（去重，上限60）
    cand_uids = list(recent_mean.head(40).index)
    if not dims.empty:
        extra = dims.sort_values("score", ascending=False).head(15)["uid"].tolist()
        cand_uids = list(dict.fromkeys(cand_uids + extra))[:60]
    detail_songs = []
    seen_disp = {}
    for u in cand_uids:
        g = df_all[df_all["uid"] == u].sort_values("data_date")
        idx = g["current_index"].dropna()
        if len(idx) < 5:
            continue
        disp = str(uid2disp.get(u, u))
        seen_disp[disp] = seen_disp.get(disp, 0) + 1
        if seen_disp[disp] > 1:
            disp = f"{disp}（版本{seen_disp[disp]}）"
        meta = name2meta.get(norm_name(uid2disp.get(u, u)), {})
        r_idx = recent[recent["uid"] == u]["current_index"].dropna()
        detail_songs.append({
            "uid": u, "name": disp,
            "attr": uid2attr.get(u, "其他追踪"),
            "release": meta.get("date", "-"),
            "latest": round(float(idx.iloc[-1]), 0),
            "mean30": round(float(r_idx.mean()), 0) if len(r_idx) > 0 else 0,
            "peak": round(float(idx.max()), 0),
            "points": [[d.strftime("%Y-%m-%d"), round(float(v), 0)]
                       for d, v in zip(g["data_date"], g["current_index"]) if pd.notna(v)],
        })

    # 全量歌曲档案索引（数据知识库搜索）：覆盖全部追踪 uid，含迷你趋势点（降采样≤48点）
    song_index = []
    dims_meta = {}
    if not dims.empty:
        for _, r in dims.iterrows():
            dims_meta[r["uid"]] = r
    seen_si = {}
    for u in uid2disp:
        g = df_all[df_all["uid"] == u].sort_values("data_date")
        idx = g["current_index"].dropna()
        disp = str(uid2disp.get(u, u))
        seen_si[disp] = seen_si.get(disp, 0) + 1
        if seen_si[disp] > 1:
            disp = f"{disp}（版本{seen_si[disp]}）"
        meta = name2meta.get(norm_name(uid2disp.get(u, u)), {})
        r_idx = recent[recent["uid"] == u]["current_index"].dropna()
        dr = dims_meta.get(u)
        # 档案扩展字段（全部来自真实计算，前端 search_engine.js 的 profile 区渲染）：
        # best_rank=历史最佳全站排名（数值越小越靠前）；active_days=有效指数记录天数；
        # profile=中文标签键值对（近90日均值/中位指数/周末溢价/上涨日占比/波动率）
        _rk = pd.to_numeric(g["current_rank"], errors="coerce").dropna() if "current_rank" in g.columns else pd.Series(dtype=float)
        best_rank = int(_rk.min()) if len(_rk) else None
        active_days = int(len(idx))
        _profile = []
        if dr is not None:
            _avg90 = int(round(float(dr["mean_index"]))) if pd.notna(dr["mean_index"]) else None
            _med = int(round(float(dr["median_index"]))) if pd.notna(dr["median_index"]) else None
            _wk = float(dr["weekend_avg"]) if pd.notna(dr["weekend_avg"]) else 0.0
            _wd = float(dr["workday_avg"]) if pd.notna(dr["workday_avg"]) else 0.0
            _prem = round(_wk / _wd, 2) if _wd > 0 else None
            _up = round(float(dr["up_ratio"]), 1) if pd.notna(dr["up_ratio"]) else None
            _vol = round(float(dr["volatility"]), 1) if pd.notna(dr["volatility"]) else None
            if _avg90 is not None: _profile.append({"k": "近90日均值", "v": f"{_avg90:,}"})
            if _med is not None: _profile.append({"k": "中位指数", "v": f"{_med:,}"})
            if _prem is not None: _profile.append({"k": "周末溢价", "v": f"{_prem:.2f}"})
            if _up is not None: _profile.append({"k": "上涨日占比", "v": f"{_up:.1f}%"})
            if _vol is not None: _profile.append({"k": "波动率", "v": f"{_vol:.1f}%"})
        if best_rank is not None:
            _profile.insert(0, {"k": "历史最佳排名", "v": f"第 {best_rank:,} 位"})
        _profile.append({"k": "有效记录天数", "v": f"{active_days} 天"})
        rec = {
            "uid": u, "name": disp,
            "attr": uid2attr.get(u, "其他追踪"),
            "release": meta.get("date", "-"),
            "latest": round(float(idx.iloc[-1]), 0) if len(idx) else 0,
            "mean30": round(float(r_idx.mean()), 0) if len(r_idx) > 0 else 0,
            "peak": round(float(idx.max()), 0) if len(idx) else 0,
            "lifecycle": str(dr["lifecycle"]) if dr is not None else "",
            "score": round(float(dr["score"]), 1) if dr is not None else "",
            "streak": int(dr["max_streak"]) if dr is not None else "",
            "points": [],
            "best_rank": best_rank,
            "active_days": active_days,
            "profile": _profile,
        }
        pts = [[d.strftime("%Y-%m-%d"), round(float(v), 0)]
               for d, v in zip(g["data_date"], g["current_index"]) if pd.notna(v)]
        if len(pts) >= 5:
            if len(pts) <= 48:
                rec["points"] = pts
            else:
                stride = len(pts) / 48.0
                rec["points"] = [pts[int(i * stride)] for i in range(48)]
                if pts[-1] not in rec["points"]:
                    rec["points"].append(pts[-1])
        song_index.append(rec)
    logger.info(f"知识库档案索引: {len(song_index)} 首歌曲")

    weekend_avg = round(float(dims["weekend_avg"].mean()), 0) if not dims.empty else 0
    workday_avg = round(float(dims["workday_avg"].mean()), 0) if not dims.empty else 0

    # 事件效应量化
    tour_fx = tour_uplift(df_all, song_info.get("tour_events", []))
    release_fx = release_performance(df_all, song_info.get("release_events", []))
    # 场次后歌曲级效应（长表为唯一输入：直接效应=歌单内，辐射带动=歌单外）
    tour_song_fx = tour_song_effects(df_all, setlists) if setlists else []

    # 事件标记：映射到月份标签
    def to_month(ev_date):
        return ev_date[:7]

    tour_events = [[to_month(e["date"]), f"{e['date']} {e['desc']} {e['name']}站"]
                   for e in song_info.get("tour_events", []) if to_month(e["date"]) in label_set]
    release_events = [[to_month(e["date"]), f"{e['date']} 《{e['name']}》发行（{e['kind']}）"]
                      for e in song_info.get("release_events", []) if to_month(e["date"]) in label_set]
    # 演出活动节点：desc=演出名，name=scene(演出名·城市)，仅取城市部分避免演出名重复
    performance_events = [[to_month(e["date"]), f"{e['date']} {e['desc']}·{_city_of(e['name'])}"]
                          for e in song_info.get("performance_events", []) if to_month(e["date"]) in label_set]

    # 属性维度：信息表收录数 vs 被追踪数
    tracked_norms = set(df_all["display_name"].map(norm_name).unique())
    attr_bucket = {}
    for row in song_info.get("attr_rows", []):
        a = row["attr"]
        if a not in attr_bucket:
            attr_bucket[a] = {"count": 0, "tracked": 0}
        attr_bucket[a]["count"] += 1
        if norm_name(row["name"]) in tracked_norms:
            attr_bucket[a]["tracked"] += 1
    matched_in_info = sum(1 for n in tracked_norms if n in name2meta)
    attr_labels = list(attr_bucket.keys()) + ["其他追踪歌曲"]
    attr_counts = [attr_bucket[a]["count"] for a in attr_bucket] + [0]
    attr_tracked = [attr_bucket[a]["tracked"] for a in attr_bucket] + [len(tracked_norms) - matched_in_info]

    date_range = f"{df_all['data_date'].min().strftime('%Y-%m-%d')} ~ {df_all['data_date'].max().strftime('%Y-%m-%d')}"
    batch_count = int(df_all["data_date"].nunique())
    tracked_links = len(registry_info.get("mid2name", {}))

    # 指令4：高级分析维度（全部以比率/偏离度/趋势表达，无新绝对数值）
    lifecycle_migration = compute_lifecycle_migration(df_all)
    release_decay = compute_release_decay(df_all, song_info)
    weekend_premium = compute_weekend_premium(df_all, song_info, max_months=6)  # 近6个月窗口：让周末溢价反映近期收听习惯
    second_spring = compute_second_spring(df_all, days=30, song_info=song_info)
    rank_waterfall = compute_rank_waterfall(df_all)
    timeline_narrative = compute_timeline_narrative(df_all, song_info)
    daily_listen = compute_daily_listen(df_all, total_songs)
    daily_fresh = compute_daily_freshness(df_all)

    # 指令4：AI 可读摘要（动态数值，不写死——避免 1.33/38个月 这类数字随数据更新失真）
    chart_summaries = {}
    _lm_links = lifecycle_migration.get("links", []) or []
    _flow_total = sum(int(l.get("value", 0)) for l in _lm_links)
    _settle_in = sum(int(l.get("value", 0)) for l in _lm_links if "经典沉淀期" in str(l.get("target", "")))
    chart_summaries["sankey"] = (
        f"作品成长生态流转分析（近60日窗口）：{_flow_total} 首作品在上升期、稳定期、经典沉淀期之间健康流转，"
        f"其中 {_settle_in} 首沉淀为经典，经典沉淀期占比最高，说明作品具有长尾生命力，无衰退迹象。"
    )
    _ap = {a.get("attr"): a.get("ratio") for a in weekend_premium.get("attr_premium", [])}
    _alb, _ost = _ap.get("专辑"), _ap.get("OST/单曲")
    _fmt_r = lambda v: "暂无" if v is None else f"{v:.2f}"
    if _alb is not None and _ost is not None:
        if _alb - _ost > 0.02:
            _wp_insight = (f"听众时间偏好洞察：专辑类作品周末溢价 {_fmt_r(_alb)}，高于 OST/单曲的 {_fmt_r(_ost)}，"
                           f"表明专辑具有周末沉浸式聆听特质，而非通勤背景音属性。")
        elif _ost - _alb > 0.02:
            _wp_insight = (f"听众时间偏好洞察：OST/单曲周末溢价 {_fmt_r(_ost)}，高于专辑类作品的 {_fmt_r(_alb)}，"
                           f"推测与周末追剧/观影场景联动相关。")
        else:
            _wp_insight = (f"听众时间偏好洞察：专辑类与 OST/单曲周末溢价接近（{_fmt_r(_alb)} vs {_fmt_r(_ost)}），"
                           f"两类作品在周末/工作日的时间偏好上无明显差异。")
    else:
        _wp_insight = "听众时间偏好洞察：专辑类或 OST/单曲数据不足，暂无法对比周末溢价。"
    chart_summaries["weekend_premium"] = _wp_insight
    _tl = timeline_narrative
    chart_summaries["timeline"] = (
        f"月度竞争格局时间轴（{_tl[0].get('month') if _tl else '-'} 至 {_tl[-1].get('month') if _tl else '-'}）："
        f"{len(_tl)} 个月共 {total_songs} 首作品的份额争夺与巡演发行事件叠加，自动播放展示每帧 Top15 竞争态势。"
    )
    _wf_names = rank_waterfall.get("names", []) or []
    chart_summaries["waterfall"] = (
        f"排名战争瀑布图：展示 {len(_wf_names)} 首作品全站排名变化的逐日累积效应，"
        f"上升用绿色、下降用红色，直观呈现每首作品在竞争中的进退轨迹。"
    )
    _tse = tour_song_fx or []
    if _tse:
        _tse_lines = "；".join(
            f"{e.get('city', '')}({e.get('date', '')})全站{'+' if (e.get('total_uplift') or 0) >= 0 else ''}{e.get('total_uplift')}%"
            f"歌单内{'+' if (e.get('setlist_uplift') or 0) >= 0 else ''}{e.get('setlist_uplift')}%"
            f"辐射带动{'+' if (e.get('radiance_uplift') or 0) >= 0 else ''}{e.get('radiance_uplift')}%"
            for e in _tse
        )
        chart_summaries["tour_song_effects"] = (
            f"巡演歌曲级效应：共 {len(_tse)} 场演出有歌曲级监测数据，"
            f"每场分全站/歌单内（直接效应）/辐射带动（歌单外）三口径统计演出后7日较前基线涨幅。{_tse_lines}。"
        )

    # KPI 第4卡 mini sparkline：近30日每日新增追踪歌曲数（完整30天窗口，0填充）
    new_track_trend = {"labels": [], "values": []}
    first_seen = df_all.sort_values("data_date").groupby("uid")["data_date"].first()
    window_start = df_all["data_date"].max() - pd.Timedelta(days=29)
    daily_new = first_seen[first_seen >= window_start].value_counts().sort_index()
    if len(daily_new) > 0:
        all_days = pd.date_range(window_start, df_all["data_date"].max(), freq="D")
        daily_new = daily_new.reindex(all_days, fill_value=0)
        new_track_trend = {
            "labels": [d.strftime("%m-%d") for d in daily_new.index],
            "values": [int(v) for v in daily_new.values],
        }

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M"),
        "total": int(total_records), "success": success_records,
        "complete_rate": complete_rate, "index_rate": complete_rate, "active_rate": active_rate,
        "total_songs": total_songs, "active_songs": active_songs,
        "link_uids": link_uids, "name_uids": name_uids, "tracked_links": tracked_links,
        "time_labels": time_labels,
        "trend_raw": [round(float(x), 0) for x in monthly["current_index"]],
        "song_count_trend": [int(x) for x in monthly["uid"]],
        "listener_ratio_trend": listener_ratio_trend,  # 归一化比例（峰值月=100），绝对人数不外发
        "listener_labels": listener_labels,
        "top_songs": top_songs, "rank_groups": rank_groups,
        "matrix_points": matrix_points, "detail_songs": detail_songs,
        "song_index": song_index,  # 数据知识库搜索：全量歌曲档案索引（含迷你趋势点）
        "weekend_workday": [weekend_avg, workday_avg],
        "tour_events": tour_events, "release_events": release_events, "performance_events": performance_events,
        "attr_stats": {"labels": attr_labels, "counts": attr_counts, "tracked": attr_tracked},
        "top_lines": top_lines, "cat_lines": cat_lines,
        "tour_fx": tour_fx, "release_fx": release_fx,
        "tour_song_effects": tour_song_fx,  # 场次后歌曲级效应：直接(歌单内)+辐射带动(歌单外)
        "batch_count": batch_count, "date_range": date_range,
        "hist_trends": hist_trends,  # 历史收听趋势 {uid: {labels:[], values:[], raw:[]}}
        "hist_uid_names": hist_uid_names or {},  # uid → 歌名（由 rebuild 传入）
        "data_policy": "aggregated_trends_only",  # 公开数据仅聚合趋势与份额，原始明细本地归档
        # 指令4 新增维度
        "lifecycle_migration": lifecycle_migration,  # 生命周期桑基图
        "release_decay": release_decay,              # 新歌衰减曲线族
        "weekend_premium": weekend_premium,          # 周末溢价热力矩阵
        "second_spring": second_spring,              # 老歌复活雷达
        "rank_waterfall": rank_waterfall,            # 排名跃迁瀑布
        "new_track_trend": new_track_trend,          # KPI sparkline：近30日新增追踪数
        "timeline_narrative": timeline_narrative,    # 月度竞争格局时间轴（指令5）
        "daily_listen_overview": daily_listen["overview"],  # 今日收听态势：活跃数/集中度/截至日期/小样本标记
        "daily_listen_trend": daily_listen["trend"],        # 今日份额 TOP20 + 环比趋势（无绝对人数）
        "daily_new_today": daily_listen["new_today"],       # 昨日无指数、今日出现指数的歌曲
        "last_update": now.strftime("%Y-%m-%d %H:%M"),      # 日报层：数据快照时间（与 timestamp 同源）
        "today_batches": batch_count,        # 修正：当日批次不可得，展示数据覆盖天数
        "daily_new_records": daily_fresh["daily_new_records"],  # 较昨日新增歌曲数
        "recent_7days": daily_fresh["recent_7days"],            # 最近7日全站平均指数
        "latest_anomaly": daily_fresh["latest_anomaly"],        # 今日最显著异动（无异动为 null）
        "daily_anomalies": daily_fresh["daily_anomalies"],      # 今日异动列表（最多3条）
        "chart_summaries": chart_summaries,  # 指令4：AI 可读摘要（隐藏层填充）
        "lineage": LINEAGE,  # #5 数据谱系：清洗日志统计（「数据谱系」折叠面板）
    }


def build_daily_brief(payload):
    """生成「每日文字分析简报」：面向当次数据更新的动态研判（"今天怎么了、意味着什么"），
    与页面内"核心数据结论"（静态档案快照）形成差异化分工：
      - 核心数据结论 = 累计覆盖/排名格局/数据速览（长期稳定，回答"是什么"）
      - 每日简报     = 当日新增/异动/环比/事件联动/结构变化/综合研判（随批次变化，回答"今天如何"）
    供爬虫/搜索引擎/AI 直接抓取（静态 HTML，非前端渲染）。所有数字均来自 payload，不写死。
    """
    from html import escape

    lines = []
    ts = str(payload.get("timestamp", ""))
    date_str = ts.split(" ")[0] if ts else ""
    new_records = payload.get("daily_new_records", 0)

    # 1) 今日概览：聚焦"本次更新本身"，不重复累计覆盖数
    snap_parts = [f"截至 {ts} 的监测更新已完成"]
    if isinstance(new_records, int) and new_records > 0:
        snap_parts.append(f"追踪曲目池较昨日新增 {new_records} 首")
    latest_anom = payload.get("latest_anomaly")
    if latest_anom:
        snap_parts.append(f"检出异动：{latest_anom.get('song','')}{latest_anom.get('desc','')}")
    else:
        snap_parts.append("无显著异动")
    lines.append("【今日概览】" + "；".join(snap_parts) + "。")

    # 2) 今日异动明细（仅当有异动时展开；无异动则合并进概览，避免空话）
    anomalies = payload.get("daily_anomalies", []) or []
    if anomalies:
        bits = "；".join(f"{a.get('song','')}{a.get('desc','')}" for a in anomalies[:3])
        lines.append(f"【异动明细】共 {len(anomalies)} 项：{bits}。"
                     f"异动需结合上下文判断是临时波动还是趋势起点，可对照近 7 日走势与事件时间轴。")

    # 3) 市场信号：近7日走势 + 涨跌极值（区别于核心结论的"平均指数最高"）
    r7 = payload.get("recent_7days", []) or []
    if len(r7) >= 3:
        vals = [r.get("avg_index") for r in r7 if isinstance(r.get("avg_index"), (int, float))]
        if len(vals) >= 3:
            first, last = vals[0], vals[-1]
            pct = (last - first) / first * 100 if first else 0
            trend_word = "上行" if pct > 1 else ("下行" if pct < -1 else "平稳")
            lines.append(f"【市场信号】近 7 日全站平均指数 {first:.0f}→{last:.0f}"
                         f"（{'↑' if pct>=0 else '↓'}{abs(pct):.1f}%），整体{trend_word}；"
                         f"7 日序列：{'、'.join(f'{v:.0f}' for v in vals)}。")
    # 涨跌极值（用 top_songs 的趋势字段：涨幅最大 vs 跌幅最大）
    top = payload.get("top_songs", []) or []
    if top:
        pos = [t for t in top if (t.get("trend") or 0) > 0][:2]
        neg = [t for t in top if (t.get("trend") or 0) < 0][:2]
        bits = []
        if pos:
            bits.append("领涨 " + "、".join(f"《{escape(t.get('name',''))}》{'+'}{t.get('trend')}%" for t in pos))
        if neg:
            bits.append("领跌 " + "、".join(f"《{escape(t.get('name',''))}》{t.get('trend')}%" for t in neg))
        if bits:
            lines.append("【涨跌结构】近 30 日活跃度变化中，" + "；".join(bits) + "。"
                         + "涨跌结构反映市场关注点的迁移方向，领涨曲目通常是近期宣发或演出的受益者。")

    # 4) 事件联动与解读（升级为分析角度，非单纯罗列）
    pe = payload.get("performance_events", []) or []
    recent_pe = [e for e in pe if e[0] >= (date_str[:7] if date_str else "")]
    if recent_pe:
        cities = []
        for e in recent_pe[-4:]:
            lbl = e[1]
            city = lbl.split("·")[-1] if "·" in lbl else lbl
            if city not in cities:
                cities.append(city)
        lines.append(f"【演出联动】本监测窗口内有演出活动：{'、'.join(cities)} 等 {len(recent_pe)} 场。"
                     f"对比演出前后歌曲指数可评估『单曲演出的辐射带动』——即观众因演出关注王晰后，"
                     f"是否带动其他歌曲收听。详见下方『巡演歌曲级效应』面板的三口径涨幅。")
    tf = payload.get("tour_fx", []) or []
    if tf:
        avg_up = round(sum(e.get("uplift", 0) for e in tf) / len(tf), 1)
        best = tf[0]
        best_lbl = str(best.get("label", "")).strip().replace("《", "").replace("》", "")
        lines.append(f"【巡演效应】已量化 {len(tf)} 个巡演节点：巡演后 7 日全站日均指数较基线"
                     f"平均{'上涨' if avg_up>=0 else '下降'} {abs(avg_up)}%；"
                     f"最强节点 {best_lbl}（{'+' if (best.get('uplift') or 0)>=0 else ''}{best.get('uplift')}%）。"
                     f"巡演对音乐收听的带动强度，是评估演出商业价值之外的另一观察维度。")
    rf = payload.get("release_fx", []) or []
    if rf:
        b = rf[0]
        b_lbl = str(b.get("label", "")).strip().replace("《", "").replace("》", "")
        lines.append(f"【新歌表现】新歌发行后 14 日表现最佳为《{escape(b_lbl)}》"
                     f"（14 日平均指数 {b.get('avg',0):.0f}，峰值 {b.get('peak',0):.0f}）。"
                     f"新歌的持久度（峰值后的衰减速率）可在『新歌衰减曲线』面板查看。")

    # 5) 结构变化：老歌复活 / 排名跃迁（核心结论未覆盖的分析维度）
    ss = payload.get("second_spring", {}) or {}
    ss_names = (ss.get("names") or [])[:3]
    if ss_names:
        ss_str = "、".join("《" + escape(n) + "》" for n in ss_names)
        lines.append(f"【老歌复活】{ss_str} 等老歌近期出现二次活跃信号（沉寂后指数回升），"
                     f"这类「复活」通常由综艺、怀旧话题或新受众涌入触发。")
    rw = payload.get("rank_waterfall", {}) or {}
    rw_names = (rw.get("names") or [])[:3]
    rw_changes = (rw.get("changes") or [])[:3]
    if rw_names:
        chg_bits = "；".join(f"《{escape(rw_names[i])}》{'↑' if rw_changes[i]>0 else '↓'}{abs(rw_changes[i])}位"
                             for i in range(min(len(rw_names), len(rw_changes))))
        lines.append(f"【排名跃迁】今日全站排名变动最显著：{chg_bits}。"
                     f"排名快速跃迁往往是算法推荐或话题热度的直接映射。")

    # 6) 综合研判：分析师式总结（把多维度串成可引用的结论）
    verdict_bits = []
    if len(r7) >= 3 and len(vals) >= 3:
        verdict_bits.append(f"近 7 日指数{'上行' if pct>1 else ('下行' if pct<-1 else '平稳')}")
    if tf:
        verdict_bits.append(f"巡演带动{'正向' if avg_up>=0 else '偏弱'}")
    if recent_pe:
        verdict_bits.append("有音乐剧演出活动在监测窗口内")
    if latest_anom:
        verdict_bits.append("存在单曲异动需关注")
    if verdict_bits:
        lines.append("【综合研判】本期数据要点：" + "；".join(verdict_bits)
                     + "。综合来看，" + ("王晰音乐热度处于阶段性上行通道，演出与宣发节点对收听的带动值得持续跟踪。"
                                        if pct > 1 else "王晰音乐热度总体平稳，未见明显拐点，关注后续演出/发行事件是否带来变化。"))

    # 7) 数据说明
    lines.append("【数据说明】本简报随每次监测更新自动生成，数字直接取自当次结果，未人工修饰；"
                 "仅反映 QQ 音乐单一平台公开指标，供研究参考，不构成对全网热度的完整度量。")

    return " ".join(lines)


def build_geo_content(payload):
    """生成面向搜索引擎与 AI 引用的静态内容：meta 标签 / JSON-LD / 文字结论 / 方法说明"""
    from html import escape
    date_start, date_end = [x.strip() for x in payload["date_range"].split("~")]
    desc = (f"{ARTIST_NAME}QQ音乐指数追踪：{payload['date_range']}，覆盖{payload['total_songs']}首作品，"
            f"{UPDATE_FREQ_DESC}。含巡演带动效应、新歌发行14日表现、"
            f"热度趋势与稳定性分析，聚合数据开放下载。")

    # ---------- 结论句子（全部由真实数据计算，无编造） ----------
    tr = payload.get("trend_raw", [])
    labels = payload.get("time_labels", [])
    trend_sentence = ""
    if len(tr) >= 2 and tr[0]:
        chg = (tr[-1] / tr[0] - 1) * 100
        pk_i = tr.index(max(tr))
        caveat = ""
        if chg < -30 and tr[0] > 0:
            caveat = "（注：期初监测批次较早、追踪曲目池覆盖与近期不同，此处变化主要反映样本规模扩大，不直接等同于热度衰减）"
        trend_sentence = (f"全曲目月度平均指数由期初（{labels[0]}）的 {tr[0]:.0f} 变化至最新月（{labels[-1]}）的 {tr[-1]:.0f}"
                          f"（{'+' if chg >= 0 else ''}{chg:.1f}%）{caveat}，历史峰值出现在 {labels[pk_i]}（{tr[pk_i]:.0f}）。")

    top_names = payload.get("top_lines", {}).get("names", [])
    top_sentence = f"近30日平均指数最高的作品为 {('、'.join('《' + escape(n) + '》' for n in top_names[:3]))}。" if top_names else ""

    anom = payload.get("top_songs", [])[:3]
    anom_sentence = ("近30日异常活跃歌曲：" + "、".join(
        f"《{escape(s['name'])}》（环比{'+' if s['trend'] >= 0 else ''}{s['trend']}%，{s['tag']}）" for s in anom) + "。") if anom else ""

    tf = payload.get("tour_fx", [])
    tour_sentence = ""
    if tf:
        avg_up = round(sum(e["uplift"] for e in tf) / len(tf), 1)
        b = tf[0]
        tour_sentence = (f"在可量化的 {len(tf)} 个巡演节点中，巡演后7日全站日均指数较基线平均上涨 {avg_up}%"
                         f"（带动最强的是 {escape(b['label'])}，{'+' if b['uplift'] >= 0 else ''}{b['uplift']}%）。")

    rf = payload.get("release_fx", [])
    release_sentence = ""
    if rf:
        b = rf[0]
        release_sentence = f"新歌发行14日表现最佳为 {escape(b['label'])}（14日平均指数 {b['avg']:.0f}，峰值 {b['peak']:.0f}）。"

    ww = payload.get("weekend_workday", [0, 0])
    week_sentence = ""
    if ww[1]:
        diff = (ww[0] / ww[1] - 1) * 100
        week_sentence = f"周末平均指数 {ww[0]:.0f}，工作日 {ww[1]:.0f}，周末{'高' if diff >= 0 else '低'}出 {abs(diff):.1f}%。"

    lr = payload.get("listener_ratio_trend", [])
    listener_sentence = ""
    if lr:
        lr_valid = [x for x in lr if x is not None]
        if lr_valid:
            first_val = lr_valid[0]
            last_val = lr_valid[-1]
            chg = last_val - first_val
            listener_sentence = f"收听热度（归一化至峰值月100%）由期初 {first_val:.0f}% 变化至最新月 {last_val:.0f}%（{'↑' if chg >= 0 else '↓'}{abs(chg):.0f}pct）。"

    rg = payload.get("rank_groups", {})
    rank_bits = []
    for attr in ("专辑", "OST/单曲", "其他追踪"):
        if rg.get(attr):
            r0 = rg[attr][0]
            rank_bits.append(f"{attr}类第一《{escape(str(r0[1]))}》（综合得分 {r0[2]}）")
    rank_sentence = ("近90日综合表现：" + "，".join(rank_bits) + "。") if rank_bits else ""

    citation_line = (f"引用本数据请注明：{escape(ARTIST_NAME)}音乐指数追踪数据集（更新至{date_end}），{SITE_URL}")

    # 每日文字分析简报：静态 HTML，供爬虫/搜索引擎/AI 直接抓取（数据全部来自 payload）
    brief_text = build_daily_brief(payload)
    brief_html = f"""  <section class="geo-summary" id="daily-brief" style="border-left:4px solid #00d2ff;background:rgba(0,210,255,0.04);">
    <h2>📋 每日文字分析简报（{escape(str(payload.get('timestamp','')))}）
      <span class="data-snapshot-badge">🤖 静态文本 · 供搜索引擎/AI 直接抓取</span>
    </h2>
    <p style="line-height:1.9;">{escape(brief_text)}</p>
    <p style="font-size:12px;color:#5a6b8c;margin-top:8px;">本简报由监测脚本随每次数据更新自动生成，数字直接取自 <a href="dashboard_data.json">dashboard_data.json</a>，未人工修饰。时间轴上的「演出活动」「巡演节点」「新歌发行」标记可与本简报交叉印证。</p>
  </section>
"""

    summary = f"""  <section class="geo-summary" id="summary">
    <h2>核心数据结论（截至 {date_end}）
      <span class="data-snapshot-badge">📅 数据快照 · <span id="snapshotDate">{escape(payload.get('timestamp',''))}</span></span>
    </h2>
    <p>本站持续追踪中国内地流行男低音歌手<strong>{escape(ARTIST_NAME)}</strong>在QQ音乐平台的公开音乐指数表现。数据周期 <strong>{payload['date_range']}</strong>，累计 <strong>{payload['batch_count']}</strong> 个监测批次，覆盖 <strong>{payload['total_songs']}</strong> 首追踪歌曲（链接身份 {payload['link_uids']} + 名称身份 {payload['name_uids']}），其中 <strong>{payload['active_songs']}</strong> 首（{payload['active_rate']}%）近期有收听记录，数据完整度 {payload['complete_rate']}%。数据集{UPDATE_FREQ_DESC}，最后更新于 <strong>{payload['timestamp']}</strong>。</p>
    <p>{trend_sentence}{top_sentence}{rank_sentence}</p>
    <p>{tour_sentence}{release_sentence}{week_sentence}{listener_sentence}{anom_sentence}</p>
    <h3>数据速览</h3>
    <ul>
      <li>时间跨度 <b>{payload['date_range']}</b></li>
      <li>监测批次 <b>{payload['batch_count']} 天</b></li>
      <li>数据完整度 <b>{payload['complete_rate']}%</b>（有指数记录占比）</li>
      <li>追踪歌曲（去重） <b>{payload['total_songs']} 首</b></li>
      <li>活跃歌曲 <b>{payload['active_songs']} 首</b></li>
      <li>巡演节点 / 发行事件 <b>{len(payload.get('tour_events', []))} / {len(payload.get('release_events', []))}</b></li>
      <li>更新频率 <b>{UPDATE_FREQ_DESC}</b></li>
      <li>开放数据 <b><a href="dashboard_data.json">dashboard_data.json</a></b></li>
    </ul>
    <p style="font-size:12px;color:#5a6b8c">{citation_line}</p>
  </section>"""
    summary = brief_html + summary  # 每日简报置顶于核心结论之前

    about = f"""  <section class="geo-summary" id="methodology">
    <h2>数据来源与方法说明</h2>
    <p><strong>追踪对象：</strong>{escape(ARTIST_NAME)}（中国内地流行男低音歌手）。<strong>数据来源：</strong>QQ音乐网页公开展示的音乐指数、实时收听人数与全站排名，基于公开页面信息按固定链接清单逐日整理，未使用任何非公开接口。</p>
    <p><strong>指数口径：</strong>以"昨日音乐指数"校准为日粒度数值。<strong>身份识别：</strong>同一链接视为同一作品（链接身份，{payload['link_uids']} 个）；无法识别链接的历史记录按歌名归并（名称身份，{payload['name_uids']} 个）；同名不同版本（如 Live / 录音室版）分开统计。</p>
    <p><strong>更新频率：</strong>{UPDATE_FREQ_DESC}，本页随每批监测自动重建；图表数据同步发布为 <a href="dashboard_data.json">dashboard_data.json</a>（JSON，每日更新）。</p>
    <p><strong>局限性：</strong>数据仅反映单一平台的公开指标，不构成对全网热度的完整度量；仅供个人研究使用，转载请注明来源。</p>
    <p><strong>维护者：</strong>{escape(AUTHOR_NAME)} · 托管于 GitHub Pages · {SITE_URL}</p>
  </section>"""

    json_ld_obj = [{
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{ARTIST_NAME}QQ音乐指数追踪数据集",
        "alternateName": "Wang Xi QQ Music Index Tracking Dataset",
        "description": desc,
        "url": SITE_URL + "/",
        "dateModified": date_end,
        "temporalCoverage": f"{date_start}/{date_end}",
        "creator": {"@type": "Person", "name": AUTHOR_NAME, "url": SITE_URL + "/"},
        "about": {"@type": "Person", "name": ARTIST_NAME, "url": ROOT_URL + "/",
                  "description": "中国内地流行男低音歌手"},
        "isPartOf": {"@type": "WebSite", "url": ROOT_URL + "/"},
        "isAccessibleForFree": True,
        "license": "https://creativecommons.org/licenses/by-nc/4.0/",
        "measurementTechnique": "基于QQ音乐公开页面信息的日粒度数据整理与口径校准",
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "音乐指数", "description": "QQ音乐昨日音乐指数校准值"},
            {"@type": "PropertyValue", "name": "实时收听人数"},
            {"@type": "PropertyValue", "name": "全站排名"}
        ],
        "distribution": {"@type": "DataDownload", "encodingFormat": "application/json",
                         "contentUrl": SITE_URL + "/dashboard_data.json"},
        "keywords": f"{ARTIST_NAME},音乐指数,QQ音乐,数据追踪,巡演"
    }, {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": f"{ARTIST_NAME}音乐数据趋势大屏",
        "url": SITE_URL + "/",
        "dateModified": date_end,
        "inLanguage": "zh-CN",
        "about": {"@type": "Person", "name": ARTIST_NAME},
        "mainEntity": {"@id": SITE_URL + "/#dataset"},
        "potentialAction": {
            "@type": "SearchAction",
            "target": SITE_URL + "/?q={search_term_string}",
            "query-input": "required name=search_term_string"
        }
    }]
    json_ld = ('<script type="application/ld+json">\n'
               + json.dumps(json_ld_obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
               + '\n</script>')

    meta_tags = f"""<meta name="description" content="{desc}">
<meta name="keywords" content="{ARTIST_NAME},音乐指数,QQ音乐,数据大屏,巡演带动,新歌发行,歌曲热度,数据分析">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="author" content="{escape(AUTHOR_NAME)}">
<link rel="canonical" href="{SITE_URL}/">
<meta property="og:type" content="website">
<meta property="og:title" content="{ARTIST_NAME}音乐数据趋势大屏 - QQ音乐指数每日追踪">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE_URL}/">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary">"""

    llms_txt = f"""# {ARTIST_NAME}音乐数据趋势大屏

> 持续追踪歌手{ARTIST_NAME}在QQ音乐的公开音乐指数（{payload['date_range']}），包含巡演带动效应、新歌发行14日表现、热度趋势与稳定性分析。数据{UPDATE_FREQ_DESC}。

## 核心页面

- [数据大屏]({SITE_URL}/): 趋势可视化、核心结论文字摘要（#summary）、方法说明（#methodology）
- 数据知识库搜索：大屏页内嵌问答式搜索（search_engine.js），支持歌名检索、数据问答（涨幅/周末/巡演/异常/生命周期）、洞察引用，并支持 `{SITE_URL}/?q=问题` 直达搜索

## 开放数据

- [聚合数据 JSON]({SITE_URL}/dashboard_data.json): 全部统计指标与图表数据，每日更新

## 引用方式

引用数据请注明：{ARTIST_NAME}音乐指数追踪数据集（更新至{date_end}），{SITE_URL}
"""

    return {
        "page_title": f"{ARTIST_NAME}音乐数据趋势大屏 - QQ音乐指数追踪（更新至{date_end}）",
        "meta_tags": meta_tags,
        "json_ld": json_ld,
        "summary": summary,
        "about": about,
        "llms_txt": llms_txt,
    }

def _load_live_url_map(dashboard_dir):
    """从站点 live/manifest.json 构建 date → live_url 映射（动态读取，不写死）。

    有独立 live 详情页的场次返回如 /live/hui-回-重庆-2026.html；
    无匹配场次返回 None，前端不渲染链接。manifest 由 generate_live_page.py 维护，
    随详情页逐场补充自动生效。
    """
    site_root = os.path.dirname(os.path.abspath(dashboard_dir))
    manifest_path = os.path.join(site_root, "live", "manifest.json")
    mapping = {}
    try:
        with open(manifest_path, encoding="utf-8") as f:
            for e in json.load(f):
                link = (e.get("link") or "").strip().lstrip("/")
                if e.get("date") and link:
                    mapping[e["date"]] = "/" + link
    except (OSError, ValueError):
        pass
    return mapping


def generate_dashboard(payload, dashboard_dir):
    os.makedirs(dashboard_dir, exist_ok=True)

    # 双向链接：为每场次补 live_url（动态读 manifest；无 live 页的场次为 null，前端不渲染链接）
    live_map = _load_live_url_map(dashboard_dir)
    for _e in payload.get("tour_song_effects") or []:
        _e["live_url"] = live_map.get(_e.get("date"))

    json_path = os.path.join(dashboard_dir, "dashboard_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    head_info = (f'<div class="subtitle" style="margin-top:6px;color:#3a7bd5">'
                 f'数据周期: {payload["date_range"]} | 共 {payload["batch_count"]} 批次 | '
                 f'追踪歌曲 {payload["total_songs"]} 个（链接身份 {payload["link_uids"]} + 名称身份 {payload["name_uids"]}） | '
                 f'链接清单 {payload["tracked_links"]} 条</div>')
    status_info = (
        f'      <div class="status-item"><span><span class="status-dot"></span>系统状态</span><span class="status-value">运行正常</span></div>\n'
        f'      <div class="status-item"><span>历史批次</span><span class="status-value">{payload["batch_count"]} 天</span></div>\n'
        f'      <div class="status-item"><span>时间跨度</span><span class="status-value">{payload["date_range"]}</span></div>\n'
        f'      <div class="status-item"><span>数据完整度</span><span class="status-value">{payload["complete_rate"]}%</span></div>\n'
        f'      <div class="status-item"><span>追踪歌曲(去重)</span><span class="status-value">{payload["total_songs"]} 个</span></div>\n'
        f'      <div class="status-item"><span>链接身份 / 名称身份</span><span class="status-value">{payload["link_uids"]} / {payload["name_uids"]}</span></div>\n'
        f'      <div class="status-item"><span>活跃歌曲</span><span class="status-value">{payload["active_songs"]} 个</span></div>\n'
        f'      <div class="status-item"><span>指数口径</span><span class="status-value">昨日音乐指数校准</span></div>\n'
        f'      <div class="status-item"><span>巡演节点 / 发行事件</span><span class="status-value">{len(payload["tour_events"])} / {len(payload["release_events"])}</span></div>\n'
        f'      <div class="status-item"><span>最后更新</span><span class="status-value">{payload["timestamp"]}</span></div>\n'
        f'      <div class="status-item"><span>下次监测</span><span class="status-value">{calc_next_run()}</span></div>'
    )

    geo = build_geo_content(payload)
    html = HTML_TEMPLATE
    html = html.replace("__ECHARTS_TAG__", build_echarts_tag())
    html = html.replace("__PAGE_TITLE__", geo["page_title"])
    html = html.replace("__META_TAGS__", geo["meta_tags"])
    html = html.replace("__JSON_LD__", geo["json_ld"])
    html = html.replace("__KPI_TOTAL__", str(payload["total_songs"]))
    html = html.replace("__UID_SPLIT__", f"链接身份 {payload['link_uids']} | 名称身份 {payload['name_uids']}")
    html = html.replace("__GEO_SUMMARY__", geo["summary"])
    html = html.replace("__ABOUT_SECTION__", geo["about"])
    html = html.replace("__HEAD_INFO__", head_info)
    html = html.replace("__STATUS_INFO__", status_info)
    # 数据已改为前端 fetch dashboard_data.json（fetch 改造），不再内嵌 __JSON_DATA__。
    # payload 仍写入 dashboard_data.json（见上方 json.dump），供前端 fetch 加载。

    html_path = os.path.join(dashboard_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # llms.txt：给 AI 爬虫的站点导览（放在站点根目录，连同 index.html 一起 push）
    llms_path = os.path.join(dashboard_dir, "llms.txt")
    with open(llms_path, "w", encoding="utf-8") as f:
        f.write(geo["llms_txt"])

    # 数据知识库搜索引擎：复制 search_engine.js 到 dashboard 目录（不存在则跳过，不影响生成）
    src_js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_engine.js")
    dst_js = os.path.join(dashboard_dir, "search_engine.js")
    if os.path.exists(src_js):
        try:
            shutil.copy2(src_js, dst_js)
            logger.info(f"知识库搜索引擎就绪: {dst_js}")
        except Exception as e:
            logger.warning(f"复制知识库搜索引擎失败: {e}")

    logger.info(f"大屏看板已生成: {os.path.abspath(html_path)}")
    logger.info(f"llms.txt 已生成: {os.path.abspath(llms_path)}")
    logger.info(f"JSON 数据: {os.path.abspath(json_path)}")
    logger.info("提示: 双击 index.html 即可查看；把 dashboard 目录 push 到仓库即可在线查看")
    return html_path, json_path

def _copy_with_retry(src, dst, retries=3, base_wait=3):
    """复制文件；Windows 下目标被其他进程占用（Permission denied）时等待后重试，
    避免自动部署因单次占用丢推送（曾致 08-06 全天数据未上线）。"""
    for i in range(retries):
        try:
            shutil.copy2(src, dst)
            return True
        except PermissionError:
            if i < retries - 1:
                logger.warning(f"自动部署: 目标被占用，{base_wait * (i + 1)} 秒后重试: {dst}")
                time.sleep(base_wait * (i + 1))
    logger.warning(f"自动部署: 复制重试 {retries} 次仍失败: {src}")
    return False


def _staged_has(repo_dir, path_prefix):
    """检测暂存区（git diff --cached --name-only）中是否有以 path_prefix 开头的文件。
    用于区分「dashboard 变更」与「源码快照变更」，从而生成精确的 commit 信息。
    注意：加 core.quotepath=false 让中文文件名按 UTF-8 原样输出（否则 git 会转义成 \\NNN 八进制，导致 startswith 失效）。"""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only"],
            cwd=repo_dir, capture_output=True, text=True, encoding="utf-8", timeout=15)
        lines = (r.stdout or "").splitlines()
        return any(ln.strip('"').startswith(path_prefix.rstrip("/")) for ln in lines if ln)
    except Exception:
        return False


def auto_deploy(dashboard_dir):
    """把 dashboard 目录复制到网站仓库并自动 git push（若失败不影响采集，仅记录警告）"""
    import subprocess, shutil
    if not WEBSITE_REPO or not os.path.isdir(WEBSITE_REPO):
        logger.warning("自动部署跳过: 网站仓库路径未配置或不存在")
        return
    repo_dashboard = os.path.join(WEBSITE_REPO, "dashboard")
    os.makedirs(repo_dashboard, exist_ok=True)
    try:
        # 复制 dashboard 文件到网站仓库（占用重试，避免丢推送）
        failed = []
        for fname in os.listdir(dashboard_dir):
            src = os.path.join(dashboard_dir, fname)
            dst = os.path.join(repo_dashboard, fname)
            if os.path.isfile(src) and not _copy_with_retry(src, dst):
                failed.append(fname)
        if failed:
            logger.warning(f"自动部署复制失败（文件占用，重试后仍失败）: {failed}")
            return
        logger.info(f"自动部署: 已复制 dashboard 文件到 {repo_dashboard}")
        # 源码快照自动同步：把本源码复制到仓库 project_b/（单一事实源之外的只读快照，供版本回溯）
        try:
            _src_file = os.path.abspath(__file__)
            _dst_file = os.path.join(WEBSITE_REPO, "project_b", os.path.basename(_src_file))
            os.makedirs(os.path.dirname(_dst_file), exist_ok=True)
            shutil.copy2(_src_file, _dst_file)
            logger.info(f"自动部署: 源码快照已同步 -> project_b/{os.path.basename(_dst_file)}")
        except Exception as _e:
            logger.warning(f"自动部署: 源码快照同步失败（不影响 dashboard 发布）: {_e}")
    except Exception as e:
        logger.warning(f"自动部署复制失败: {e}")
        return
    try:
        # git add：dashboard 与源码快照分开暂存，据此区分各自是否有变更，动态拼 commit 信息
        _src_rel = os.path.join("project_b", os.path.basename(__file__))

        # 1) dashboard 是否变更
        subprocess.run(["git", "add", "dashboard/"], cwd=WEBSITE_REPO,
                       check=True, capture_output=True, timeout=30)
        _dash_changed = _staged_has(WEBSITE_REPO, "dashboard/")

        # 2) 源码快照是否变更
        subprocess.run(["git", "add", _src_rel], cwd=WEBSITE_REPO,
                       check=True, capture_output=True, timeout=30)
        _src_changed = _staged_has(WEBSITE_REPO, _src_rel)

        ts = datetime.now().strftime("%m-%d %H:%M")
        if _src_changed and _dash_changed:
            msg = f"自动部署: 源码快照更新 + dashboard 数据更新 ({ts})"
        elif _src_changed:
            msg = f"自动部署: 源码快照更新 ({ts})"
        elif _dash_changed:
            msg = f"自动部署: dashboard 数据更新 ({ts})"
        else:
            logger.info("自动部署: dashboard 与源码快照均无新变更，跳过 commit")
            return
        r = subprocess.run(["git", "commit", "-m", msg], cwd=WEBSITE_REPO,
                           capture_output=True, timeout=30)
        if r.returncode != 0:
            logger.info(f"自动部署: commit 失败（可能无变更）: {r.stderr.strip()[:120]}")
            return
        subprocess.run(["git", "push", "origin", "main"], cwd=WEBSITE_REPO,
                       check=True, capture_output=True, timeout=60)
        logger.info(f"自动部署: git push 成功 -> https://wx409.github.io/dashboard/")
    except FileNotFoundError:
        logger.warning("自动部署跳过: git 命令不可用")
    except subprocess.TimeoutExpired:
        logger.warning("自动部署超时（网络问题？），下次监测会重试")
    except Exception as e:
        logger.warning(f"自动部署 git 操作失败: {e}")

# ============================================================
# 第四部分A：历史收听人数清洗（2022-2024 原始记录 → 清洁数据表）
# ============================================================
HISTORICAL_LISTENER_DIRS = [
    r"E:\wx\数据",                # 主数据目录（全遍历）
    r"E:\wx\指数vs1",             # 2024-2025 补充数据
    r"E:\wx\收听人数历史版本",     # 历史版本快照
]
LISTENER_CLEAN_CSV = os.path.join(OUTPUT_DIR, "historical_listeners_clean.csv")
REFERENCE_LINK_XLSX = os.path.join(OUTPUT_DIR, "收听人数（2026.7.24）.xlsx")

# 跳过非数据文件（后羿采集器歌曲目录、价格表、汇总文件等）
_HIST_SKIP_PATTERNS = [
    "后羿采集器", "人民网", "ISRC", "中国标准", "价格", "转赞评",
    "成绩榜单", "弘扬", "序号之谜", "工作簿", "mv播放",
    "汇总", "去重", "总表",
]

def _should_skip_hist_file(filename):
    fname = filename.lower()
    for pat in _HIST_SKIP_PATTERNS:
        if pat.lower() in fname:
            return True
    # 跳过 macOS 资源分支文件
    if filename.startswith("._"):
        return True
    return False

def norm_song_name(name):
    """广义歌曲名归一化：去掉 (Live)/(live)/（Live）/含斜杠的歌手名/纯叙述性标题"""
    s = str(name).strip()
    s = re.sub(r"\s*[（(][Ll]ive[）)]\s*", "", s)
    s = re.sub(r"\s*-\s*(Live|live)\s*$", "", s, flags=re.IGNORECASE)
    # 去掉 "王晰/刘也" 这种合唱歌手后缀（不处理纯歌手行）
    s = re.sub(r"\s*/\s*.+", "", s)  # "神魂颠倒 / 王晰"
    s = s.strip()
    return s

def build_reference_map(ref_xlsx):
    """从参考文件解析 mid → 清洁歌名 映射（排除非歌曲条目）"""
    try:
        df = pd.read_excel(ref_xlsx, header=0)
    except Exception:
        return {}, {}
    # 找链接列
    link_col = None
    for c in df.columns:
        if "ngrid" in str(c).lower() or ("链" in str(c) and "接" in str(c)):
            link_col = c; break
    if link_col is None:
        return {}, {}
    # 找清洁歌名列
    clean_col = None
    for c in df.columns:
        cstr = str(c).strip()
        if "歌曲名称" in cstr and ("1" in cstr or "." in cstr):
            clean_col = c; break
    if clean_col is None:
        for c in df.columns:
            if "歌曲名" in str(c):
                clean_col = c; break
    name_col = "歌曲名称" if "歌曲名称" in df.columns else None

    mid2name = {}
    name2mid = {}
    nonsong_skipped = 0
    for _, row in df.iterrows():
        link = row[link_col] if pd.notna(row[link_col]) else ""
        mid = extract_mid(link)
        clean_name = str(row[clean_col]).strip() if clean_col and pd.notna(row.get(clean_col)) else ""
        raw_name = str(row[name_col]).strip() if name_col and pd.notna(row.get(name_col)) else ""
        
        # 排除非歌曲条目（播客/电台/综艺等）
        combined = clean_name + " " + raw_name
        if NONSONG_PATTERN and re.search(NONSONG_PATTERN, combined, re.IGNORECASE):
            nonsong_skipped += 1
            continue
        
        norm = norm_song_name(raw_name) if raw_name else norm_song_name(clean_name) if clean_name else ""
        key = clean_name if clean_name and clean_name != "nan" else norm
        if not key or key == "nan" or len(key) < 2:
            continue
        if mid and key:
            mid2name[mid] = key
            name2mid.setdefault(key, set()).add(mid)
    # 只保留 1:1 的 name→mid 映射（避免歧义）
    name2mid_clean = {k: next(iter(v)) for k, v in name2mid.items() if len(v) == 1}
    logger.info(f"参考映射: {len(mid2name)} mid→name, {len(name2mid_clean)} name→mid (1:1), 排除非歌曲 {nonsong_skipped}")
    LINEAGE["reference_map"] = {"mid2name": int(len(mid2name)), "name2mid_1to1": int(len(name2mid_clean)),
                                "nonsong_skipped": int(nonsong_skipped)}
    return mid2name, name2mid_clean

def clean_historical_listeners():
    """扫描历史目录，清洗输出 historical_listeners_clean.csv（流式写入，避免内存溢出）"""
    ref_mid2name, ref_name2mid = build_reference_map(REFERENCE_LINK_XLSX)
    if not ref_mid2name and not ref_name2mid:
        logger.warning("参考文件无有效映射，历史清洗跳过")
        return None

    bad_names = {"歌曲名称", "歌曲名", "歌名", "曲名", "nan", "None", ""}
    total_files = 0
    skipped_files = 0
    success_files = 0
    total_rows = 0

    # 流式写入临时 CSV（不累积内存）
    tmp_csv = os.path.join(tempfile.gettempdir(), "hist_listeners_stream.csv")
    first_batch = True

    for base_dir in HISTORICAL_LISTENER_DIRS:
        if not base_dir or not os.path.isdir(base_dir):
            continue
        for root, dirs, files in os.walk(base_dir):
            if "dashboard" in root.lower():
                continue
            for f in files:
                if not f.endswith((".xlsx", ".xls")) or f.startswith("~$"):
                    continue
                if _should_skip_hist_file(f):
                    skipped_files += 1; continue
                total_files += 1
                fpath = os.path.join(root, f)
                try:
                    header_row = detect_header_row(fpath)
                    df_raw = pd.read_excel(fpath, header=header_row)
                except Exception:
                    continue
                if df_raw.empty:
                    continue

                # 列名标准化
                cols_std = {}
                has_listeners = False
                has_time_col = False
                time_col_name = None
                for c in df_raw.columns:
                    std = fuzzy_match_column(str(c))
                    if std == "listeners":
                        has_listeners = True
                        cols_std[c] = "listeners"
                    elif std == "song_name":
                        cols_std[c] = "song_name"
                    elif std == "link":
                        cols_std[c] = "link"
                    cstr = str(c).replace(" ", "")
                    if "时间" in cstr and ("当前" in cstr or "更新" in cstr or "采集" in cstr):
                        has_time_col = True
                        time_col_name = c
                        cols_std[c] = "current_time"

                if not has_listeners:
                    continue

                df_s = pd.DataFrame()
                for orig, std in cols_std.items():
                    if std not in df_s.columns:
                        df_s[std] = df_raw[orig]

                if "song_name" not in df_s.columns:
                    continue

                df_s["song_name"] = df_s["song_name"].astype(str).str.strip()
                df_s = df_s[~df_s["song_name"].isin(bad_names)]
                df_s = df_s[~df_s["song_name"].str.contains("名称|歌名", na=False) & (df_s["song_name"].str.len() <= 80)]
                df_s = df_s[~df_s["song_name"].str.match(r"^(王晰|周深|张韶涵|高杨|刘也|郑云龙)[：:：\s]*$", na=False)]

                df_s["listeners"] = df_s["listeners"].apply(clean_numeric)
                df_s = df_s[df_s["listeners"].notna() & (df_s["listeners"] > 0)]
                if df_s.empty:
                    continue

                # 日期推断
                if has_time_col and time_col_name:
                    df_s["_raw_time"] = df_raw[time_col_name].astype(str)
                    df_s["_dt"] = pd.to_datetime(df_s["_raw_time"], errors="coerce", format="mixed")
                    if df_s["_dt"].notna().any():
                        df_s["data_date"] = df_s["_dt"].dt.date
                    else:
                        df_s["data_date"] = parse_date_from_filename(f)
                else:
                    df_s["data_date"] = parse_date_from_filename(f)
                    if not df_s["data_date"].iloc[0] if isinstance(df_s["data_date"], pd.Series) else not df_s["data_date"]:
                        dir_name = os.path.basename(root)
                        m_yr = re.search(r"(\d{4})", dir_name)
                        m_md = re.search(r"(\d{1,2})[.](\d{1,2})", f)
                        if m_md and m_yr:
                            mo, d = m_md.groups()
                            df_s["data_date"] = f"{m_yr.group(1)}-{int(mo):02d}-{int(d):02d}"

                if "data_date" not in df_s.columns:
                    continue
                
                # 统一 data_date 为字符串后再转 datetime
                df_s["data_date"] = df_s["data_date"].astype(str).str.strip()
                df_s = df_s[df_s["data_date"].notna() & (df_s["data_date"] != "")]
                df_s["data_date"] = pd.to_datetime(df_s["data_date"], errors="coerce")
                df_s = df_s[df_s["data_date"].notna()]
                if df_s.empty:
                    continue

                # 歌名归一化
                df_s["norm_name"] = df_s["song_name"].apply(norm_song_name)
                if "link" in df_s.columns:
                    df_s["mid"] = df_s["link"].apply(lambda x: extract_mid(str(x)) if pd.notna(x) else None)
                else:
                    df_s["mid"] = None

                # 身份匹配
                def match_uid(row):
                    if pd.notna(row["mid"]) and row["mid"] in ref_mid2name:
                        return "M:" + row["mid"]
                    if row["norm_name"] in ref_name2mid:
                        return "N:" + ref_name2mid[row["norm_name"]]
                    for ref_name, ref_mid in ref_name2mid.items():
                        if ref_name and len(ref_name) >= 2 and (ref_name in row["norm_name"] or row["norm_name"] in ref_name):
                            return "N:" + ref_mid
                    return None

                df_s["uid"] = df_s.apply(match_uid, axis=1)
                df_s = df_s[df_s["uid"].notna()]
                if df_s.empty:
                    continue

                # 流式写入临时 CSV（不累积内存）
                df_s[["uid", "data_date", "listeners"]].to_csv(
                    tmp_csv, mode='a', index=False, header=first_batch, encoding="utf-8-sig"
                )
                first_batch = False
                success_files += 1
                total_rows += len(df_s)
                
                if success_files % 200 == 0:
                    logger.info(f"  历史清洗进度: {success_files} 个有效文件, {total_rows} 行 (遍历 {total_files}/{skipped_files+total_files})")

    logger.info(f"历史清洗扫描完成: 遍历 {total_files} 文件, 跳过 {skipped_files}, 有效 {success_files}, 总行 {total_rows}")

    if not success_files:
        logger.warning("历史收听数据清洗：未找到任何有效记录")
        if os.path.exists(tmp_csv):
            os.remove(tmp_csv)
        return None

    # 从临时 CSV 加载并聚合
    logger.info("加载临时 CSV 并聚合...")
    df_all = pd.read_csv(tmp_csv, encoding="utf-8-sig")
    df_all["data_date"] = pd.to_datetime(df_all["data_date"], errors="coerce")
    df_all = df_all[df_all["data_date"].notna()]
    
    # 同歌同日取最大值
    df_clean = df_all.groupby(["uid", "data_date"])["listeners"].max().reset_index()
    df_clean = df_clean.rename(columns={"listeners": "peak_listeners"})
    df_clean = df_clean.sort_values(["uid", "data_date"])
    df_clean.to_csv(LISTENER_CLEAN_CSV, index=False, encoding="utf-8-sig")

    # 清理临时文件
    try:
        os.remove(tmp_csv)
    except:
        pass

    n_songs = df_clean["uid"].nunique()
    n_records = len(df_clean)
    date_range = f"{df_clean['data_date'].min().date()} ~ {df_clean['data_date'].max().date()}"
    logger.info(f"历史收听数据清洗完成: {n_records} 条 (uid×日期), {n_songs} 首歌, 时间: {date_range}")
    logger.info(f"输出: {LISTENER_CLEAN_CSV}")
    return df_clean

def build_historical_trends(df_clean):
    """从清洗后的历史收听数据构建归一化趋势（首日=100）"""
    if df_clean is None or df_clean.empty:
        return None
    df = df_clean.copy()
    df["year_month"] = df["data_date"].dt.to_period("M")
    monthly = df.groupby(["uid", "year_month"])["peak_listeners"].sum().reset_index()

    # 每个 uid 的归一化曲线
    trends = {}
    for uid, grp in monthly.groupby("uid"):
        grp = grp.sort_values("year_month")
        if len(grp) < 3:
            continue
        baseline = grp["peak_listeners"].iloc[0]
        if baseline <= 0:
            continue
        normalized = [round(v / baseline * 100, 1) for v in grp["peak_listeners"]]
        labels = [str(p) for p in grp["year_month"]]
        trends[uid] = {"labels": labels, "values": normalized, "raw": grp["peak_listeners"].tolist()}
    return trends

# ============================================================
def rebuild_dashboard():
    scan_dirs = [HISTORY_DIR, OUTPUT_DIR, DOWNLOAD_MAIN, DB_INCREMENT, QUICK_DIR]
    df_all, registry_info = load_all_history(scan_dirs)
    if df_all.empty:
        logger.error("未读取到任何数据，请检查 HISTORY_DIR / OUTPUT_DIR 等路径")
        return None

    # 从三个指定目录独立提取收听人数（同歌同日取最大值，归一化为比例趋势）
    listener_dirs = [HISTORY_DIR, DOWNLOAD_MAIN, QUICK_DIR]
    peak = extract_listener_from_dirs(listener_dirs)
    if peak is not None:
        df_all = df_all.merge(peak, on=["uid", "data_date"], how="left")

    logger.info(f"合并后歌曲记录: {len(df_all)} | 时间范围: {df_all['data_date'].min().date()} ~ {df_all['data_date'].max().date()} | 追踪歌曲(uid): {df_all['uid'].nunique()}")
    LINEAGE["dataset"] = {"records": int(len(df_all)),
                          "date_range": f"{df_all['data_date'].min().date()} ~ {df_all['data_date'].max().date()}",
                          "tracked_uids": int(df_all['uid'].nunique())}
    df_stats = analyze_recent_anomaly(df_all)
    dims = compute_dimensions(df_all, window_days=90)
    if not dims.empty:
        lc = dims["lifecycle"].value_counts().to_dict()
        logger.info(f"维度分析: {len(dims)} 首 | 近30日异常活跃: {len(df_stats)} 首")
        LINEAGE["lifecycle_dist"] = {str(k): int(v) for k, v in lc.items()}
    song_info = load_song_info(SONG_INFO_XLSX)
    # 长表为唯一输入：读巡演歌单长表（场次+歌单），并以其场次替代权威表巡演节点参与全站效应/时间轴
    setlists = load_setlist(SETLIST_LONG_XLSX)
    if setlists:
        song_info["tour_events"] = [
            {"date": d, "name": scene, "desc": info["tour"], "kind": "巡演"}
            for (d, scene), info in sorted(setlists.items(), key=lambda x: x[0][0])
        ]
        logger.info(f"场次事件改用长表: {len(song_info['tour_events'])} 场（巡演名称/日期以长表为准）")
    # 演出活动表（音乐剧等）：并入 setlists 参与歌曲级效应（辐射带动）分析；
    # 场次键已用"演出名·城市"避免与巡演键冲突，可安全 update。
    perf_events = load_performance_events(PERFORMANCE_EVENTS_XLSX)
    if perf_events:
        setlists.update(perf_events)
        song_info.setdefault("performance_events", []).extend(
            {"date": d, "name": scene, "desc": info["tour"], "kind": "音乐剧"}
            for (d, scene), info in sorted(perf_events.items(), key=lambda x: x[0][0])
        )
        logger.info(f"演出活动并入歌曲级效应: {len(perf_events)} 场（辐射带动分析含音乐剧演出）")
    # 清洗历史收听数据（首次运行较慢，后续读缓存CSV）
    df_hist = None
    hist_trends = None
    if os.path.exists(LISTENER_CLEAN_CSV):
        try:
            df_hist = pd.read_csv(LISTENER_CLEAN_CSV, encoding="utf-8-sig")
            df_hist["data_date"] = pd.to_datetime(df_hist["data_date"])
            logger.info(f"历史收听缓存已加载: {len(df_hist)} 条")
            LINEAGE["hist_cache_rows"] = int(len(df_hist))
        except Exception:
            pass
    if df_hist is None:
        df_hist = clean_historical_listeners()
    if df_hist is not None and not df_hist.empty:
        hist_trends = build_historical_trends(df_hist)
        if hist_trends:
            logger.info(f"历史收听趋势: {len(hist_trends)} 首歌曲有3月以上有效数据")
            LINEAGE["hist_trend_songs"] = int(len(hist_trends))
    # 构建 hist uid → 歌名 映射（通过参考文件 mid→name）
    hist_uid_names = {}
    if hist_trends:
        ref_mid2name, _ = build_reference_map(REFERENCE_LINK_XLSX)
        for uid in hist_trends:
            # uid 格式: M:mid 或 N:mid
            mid = uid[2:] if len(uid) > 2 else uid
            name = ref_mid2name.get(mid, "")
            if not name:
                name = uid  # fallback
            hist_uid_names[uid] = name
        
        # 合并同名歌曲：同一歌名可能对应多个 uid（不同版本/链接），按月汇总 raw 值
        name_to_uids = {}
        for uid, name in hist_uid_names.items():
            name_to_uids.setdefault(name, []).append(uid)
        merged_trends = {}
        merged_names = {}
        for name, uid_list in name_to_uids.items():
            if len(uid_list) == 1:
                merged_trends[uid_list[0]] = hist_trends[uid_list[0]]
                merged_names[uid_list[0]] = name
                continue
            # 多 uid 合并：按月汇总 raw 值
            monthly_raw = {}  # year_month → sum
            for uid in uid_list:
                ht = hist_trends.get(uid)
                if not ht:
                    continue
                for label, raw_val in zip(ht["labels"], ht["raw"]):
                    monthly_raw[label] = monthly_raw.get(label, 0) + raw_val
            if len(monthly_raw) < 3:
                continue
            sorted_months = sorted(monthly_raw.keys())
            raw_list = [monthly_raw[m] for m in sorted_months]
            baseline = raw_list[0]
            if baseline <= 0:
                continue
            normalized = [round(v / baseline * 100, 1) for v in raw_list]
            # 用第一个 uid 作为合并后的 key
            merged_uid = uid_list[0]
            merged_trends[merged_uid] = {"labels": sorted_months, "values": normalized, "raw": raw_list}
            merged_names[merged_uid] = name
        hist_trends = merged_trends
        hist_uid_names = merged_names
        logger.info(f"同名合并后: {len(hist_trends)} 首歌（含 {sum(1 for v in name_to_uids.values() if len(v)>1)} 组合并）")
    payload = build_dashboard_payload(df_all, df_stats, dims, song_info, registry_info, hist_trends, hist_uid_names, setlists=setlists)

    # === 原始数据本地归档（不公开，仅本地留存供深度分析）===
    raw_dir = os.path.join(OUTPUT_DIR, "raw_archive")
    os.makedirs(raw_dir, exist_ok=True)
    # 文件名带秒级时间戳 + 进程ID：防止手动 rebuild 与常驻批次并发时同分钟同名覆盖/读到半写文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid_tag = os.getpid()
    raw_excel = os.path.join(raw_dir, f"raw_{timestamp}_{pid_tag}.xlsx")
    df_all.to_excel(raw_excel, index=False)
    raw_json = os.path.join(raw_dir, f"raw_{timestamp}_{pid_tag}.json")
    df_all.to_json(raw_json, orient="records", force_ascii=False, date_format="iso")
    latest_excel = os.path.join(raw_dir, "raw_latest.xlsx")
    df_all.to_excel(latest_excel, index=False)
    logger.info(f"原始数据已本地归档: {raw_excel}（{len(df_all)} 行）")

    result = generate_dashboard(payload, DASHBOARD_DIR)
    # 自动部署到网站（失败不影响采集，仅记录日志）
    auto_deploy(DASHBOARD_DIR)
    return result

# ============================================================
# 第四部分：主采集流程 + 定时调度
# ============================================================
def main(mode="full", run_time_str=""):
    if not HAS_DRISSION:
        logger.error("未安装 DrissionPage，无法执行浏览器监测。请运行: pip install DrissionPage")
        return
    links = read_links(EXCEL_INPUT)
    total = len(links)
    if total == 0:
        return

    tab_count = TAB_COUNT_QUICK if mode == "quick" else TAB_COUNT_FULL
    est_per_item = 1.2 if mode == "quick" else 3.5
    est_seconds = (total / tab_count) * est_per_item
    logger.info(f"【{mode.upper()}模式】预估: {total}条 / {tab_count}并发 ≈ {est_seconds/60:.1f} 分钟")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    debug_dir = os.path.join(OUTPUT_DIR, "debug_html")
    os.makedirs(debug_dir, exist_ok=True)

    logger.info(f"启动 {mode.upper()} 监测 | 标签: {tab_count} | 任务: {total}条")
    start = time.time()

    browser = init_browser()

    tabs = [browser]
    for _ in range(tab_count - 1):
        tabs.append(browser.new_tab())

    q = queue.Queue()
    for item in links:
        q.put(item)

    results = []
    lock = threading.Lock()
    threads = []
    for tab in tabs:
        t = threading.Thread(target=worker, args=(tab, q, results, lock, debug_dir, total, mode))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    browser.quit()

    results.sort(key=lambda x: x["序号"])
    df_out = pd.DataFrame(results)

    if mode == "quick":
        col_order = ["序号", "歌曲名称", "演唱者", "当前时间", "当前收听人数", "链接", "状态"]
    else:
        col_order = ["序号", "歌曲名称", "演唱者", "昨日音乐指数", "较前一日",
                     "昨日全站排名", "较前一日1", "当前时间", "全站排名",
                     "音乐指数", "当前收听人数", "历史成绩", "链接", "状态"]
    col_order = [c for c in col_order if c in df_out.columns]
    df_out = df_out[col_order]

    out_name = get_output_filename(mode, run_time_str)

    # 归档路由：23:55 终批同时写入 download 与增补数据库；其余批次写入 指数vs
    if mode == "full" and run_time_str == "23:55":
        targets = [DOWNLOAD_MAIN, DB_INCREMENT]
    else:
        targets = [QUICK_DIR]
    saved_paths = []
    for d in targets:
        try:
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, out_name)
            base, ext = os.path.splitext(p)
            c = 1
            while os.path.exists(p):
                p = f"{base}_{c}{ext}"
                c += 1
            df_out.to_excel(p, index=False)
            saved_paths.append(p)
        except Exception as e:
            logger.error(f"保存到 {d} 失败: {e}")

    # 采集完成 -> 合并历史 + 新数据，重建大屏网页
    try:
        rebuild_dashboard()
    except Exception as e:
        logger.error(f"看板重建失败（监测数据已保存，不影响）: {e}", exc_info=True)

    elapsed = time.time() - start
    success = sum(1 for r in results if r["状态"] == "成功")
    warn = sum(1 for r in results if "警告" in r["状态"])
    fail = total - success - warn
    logger.info("=" * 60)
    logger.info(f"【{mode.upper()}完成】总计: {total} | 成功: {success} | 警告: {warn} | 失败: {fail} | 耗时: {elapsed:.1f}秒")
    for sp in saved_paths:
        logger.info(f"Excel 已存: {os.path.abspath(sp)}")
    logger.info("=" * 60)

# ==================== 定时调度与关机 ====================
def get_next_run_time():
    now = datetime.now()
    today = now.date()
    for t_str, mode in SCHEDULE:
        t = datetime.strptime(t_str, "%H:%M")
        target = datetime.combine(today, t.time())
        if target > now:
            return target, t_str, mode
    t_str, mode = SCHEDULE[0]
    t = datetime.strptime(t_str, "%H:%M")
    target = datetime.combine(today + timedelta(days=1), t.time())
    return target, t_str, mode

def schedule_shutdown():
    now = datetime.now()
    target = now.replace(hour=0, minute=10, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    seconds = int((target - now).total_seconds())
    if seconds > 0:
        os.system(f"shutdown -s -t {seconds}")
        logger.info(f"已设置自动关机: {target.strftime('%m-%d %H:%M')}，还有 {seconds//60} 分钟（每日 00:10 自动关机）")

def run_scheduler():
    logger.info("=" * 60)
    logger.info("QQ音乐双模式定时监测 + 大屏看板服务已启动（v3 维度增强版）")
    logger.info("=" * 60)
    for t_str, mode in SCHEDULE:
        tag = "【全量】" if mode == "full" else "【极速】"
        logger.info(f"  {tag} {t_str}")
    logger.info("=" * 60)

    try:
        rebuild_dashboard()
    except Exception as e:
        logger.warning(f"启动时重建看板失败（不影响监测）: {e}")

    while True:
        next_run, run_time_str, mode = get_next_run_time()
        now = datetime.now()
        wait_seconds = (next_run - now).total_seconds()

        if wait_seconds > 0:
            tag = "【全量】" if mode == "full" else "【极速】"
            logger.info(f"等待中... 下次{tag}: {next_run.strftime('%m-%d %H:%M')}，还需 {wait_seconds/60:.1f} 分钟")
            time.sleep(wait_seconds)

        logger.info(f">>> 开始执行 {run_time_str} {mode.upper()} 批次 <<<")
        try:
            main(mode=mode, run_time_str=run_time_str)
        except Exception as e:
            logger.error(f"监测异常: {e}", exc_info=True)

        if run_time_str == "23:55" and mode == "full":
            schedule_shutdown()

        time.sleep(60)

# ==================== 命令行入口 ====================
def parse_args():
    p = argparse.ArgumentParser(description="QQ音乐监测 + 历史归档 + 大屏看板 v3")
    p.add_argument("--once", action="store_true", help="立刻监测一次后退出")
    p.add_argument("--full", action="store_true", help="配合 --once：全量模式")
    p.add_argument("--quick", action="store_true", help="配合 --once：极速模式")
    p.add_argument("--rebuild", action="store_true", help="不监测，仅用已有 Excel 重建网页")
    p.add_argument("--excel", default=None, help="链接清单 xlsx 路径")
    p.add_argument("--records", default=None, help="监测数据输出目录")
    p.add_argument("--history", default=None, help="历史归档目录")
    p.add_argument("--dashboard", default=None, help="网页输出目录")
    p.add_argument("--song-info", default=None, help="歌曲信息汇总 xlsx 路径")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.excel:
        EXCEL_INPUT = args.excel
    if args.records:
        OUTPUT_DIR = args.records
    if args.history:
        HISTORY_DIR = args.history
    if args.song_info:
        SONG_INFO_XLSX = args.song_info
    if args.dashboard:
        DASHBOARD_DIR = args.dashboard
    elif args.records:
        DASHBOARD_DIR = os.path.join(OUTPUT_DIR, "dashboard")

    if args.rebuild:
        rebuild_dashboard()
    elif args.once:
        mode = "quick" if args.quick else "full"
        main(mode=mode, run_time_str=datetime.now().strftime("%H:%M"))
    else:
        run_scheduler()
