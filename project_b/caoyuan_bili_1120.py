# -*- coding: utf-8 -*-
import subprocess, sys
base = r"D:\wx409.github.io\project_b"
args = [sys.executable, "-X", "utf8", base + r"\collect_show_feedback.py",
        "--date", "2026-11-20", "--city", "苏州", "--bili-only",
        "--bili-pages", "3", "--bili-order", "pubdate"]
raise SystemExit(subprocess.run(args).returncode)
