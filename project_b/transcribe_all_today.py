# -*- coding: utf-8 -*-
import subprocess, sys
from pathlib import Path
ROOT = Path(r"D:\wx409.github.io")
py = sys.executable
subprocess.run([py, "-X", "utf8", str(ROOT / "project_b" / "transcribe_video_songs.py"), "--resume"])
subprocess.run([py, "-X", "utf8", str(ROOT / "project_b" / "match_video_lyrics.py")])
