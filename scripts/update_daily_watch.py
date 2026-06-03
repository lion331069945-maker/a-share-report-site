import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "daily_watch.json"
CN_TZ = timezone(timedelta(hours=8))

THEME_BY_INDUSTRY = {
    "元件": "AI硬件/CPO/半导体",
    "光学光电": "AI硬件/CPO/半导体",
    "通信设备": "AI硬件/CPO/半导体",
    "消费电子": "AI硬件/CPO/半导体",
    "半导体": "AI硬件/CPO/半导体",
    "其他电子": "AI硬件/CPO/半导体",
    "电子化学": "AI硬件/CPO/半导体",
    "电力": "电力能源/算力用电",
    "煤炭开采": "资源品/金属材料/高股息",
    "金属新材": "资源品/金属材料/高股息",
    "小金属": "资源品/金属材料/高股息",
    "冶钢原料": "资源品/金属材料/高股息",
    "炼化及贸": "化工材料/新能源材料",
    "化学原料": "化工材料/新能源材料",
    "化学制品": "化工材料/新能源材料",
    "塑料": "化工材料/新能源材料",
    "电池": "化工材料/新能源材料",
    "农化制品": "化工材料/新能源材料",
    "专用设备": "机器人/高端制造/汽车链",
    "自动化设": "机器人/高端制造/汽车链",
    "通用设备": "机器人/高端制造/汽车链",
    "航空装备": "机器人/高端制造/汽车链",
    "汽车零部": "机器人/高端制造/汽车链",
    "摩托车及": "机器人/高端制造/汽车链",
    "房地产开": "地产基建/城市更新",
    "基础建设": "地产基建/城市更新",
    "装修建材": "地产基建/城市更新",
    "小家电": "消费零售/家电服饰",
    "服装家纺": "消费零售/家电服饰",
    "饰品": "消费零售/家电服饰",
    "休闲食品": "消费零售/家电服饰",
    "包装印刷": "消费零售/家电服饰",
    "造纸": "消费零售/家电服饰",
    "家电零部": "消费零售/家电服饰",
    "IT服务Ⅱ": "AI应用/数据要素/服务",
    "专业服务": "AI应用/数据要素/服务",
}


def now_cn():
    return datetime.now(CN_TZ)


def parse_watch_until(value, current):
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) != 6:
        return None
    try:
        return current.replace(
            hour=int(digits[0:2]),
            minute=int(digits[2:4]),
            second=int(digits[4:6]),
            microsecond=0,
        )
    except ValueError:
        return None


def request_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/ztb/detail",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_zt_pool(date_compact):
    rows = []
    meta = {}
    for page in range(8):
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": str(page),
            "pagesize": "50",
            "sort": "fbt:asc",
            "date": date_compact,
            "_": str(int(time.time() * 1000)),
        }
        url = "https://push2ex.eastmoney.com/getTopicZTPool?" + urllib.parse.urlencode(params)
        payload = request_json(url)
        data = payload.get("data") or {}
        meta = {"qdate": data.get("qdate"), "tc": data.get("tc")}
        pool = data.get("pool") or []
        rows.extend(pool)
        if len(pool) < 50:
            break
    return rows, meta


def load_previous(date):
    if not OUT.exists():
        return None
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if data.get("date") == date else None


def format_time(value):
    if not value:
        return ""
    raw = str(int(value)).zfill(6)
    return f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}"


def code_with_market(row):
    code = str(row.get("c") or "")
    suffix = ".SH" if row.get("m") == 1 else ".SZ"
    return f"{code}{suffix}"


def money_text(value):
    value = float(value or 0)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿元"
    if value >= 10_000:
        return f"{value / 10_000:.0f}万元"
    return f"{value:.0f}元"


def status_text(row):
    reopen_count = int(row.get("zbc") or 0)
    if reopen_count == 0:
        return "竞价封板"
    return f"竞价封板，后续开板{reopen_count}次"


def theme_for(row):
    return THEME_BY_INDUSTRY.get(row.get("hybk") or "", "其他轮动")


def explain_stock(stock):
    if stock["ladder"] >= 3:
        return f"{stock['ladder']}连板竞价封住，是短线高度和情绪强弱的核心观察点。"
    if stock["sealFund"] >= 300_000_000:
        return f"封单金额靠前，代表{stock['theme']}方向开盘资金态度较强。"
    return f"{stock['theme']}方向竞价封板，观察同板块是否扩散。"


def row_to_stock(row, captured_at):
    price = float(row.get("p") or 0) / 1000
    fund = float(row.get("fund") or 0)
    seal_volume = fund / price if price else 0
    stock = {
        "code": code_with_market(row),
        "name": row.get("n") or "",
        "sector": row.get("hybk") or "未分类",
        "theme": theme_for(row),
        "ladder": int(row.get("lbc") or row.get("zttj", {}).get("ct") or 1),
        "price": round(price, 3),
        "sealFund": round(fund, 2),
        "sealVolume": round(seal_volume, 0),
        "firstLimitTime": format_time(row.get("fbt")),
        "lastLimitTime": format_time(row.get("lbt")),
        "reopenCount": int(row.get("zbc") or 0),
        "status": status_text(row),
        "pct": round(float(row.get("zdp") or 0), 2),
        "amount": round(float(row.get("amount") or 0), 2),
        "turnover": round(float(row.get("hs") or 0), 2),
        "capturedAt": captured_at,
    }
    stock["note"] = explain_stock(stock)
    return stock


def merge_stocks(previous, current):
    merged = {}
    for item in previous or []:
        if item.get("code"):
            merged[item["code"]] = item
    for item in current:
        old = merged.get(item["code"], {})
        merged[item["code"]] = {**old, **item, "capturedAt": old.get("capturedAt") or item["capturedAt"]}
    return sorted(merged.values(), key=lambda item: (item.get("ladder", 0), item.get("sealFund", 0)), reverse=True)


def build_forecast(stocks, hot_sectors, total_fund, max_ladder):
    count = len(stocks)
    top_sectors = "、".join([f"{item['name']}({item['count']})" for item in hot_sectors[:3]]) or "暂无集中方向"
    if count >= 8 and total_fund >= 1_500_000_000:
        mood = "竞价强度偏强"
        mood_text = f"竞价封板达到{count}只，封单总额约{money_text(total_fund)}，说明开盘资金风险偏好较高。"
    elif count >= 3:
        mood = "结构性活跃"
        mood_text = f"竞价封板{count}只，更多是结构性机会。重点看{top_sectors}能否带动同方向后排。"
    else:
        mood = "竞价偏谨慎"
        mood_text = f"竞价封板只有{count}只，盘前情绪不算强。若指数不能快速放量，早盘更适合等分歧后的承接。"

    ladder_text = "短线高度暂不明显"
    if max_ladder >= 3:
        ladder_text = f"最高{max_ladder}连板若继续大单封死，说明短线空间仍在；若高标开板回落，要防情绪退潮。"

    return [
        {"title": mood, "text": mood_text},
        {"title": "主线观察", "text": f"板块上优先看{top_sectors}。若开盘15分钟内同方向出现换手板或趋势核心放量上攻，说明竞价强度有扩散价值。"},
        {"title": "风险信号", "text": f"{ladder_text} 若竞价封板票开盘后封单快速衰减、前排炸板不回封，今日盘面容易从强预期转入分歧。"},
    ]


def main():
    current = now_cn()
    date = os.environ.get("WATCH_DATE") or current.strftime("%Y-%m-%d")
    date_compact = date.replace("-", "")
    previous = load_previous(date)
    rows = []
    meta = {}
    sample_seconds = int(os.environ.get("WATCH_SAMPLE_SECONDS", "0"))
    deadline = time.monotonic() + max(sample_seconds, 0)
    watch_until = parse_watch_until(os.environ.get("WATCH_UNTIL_HHMMSS"), current)
    if watch_until and current < watch_until:
        deadline = max(deadline, time.monotonic() + (watch_until - current).total_seconds())

    while True:
        latest_rows, meta = fetch_zt_pool(date_compact)
        if latest_rows:
            by_code = {str(row.get("c")): row for row in rows}
            for row in latest_rows:
                by_code[str(row.get("c"))] = row
            rows = list(by_code.values())
        if time.monotonic() >= deadline:
            break
        time.sleep(15)

    current = now_cn()
    captured_at = current.strftime("%H:%M:%S")

    if meta.get("qdate") and str(meta["qdate"]) != date_compact:
        result = {
            "date": date,
            "session": "竞价观察",
            "updatedAt": current.strftime("%Y-%m-%d %H:%M:%S +08:00"),
            "source": f"东方财富涨停池暂未返回当日数据，接口 qdate={meta.get('qdate')}",
            "limitUpCount": 0,
            "totalSealFund": 0,
            "maxLadder": 0,
            "hotSectors": [],
            "forecast": [{"title": "数据未更新", "text": "早盘数据源尚未切到当天，未使用旧日期数据冒充。"}],
            "stocks": [],
        }
    else:
        auction_rows = [row for row in rows if int(row.get("fbt") or 999999) <= 93000]
        current_stocks = [row_to_stock(row, captured_at) for row in auction_rows]
        stocks = merge_stocks((previous or {}).get("stocks", []), current_stocks)
        sector_counter = Counter(item["theme"] for item in stocks)
        hot_sectors = [
            {
                "name": name,
                "count": count,
                "sealFund": round(sum(item["sealFund"] for item in stocks if item["theme"] == name), 2),
            }
            for name, count in sector_counter.most_common(8)
        ]
        total_fund = round(sum(item["sealFund"] for item in stocks), 2)
        max_ladder = max([item["ladder"] for item in stocks], default=0)
        result = {
            "date": date,
            "session": "竞价观察",
            "updatedAt": current.strftime("%Y-%m-%d %H:%M:%S +08:00"),
            "source": f"东方财富涨停池 getTopicZTPool(date={date_compact})；口径为 09:25-09:30 期间已封住涨停的竞价/早盘封板票，后续炸板仍保留并标注状态。",
            "limitUpCount": len(stocks),
            "totalSealFund": total_fund,
            "maxLadder": max_ladder,
            "hotSectors": hot_sectors,
            "forecast": build_forecast(stocks, hot_sectors, total_fund, max_ladder),
            "stocks": stocks,
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"{result['date']} auction sealed limit-ups: {result['limitUpCount']}, total seal fund: {money_text(result['totalSealFund'])}")


if __name__ == "__main__":
    main()
