# -*- coding: utf-8 -*-
"""notify.py —— 通知模块（默认留存本地表格，不再使用 Server酱推送）

本地表格：D:\wx409.github.io\data\notifications.json
网站查看：https://wx409.github.io/notifications.html

SMTP 邮件仍为可选通道；若未配置则只写本地表格。
若确实需要临时启用 Server酱，可设环境变量 ALLOW_SERVERCHAN=1。

配置（敏感，不进 git！）：E:\wx\私有工具\notify_config.json
{
  "smtp": {                                  # 可选：邮件通道（如 QQ 邮箱授权码）
    "host": "smtp.qq.com", "port": 465,
    "user": "your@qq.com", "password": "授权码",
    "to": ["your@qq.com"]
  }
}
未配置邮件时静默跳过，只留存本地表格，不影响主流程。
"""
import json
import os
import ssl
import smtplib
import urllib.parse
import urllib.request
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_PATH = r"E:\wx\私有工具\notify_config.json"
LOCAL_JSON = Path(r"D:\wx409.github.io\data\notifications.json")
_CONFIG = None


def _cfg():
    global _CONFIG
    if _CONFIG is None:
        try:
            _CONFIG = json.load(open(CONFIG_PATH, encoding="utf-8"))
        except Exception:
            _CONFIG = {}
    return _CONFIG


def append_local(title, content):
    """把通知追加到 data/notifications.json，供网站 notifications.html 展示。"""
    try:
        LOCAL_JSON.parent.mkdir(parents=True, exist_ok=True)
        if LOCAL_JSON.exists():
            data = json.loads(LOCAL_JSON.read_text(encoding="utf-8"))
        else:
            data = {}
        items = data.get("items", [])
        items.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": str(title)[:200],
            "content": str(content)[:4000],
        })
        # 只保留最近 500 条，避免文件无限变大
        data["items"] = items[-500:]
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        LOCAL_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return True
    except Exception as e:
        print("[notify] 本地表格写入失败: %s" % e)
        return False


def serverchan(title, content):
    """Server酱 Turbo：微信推送（免费版每日 5 条，足够）"""
    key = _cfg().get("serverchan_key")
    if not key:
        return False
    try:
        url = "https://sctapi.ftqq.com/%s.send" % key
        data = urllib.parse.urlencode({"title": title[:32], "desp": content[:4000]}).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        r = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "ignore"))
        return r.get("code") == 0
    except Exception:
        return False


def email(title, content):
    """SMTP 邮件（国内邮箱稳定）"""
    sm = _cfg().get("smtp")
    if not sm:
        return False
    try:
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = Header(title, "utf-8")
        msg["From"] = sm["user"]
        msg["To"] = ",".join(sm["to"])
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(sm["host"], sm["port"], context=ctx, timeout=15) as s:
            s.login(sm["user"], sm["password"])
            s.sendmail(sm["user"], sm["to"], msg.as_string())
        return True
    except Exception:
        return False


def send(title, content):
    """发送通知；默认留存本地表格，不再使用 Server酱。

    如需临时启用 Server酱：设置环境变量 ALLOW_SERVERCHAN=1。
    SMTP 邮件仍为可选；未配置时只写本地表格。
    """
    ok_local = append_local(title, content)

    # Server酱默认停用
    ok1 = False
    if os.environ.get("ALLOW_SERVERCHAN") == "1":
        ok1 = serverchan(title, content)

    ok2 = email(title, content)

    if ok_local:
        print("[notify] 已写入本地表格: %s" % LOCAL_JSON)
    if ok1 or ok2:
        print("[notify] 外部推送完成（微信:%s 邮件:%s）" % ("OK" if ok1 else "-", "OK" if ok2 else "-"))
    elif not ok_local:
        print("[notify] 未配置通知通道（%s），跳过推送" % CONFIG_PATH)
    return ok_local or ok1 or ok2


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "测试通知"
    c = sys.argv[2] if len(sys.argv) > 2 else "王晰数字档案通知通道测试 ✅"
    send(t, c)
