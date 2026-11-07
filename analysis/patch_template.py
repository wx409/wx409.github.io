# -*- coding: utf-8 -*-
"""模板补丁（已统一）：本文件只做转发。

真正的唯一入口是 `project_b/template_patches.py`：
  · 幂等：已打过就跳过，锚点丢了报 DRIFT 并退出 1
  · 一处改动：只写母版 E:\wx，然后同步仓库快照 project_b
所以不要再在这里写替换逻辑，改补丁去改 template_patches.py 的 PATCHES 表。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "project_b" / "template_patches.py"
raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", str(TARGET), *sys.argv[1:]]))
