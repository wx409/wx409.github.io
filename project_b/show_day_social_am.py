#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""次日早晨补收：调用 show_day_social.py --slot am（独立脚本名，便于计划任务登记）。"""
import sys

sys.argv = [sys.argv[0], "--slot", "am"]
from show_day_social import main  # noqa: E402

raise SystemExit(main())
