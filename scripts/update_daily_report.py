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
    "航空装备": "机器人/高端制造/汽车链",
    "汽车零部": "机器人/高端制造/汽车链",
    "其他电源": "电力设备/新能源设备",
    "光伏设备": "电力设备/新能源设备",
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
        "https://push2test.eastmoney.com/api/qt/stock/kline/get",
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://push2.eastmoney.com/api/qt/stock/kline/get",
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


def build_market_news():
    return [
        {
            "category": "科技",
            "heat": "当日盘面核心",
            "title": "电子化学品、半导体和AI硬件逆势走强，弱指数下资金继续抱团硬科技",
            "impact": "三大指数收跌背景下，半导体、电子化学品、光学光电、元件和通信设备仍有多只涨停，说明资金没有离开科技，而是从泛AI扩散到材料、存储、CPO和算力硬件细分。",
            "whyHot": "电子化学品低开高走全天强势，叠加存储芯片、先进封装、光刻机和CPO叙事，形成今天盘面最清晰的科技防线。",
            "relatedThemes": ["AI硬件/CPO/半导体", "化工材料/电子化学品", "存储芯片", "CPO/光通信"],
            "watch": "看中船特气、三安光电、京东方A、德明利、通鼎互联等科技中军和涨停前排能否继续带动板块扩散。",
            "source": "每日经济新闻、东方财富涨停池与板块K线归档",
            "url": "https://www.nbd.com.cn/articles/2026-06-04/4417379.html",
        },
        {
            "category": "科技",
            "heat": "全球科技焦点",
            "title": "OpenAI推动Codex从编程工具升级为工作流智能体，AI Agent商业化继续加速",
            "impact": "AI Agent叙事不只影响软件股，也会反向强化本地推理、AI PC、企业数据、权限编排和安全工作流需求。",
            "whyHot": "Codex与ChatGPT工作流合体代表智能体从单点问答进入跨岗位执行，市场会继续追踪企业软件、开发工具、数据治理和端侧AI。",
            "relatedThemes": ["AI Agent", "AI应用/数据要素/服务", "AI PC", "企业软件"],
            "watch": "看AI应用端能否在硬件强势之后接力，重点筛有产品收入和工作流落地的公司。",
            "source": "每日经济新闻全球科技早参",
            "url": "https://www.nbd.com.cn/articles/2026-06-03/4415966.html",
        },
        {
            "category": "科技",
            "heat": "AI基础设施",
            "title": "英伟达Spectrum-X硅光交换机量产，CPO和光互联继续成为AI工厂关键环节",
            "impact": "硅光/CPO量产强化AI数据中心横向扩容逻辑，映射到光模块、PCB、交换机、连接器、液冷和电力链条。",
            "whyHot": "AI工厂从GPU采购进入网络、光互联和机架级系统竞争，A股光模块和通信设备连续多日受资金关注。",
            "relatedThemes": ["CPO/光通信", "AI基础设施", "数据中心", "液冷"],
            "watch": "看光通信强势股是否出现换手承接，以及AI服务器中军是否配合放量。",
            "source": "每日经济新闻全球科技早参、英伟达GTC Taipei公开报道",
            "url": "https://www.nbd.com.cn/articles/2026-06-03/4415966.html",
        },
        {
            "category": "科技",
            "heat": "机器人前沿",
            "title": "英伟达Cosmos 3与Isaac GR00T延续物理AI热度，设备端仍有扩散机会",
            "impact": "物理AI继续提升机器人、机器视觉、边缘计算、运动控制和自动化设备关注度；今天通用设备、专用设备、汽车链仍有较多涨停。",
            "whyHot": "GTC Taipei把机器人开发平台、世界模型和硬件参考设计组合在一起，机器人从概念演示走向可复用开发平台。",
            "relatedThemes": ["机器人/高端制造/汽车链", "具身智能", "边缘AI"],
            "watch": "看设备端是否出现二板和趋势中军，否则按轮动扩散处理。",
            "source": "AITNT全球AI新闻日报、钛媒体GTC Taipei报道",
            "url": "https://www.aitntnews.com/ainews/zh-CN",
        },
        {
            "category": "财经",
            "heat": "防御主线",
            "title": "三大指数集体收跌，煤炭加工和电力逆势承接，资金保留高股息防线",
            "impact": "大有能源4连板，电力股继续有数量优势，说明弱指数环境下资金仍用煤炭、电力和高股息方向做防守。",
            "whyHot": "指数下跌、个股跌多涨少时，资源和公用事业容易成为风险偏好回落阶段的承接方向。",
            "relatedThemes": ["资源品/煤炭/高股息", "电力能源/算力用电"],
            "watch": "看大有能源能否继续打开空间，以及电力是否从防御承接升级为算力用电主线。",
            "source": "每日经济新闻A股收评、东方财富涨停池归档",
            "url": "https://www.nbd.com.cn/articles/2026-06-04/4417379.html",
        },
        {
            "category": "科技",
            "heat": "AI PC延续",
            "title": "英伟达RTX Spark入局AI PC处理器，AMD表态欢迎竞争，端侧AI硬件叙事延续",
            "impact": "AI PC从单纯换机题材升级为本地智能体入口，映射到CPU/GPU、内存、PCB、散热、连接器、端侧AI软件。",
            "whyHot": "英伟达、AMD、微软和PC厂商围绕AI PC重新定义个人计算平台，A股消费电子和元件链仍会反复受到催化。",
            "relatedThemes": ["AI PC", "端侧AI", "消费电子/AI硬件/半导体"],
            "watch": "看AI PC是否能从新闻催化进入订单、产品和换机周期验证。",
            "source": "新浪科技热点小时报、每日经济新闻Computex报道",
            "url": "https://k.sina.com.cn/article_7857201856_1d45362c001906db0k.html",
        },
    ]


def update_charts(target_date, date_compact):
    charts = json.loads(CHARTS.read_text(encoding="utf-8"))
    for series in charts["series"]:
        points = fetch_kline(CHART_SECIDS[series["id"]], date_compact, limit=190)
        latest = next((point for point in reversed(points) if point["date"] == target_date), None)
        if not latest:
            raise RuntimeError(f"{series['id']} missing {target_date}")
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


def update_report(target_date):
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
        "summary": [
            f"{target_date}收盘，东方财富涨停池 qdate={date_compact}、tc={meta.get('tc')}；最高高度为4连板，大有能源、红星发展、天洋新材继续维持短线空间。",
            "三大指数集体收跌、个股跌多涨少，但涨停数升至80只，说明资金从指数交易切换到结构性题材抱团。",
            "科技线没有熄火，半导体、电子化学品、元件、光学光电和通信设备仍有多只涨停，AI硬件/CPO/半导体继续是最重要的弹性来源。",
            "煤炭、电力和高股息方向继续逆势承接，大有能源4连板强化资源防御辨识度，电力股维持数量优势。",
            "市场与科技新闻雷达继续覆盖盘面主线和泛科技新闻：重点跟踪AI Agent、CPO硅光、电子化学品、物理AI和AI PC。"
        ],
        "themes": themes,
        "ladder": ladder,
        "leaders": [
            {"type": "空间核心", "stocks": "大有能源、红星发展、天洋新材", "theme": "资源品/材料/高股息", "logic": "4连板高度扩展到资源和材料方向，说明弱指数环境下仍有短线高度，但主线并不单一。"},
            {"type": "科技中军", "stocks": "京东方A、三安光电、德明利、通鼎互联、中船特气", "theme": "AI硬件/CPO/半导体", "logic": "科技权重和硬件中军在指数回落中仍能涨停或强势，代表资金继续围绕AI硬件和半导体定价。"},
            {"type": "电力承接", "stocks": "豫能控股、新中港、百通能源、梅雁吉祥", "theme": "电力能源/算力用电", "logic": "电力股连续活跃，兼具迎峰度夏、公用事业防御和算力用电映射。"},
            {"type": "设备扩散", "stocks": "山科智能、泰坦股份、日发精机、联德股份", "theme": "机器人/高端制造/汽车链", "logic": "设备端和汽车链继续扩散，但需要观察是否能从首板扩散走出连板确认。"},
        ],
        "stats": [{"category": item["name"], "count": item["count"]} for item in themes],
        "stocks": stocks,
        "newHighScope": "收盘报告已生成，创新高模块待 scripts/update_screeners.py 补算。",
        "newHighStocks": [],
        "maConvergenceScope": "收盘报告已生成，均线粘合模块待 scripts/update_screeners.py 补算。",
        "maConvergenceStocks": [],
        "warnings": [
            "指数和多数个股偏弱，今天更适合按结构性题材处理，不宜把涨停数增加简单理解为全面风险偏好回升。",
            "科技线强在硬件和材料，中低位扩散较多，次日需要观察高标和中军是否同步承接。"
        ],
        "pdf": None,
        "marketNews": build_market_news(),
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
    update_report(args.date)
    charts = update_charts(args.date, date_compact)
    print(f"Updated report and charts for {args.date}")
    print([(series["id"], series["latestDate"], series["latestPct"]) for series in charts["series"]])


if __name__ == "__main__":
    main()
