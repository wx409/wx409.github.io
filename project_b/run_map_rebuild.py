# -*- coding: utf-8 -*-
"""薄包装：从 ASCII 路径调用地图/巡演目录生成器（供 操作中心.bat 菜单项）
规避 cmd chcp 65001 下中文路径传参乱码的问题。
生成内容：
  - data/cities.json + map/index.html   （generate_cities_json.py，读长表）
  - live/index.html                      （generate_tour_index.py，读长表）
单一事实源：巡演歌单长表。改长表后跑本脚本，地图/目录自动联动。
"""
import runpy
import sys

sys.path.insert(0, r"D:\wx409.github.io")

# 1) 地图（含城市一览/JSON-LD）—— 输出 data/cities.json + map/index.html
runpy.run_path(r"E:\wx\私有工具\generate_cities_json.py", run_name="__main__")
# 2) 巡演目录页 —— 输出 live/index.html
runpy.run_path(r"D:\wx409.github.io\generate_tour_index.py", run_name="__main__")

print("地图 + 巡演目录已重建（长表 → cities.json / map / live 目录）")
