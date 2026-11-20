# -*- coding: utf-8 -*-
import subprocess, sys
base = r"D:\wx409.github.io\project_b"
args = [sys.executable, "-X", "utf8", base + r"\feedback_week.py",
        "--date", "2026-11-20", "--city", "苏州", "--no-collect"]
raise SystemExit(subprocess.run(args).returncode)
