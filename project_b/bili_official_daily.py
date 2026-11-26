# -*- coding: utf-8 -*-
import subprocess, sys
args = [sys.executable, "-X", "utf8", r"D:\wx409.github.io\project_b\download_bilibili.py",
        "--space", "3493257487059302",
        "--out", r"E:\wx\论文素材_王晰作传\B站\官方空间"]
raise SystemExit(subprocess.run(args).returncode)
