# -*- coding: utf-8 -*-
# 薄包装：从 ASCII 路径调用 E:/wx/私有工具/xhs_proxy/rebuild_xhs_summary.py
# 规避 cmd chcp 65001 下中文路径传参乱码（与 run_weibo_snapshot 同理）。
import runpy
import sys

sys.argv[0] = r"E:\wx\私有工具\xhs_proxy\rebuild_xhs_summary.py"
runpy.run_path(r"E:\wx\私有工具\xhs_proxy\rebuild_xhs_summary.py",
               run_name="__main__")
