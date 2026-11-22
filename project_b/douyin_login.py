# -*- coding: utf-8 -*-
"""douyin_login.py —— 打开抖音扫码登录，成功后把 cookie 写回 douyin_cookie_raw.txt"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"E:\wx\index_records\douyin_cookie_raw.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(user_agent=UA, viewport={"width": 1280, "height": 900}, locale="zh-CN")
    page = ctx.new_page()
    page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
    print("请在弹出的浏览器里扫码登录抖音；最多等 600 秒…", flush=True)
    ok = False
    for _ in range(200):
        page.wait_for_timeout(3000)
        cs = ctx.cookies()
        if any(c.get("name") == "sessionid" and c.get("value") for c in cs):
            raw = "; ".join("%s=%s" % (c["name"], c["value"]) for c in cs if c.get("domain", "").endswith("douyin.com"))
            OUT.write_text(raw, encoding="utf-8")
            print("登录成功，cookie 已写入", len(raw), flush=True)
            ok = True
            break
    if not ok:
        print("未检测到登录（600 秒超时）", flush=True)
    b.close()
