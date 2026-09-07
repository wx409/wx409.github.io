# -*- coding: utf-8 -*-
"""verify_dashboard.py —— dashboard/index.html 结构三查（防裸 CSS / 悬空 style 复发）

用法:
    python tools/verify_dashboard.py [dashboard/index.html 路径]
    不带参数时默认检查仓库内 dashboard/index.html。

三查:
    1) <style> 与 </style> 计数配对（各 >=1 且相等，杜绝悬空 / 提前闭合）
    2) </head> 之前无裸文本（最后一个 </style> 与 </head> 之间必须为空白）
    3) <body> 必须位于 </head> 之后

退出码: 0=通过   1=不通过
"""
import os
import sys


def check(html):
    """返回错误列表；空列表 = 通过。"""
    errs = []
    opens = html.count("<style")
    closes = html.count("</style>")
    if opens == 0 or opens != closes:
        errs.append("<style> 开/闭不配对: open=%d close=%d" % (opens, closes))
    head_end = html.find("</head>")
    if head_end == -1:
        errs.append("缺少 </head>")
    else:
        last_style_end = html.rfind("</style>")
        if last_style_end == -1 or last_style_end > head_end:
            errs.append("</style> 应整体位于 </head> 之前")
        else:
            between = html[last_style_end + len("</style>"):head_end]
            if between.strip():
                errs.append("</style> 与 </head> 之间有裸文本: %r" % between.strip()[:60])
    body_at = html.find("<body")
    if body_at == -1 or (head_end != -1 and body_at < head_end):
        errs.append("<body> 缺失或位于 </head> 之前")
    return errs


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default = os.path.normpath(os.path.join(here, "..", "dashboard", "index.html"))
    p = sys.argv[1] if len(sys.argv) > 1 else default
    if not os.path.exists(p):
        print("[FAIL] 文件不存在: %s" % p)
        return 1
    with open(p, encoding="utf-8") as f:
        html = f.read()
    errs = check(html)
    if errs:
        print("[FAIL] %s" % p)
        for e in errs:
            print("  -", e)
        return 1
    print("[OK] %s  <style>配对=%d 组 | </head> 前无裸文本 | <body> 位置正常"
          % (p, html.count("<style")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
