import argparse
import json
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reports.json"
CHARTS = ROOT / "data" / "market_charts.json"
CN_TZ = timezone(timedelta(hours=8))

CHART_SECIDS = {
    "shanghai": "1.000001",
    "chinext": "0.399006",
    "securities": "0.399975",
    "avg_price": "47.800005",
    "semiconductor": "90.BK0917",
    "optical_module": "90.BK1136",
    "fiber_optic": "90.BK1660",
}

SERENITY_DEMAND_THEME_SCORE = {
    "AI硬件/CPO/半导体": 22,
    "化工材料/电子化学品": 20,
    "机器人/高端制造/汽车链": 18,
    "电力能源/算力用电": 16,
    "电力设备/新能源设备": 15,
    "资源品/金属材料": 14,
    "AI应用/数据要素/服务": 10,
}

SERENITY_UPSTREAM_KEYWORDS = (
    "半导体",
    "光学光电",
    "通信设备",
    "元件",
    "电子化学",
    "金属新材",
    "小金属",
    "电池",
    "电网设备",
    "其他电源",
    "专用设备",
    "自动化设",
    "航空装备",
    "航天装备",
    "轨交设备",
)

SERENITY_WEAK_KEYWORDS = (
    "地产",
    "房地产",
    "装修建材",
    "一般零售",
    "服装家纺",
    "饰品",
    "白酒",
    "休闲食品",
)

THEME_BY_INDUSTRY = {
    "元件": "AI硬件/CPO/半导体",
    "光学光电": "AI硬件/CPO/半导体",
    "通信设备": "AI硬件/CPO/半导体",
    "消费电子": "AI硬件/CPO/半导体",
    "半导体": "AI硬件/CPO/半导体",
    "其他电子": "AI硬件/CPO/半导体",
    "电子化学": "AI硬件/CPO/半导体",
    "军工电子": "AI硬件/CPO/半导体",
    "计算机设": "AI应用/数据要素/服务",
    "IT服务Ⅱ": "AI应用/数据要素/服务",
    "软件开发": "AI应用/数据要素/服务",
    "专业服务": "AI应用/数据要素/服务",
    "广告营销": "AI应用/数据要素/服务",
    "数字媒体": "AI应用/数据要素/服务",
    "电力": "电力能源/算力用电",
    "煤炭开采": "资源品/煤炭/高股息",
    "焦炭Ⅱ": "资源品/煤炭/高股息",
    "金属新材": "资源品/金属材料",
    "工业金属": "资源品/金属材料",
    "小金属": "资源品/金属材料",
    "冶钢原料": "资源品/金属材料",
    "炼化及贸": "化工材料/电子化学品",
    "化学原料": "化工材料/电子化学品",
    "化学制品": "化工材料/电子化学品",
    "塑料": "化工材料/电子化学品",
    "玻璃玻纤": "化工材料/电子化学品",
    "电池": "化工材料/电子化学品",
    "农化制品": "化工材料/电子化学品",
    "通用设备": "机器人/高端制造/汽车链",
    "专用设备": "机器人/高端制造/汽车链",
    "轨交设备": "机器人/高端制造/汽车链",
    "自动化设": "机器人/高端制造/汽车链",
    "电机Ⅱ": "机器人/高端制造/汽车链",
    "航空装备": "机器人/高端制造/汽车链",
    "航天装备": "机器人/高端制造/汽车链",
    "汽车零部": "机器人/高端制造/汽车链",
    "商用车": "机器人/高端制造/汽车链",
    "其他电源": "电力设备/新能源设备",
    "光伏设备": "电力设备/新能源设备",
    "电网设备": "电力设备/新能源设备",
    "房地产开": "地产基建/城市更新",
    "基础建设": "地产基建/城市更新",
    "装修建材": "地产基建/城市更新",
    "工程咨询": "地产基建/城市更新",
    "专业工程": "地产基建/城市更新",
    "环境治理": "环保/公用事业",
    "环保设备": "环保/公用事业",
    "小家电": "消费零售/家居服饰",
    "家居用品": "消费零售/家居服饰",
    "家电零部": "消费零售/家居服饰",
    "服装家纺": "消费零售/家居服饰",
    "饰品": "消费零售/家居服饰",
    "休闲食品": "消费零售/家居服饰",
    "饮料乳品": "消费零售/家居服饰",
    "一般零售": "消费零售/家居服饰",
    "包装印刷": "消费零售/家居服饰",
    "造纸": "消费零售/家居服饰",
    "白酒Ⅱ": "消费零售/家居服饰",
    "化学纤维": "化工材料/电子化学品",
    "医疗器械": "医药医疗",
    "生物制品": "医药医疗",
    "航运港口": "航运港口/交运",
    "贸易Ⅱ": "贸易/综合",
}


def now_text():
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S +08:00")


def fetch_json(url, params=None, referer="https://quote.eastmoney.com/", retries=4, timeout=28):
    full_url = url
    if params:
        full_url = url + "?" + urllib.parse.urlencode(params)
    last_error = None
    for attempt in range(retries):
        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": referer,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "close",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(0.4 * (attempt + 1))
    raise last_error


def fetch_zt_pool(date_compact):
    rows = []
    meta = {}
    for page in range(10):
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": str(page),
            "pagesize": "50",
            "sort": "fbt:asc",
            "date": date_compact,
            "_": int(time.time() * 1000),
        }
        payload = fetch_json(
            "https://push2ex.eastmoney.com/getTopicZTPool",
            params=params,
            referer="https://quote.eastmoney.com/ztb/detail",
        )
        data = payload.get("data") or {}
        meta = {"qdate": data.get("qdate"), "tc": data.get("tc")}
        pool = data.get("pool") or []
        rows.extend(pool)
        if len(pool) < 50:
            break
    return rows, meta


def fetch_kline(secid, date_compact, limit=190):
    params = {
        "secid": secid,
        "klt": "101",
        "fqt": "1",
        "lmt": str(limit),
        "end": date_compact,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "_": int(time.time() * 1000),
    }
    hosts = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://push2.eastmoney.com/api/qt/stock/kline/get",
        "https://push2test.eastmoney.com/api/qt/stock/kline/get",
    )
    last_error = None
    for host in hosts:
        try:
            payload = fetch_json(host, params=params, retries=3, timeout=20)
            points = []
            for row in (payload.get("data") or {}).get("klines") or []:
                date, open_, close, high, low, volume, amount, amplitude, pct, change, turnover = row.split(",")
                points.append(
                    {
                        "date": date,
                        "open": round(float(open_), 2),
                        "close": round(float(close), 2),
                        "high": round(float(high), 2),
                        "low": round(float(low), 2),
                        "volume": float(volume),
                        "pct": round(float(pct), 2),
                        "change": round(float(change), 2),
                    }
                )
            if points:
                return points
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"kline failed {secid}: {last_error}")


def format_time(value):
    raw = str(int(value or 0)).zfill(6)
    return f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}" if raw != "000000" else ""


def code_with_market(row):
    return str(row.get("c") or "") + (".SH" if row.get("m") == 1 else ".SZ")


def money(value):
    value = float(value or 0)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿"
    if value >= 10_000:
        return f"{value / 10_000:.0f}万"
    return f"{value:.0f}"


def theme_for(row):
    return THEME_BY_INDUSTRY.get(row.get("hybk") or "", "其他轮动")


def reason_for(theme):
    mapping = {
        "AI硬件/CPO/半导体": "半导体、光学光电、元件和通信设备继续活跃，资金围绕AI硬件、CPO、存储芯片和电子化学品寻找弹性。",
        "电力能源/算力用电": "迎峰度夏、电力负荷和AI数据中心用电预期共振，电力方向继续承担资金承接。",
        "资源品/煤炭/高股息": "煤炭和焦炭维持逆势防御与高股息逻辑，大有能源继续打开短线高度。",
        "资源品/金属材料": "金属材料和工业金属更多体现资源品轮动和材料端弹性。",
        "化工材料/电子化学品": "电子化学品、化学原料和塑料材料强势，既有半导体材料映射，也有低位材料补涨。",
        "机器人/高端制造/汽车链": "通用设备、专用设备、汽车零部件和轨交设备活跃，受机器人、制造业设备和汽车链轮动带动。",
        "电力设备/新能源设备": "电力设备和新能源设备补涨，更多与电力、储能、光伏和电源链条相关。",
        "地产基建/城市更新": "地产、基建和工程咨询局部轮动，但不是当天第一主线。",
        "消费零售/家居服饰": "消费、家居、饰品和包装方向有扩散，主要承担轮动补涨。",
        "AI应用/数据要素/服务": "AI应用、IT服务和软件端局部活跃，强度弱于AI硬件和材料端。",
    }
    return mapping.get(theme, "非主线个股以事件驱动和低位轮动为主，持续性需要次日确认。")


def stock_position(ladder):
    if ladder >= 4:
        return "空间核心"
    if ladder >= 3:
        return "高度核心"
    if ladder == 2:
        return "连板前排"
    return "首板扩散"


def stock_obj(row):
    ladder = int(row.get("lbc") or row.get("zttj", {}).get("ct") or 1)
    price = round(float(row.get("p") or 0) / 1000, 3)
    theme = theme_for(row)
    return {
        "code": code_with_market(row),
        "name": row.get("n") or "",
        "theme": theme,
        "reason": reason_for(theme),
        "position": stock_position(ladder),
        "firstLimitTime": format_time(row.get("fbt")),
        "lastLimitTime": format_time(row.get("lbt")),
        "consecutive": ladder,
        "reopenCount": int(row.get("zbc") or 0),
        "pct": round(float(row.get("zdp") or 0), 2),
        "price": price,
        "amount": money(row.get("amount")),
        "amountRaw": round(float(row.get("amount") or 0), 2),
        "sealFund": money(row.get("fund")),
        "turnover": round(float(row.get("hs") or 0), 2),
        "category": row.get("hybk") or "未分类",
    }


def board_text(height):
    height = int(height or 0)
    return "首板" if height <= 1 else f"{height}连板"


def format_pct(value):
    number = float(value or 0)
    prefix = "+" if number > 0 else ""
    return f"{prefix}{number:.2f}%"


def join_names(rows, limit=4):
    names = []
    for item in rows[:limit]:
        if isinstance(item, dict):
            names.append(item.get("name") or "")
        else:
            names.append(str(item))
    names = [name for name in names if name]
    if not names:
        return "暂无"
    return "、".join(names) + ("等" if len(rows) > limit else "")


def theme_category(theme):
    if any(keyword in theme for keyword in ("AI", "机器人", "半导体", "电子", "光", "通信")):
        return "科技"
    return "财经"


def chart_snapshot(source, target_date):
    snapshot = {}
    for series in (source or {}).get("series", []):
        latest = next((point for point in reversed(series.get("points", [])) if point.get("date") == target_date), None)
        if latest:
            snapshot[series["id"]] = latest
        elif series.get("latestDate") == target_date:
            snapshot[series["id"]] = {
                "date": target_date,
                "close": series.get("latestClose"),
                "pct": series.get("latestPct"),
                "change": series.get("latestChange"),
            }
    return snapshot


def top_theme_name(by_theme, candidates, exclude=None):
    blocked = set(exclude or [])
    for name in candidates:
        if name in by_theme and name not in blocked:
            return name
    for name in by_theme:
        if name not in blocked:
            return name
    return None


def build_summary(target_date, date_compact, meta, stocks, themes, by_theme, charts):
    high_board = sorted([stock for stock in stocks if stock["consecutive"] >= 2], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
    max_height = high_board[0]["consecutive"] if high_board else max((stock["consecutive"] for stock in stocks), default=1)
    top_theme = themes[0] if themes else None
    second_theme = themes[1] if len(themes) > 1 else None
    third_theme = themes[2] if len(themes) > 2 else None
    tech_theme = top_theme_name(by_theme, ["AI硬件/CPO/半导体", "AI应用/数据要素/服务", "化工材料/电子化学品"])
    multi_board_count = sum(1 for stock in stocks if stock["consecutive"] >= 2)
    reopen_count = sum(1 for stock in stocks if stock["reopenCount"] > 0)
    early_count = sum(1 for stock in stocks if stock["firstLimitTime"] and stock["firstLimitTime"] <= "09:35:00")

    summary = [
        f"{target_date}收盘，东方财富涨停池 qdate={date_compact}、tc={meta.get('tc')}；最高高度为{board_text(max_height)}，{join_names(high_board or stocks, 3)}处在连板前列。",
    ]
    if charts.get("shanghai") and charts.get("chinext") and charts.get("avg_price"):
        summary.append(
            f"指数端，上证{format_pct(charts['shanghai'].get('pct'))}，创业板指{format_pct(charts['chinext'].get('pct'))}，A股平均股价{format_pct(charts['avg_price'].get('pct'))}，指数承压下资金更偏结构性抱团。"
        )
    if top_theme:
        theme_text = f"{top_theme['name']}{top_theme['count']}只居前"
        if second_theme:
            theme_text += f"，{second_theme['name']}{second_theme['count']}只紧随"
        if third_theme:
            theme_text += f"，{third_theme['name']}{third_theme['count']}只跟随"
        summary.append(f"涨停分布上，{theme_text}，主线仍以题材轮动和局部扩散为主。")
    if tech_theme:
        summary.append(
            f"科技方向里，{tech_theme}{len(by_theme.get(tech_theme, []))}只涨停，{join_names(sorted(by_theme[tech_theme], key=lambda item: (item['consecutive'], item['amountRaw']), reverse=True), 4)}提供辨识度。"
        )
    summary.append(
        f"封板质量方面，2板及以上共有{multi_board_count}只，{reopen_count}只个股出现过开板，早盘09:35前完成首封的有{early_count}只，次日更要看前排承接而不是只看总数。"
    )
    return summary


def build_leaders(stocks, themes, by_theme):
    leaders = []
    used_themes = set()
    high_board = sorted([stock for stock in stocks if stock["consecutive"] >= 2], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
    if high_board:
        max_height = high_board[0]["consecutive"]
        leaders.append(
            {
                "type": "空间核心",
                "stocks": join_names(high_board, 3),
                "theme": high_board[0]["theme"],
                "logic": f"最高高度来到{board_text(max_height)}，{join_names(high_board, 3)}是短线情绪最直接的锚点。",
            }
        )
        used_themes.add(high_board[0]["theme"])

    if themes:
        top_name = themes[0]["name"]
        top_rows = sorted(by_theme[top_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        leaders.append(
            {
                "type": "主线热点",
                "stocks": join_names(top_rows, 4),
                "theme": top_name,
                "logic": f"{top_name}当天共有{len(top_rows)}只涨停，{join_names(top_rows, 4)}带动了最明显的板块扩散。",
            }
        )
        used_themes.add(top_name)

    tech_name = top_theme_name(by_theme, ["AI硬件/CPO/半导体", "AI应用/数据要素/服务", "化工材料/电子化学品"], exclude=used_themes)
    if tech_name:
        tech_rows = sorted(by_theme[tech_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        leaders.append(
            {
                "type": "科技活跃",
                "stocks": join_names(tech_rows, 4),
                "theme": tech_name,
                "logic": f"{tech_name}维持活跃，{join_names(tech_rows, 4)}提供了当天科技线的辨识度与弹性。",
            }
        )
        used_themes.add(tech_name)

    defend_name = top_theme_name(by_theme, ["资源品/煤炭/高股息", "电力能源/算力用电", "电力设备/新能源设备"], exclude=used_themes)
    if defend_name:
        defend_rows = sorted(by_theme[defend_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        leaders.append(
            {
                "type": "防御承接",
                "stocks": join_names(defend_rows, 4),
                "theme": defend_name,
                "logic": f"{defend_name}有{len(defend_rows)}只涨停，{join_names(defend_rows, 4)}承担了弱指数环境下的资金承接。",
            }
        )
    elif len(themes) > 1:
        fallback_name = next((theme["name"] for theme in themes[1:] if theme["name"] not in used_themes), None)
        if fallback_name:
            fallback_rows = sorted(by_theme[fallback_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
            leaders.append(
                {
                    "type": "轮动补涨",
                    "stocks": join_names(fallback_rows, 4),
                    "theme": fallback_name,
                    "logic": f"{fallback_name}当天也有{len(fallback_rows)}只涨停，{join_names(fallback_rows, 4)}承担轮动扩散角色，持续性要看次日确认。",
                }
            )
    return leaders[:4]


def build_warnings(stocks, charts):
    warnings = []
    reopen_count = sum(1 for stock in stocks if stock["reopenCount"] > 0)
    first_board_count = sum(1 for stock in stocks if stock["consecutive"] == 1)
    total = len(stocks)

    if charts.get("shanghai") and charts.get("chinext") and charts.get("avg_price"):
        if all(charts[key].get("pct", 0) < 0 for key in ("shanghai", "chinext", "avg_price")):
            warnings.append("指数与平均股价同步走弱，若高标和主线前排不能继续承接，追高容易演变成隔日兑现。")
    if reopen_count >= max(10, total // 3):
        warnings.append(f"{reopen_count}只涨停股出现过开板，封板质量不算稳，明天更应重视回封强度和溢价反馈。")
    if first_board_count >= max(20, total // 2):
        warnings.append(f"首板占比达到{first_board_count}/{total}，说明扩散多于共振，接力最好围绕少数高辨识度核心。")
    if not warnings:
        warnings.append("连板与首板分布相对均衡，但次日仍要重点观察高标溢价和主线前排的承接质量。")
    return warnings[:3]


def clamp_score(value):
    return max(0, min(100, int(round(value))))


def serenity_grade(score):
    if score >= 78:
        return "A"
    if score >= 64:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def score_white_hair_candidate(stock, theme_rank):
    stock_text = "".join(
        str(stock.get(key) or "")
        for key in ("name", "code", "theme", "position", "category")
    )
    category_text = "".join(str(stock.get(key) or "") for key in ("name", "code", "category"))
    score = 40
    reasons = []
    risks = []

    demand_score = SERENITY_DEMAND_THEME_SCORE.get(stock["theme"], 0)
    if demand_score:
        score += demand_score
        reasons.append(f"{stock['theme']}贴近AI/机器人/电力/材料需求链")

    upstream_hits = [keyword for keyword in SERENITY_UPSTREAM_KEYWORDS if keyword in category_text]
    if upstream_hits:
        add_score = min(18, 6 * len(upstream_hits))
        score += add_score
        reasons.append(f"上游/瓶颈关键词：{'、'.join(upstream_hits[:3])}")

    rank = theme_rank.get(stock["theme"])
    if rank and rank <= 3:
        score += 8
        reasons.append(f"所属主线强度排名第{rank}")
    elif rank and rank <= 6:
        score += 4
        reasons.append(f"所属主线仍在涨停扩散区")

    first_time = stock.get("firstLimitTime") or ""
    if first_time and first_time <= "09:35:00":
        score += 6
        reasons.append("早盘完成封板，资金确认较快")
    elif first_time and first_time > "13:30:00":
        score -= 8
        risks.append("尾盘封板，次日承接验证要求更高")

    reopen_count = int(stock.get("reopenCount") or 0)
    if reopen_count == 0:
        score += 6
        reasons.append("封板未开，筹码稳定性较好")
    else:
        score -= min(14, reopen_count * 4)
        risks.append(f"封板后开板{reopen_count}次")

    amount_raw = float(stock.get("amountRaw") or 0)
    if amount_raw >= 1_000_000_000:
        score += 7
        reasons.append("成交额过10亿，具备容量票观察价值")
    elif amount_raw >= 500_000_000:
        score += 5
        reasons.append("成交额过5亿，流动性可观察")
    elif amount_raw >= 200_000_000:
        score += 3
        reasons.append("成交额过2亿，低位启动有基本流动性")
    else:
        score -= 4
        risks.append("成交额偏小，容量不足")

    turnover = float(stock.get("turnover") or 0)
    if 2 <= turnover <= 12:
        score += 4
        reasons.append("换手处于可承接区间")
    elif turnover > 18:
        score -= 6
        risks.append("换手偏高，分歧较重")

    if any(keyword in stock_text for keyword in SERENITY_WEAK_KEYWORDS) and not upstream_hits:
        score -= 10
        risks.append("偏传统轮动，缺少Serenity式供应链瓶颈特征")

    if stock["theme"] == "其他轮动" and not upstream_hits:
        score -= 8
        risks.append("题材归因不清，供应链映射不足")

    score = clamp_score(score)
    grade = serenity_grade(score)
    return {
        "code": stock["code"],
        "name": stock["name"],
        "theme": stock["theme"],
        "category": stock["category"],
        "score": score,
        "grade": grade,
        "firstLimitTime": stock.get("firstLimitTime") or "",
        "amount": stock.get("amount") or "",
        "amountRaw": amount_raw,
        "turnover": stock.get("turnover"),
        "reopenCount": reopen_count,
        "serenityReason": "；".join(reasons[:4]) or "首板样本，但供应链优势仍需人工复核",
        "risk": "；".join(risks[:3]) or "暂无明显结构性扣分，仍需补充基本面和公告核验",
    }


def build_white_hair_picks(stocks, themes):
    theme_rank = {theme["name"]: index + 1 for index, theme in enumerate(themes)}
    first_boards = [stock for stock in stocks if int(stock.get("consecutive") or 0) == 1]
    scored = [score_white_hair_candidate(stock, theme_rank) for stock in first_boards]
    picks = [item for item in scored if item["grade"] == "A"]
    picks.sort(key=lambda item: (-item["score"], item["firstLimitTime"], -item["amountRaw"]))
    return {
        "title": "白毛严选",
        "source": "仅从当天首板中筛选；按 Serenity 方法论的供应链瓶颈、上游稀缺、AI/机器人/电力/材料需求、主线强度、封板质量和风险扣分生成 A 评价。",
        "methodology": [
            "优先：AI硬件/CPO/半导体、电子化学品、机器人/高端制造、电力/算力用电、上游材料。",
            "加分：上游瓶颈关键词、强主线排名靠前、早盘封板、未开板、成交额与换手可承接。",
            "扣分：题材归因不清、尾盘封板、多次开板、成交额过小、纯传统轮动且缺少供应链映射。",
        ],
        "totalFirstBoard": len(first_boards),
        "aCount": len(picks),
        "items": picks[:12],
    }


def build_market_news(stocks, themes, by_theme, charts):
    total = len(stocks)
    max_height = max((stock["consecutive"] for stock in stocks), default=1)
    top_theme = themes[0]["name"] if themes else "暂无明确主线"
    tech_name = top_theme_name(by_theme, ["AI硬件/CPO/半导体", "AI应用/数据要素/服务", "化工材料/电子化学品"])
    defend_name = top_theme_name(by_theme, ["资源品/煤炭/高股息", "电力能源/算力用电", "电力设备/新能源设备"])

    rows = [
        {
            "category": "财经",
            "heat": "盘面总览",
            "title": "指数承压下，涨停资金继续做结构性抱团",
            "impact": f"当日涨停池共{total}只，最高高度{board_text(max_height)}；若指数端继续偏弱，情绪会更依赖少数高标和前排主题。",
            "whyHot": "弱指数环境里，连板高度、涨停分布和前排封板质量比总成交额更能反映短线偏好。",
            "watch": "看高标溢价与主线前排是否继续强化。",
            "relatedThemes": [top_theme],
            "source": "复盘交叉核验",
            "url": "",
        }
    ]
    if charts.get("shanghai") and charts.get("chinext") and charts.get("avg_price"):
        rows[0]["impact"] = (
            f"上证{format_pct(charts['shanghai'].get('pct'))}、创业板指{format_pct(charts['chinext'].get('pct'))}、A股平均股价{format_pct(charts['avg_price'].get('pct'))}；"
            f"当日涨停池共{total}只，最高高度{board_text(max_height)}，情绪主要依赖结构性热点。"
        )

    for theme_name in [top_theme, tech_name, defend_name]:
        if not theme_name or any(theme_name in item["relatedThemes"] for item in rows):
            continue
        theme_rows = sorted(by_theme[theme_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        rows.append(
            {
                "category": theme_category(theme_name),
                "heat": "板块焦点" if len(rows) == 1 else "结构主线",
                "title": f"{theme_name}成为当天重点方向",
                "impact": f"{theme_name}共有{len(theme_rows)}只涨停，{join_names(theme_rows, 4)}处在前排，体现出该方向的扩散和承接强度。",
                "whyHot": reason_for(theme_name),
                "watch": f"看{join_names(theme_rows, 3)}能否继续打开高度并带动后排承接。",
                "relatedThemes": [theme_name],
                "source": "涨停池与板块分布归纳",
                "url": "",
            }
        )
    return rows[:4]


def update_charts(target_date, date_compact):
    charts = json.loads(CHARTS.read_text(encoding="utf-8"))
    for series in charts["series"]:
        points = fetch_kline(CHART_SECIDS[series["id"]], date_compact, limit=190)
        latest = next((point for point in reversed(points) if point["date"] == target_date), None)
        if not latest:
            raise RuntimeError(f"{series['id']} missing {target_date}")
        cached_latest = next((point for point in reversed(series.get("points", [])) if point.get("date") == target_date), None)
        if cached_latest and abs(float(latest.get("pct") or 0)) > 15 and abs(float(cached_latest.get("pct") or 0)) <= 15:
            latest = cached_latest
            series["cachedReason"] = "行情接口返回异常涨跌幅，保留本地已核验缓存点"
        else:
            series.pop("cachedReason", None)
        merged = {point["date"]: point for point in series.get("points", [])}
        merged[target_date] = latest
        series["points"] = [merged[key] for key in sorted(merged)]
        first = series["points"][0]
        series["latestDate"] = latest["date"]
        series["latestClose"] = latest["close"]
        series["latestPct"] = latest["pct"]
        series["latestChange"] = latest["change"]
        series["latestTime"] = now_text()
        series["rangePct"] = round((latest["close"] / first["close"] - 1) * 100, 2) if first["close"] else 0
    charts["updatedAt"] = now_text()
    CHARTS.write_text(json.dumps(charts, ensure_ascii=False, indent=2), encoding="utf-8")
    return charts


def update_report(target_date, charts_data=None):
    date_compact = target_date.replace("-", "")
    rows, meta = fetch_zt_pool(date_compact)
    if str(meta.get("qdate")) != date_compact:
        raise RuntimeError(f"zt pool qdate mismatch: {meta}")
    stocks = [stock_obj(row) for row in rows]
    by_theme = defaultdict(list)
    for stock in stocks:
        by_theme[stock["theme"]].append(stock)
    theme_names = sorted(by_theme, key=lambda name: (len(by_theme[name]), max(item["consecutive"] for item in by_theme[name])), reverse=True)
    themes = []
    for name in theme_names:
        leaders = sorted(by_theme[name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)[:6]
        themes.append({"name": name, "count": len(by_theme[name]), "catalyst": reason_for(name), "leaders": [item["name"] for item in leaders]})
    charts = chart_snapshot(charts_data or json.loads(CHARTS.read_text(encoding="utf-8")), target_date)
    ladder = []
    for height in sorted({stock["consecutive"] for stock in stocks}, reverse=True):
        same_height = sorted([stock for stock in stocks if stock["consecutive"] == height], key=lambda item: item["firstLimitTime"])
        top = same_height[:12]
        main_theme = Counter(item["theme"] for item in same_height).most_common(1)[0][0]
        ladder.append(
            {
                "height": "首板" if height == 1 else f"{height}连板",
                "stocks": "、".join(item["name"] for item in top) + ("等" if len(same_height) > 12 else ""),
                "theme": main_theme,
                "note": f"共{len(same_height)}只；代表个股：" + "、".join(f"{item['name']}({item['firstLimitTime']})" for item in top[:5]) + "。",
            }
        )
    report = {
        "date": target_date,
        "session": "收盘复盘",
        "title": "A股涨停复盘报告",
        "market": {
            "limitUpCount": int(meta.get("tc") or len(rows)),
            "dataSource": f"东方财富涨停池 getTopicZTPool(date={date_compact}) 返回 qdate={meta.get('qdate')}、tc={meta.get('tc')}；指数和板块K线来自东方财富日K接口；市场与科技新闻雷达结合公开财经/科技报道归档。",
            "sampleScope": f"收盘口径纳入东方财富专题涨停池 qdate={date_compact} 且收盘仍封涨停的A股样本，共{len(rows)}只；不纳入盘中炸板未封回或旧日期数据。",
        },
        "summary": build_summary(target_date, date_compact, meta, stocks, themes, by_theme, charts),
        "themes": themes,
        "ladder": ladder,
        "leaders": build_leaders(stocks, themes, by_theme),
        "stats": [{"category": item["name"], "count": item["count"]} for item in themes],
        "stocks": stocks,
        "whiteHairPicks": build_white_hair_picks(stocks, themes),
        "newHighScope": "收盘报告已生成，创新高模块待 scripts/update_screeners.py 补算。",
        "newHighStocks": [],
        "maConvergenceScope": "收盘报告已生成，均线粘合模块待 scripts/update_screeners.py 补算。",
        "maConvergenceStocks": [],
        "warnings": build_warnings(stocks, charts),
        "pdf": None,
        "marketNews": build_market_news(stocks, themes, by_theme, charts),
    }
    data = json.loads(REPORTS.read_text(encoding="utf-8"))
    data["reports"] = [item for item in data.get("reports", []) if item.get("date") != target_date]
    data["reports"].insert(0, report)
    data["updatedAt"] = now_text()
    REPORTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Update daily A-share report and market charts")
    parser.add_argument("--date", required=True, help="Trading date, for example 2026-06-04")
    args = parser.parse_args()
    date_compact = args.date.replace("-", "")
    charts = update_charts(args.date, date_compact)
    update_report(args.date, charts)
    print(f"Updated report and charts for {args.date}")
    print([(series["id"], series["latestDate"], series["latestPct"]) for series in charts["series"]])


if __name__ == "__main__":
    main()
