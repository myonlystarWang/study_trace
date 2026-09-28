import datetime
from datetime import date, timedelta
from typing import Optional, Dict, Any
import chinese_calendar as cc

HOLIDAY_NAMES = {
    "New Year's Day": "元旦",
    "Spring Festival": "春节",
    "Tomb-sweeping Day": "清明节",
    "Labour Day": "劳动节",
    "Dragon Boat Festival": "端午节",
    "Mid-autumn Festival": "中秋节",
    "National Day": "国庆节",
}


def is_workday(d: date) -> bool:
    """判断指定日期是否为工作日（含法定调休上班上学日）"""
    return cc.is_workday(d)


def get_break_span(d: date) -> Optional[Dict[str, Any]]:
    """
    如果指定日期处于放假休息区间（法定节假日长假或普通周末），
    返回该连续休息周期的完整信息：
    - span_start: 该放假周期的起始日期
    - span_end: 该放假周期的截止日期
    - last_workday: 放假前最后一个工作日（大作业布置源头日）
    - holiday_name: 假期名称（如 '国庆节'、'中秋节' 或 '周末'）
    - display_name: 展示标签（如 '国庆长假'、'中秋假期'、'周末顺延'）
    - days: 连续放假天数
    - is_statutory: 是否属于国家法定节假日
    """
    if cc.is_workday(d):
        return None

    # 向前推导连休起点与放假前最后一个工作日
    curr = d
    while not cc.is_workday(curr - timedelta(days=1)):
        curr -= timedelta(days=1)
    span_start = curr
    last_workday = curr - timedelta(days=1)

    # 向后推导连休终点
    curr = d
    while not cc.is_workday(curr + timedelta(days=1)):
        curr += timedelta(days=1)
    span_end = curr

    # 检测连休期间是否存在法定节假日名称
    holiday_name = "周末"
    step = span_start
    while step <= span_end:
        is_h, h_name = cc.get_holiday_detail(step)
        if is_h and h_name:
            holiday_name = HOLIDAY_NAMES.get(h_name, h_name)
            break
        step += timedelta(days=1)

    is_statutory = holiday_name != "周末"
    if is_statutory:
        display_name = f"{holiday_name}假期" if "节" in holiday_name else f"{holiday_name}长假"
    else:
        display_name = "周末顺延"

    return {
        "span_start": span_start,
        "span_end": span_end,
        "last_workday": last_workday,
        "holiday_name": holiday_name,
        "display_name": display_name,
        "days": (span_end - span_start).days + 1,
        "is_statutory": is_statutory,
    }


def get_holiday_context(d: date) -> Dict[str, Any]:
    """
    获取指定日期的节假日上下文信息（供前端/接口快速消费）：
    包括当前是否在连休中、连休详情，以及未来7天内是否有即将来临的长假
    """
    current_break = get_break_span(d)
    upcoming_break = None

    if not current_break:
        # 如果当天是工作日，探测未来 7 天内是否有法定长假
        check = d + timedelta(days=1)
        for _ in range(7):
            b = get_break_span(check)
            if b and b["is_statutory"]:
                upcoming_break = b
                break
            check += timedelta(days=1)

    return {
        "date": d,
        "is_workday": cc.is_workday(d),
        "current_break": current_break,
        "upcoming_break": upcoming_break,
    }
