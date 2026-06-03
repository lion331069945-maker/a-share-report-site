import argparse
import json
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reports.json"
CN_TZ = timezone(timedelta(hours=8))

CLIST_URL = "https://push2delay.eastmoney.com/api/qt/clist/get"
KLINE_HOSTS = (
    "https://push2test.eastmoney.com/api/qt/stock/kline/get",
    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
    "https://push2.eastmoney.com/api/qt/stock/kline/get",
)
FIELDS = "f2,f3,f6,f12,f14,f20,f21,f100"
FS_ALL_A = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
MAIN_BOARD_PREFIXES = ("600", "601", "603", "605", "000", "001", "002", "003")
MA_PERIODS = (5, 10, 15, 20)
MA_RANGE_LIMIT_YUAN = 5.0
MAX_DAILY_PCT = 10.0


def safe_float(value, default=0.0):
    try:
        if value in (None, "", "-"):
            return default
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return default


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


def market_for_code(code):
    return "1" if str(code).startswith(("5", "6", "9")) else "0"


def is_main_board(code):
    return str(code).startswith(MAIN_BOARD_PREFIXES)


def amount_yi(value):
    amount = safe_float(value)
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.2f}亿"
    if amount >= 10_000:
        return f"{amount / 10_000:.0f}万"
    return f"{amount:.0f}"


def load_reports():
    return json.loads(REPORTS.read_text(encoding="utf-8-sig"))


def find_report(data, report_date=None):
    for report in data.get("reports", []):
        if report_date is None or report.get("date") == report_date:
            return report
    raise RuntimeError(f"No report found for {report_date or 'latest'}")


def fetch_quotes():
    rows = []
    page = 1
    while True:
        payload = fetch_json(
            CLIST_URL,
            {
                "pn": page,
                "pz": 100,
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": FS_ALL_A,
                "fields": FIELDS,
                "_": int(time.time() * 1000),
            },
        )
        data = payload.get("data") or {}
        diff = data.get("diff") or []
        if not diff:
            break
        for item in diff:
            code = str(item.get("f12") or "")
            name = str(item.get("f14") or "")
            if not code or not name or "ST" in name.upper() or name.startswith(("N", "C")):
                continue
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "market": market_for_code(code),
                    "close": safe_float(item.get("f2")),
                    "pct": safe_float(item.get("f3")),
                    "amount": safe_float(item.get("f6")),
                    "industry": item.get("f100") or "未分类",
                }
            )
        total = int(data.get("total") or 0)
        if len(diff) < 100 or (total and page * 100 >= total):
            break
        page += 1
    if len(rows) < 4000:
        raise RuntimeError(f"Quote list incomplete: {len(rows)} rows")
    return rows


def fetch_kline(quote, target_date):
    params = {
        "secid": f"{quote['market']}.{quote['code']}",
        "klt": "101",
        "fqt": "1",
        "lmt": "280",
        "end": target_date.replace("-", ""),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "_": int(time.time() * 1000),
    }
    last_error = None
    for host in KLINE_HOSTS:
        try:
            payload = fetch_json(host, params=params, retries=2, timeout=20)
            points = []
            for row in (payload.get("data") or {}).get("klines") or []:
                date, open_, close, high, low, volume, amount, amplitude, pct, change, turnover = row.split(",")
                points.append(
                    {
                        "date": date,
                        "open": safe_float(open_),
                        "close": safe_float(close),
                        "high": safe_float(high),
                        "low": safe_float(low),
                        "volume": safe_float(volume),
                        "amount": safe_float(amount),
                        "pct": safe_float(pct),
                    }
                )
            if points and points[-1]["date"] == target_date:
                return points
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"{quote['code']} kline failed: {last_error}")


def moving_average(values, period):
    if len(values) < period:
        return None
    window = values[-period:]
    if any(value <= 0 for value in window):
        return None
    return sum(window) / period


def ma_pack(points):
    closes = [point["close"] for point in points]
    result = {}
    for period in MA_PERIODS:
        value = moving_average(closes, period)
        if value is None:
            return None
        result[f"ma{period}"] = value
    return result


def ma_type(today, prev, ma_values, prev_ma_values, volume_ratio):
    values = [ma_values[f"ma{period}"] for period in MA_PERIODS]
    prev_values = [prev_ma_values[f"ma{period}"] for period in MA_PERIODS]
    ma_range = max(values) - min(values)
    prev_range = max(prev_values) - min(prev_values)
    max_ma = max(values)
    prev_max_ma = max(prev_values)
    types = []
    if prev_range <= MA_RANGE_LIMIT_YUAN and today["close"] >= max_ma * 1.005 and prev["close"] <= prev_max_ma * 1.012 and today["pct"] >= 3 and volume_ratio >= 1.5:
        types.append("均线粘合 + 放量突破")
    if all(values[index] > values[index + 1] for index in range(len(values) - 1)) and today["close"] >= ma_values["ma10"]:
        types.append("粘合后均线多头发散")
    if not types:
        types.append("均线区间内偏强" if today["close"] >= max_ma else "均线区间内观察")
    return " / ".join(types), ma_range


def evaluate(quote, target_date):
    points = fetch_kline(quote, target_date)
    if len(points) < 35:
        return None, None
    today = points[-1]
    prev = points[-2]

    new_high = None
    windows = [
        ("近1月新高", 20),
        ("近3月新高", 60),
        ("近半年新高", 120),
        ("近一年新高", min(250, len(points) - 1)),
    ]
    previous_points = points[:-1]
    best_type = None
    for label, size in windows:
        if len(previous_points) >= size:
            previous_high = max(point["high"] for point in previous_points[-size:])
            if today["close"] > previous_high:
                best_type = f"收盘创{label}"
            elif today["high"] > previous_high and best_type is None:
                best_type = f"盘中创{label}"
    if best_type:
        new_high = {
            "code": quote["code"],
            "name": quote["name"],
            "highType": best_type,
            "sector": quote["industry"],
            "catalyst": "收盘后按东方财富日K计算出的阶段新高样本，结合行业景气、资金趋势和当日强弱观察。",
            "note": f"收盘{today['close']:.2f}，日涨幅{today['pct']:.2f}%，盘中高点{today['high']:.2f}。",
        }

    ma_row = None
    if is_main_board(quote["code"]) and today["pct"] <= MAX_DAILY_PCT:
        ma_values = ma_pack(points)
        prev_ma_values = ma_pack(points[:-1])
        if ma_values and prev_ma_values:
            values = [ma_values[f"ma{period}"] for period in MA_PERIODS]
            ma_range = max(values) - min(values)
            if ma_range <= MA_RANGE_LIMIT_YUAN:
                volume_base = sum(point["volume"] for point in points[-6:-1]) / 5
                volume_ratio = today["volume"] / volume_base if volume_base else 0
                type_text, ma_range = ma_type(today, prev, ma_values, prev_ma_values, volume_ratio)
                recent_gain = (today["close"] / points[-11]["close"] - 1) * 100 if len(points) >= 11 and points[-11]["close"] else 0
                ma_text = "、".join(f"MA{period} {ma_values[f'ma{period}']:.2f}" for period in MA_PERIODS)
                ma_row = {
                    "code": quote["code"],
                    "name": quote["name"],
                    "type": type_text,
                    "sector": quote["industry"],
                    "pct": round(today["pct"], 2),
                    "recentGainPct": round(recent_gain, 2),
                    "maRangeYuan": round(ma_range, 2),
                    "volumeRatio": round(volume_ratio, 2),
                    "amount": amount_yi(today["amount"] or quote["amount"]),
                    "close": round(today["close"], 3),
                    "ma5": round(ma_values["ma5"], 3),
                    "ma10": round(ma_values["ma10"], 3),
                    "ma15": round(ma_values["ma15"], 3),
                    "ma20": round(ma_values["ma20"], 3),
                    "note": f"收盘{today['close']:.2f}，{ma_text}，均线区间{ma_range:.2f}元，成交量为5日均量{volume_ratio:.2f}倍。",
                }
    return new_high, ma_row


def update_report(report_date=None, max_workers=24):
    data = load_reports()
    report = find_report(data, report_date)
    target = report["date"]
    quotes = fetch_quotes()
    new_high_rows = []
    ma_rows = []
    checked = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(evaluate, quote, target): quote for quote in quotes}
        for future in as_completed(futures):
            checked += 1
            try:
                new_high, ma_row = future.result()
            except Exception:
                continue
            if new_high:
                new_high_rows.append(new_high)
            if ma_row:
                ma_rows.append(ma_row)
            if checked % 500 == 0:
                print(f"Checked {checked}/{len(quotes)}, new highs {len(new_high_rows)}, MA {len(ma_rows)}")

    high_order = {"收盘创近一年新高": 0, "盘中创近一年新高": 1, "收盘创近半年新高": 2, "盘中创近半年新高": 3}
    new_high_rows.sort(key=lambda item: (high_order.get(item["highType"], 9), item["sector"], item["code"]))
    ma_rows.sort(
        key=lambda item: (
            0 if "放量突破" in item["type"] else 1,
            0 if "多头发散" in item["type"] else 1,
            -item["pct"],
            -item["volumeRatio"],
            item["maRangeYuan"],
        )
    )
    new_high_rows = new_high_rows[:180]
    ma_rows = ma_rows[:180]
    report["newHighScope"] = (
        f"东方财富全A股票池{len(quotes)}只，使用前复权日K按收盘价/盘中最高价计算近1月、近3月、近半年、近一年阶段新高；"
        f"本次命中{len(new_high_rows)}只展示样本。"
    )
    report["newHighStocks"] = new_high_rows
    report["maConvergenceScope"] = (
        f"筛选口径：东方财富全A股票池中主板股票，使用前复权日K计算5/10/15/20日均线；"
        f"四条均线最高值与最低值落在{MA_RANGE_LIMIT_YUAN:.0f}元价格区间内即可进入筛选，同时剔除当日涨幅超过{MAX_DAILY_PCT:.0f}%的股票；"
        f"本次命中{len(ma_rows)}只展示样本。"
    )
    report["maConvergenceStocks"] = ma_rows
    data["updatedAt"] = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S +08:00")
    REPORTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_high_rows, ma_rows


def main():
    parser = argparse.ArgumentParser(description="Update new-high and MA-convergence screeners in reports.json")
    parser.add_argument("--report-date", help="Report date such as 2026-06-03. Defaults to latest report.")
    parser.add_argument("--max-workers", type=int, default=24)
    args = parser.parse_args()
    new_highs, ma_rows = update_report(args.report_date, max_workers=args.max_workers)
    print(f"Saved new high rows: {len(new_highs)}")
    print(f"Saved MA convergence rows: {len(ma_rows)}")


if __name__ == "__main__":
    main()
