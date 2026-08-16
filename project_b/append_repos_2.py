# -*- coding: utf-8 -*-
"""合并三巡~六巡 repo 数据到 data/live_repos.json（子代理全网调研，2026-08-16）"""
import json

P = r"D:\wx409.github.io\data\live_repos.json"
d = json.load(open(P, encoding="utf-8"))
R = d["repos"]

ADD = {
    # ---- 三巡 图景 ----
    "2021-12-04": [
        {"title": "王晰图景个人巡回音乐会 三巡广州站（上半场）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1tZ4y197q4/", "level": "verified"},
        {"title": "【王晰】Moon River @ 20211204 图景个巡 广州站", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1TS4y197iv/", "level": "verified"},
        {"title": "【王晰】时空 @ 20211204 图景个巡 广州站", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1dP4y1377Y/", "level": "verified"},
        {"title": "《这世界那么多人》降噪纯净版live音频 图景广州站", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1cS4y117QZ/", "level": "verified"}
    ],
    "2022-01-09": [
        {"title": "【王晰三巡】《You Needed Me》20220109 无锡", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Em421472q/", "level": "single"},
        {"title": "2022开年巡演无锡上海站幕后vlog（晰息TV）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1WP4y177Vf/", "level": "single"}
    ],
    "2022-01-10": [
        {"title": "《高级动物》20220110 上海 东方艺术中心", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Tz421z7YD/", "level": "verified"},
        {"title": "《知晓》20220110 上海 东方艺术中心", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Cb421J7Vt/", "level": "verified"},
        {"title": "被声浪死死拍在座位上的感受 20220110 上海", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Pu4y1z7bN/", "level": "verified"},
        {"title": "“低音绅士”王晰登台上海：嗓音亦是乐器", "platform": "文汇网", "url": "https://www.whb.cn/zhuzhan/yingshi/20220111/443547.html", "level": "official"}
    ],
    "2022-04-09": [
        {"title": "王晰合作Pico打造VR线上音乐会", "platform": "93913", "url": "https://www.93913.com/71890.html", "level": "official"},
        {"title": "王晰与Pico合作的VR音乐会圆满落幕", "platform": "网易", "url": "http://www.163.com/dy/article/H4MH7BNS05269O3G.html", "level": "official"},
        {"title": "火山引擎支持Pico完成业界首场8K 3D实时互动VR演唱会", "platform": "太平洋电脑网", "url": "https://news.pconline.com.cn/1494/14945506.html", "level": "official"},
        {"title": "PICO Community 用户帖", "platform": "PICO社区", "url": "https://bbs.picoxr.com/post/7096148040251080735", "level": "single"}
    ],
    "2022-07-15": [
        {"title": "20220715王晰图景音乐会太原站全程自录存档", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1MT411n7CK/", "level": "verified"},
        {"title": "王晰《知晓》图景三巡 太原", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Rg411o7uU/", "level": "verified"},
        {"title": "王晰《突然想爱你|眼泪》图景三巡 太原", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1fa411n72Z/", "level": "verified"}
    ],
    "2022-07-17": [
        {"title": "王晰点歌part【旋木/朋友别哭/在水一方】鄂尔多斯站20220717", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1WF411K75D/", "level": "verified"},
        {"title": "王晰《达尔文|车站》图景三巡 鄂尔多斯", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV18F411N7PF/", "level": "verified"},
        {"title": "王晰《突然想爱你|眼泪》图景三巡 鄂尔多斯", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1md4y1Q72Z/", "level": "verified"}
    ],
    "2022-09-17": [
        {"title": "《月半弯》20220917 武汉 琴台大剧院", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV19YsDeSEKe/", "level": "single"},
        {"title": "《倒叙》20220917 武汉 琴台大剧院", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1m8UKY4E4C/", "level": "single"}
    ],
    "2023-05-01": [
        {"title": "《Close to you》王晰三巡郑州站 20230501", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV14T411h7Ti/", "level": "verified"},
        {"title": "王晰【高级动物】20230501图景音乐会郑州站", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1GT411477S/", "level": "verified"},
        {"title": "王晰图景个巡郑州站talk点歌", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Ng4y1j7rr/", "level": "verified"},
        {"title": "王晰《你的样子》图景郑州站 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1vh4y1b7n2/", "level": "verified"}
    ],
    "2023-05-03": [
        {"title": "《Close to you》王晰三巡昆明站 20230503", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1yz4y1t7zg/", "level": "verified"},
        {"title": "《爱你》20230503 昆明 云南省大剧院", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV13xDCYkEEk/", "level": "verified"},
        {"title": "《突然想爱你|眼泪》20230503 昆明", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1AS411A7jp/", "level": "verified"},
        {"title": "王晰图景个巡昆明站talk点歌", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1zc411T7zq/", "level": "verified"},
        {"title": "昆明王晰“图景”巡回音乐会曲目单", "platform": "昆明本地宝", "url": "http://km.bendibao.com/xiuxian/2022923/65419.shtm", "level": "official"}
    ],
    "2023-05-20": [
        {"title": "《车站》图景南宁站 20230520", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1iM4y1v7X7/", "level": "verified"},
        {"title": "《Moon River》20230520 南宁 广西文化艺术中心", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1gPyxYGEoe/", "level": "verified"},
        {"title": "点歌《白鸽》20230520 南宁", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1LeY7eJE3y/", "level": "verified"},
        {"title": "《一生中最爱》20230520 南宁", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1zbzSYyEbz/", "level": "verified"},
        {"title": "钢伴组曲《这世界那么多人/暧昧/叶子/同类》南宁站", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1HP41197Nx/", "level": "verified"}
    ],
    # ---- 四巡 肆益 ----
    "2023-12-31": [
        {"title": "《海然海然|嘎达梅林》20231231 上海", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Me411m7DA/", "level": "verified"},
        {"title": "点歌《听海》20231231 上海 北外滩友邦大剧院", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1EwiUYYEHx/", "level": "verified"},
        {"title": "《友谊地久天长》20231231 上海", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1te411i7to/", "level": "verified"},
        {"title": "《也许》231231 上海", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Cc411477j/", "level": "verified"},
        {"title": "《人世间》231231 上海", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV115411q713/", "level": "verified"},
        {"title": "《人世间》三机位字幕 上海跨年站 20231231", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1QK411s7C9/", "level": "verified"}
    ],
    "2024-01-27": [
        {"title": "王晰《甩啦甩啦》肆益南京站 20240127", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1tv421i75o/", "level": "verified"},
        {"title": "王晰《友谊地久天长》肆益南京站 20240127", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1pc411v7gU/", "level": "verified"}
    ],
    "2024-03-30": [
        {"title": "点歌《美丽的草原我的家》肆益重庆站20240330", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Bm411k72j/", "level": "verified"},
        {"title": "点歌《亲爱的小孩》20240330 重庆 施光南大剧院", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1y5VV67Eiq/", "level": "verified"},
        {"title": "王晰肆益个人巡回音乐会重庆站talk点歌", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1kD421V7i1/", "level": "verified"}
    ],
    "2024-04-06": [
        {"title": "4.6肆益上海生日特别场《梦醒时分》", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Jp42197jA/", "level": "verified"},
        {"title": "梦醒时分 20240406上海生日特别场点歌", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Vq421c74B/", "level": "verified"},
        {"title": "人世间 20240406上海生日特别场", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1yD421G7kS/", "level": "verified"},
        {"title": "《崇拜》肆益上海生日特别场 20240406", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1qT421m7Sd/", "level": "verified"},
        {"title": "王晰“肆益”上海生日特别场票务", "platform": "有票网", "url": "http://www.piaoniu.com/activity/327700", "level": "official"}
    ],
    "2024-05-25": [
        {"title": "杭州站《多听有益》（饭拍，检索标注日期待核）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1ArKxe7E8H/", "level": "single", "note": "检索未标注具体日期，按站内杭州场日期收录"},
        {"title": "是你-王晰肆益音乐会（杭州场）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1Ay411Y7NR/", "level": "single", "note": "检索未标注具体日期，按站内杭州场日期收录"}
    ],
    # ---- 五巡 吾 ----
    "2024-12-21": [
        {"title": "【王晰】新专辑主打曲《在路上》4K混剪（含杭州20241221/南昌20241229/长沙20250101）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1FprNYZELg/", "level": "single", "note": "综合剪辑，覆盖五巡首三场"}
    ],
    "2024-12-29": [
        {"title": "王晰《当爱已成往事》巡演点歌part｜现场听到没忍住掉眼泪", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1fMcjevEJ4/", "level": "single", "note": "检索标注南昌20241229"},
        {"title": "【王晰】《在路上》4K混剪（含南昌20241229片段）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1FprNYZELg/", "level": "single"}
    ],
    "2025-01-01": [
        {"title": "王晰《晚婚》「吾」个人巡回音乐会长沙场 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1zwrwYyEL5/", "level": "verified", "note": "检索标注日期待核，按站内长沙场日期收录"},
        {"title": "王晰《暗潮涌动》「吾」个人巡回音乐会长沙场", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1rPrKYfEBf/", "level": "verified", "note": "检索标注日期待核，按站内长沙场日期收录"},
        {"title": "王晰《在路上》吾个人巡回音乐会长沙站（标注20250101）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1kRrcYJEDW/", "level": "single"}
    ],
    "2025-05-24": [
        {"title": "曲目单揭秘！王晰邀你共赴星河夜宴", "platform": "有演出网", "url": "https://www.youyanchu.com/yanchu/32896.html", "level": "official", "note": "检索标注2025-05-24成都场，与站内广州场日期口径不一致，待核"},
        {"title": "王晰相关现场视频", "platform": "微博（@四川卫视）", "url": "https://weibo.com/tv/show/1034:5157193771581481", "level": "single", "note": "检索标注2025-05-24成都场，待核"},
        {"title": "王晰《囚鸟》「吾」个人巡回音乐会广州站 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1dkjSzREJA/", "level": "verified", "note": "检索标注2025-06-14，与站内05-24口径不一致，待核"},
        {"title": "王晰《爱情转移》「吾」个人巡回音乐会广州站 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1s9jRzXEH3/", "level": "verified", "note": "检索标注2025-06-14，与站内05-24口径不一致，待核"},
        {"title": "王晰【钢伴组曲】《我真的受伤了•遗憾•从前的我•萱草花》广州场", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1M4jGz3Edk/", "level": "verified", "note": "检索标注2025-06-14，与站内05-24口径不一致，待核"}
    ],
    "2025-11-21": [
        {"title": "王晰携个人巡回音乐会“吾”登陆北外滩，歌单藏着“心灵处方”", "platform": "澎湃新闻", "url": "https://m.thepaper.cn/newsDetail_forward_32014074", "level": "official"},
        {"title": "（同稿）腾讯新闻", "platform": "腾讯新闻", "url": "https://news.qq.com/rain/a/20251121A03OT600", "level": "official"},
        {"title": "你怎么舍得我难过 王晰吾巡上海北外滩点歌20251121", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1bMU7BDEYV/", "level": "verified"},
        {"title": "【王晰】《床前明月光》4K字幕 20251121上海北外滩友邦大剧院", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1s3qCBsEt7/", "level": "verified"},
        {"title": "王晰吾个人巡回音乐会视频", "platform": "微博（@王晰的杂货铺）", "url": "https://weibo.com/tv/show/1034:5236077569441819", "level": "verified"},
        {"title": "摘一兜月光（现场文字repo）", "platform": "微博", "url": "https://m.weibo.cn/detail/5236251335590425", "level": "single"},
        {"title": "06 萱草花", "platform": "微博（@_After18_）", "url": "https://weibo.com/tv/show/1034:5235563813601354", "level": "single"}
    ],
    "2026-04-10": [
        {"title": "王晰五巡「吾」个人巡回音乐会北京生日收官站全程", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1yWQMB8EoK/", "level": "verified", "note": "检索标注2025-12-13，与站内2026-04-10口径不一致，待核"},
        {"title": "王晰《我变了我没变》北京收官场 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1gJDmBkEb3/", "level": "verified", "note": "同上，待核"},
        {"title": "王晰《My oh My》北京收官场", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1XMQbBcE8m/", "level": "verified", "note": "同上，待核"},
        {"title": "王晰《鹅毛信》北京收官场", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1kZDUBvEE2/", "level": "verified", "note": "同上，待核"},
        {"title": "王晰《哭砂》北京收官场", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV19cDXBFEng/", "level": "verified", "note": "同上，待核"},
        {"title": "王晰《给电影人的情书》北京收官场 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1z4DDBeEaM/", "level": "verified", "note": "同上，待核"},
        {"title": "王晰《十年》北京收官场 点歌环节", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1LAD1B1Eou/", "level": "verified", "note": "同上，待核"},
        {"title": "王晰Elvis-晰息相关", "platform": "微博", "url": "https://weibo.com/tv/show/1034:5292304144203789", "level": "single", "note": "同上，待核"},
        {"title": "王晰《钟爱一生》4K", "platform": "微博（@不要总是哭唧唧）", "url": "https://weibo.com/tv/show/1034:5293073622827030", "level": "single", "note": "同上，待核"}
    ],
    # ---- 六巡 回 ----
    "2026-06-13": [
        {"title": "第四届重庆都市艺术节｜低音绅士回归舞台 王晰“回”巡回音乐会重庆站本周六开唱", "platform": "华龙网/重庆新闻网", "url": "https://www.cqnews.net/web/content_1514730735102521344.html", "level": "official"},
        {"title": "王晰「回×重庆」20260613 回溯之巡 重逢之庆（全场纯享）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1KwJx6iEza/", "level": "verified"},
        {"title": "王晰【情网】4K字幕 王晰回个人巡回音乐会重庆站20260613", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1wvJP6eE5M/", "level": "verified"},
        {"title": "王晰 20260613“回”重庆站《女人花》×《水中花》", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1eyJ366Erx/", "level": "verified"},
        {"title": "王晰你是不是故意的（重庆站）", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1DE6bBPE6c/", "level": "single"},
        {"title": "情网丨王晰六巡重庆", "platform": "微博（@狐狐美梦窝）", "url": "https://weibo.com/tv/show/1034:5310935812997130", "level": "verified"},
        {"title": "王晰《情网》六巡重庆", "platform": "微博（@不要总是哭唧唧）", "url": "https://weibo.com/tv/show/1034:5309457828085791", "level": "verified"},
        {"title": "王晰《Goodbye…》", "platform": "微博（@不要总是哭唧唧）", "url": "https://weibo.com/tv/show/1034:5309440891748623", "level": "verified"},
        {"title": "现场视频", "platform": "微博（@静观就好）", "url": "https://weibo.com/tv/show/1034:5309649545789448", "level": "single"},
        {"title": "现场视频", "platform": "微博（@春光明媚下的傻猪）", "url": "https://weibo.com/tv/show/1034:5311116562333741", "level": "single"},
        {"title": "现场帖", "platform": "微博（@不要总是哭唧唧）", "url": "https://m.weibo.cn/detail/5309438831624347", "level": "single"},
        {"title": "现场帖", "platform": "微博（@麟Lin-白羊座）", "url": "https://m.weibo.cn/detail/5309616068231912", "level": "single"}
    ],
    "2026-08-23": [
        {"title": "2026王晰「回」个人巡回音乐会（豆瓣活动页，未举办）", "platform": "豆瓣", "url": "https://www.douban.com/event/37949806/", "level": "official", "note": "官宣后未举办"},
        {"title": "【广州】2026王晰「回」个人巡回音乐会（票务页，待举办）", "platform": "演出票务网", "url": "https://www.yanchupiaowu.com/event.html?id=VGl6QWhKbDVjbTVIR1U2dWlCUW1rQT09", "level": "official", "note": "官宣后未举办"},
        {"title": "2026年8月行政许可事项（营业性演出 2026.8.6-8.12）", "platform": "广州市文旅局", "url": "http://wglj.gz.gov.cn/xxgk/bmwj/ywxx/wgl/content/post_10965083.html", "level": "official", "note": "许可佐证"}
    ]
}

n = 0
for date, items in ADD.items():
    R.setdefault(date, [])
    have_urls = {x["url"] for x in R[date]}
    for it in items:
        if it["url"] not in have_urls:
            R[date].append(it)
            have_urls.add(it["url"])
            n += 1

d["repos"] = dict(sorted(R.items()))
d["_meta"]["note"] = "巡演现场 repo 索引（公开来源收集，2026-08-16 汇总；三巡~六巡为全网检索结果）。level: official=官方媒体/通告, verified=多源交叉, single=单源。带 note 的条目存在日期口径待核（以站内 cities.json 为准）。"
json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("新增 %d 条 repo，当前共 %d 个场次有 repo" % (n, len(R)))
