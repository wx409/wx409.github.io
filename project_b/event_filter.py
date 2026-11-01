"""事件过滤（Fast Path）：用确定性规则决定「这一轮要不要真的去抓」

对应 Super-agent 文档 3.1「Fast Path / Slow Path」：
  Fast Path（本模块）：价格低的确定性判断，先挡掉大部分无意义轮次
  Slow Path（后续脚本）：真正调用网络/模型

规则：
  1. 距上次运行 < MIN_GAP 且上次新增为 0 → 视为无变化，跳过
  2. 最近一次运行处于夜间安静期（默认 00:00–07:30）→ 跳过
  3. --force 一律放行
状态文件：data/.event_state.json
"""
import json
import os
import time

STATE = r"D:\wx409.github.io\data\.event_state.json"
MIN_GAP = 2 * 3600          # 2 小时
QUIET_START, QUIET_END = 0, 730   # 分钟：0:00–7:30


def _load():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(d):
    json.dump(d, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def should_run(job="interview_patrol", force=False):
    """返回 (bool, 原因)"""
    if force:
        return True, "force"
    now = time.time()
    tm = time.localtime(now)
    minute = tm.tm_hour * 60 + tm.tm_min
    if QUIET_START <= minute < QUIET_END:
        return False, "夜间安静期（%02d:%02d）" % (tm.tm_hour, tm.tm_min)
    st = _load().get(job) or {}
    last = st.get("ts", 0)
    last_new = st.get("new", -1)
    if last and (now - last) < MIN_GAP and last_new == 0:
        return False, "距上次 %.0f 分钟且上次新增 0 条" % ((now - last) / 60)
    return True, "有运行条件"


def done(job="interview_patrol", new_count=0, note=""):
    d = _load()
    d[job] = {"ts": time.time(), "at": time.strftime("%Y-%m-%d %H:%M"), "new": new_count, "note": note}
    _save(d)
