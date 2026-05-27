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


def now_cn():
    return datetime.now(CN_TZ)


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


def format_time(value):
    if not value:
        return ""
    raw = str(int(value)).zfill(6)
    return f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}"


def code_with_market(row):
    code = str(row.get("c") or "")
    market = row.get("m")
    suffix = ".SH" if market == 1 else ".SZ"
    return f"{code}{suffix}"


def explain_stock(row):
    ladder = int(row.get("lbc") or row.get("zttj", {}).get("ct") or 1)
    fund = float(row.get("fund") or 0)
    sector = row.get("hybk") or "未分类"
    if ladder >= 3:
        return f"{ladder}连板竞价封死，是短线高度和情绪强弱的核心观察点。"
    if fund >= 300_000_000:
        return f"封单金额靠前，代表{sector}方向开盘资金态度较强。"
    return f"{sector}方向竞价一字板，观察同板块是否扩散。"


def build_forecast(stocks, hot_sectors, total_fund, max_ladder):
    count = len(stocks)
    top_sectors = "、".join([f"{item['name']}({item['count']})" for item in hot_sectors[:3]]) or "暂无集中方向"
    if count >= 8 and total_fund >= 1_500_000_000:
        mood = "竞价强度偏强"
        mood_text = f"竞价一字板达到{count}只，封单总额约{money_text(total_fund)}，说明开盘资金风险偏好较高。若开盘后前排不炸板，盘面大概率先看强修复或题材扩散。"
    elif count >= 3:
        mood = "结构性活跃"
        mood_text = f"竞价一字板{count}只，更多是结构性机会。重点看{top_sectors}能否带动同方向后排，而不是简单追一字板本身。"
    else:
        mood = "竞价偏谨慎"
        mood_text = f"竞价一字板只有{count}只，盘前情绪不算强。若指数不能快速放量，早盘更适合等分歧后的承接。"

    ladder_text = "短线高度暂不明显"
    if max_ladder >= 3:
        ladder_text = f"最高{max_ladder}连板若继续大单封死，说明短线空间仍在；若高标开板回落，要防情绪退潮。"

    return [
        {"title": mood, "text": mood_text},
        {"title": "主线观察", "text": f"板块上优先看{top_sectors}。如果开盘 15 分钟内同方向出现换手板或趋势核心放量上攻，说明竞价强度有扩散价值。"},
        {"title": "风险信号", "text": f"{ladder_text} 若一字板封单快速衰减、前排炸板不回封，今日盘面容易从强预期转入分歧。"},
    ]


def money_text(value):
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿"
    if value >= 10_000:
        return f"{value / 10_000:.0f}万"
    return f"{value:.0f}"


def main():
    current = now_cn()
    date = os.environ.get("WATCH_DATE") or current.strftime("%Y-%m-%d")
    date_compact = date.replace("-", "")
    rows, meta = fetch_zt_pool(date_compact)

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
        auction_rows = [
            row for row in rows
            if int(row.get("fbt") or 999999) <= 93000 and int(row.get("zbc") or 0) == 0
        ]
        stocks = []
        for row in auction_rows:
            price = float(row.get("p") or 0) / 1000
            fund = float(row.get("fund") or 0)
            seal_volume = fund / price if price else 0
            stocks.append(
                {
                    "code": code_with_market(row),
                    "name": row.get("n") or "",
                    "sector": row.get("hybk") or "未分类",
                    "ladder": int(row.get("lbc") or row.get("zttj", {}).get("ct") or 1),
                    "price": round(price, 3),
                    "sealFund": round(fund, 2),
                    "sealVolume": round(seal_volume, 0),
                    "firstLimitTime": format_time(row.get("fbt")),
                    "pct": round(float(row.get("zdp") or 0), 2),
                    "note": explain_stock(row),
                }
            )
        stocks.sort(key=lambda item: (item["ladder"], item["sealFund"]), reverse=True)
        sector_counter = Counter(item["sector"] for item in stocks)
        hot_sectors = [
            {"name": name, "count": count, "sealFund": sum(item["sealFund"] for item in stocks if item["sector"] == name)}
            for name, count in sector_counter.most_common(8)
        ]
        total_fund = sum(item["sealFund"] for item in stocks)
        max_ladder = max([item["ladder"] for item in stocks], default=0)
        result = {
            "date": date,
            "session": "竞价观察",
            "updatedAt": current.strftime("%Y-%m-%d %H:%M:%S +08:00"),
            "source": f"东方财富涨停池 getTopicZTPool(date={date_compact})，筛选首次封板时间 fbt<=09:30 且未开板 zbc=0 的竞价/开盘一字板；fund 为封单金额，封单量按 fund/涨停价估算。",
            "limitUpCount": len(stocks),
            "totalSealFund": round(total_fund, 2),
            "maxLadder": max_ladder,
            "hotSectors": hot_sectors,
            "forecast": build_forecast(stocks, hot_sectors, total_fund, max_ladder),
            "stocks": stocks,
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"{result['date']} auction limit-ups: {result['limitUpCount']}, total seal fund: {money_text(result['totalSealFund'])}")


if __name__ == "__main__":
    main()
