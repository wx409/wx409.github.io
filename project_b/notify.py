# -*- coding: utf-8 -*-
"""notify.py —— 通知模块（双通道：Server酱微信推送 + SMTP 邮件，失败静默不阻塞）

配置（敏感，不进 git！）：E:\wx\私有工具\notify_config.json
{
  "serverchan_key": "SCTxxxxx",              # 可选：Server酱 Turbo SendKey（sct.ftqq.com 免费注册）
  "smtp": {                                  # 可选：邮件通道（如 QQ 邮箱授权码）
    "host": "smtp.qq.com", "port": 465,
    "user": "your@qq.com", "password": "授权码",
    "to": ["your@qq.com"]
  }
}
未配置时静默跳过并打印提示，不影响主流程。
"""
import json
import ssl
import smtplib
import urllib.parse
import urllib.request
from email.header import Header
from email.mime.text import MIMEText

CONFIG_PATH = r"E:\wx\私有工具\notify_config.json"
_CONFIG = None


def _cfg():
    global _CONFIG
    if _CONFIG is None:
        try:
            _CONFIG = json.load(open(CONFIG_PATH, encoding="utf-8"))
        except Exception:
            _CONFIG = {}
    return _CONFIG


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
    """发送通知；未配置/失败均不抛异常"""
    ok1 = serverchan(title, content)
    ok2 = email(title, content)
    if not ok1 and not ok2:
        print("[notify] 未配置通知通道（%s），跳过推送" % CONFIG_PATH)
        return False
    print("[notify] 推送完成（微信:%s 邮件:%s）" % ("OK" if ok1 else "-", "OK" if ok2 else "-"))
    return ok1 or ok2


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "测试通知"
    c = sys.argv[2] if len(sys.argv) > 2 else "王晰数字档案通知通道测试 ✅"
    send(t, c)
