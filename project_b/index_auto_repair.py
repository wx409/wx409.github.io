"""每日 23:50 兜底：检查并自动补录昨天之前的指数缺日（语义同 check_index_freshness，但独立成脚本以便登记）"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "project_b" / "check_index_freshness.py"
sys.exit(subprocess.call([sys.executable, "-X", "utf8", str(TARGET)]))
