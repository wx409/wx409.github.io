# -*- coding: utf-8 -*-
"""把 2026-09-03 晚间的补充修改追加到 D:\\一些常用的命令.txt。

用法（在普通 PowerShell 中运行，需要有 D:\\ 写权限）：
  python -X utf8 D:\\wx409.github.io\\tools\\append_common_cmds_0903b.py
"""
from pathlib import Path

p = Path(r"D:\一些常用的命令.txt")
section = """

# ============================================================
# 9-03b 追加：全量同步执行结果 / 长表核对结论 / 点歌补全
# 完整备忘: D:\\wx409.github.io\\temp\\运维备忘_20260903.md
# ============================================================

# 1) 工作室微博全量同步已执行成功
#    归档 2204 篇；文本语料在 weibo_merged\\工作室微博_完整
#    活动表已追加 5 条高置信演出；live-reviews 已插入 274 条工作室微博
#    日志: logs\\studio_full_20260903_181054.log

# 2) 长表核对结论：巡演场次不需要增加
#    5 条疑似歌单差异经人工复核：
#    - 甩啦甩啦 = 长表已有 甩了甩了
#    - 千万次地问 = 长表已有 千万次的问
#    - 敕勒川 = 长表已有 敕勒歌
#    - 南昌“不说，不散” = 专辑宣传语，不是演唱曲
#    - 漫长的告别 = 长表确实缺失，确认为 2021-01-10 武汉站点歌
#    因此只需要补《漫长的告别》。

# 3) 点歌安全补全脚本（带备份 + 别名去重）
python -X utf8 D:\\wx409.github.io\\tools\\append_point_songs_to_longtable.py --dry-run   # 预览
python -X utf8 D:\\wx409.github.io\\tools\\append_point_songs_to_longtable.py             # 正式写入

# 4) 如果以后继续做“全量点歌自动补全”，可扩展 append_point_songs_to_longtable.py
"""
text = p.read_text(encoding="utf-8")
if "9-03b 追加" in text:
    print("已存在 9-03b 段落，跳过。")
else:
    p.write_text(text + section, encoding="utf-8")
    print(f"已追加 9-03b 到 {p}")
