#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动生成购物攻略工作台的活动数据 activities.json。
由 GitHub Actions 在北京时间 08:00 自动运行（UTC 00:00）。

逻辑：
- 维护一个「2026 大促日历」模板（基于各平台已公布/年度规律整理）。
- 每天按北京时间计算：哪些活动处于 [今天, 今天+30天] 窗口内。
- 自动剔除已过期活动、自动加入临近活动。
- urgent 自动判定：① 大促类「今天或明天结束」标 urgent；② 李佳琦直播间红包为「当晚进行」常态标 urgent。
- 输出 activities.json：{"updated":"YYYY-MM-DD","activities":[...]}
"""
import json
import datetime

# 北京时间
CST = datetime.timezone(datetime.timedelta(hours=8))

# ---------------------------------------------------------------------------
# 2026 大促日历模板
# type 取值：平台大促 / 定金红包 / 消费券 / 直播间红包 / 其他
# urgent_mode:
#   'end_near'  -> 活动结束日在今天或明天时标 urgent（大促倒计时提醒）
#   'daily_live'-> 仅生成「今天当晚」一场，恒标 urgent（李佳琦红包雨）
#   'none'      -> 不自动标 urgent
# source 标注数据来源，便于核对。
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "title": "国家以旧换新补贴（第三批）",
        "type": "其他",
        "start": "2026-08-01T00:00",
        "end": "2026-12-31T23:59",
        "urgent_mode": "end_near",
        "detail": "国家级以旧换新补贴第三批，覆盖空调/冰箱/洗衣机/电视/手机/电脑等。一级能效家电可享成交价 15%、单件最高 1500 元；手机等数码类按 15%（封顶 500 元）。下单前在云闪付/京东/天猫对应页面领取资格，跨店可叠平台券。全年可用，买大件前务必先核补贴资格。",
        "source": "国家发改委 / 财政部 2026 以旧换新政策",
    },
    {
        "title": "天猫新势力周 & 开学季",
        "type": "平台大促",
        "start": "2026-08-25T20:00",
        "end": "2026-08-31T23:59",
        "urgent_mode": "end_near",
        "detail": "双场同期：新势力周全行业新品集中上新；开学季覆盖宿舍好物、文具书包、学生服饰与数码配件。88VIP 可叠消费券包，开学采购锁定这一档。淘宝 App 搜「开学季」进会场。",
        "source": "淘宝天猫官方 8 月大促排期",
    },
    {
        "title": "京东开学季",
        "type": "平台大促",
        "start": "2026-08-21T00:00",
        "end": "2026-08-31T23:59",
        "urgent_mode": "end_near",
        "detail": "京东 8 月末开学季，笔记本/平板/手机/宿舍家电/文具低至探底，PLUS 会员可领超级补贴券，部分可叠国补。学生党数码大件压这一档。京东 App 搜「开学季」进会场。",
        "source": "京东官方活动排期",
    },
    {
        "title": "抖音商城 惠购消费券（区域）",
        "type": "消费券",
        "start": "2026-08-16T00:00",
        "end": "2026-10-15T23:59",
        "urgent_mode": "none",
        "detail": "抖音商城联合地方政府发放区域消费券（如广西等），满减力度按地区不同。抖音 App 搜「惠购+省份」或进本地生活频道领券，本地商户/直播间可用。",
        "source": "抖音电商 + 地方政府消费券公告",
    },
    {
        "title": "天猫 9 月超级 88",
        "type": "平台大促",
        "start": "2026-09-08T00:00",
        "end": "2026-09-19T23:59",
        "urgent_mode": "end_near",
        "detail": "88VIP 年度主场，官方立减 12% 打底，88VIP 消费券包（满 200-25/满 480-60/满 1500-150）可叠，到手低至 7.7 折。美妆、母婴、个护、食品重点补货窗口。淘宝搜「超级88」进会场。",
        "source": "天猫 88 会员节年度规律 / 招商规则",
    },
    {
        "title": "抖音 921 好物节",
        "type": "平台大促",
        "start": "2026-09-15T00:00",
        "end": "2026-09-21T23:59",
        "urgent_mode": "end_near",
        "detail": "抖音商城 921 好物节，跨店立减 + 直播间红包 + 达人券，主打国潮与匠心好物。抖音 App 搜「921好物节」进会场。",
        "source": "抖音电商年度大促规律",
    },
    {
        "title": "天猫中秋礼遇 & 家装季",
        "type": "平台大促",
        "start": "2026-09-20T00:00",
        "end": "2026-10-07T23:59",
        "urgent_mode": "end_near",
        "detail": "中秋礼遇（月饼礼盒、送礼、家清洗护）+ 家装季（建材、家具、智能家居）双线。前有国庆囤货需求可一并规划。淘宝搜「中秋礼遇」「天猫家装」进会场。",
        "source": "天猫官方月度大促规律",
    },
    {
        "title": "拼多多 百亿补贴常态 + 大促",
        "type": "平台大促",
        "start": "2026-01-01T00:00",
        "end": "2026-12-31T23:59",
        "urgent_mode": "none",
        "detail": "拼多多百亿补贴长期在线，iPhone/美妆/日用品普遍低于其他平台。大促节点（38/618/双11/双12）额外加码。买标品前先比拼多多到手价。拼多多 App 搜「百亿补贴」进频道。",
        "source": "拼多多平台常态活动",
    },
    {
        "title": "天猫双 11 全球狂欢季（预售+现货）",
        "type": "平台大促",
        "start": "2026-10-20T00:00",
        "end": "2026-11-13T23:59",
        "urgent_mode": "end_near",
        "detail": "年度最大促。预售 10/20 起付定金，11/10-11/11 付尾款+现货开卖。跨店每满 300-50，88VIP 额外券包，价保到 11/26。大件、囤货、送礼集中这一档。淘宝搜「双11」进会场。",
        "source": "天猫双 11 年度规律 / 招商规则",
    },
    {
        "title": "京东 11.11 全球热爱季",
        "type": "平台大促",
        "start": "2026-10-23T00:00",
        "end": "2026-11-13T23:59",
        "urgent_mode": "end_near",
        "detail": "京东双 11，数码 3C/家电主场，PLUS 超级补贴 + 跨店满减，可叠国补。10/31、11/10 两波爆发。京东 App 搜「11.11」进会场。",
        "source": "京东双 11 年度规律",
    },
    {
        "title": "天猫双 12（年终庆）",
        "type": "平台大促",
        "start": "2026-12-08T00:00",
        "end": "2026-12-12T23:59",
        "urgent_mode": "end_near",
        "detail": "双 11 后的返场清仓，服饰、日用品、食品尾货低至全年低位。跨店满减 + 店铺券。淘宝搜「双12」进会场。",
        "source": "天猫双 12 年度规律",
    },
    {
        "title": "京东双 12 年终盛典",
        "type": "平台大促",
        "start": "2026-12-08T00:00",
        "end": "2026-12-12T23:59",
        "urgent_mode": "end_near",
        "detail": "京东双 12 年终清仓，家电尾货、数码配件、日用补货。PLUS 补贴 + 满减。京东 App 搜「双12」进会场。",
        "source": "京东双 12 年度规律",
    },
    # 李佳琦直播间红包雨：每晚进行，常态紧急提醒
    {
        "title": "李佳琦直播间 红包雨 / 隐藏红包（今晚）",
        "type": "直播间红包",
        "start": "DAILY_TONIGHT_20",
        "end": "DAILY_TONIGHT_2330",
        "urgent_mode": "daily_live",
        "detail": "李佳琦 Austin 直播间每晚福利：① 红包雨——开淘宝/点淘进直播间，右上角红包雨倒计时剩 2 秒点抢大额专属红包（限本场下单）；② 隐藏福利——停留 30 分钟/点赞/评论/分享弹加码隐藏券；③ 加车隐藏礼金——商品加购后淘宝顶部搜「好运购物车」弹 0.5-88 元随机红包；④ 外部搜「李佳琦」每日弹 3 个惊喜小红包。多设备分开蹲提升中奖。今晚 20:00 开播，21:30 中场加码。",
        "source": "李佳琦直播间 / 微博 / 小红书官方号 + 优惠爆料",
    },
]


def parse_dt(s):
    """解析 'YYYY-MM-DDTHH:MM' 为北京时间 datetime；无时间部分默认 00:00。"""
    s = s.strip()
    if "T" in s:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M").replace(tzinfo=CST)
    return datetime.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=CST)


def main():
    now = datetime.datetime.now(CST)
    today = now.date()
    window_end = today + datetime.timedelta(days=30)
    window_end_dt = datetime.datetime(today.year, today.month, today.day, 23, 59, tzinfo=CST) + datetime.timedelta(days=30)

    activities = []
    counter = 1

    for t in TEMPLATES:
        mode = t.get("urgent_mode", "none")

        # 李佳琦：仅生成「今天当晚」一场
        if mode == "daily_live":
            start = datetime.datetime(today.year, today.month, today.day, 20, 0, tzinfo=CST)
            end = datetime.datetime(today.year, today.month, today.day, 23, 30, tzinfo=CST)
            activities.append({
                "id": f"auto{counter:02d}",
                "title": t["title"],
                "type": t["type"],
                "start": start.strftime("%Y-%m-%dT%H:%M"),
                "end": end.strftime("%Y-%m-%dT%H:%M"),
                "urgent": True,
                "detail": t["detail"],
                "source": t["source"],
            })
            counter += 1
            continue

        s = parse_dt(t["start"])
        e = parse_dt(t["end"])
        # 与 [today 00:00, window_end 23:59] 有交集才保留
        if e.date() < today or s > window_end_dt:
            continue
        days_left = (e.date() - today).days
        urgent = (mode == "end_near") and (days_left <= 1)
        activities.append({
            "id": f"auto{counter:02d}",
            "title": t["title"],
            "type": t["type"],
            "start": t["start"],
            "end": t["end"],
            "urgent": urgent,
            "detail": t["detail"],
            "source": t["source"],
        })
        counter += 1

    out = {
        "updated": today.strftime("%Y-%m-%d"),
        "activities": activities,
    }
    with open("activities.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[update_activities] 已生成 {len(activities)} 条活动，updated={out['updated']}")


if __name__ == "__main__":
    main()
