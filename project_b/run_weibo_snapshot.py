# -*- coding: utf-8 -*-
"""薄包装：从 ASCII 路径调用 temp\预测实验\make_weibo_snapshot.py
用途：操作中心.bat 在 chcp 65001 下无法正确传中文路径参数给 python，
      用本包装避免命令行出现中文。用法同原脚本：--once 增量 / 默认全量。
"""
import runpy
import sys

sys.argv[0] = r"temp\预测实验\make_weibo_snapshot.py"
runpy.run_path(r"D:\wx409.github.io\temp\预测实验\make_weibo_snapshot.py",
               run_name="__main__")
