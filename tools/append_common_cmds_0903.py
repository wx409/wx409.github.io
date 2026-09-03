# -*- coding: utf-8 -*-
"""把 2026-09-03 的工作室微博全量同步说明追加到 D:\\一些常用的命令.txt。

用法（在普通 PowerShell 中运行，需要有 D:\\ 写权限）：
  python -X utf8 D:\\wx409.github.io\\tools\\append_common_cmds_0903.py
"""
from pathlib import Path

p = Path(r"D:\一些常用的命令.txt")
section = """

# ============================================================
# 9-03 追加：工作室微博全量爬取后 -> 活动表 / 长表 / 网站全量更新
# 完整备忘: D:\\wx409.github.io\\temp\\运维备忘_20260903.md
# ============================================================

# 0) 已确认最新版长表（截至 2026-09-03）:
#    E:\\wx\\index_records\\历次巡演歌单\\王晰巡演歌单长表_单一事实源.xlsx
#    - 主文件 LastWriteTime: 2026-08-24 13:14
#    - 无更新的备份文件；该路径是所有脚本读取的唯一事实源
#    - 活动表: E:\\wx\\index_records\\王晰演出活动.xlsx (LastWriteTime: 2026-09-01)

# 1) 工作室微博 -> 活动表（可以自动追加）
#    提取管线：
cd /d E:\\wx\\私有工具\\weibo_proxy
python -X utf8 classify_events.py
python -X utf8 cluster_events.py
python -X utf8 extract_events_llm.py            # 需 DeepSeek key；无 key 用 --no-llm 跳过
python -X utf8 build_events_excel.py
python -X utf8 append_perf_to_table.py          # 高置信“演出”追加到活动表 xlsx

# 2) 工作室微博 -> 巡演歌单长表（不能直接整段文本加入）
#    长表每行 = 一场巡演里的一首歌；只有确认是“巡演场次/歌单/曲序”才追加。
#    活动类（晚会/音乐节/发布会/音乐剧等）只进活动表，不进长表。

# 3) 网站/知识库全量更新（一次跑完）
python -X utf8 D:\\wx409.github.io\\tools\\update_studio_full_pipeline.py
# 无 DeepSeek key 时：
python -X utf8 D:\\wx409.github.io\\tools\\update_studio_full_pipeline.py --no-llm

# 4) 多视频补下载/高清修复
cd /d E:\\wx\\私有工具\\weibo_proxy
python -X utf8 weibo_proxy_studio.py fetch --fix-videos --multi-only --since 2026-08-01
python -X utf8 archive_studio_full.py

# 5) 工作室微博全量（不过滤关键词，已更新 --all）
cd /d E:\\wx\\私有工具\\weibo_proxy
python -X utf8 weibo_proxy_studio.py fetch --all
"""

if not p.exists():
    raise SystemExit(f"找不到 {p}")

text = p.read_text(encoding="utf-8")
if "9-03 追加：工作室微博全量爬取后" in text:
    print("已存在 9-03 段落，跳过。")
else:
    p.write_text(text + section, encoding="utf-8")
    print(f"已追加到 {p}")
