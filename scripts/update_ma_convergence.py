import argparse
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "site" / "data" if (ROOT / "site" / "data" / "reports.json").exists() else ROOT / "data"
REPORTS = SITE_DATA / "reports.json"
CACHE_DIR = SITE_DATA / "cache"
EASTMONEY_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
QUOTE_PAGE_SIZE = 100
MIN_MAIN_BOARD_QUOTE_COUNT = 1500
MA_PERIODS = (5, 10, 15, 20)
MA_RANGE_LIMIT_YUAN = 5.0
MAX_DAILY_PCT = 10.0
MAIN_BOARD_PREFIXES = ("600", "601", "603", "605", "000", "001", "002", "003")
FILTER_CACHE_VERSION = 4


def safe_float(value, default=0.0):
    try:
        if value in (None, "", "-"):
            return default
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return default


def normalize_code(value):
    return str(value or "").strip().split(".")[0]


def infer_market(code):
    code = normalize_code(code)
    if code.startswith(("5", "6", "9")):
        return "1"
    return "0"


def is_main_board_code(code):
    code = normalize_code(code)
    return code.startswith(MAIN_BOARD_PREFIXES)


def amount_yi(value):
    amount = safe_float(value)
    if not amount:
        return "--"
    return f"{amount / 100000000:.2f}亿"


def fetch_json_requests(url, params=None, referer="https://quote.eastmoney.com/"):
    if requests is not None:
        last_error = None
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": referer,
            "Accept": "application/json,text/plain,*/*",
            "Connection": "close",
        }
        for attempt in range(5):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=35)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_error = exc
                time.sleep(1.2 * (attempt + 1))
        raise last_error

    full_url = url
    if params:
        full_url = url + "?" + urllib.parse.urlencode(params)
    return json.loads(fetch_text(full_url, headers={"Referer": referer}, timeout=35, retries=5))


def fetch_text(url, encoding="utf-8", headers=None, timeout=18, retries=3):
    last_error = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/",
                "Accept": "application/json,text/plain,*/*",
                "Connection": "close",
                **(headers or {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
                return resp.read().decode(encoding, errors="replace")
        except Exception as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    raise last_error


def parse_json_or_jsonp(text):
    stripped = text.strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1]
    open_paren = stripped.find("(")
    close_paren = stripped.rfind(")")
    if open_paren > 0 and close_paren > open_paren:
        stripped = stripped[open_paren + 1 : close_paren]
    return json.loads(stripped)


def load_reports():
    return json.loads(REPORTS.read_text(encoding="utf-8-sig"))


def find_report(data, report_date=None):
    for report in data.get("reports", []):
        if report_date is None or report.get("date") == report_date:
            return report
    raise RuntimeError(f"No report found for {report_date or 'latest'}")


def fetch_all_a_quotes():
    fields = "f2,f3,f6,f12,f14,f20,f21,f100"
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
    rows = []
    page = 1
    while True:
        params = {
            "pn": page,
            "pz": QUOTE_PAGE_SIZE,
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": fs,
            "fields": fields,
            "_": int(time.time() * 1000),
        }
        payload = fetch_json_requests(EASTMONEY_CLIST_URL, params=params)
        diff = (payload.get("data") or {}).get("diff") or []
        if not diff:
            break
        for item in diff:
            code = normalize_code(item.get("f12"))
            name = str(item.get("f14") or "")
            if not code or not name or "ST" in name.upper() or name.startswith(("N", "C")):
                continue
            if not is_main_board_code(code):
                continue
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "market": infer_market(code),
                    "close": safe_float(item.get("f2")),
                    "pct": safe_float(item.get("f3")),
                    "amount": safe_float(item.get("f6")),
                    "totalMarketCap": safe_float(item.get("f20")),
                    "floatMarketCap": safe_float(item.get("f21")),
                    "industry": item.get("f100") or "未分类",
                }
            )
        total = safe_float((payload.get("data") or {}).get("total"))
        if len(diff) < QUOTE_PAGE_SIZE or (total and page * QUOTE_PAGE_SIZE >= total):
            break
        page += 1
    if len(rows) < MIN_MAIN_BOARD_QUOTE_COUNT:
        raise RuntimeError(f"Full A main-board quote list is incomplete: {len(rows)} rows")
    return rows


def fallback_quotes_from_report(report):
    seen = {}
    for source in ("stocks", "newHighStocks", "newHighs", "techPullbackStocks"):
        for item in report.get(source, []) or []:
            code = normalize_code(item.get("code"))
            name = item.get("name") or ""
            if not code or not name or code in seen:
                continue
            if not is_main_board_code(code):
                continue
            seen[code] = {
                "code": code,
                "name": name,
                "market": infer_market(code),
                "close": safe_float(item.get("close") or item.get("price")),
                "pct": safe_float(item.get("pct") or item.get("changePct")),
                "amount": safe_float(item.get("amount")),
                "totalMarketCap": 0,
                "floatMarketCap": 0,
                "industry": item.get("industry") or item.get("sector") or item.get("category") or item.get("board") or "未分类",
            }
    return list(seen.values())


def fetch_kline(secid, end_date):
    params = {
        "secid": secid,
        "klt": "101",
        "fqt": "1",
        "lmt": "70",
        "end": end_date.replace("-", ""),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    urls = [
        "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params),
        "https://push2test.eastmoney.com/api/qt/stock/kline/get?"
        + urllib.parse.urlencode(
            {
                **params,
                "cb": "callback",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "beg": "0",
                "smplmt": "1000000",
            }
        ),
    ]
    last_error = None
    for url in urls:
        try:
            payload = parse_json_or_jsonp(fetch_text(url)) if "push2test" in url else json.loads(fetch_text(url))
            break
        except Exception as exc:
            last_error = exc
    else:
        raise last_error

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
    return points


def moving_average(values, period, end_index):
    start = end_index - period + 1
    if start < 0:
        return None
    window = values[start : end_index + 1]
    if len(window) != period or any(value <= 0 for value in window):
        return None
    return sum(window) / period


def ma_pack(points, end_index):
    closes = [point["close"] for point in points]
    result = {}
    for period in MA_PERIODS:
        value = moving_average(closes, period, end_index)
        if value is None:
            return None
        result[f"ma{period}"] = value
    return result


def ma_spread(ma_values):
    values = [ma_values[f"ma{period}"] for period in MA_PERIODS if ma_values.get(f"ma{period}", 0) > 0]
    if len(values) != len(MA_PERIODS):
        return 999.0
    return (max(values) / min(values) - 1) * 100


def ma_range_yuan(ma_values):
    values = [ma_values[f"ma{period}"] for period in MA_PERIODS if ma_values.get(f"ma{period}", 0) > 0]
    if len(values) != len(MA_PERIODS):
        return 999.0
    return max(values) - min(values)


def is_bullish(ma_values):
    return all(ma_values[f"ma{left}"] > ma_values[f"ma{right}"] for left, right in zip(MA_PERIODS, MA_PERIODS[1:]))


def build_note(today, ma_values, spread, range_yuan, volume_ratio, recent_gain):
    ma_text = "、".join(f"MA{period} {ma_values[f'ma{period}']:.2f}" for period in MA_PERIODS)
    return (
        f"收盘{today['close']:.2f}，当日涨幅{today['pct']:.2f}%；"
        f"均线区间宽度{range_yuan:.2f}元，最大乖离{spread:.2f}%，{ma_text}；"
        f"成交量为5日均量{volume_ratio:.2f}倍，近10日涨幅{recent_gain:.2f}%。"
    )


def evaluate_quote(quote, target_date):
    secid = f"{quote['market']}.{quote['code']}"
    points = fetch_kline(secid, target_date)
    if len(points) < 35 or points[-1]["date"] != target_date:
        return None

    today_index = len(points) - 1
    today = points[today_index]
    if today["pct"] > MAX_DAILY_PCT:
        return None
    prev_index = today_index - 1
    today_ma = ma_pack(points, today_index)
    prev_ma = ma_pack(points, prev_index)
    if not today_ma or not prev_ma:
        return None

    recent_ma = []
    for offset in range(0, 6):
        packed = ma_pack(points, today_index - offset)
        if packed:
            recent_ma.append((offset, packed, ma_spread(packed), ma_range_yuan(packed)))
    if not recent_ma:
        return None

    min_recent_range = min(item[3] for item in recent_ma)
    prev_spread = ma_spread(prev_ma)
    today_spread = ma_spread(today_ma)
    prev_range = ma_range_yuan(prev_ma)
    today_range = ma_range_yuan(today_ma)
    volume_base = sum(point["volume"] for point in points[-6:-1]) / 5
    volume_ratio = today["volume"] / volume_base if volume_base else 0
    recent_gain = (today["close"] / points[-11]["close"] - 1) * 100 if points[-11]["close"] else 0

    max_ma = max(today_ma[f"ma{period}"] for period in MA_PERIODS)
    prev_max_ma = max(prev_ma[f"ma{period}"] for period in MA_PERIODS)
    types = []

    in_range_today = today_range <= MA_RANGE_LIMIT_YUAN
    in_range_recent = min_recent_range <= MA_RANGE_LIMIT_YUAN
    if not in_range_today:
        return None

    breakout = (
        prev_range <= MA_RANGE_LIMIT_YUAN
        and today["close"] >= max_ma * 1.005
        and points[-2]["close"] <= prev_max_ma * 1.012
        and today["pct"] >= 3
        and volume_ratio >= 1.5
    )
    if breakout:
        types.append("均线黏合 + 放量突破")

    bullish_spread = (
        in_range_recent
        and is_bullish(today_ma)
        and today_ma["ma5"] > ma_pack(points, today_index - 3)["ma5"]
        and today["close"] >= today_ma["ma10"]
    )
    if bullish_spread:
        types.append("黏合后均线多头发散")

    if not types and in_range_today:
        if today["close"] < max_ma:
            types.append("均线区间内观察")
        else:
            types.append("均线区间内偏强")

    if not types:
        return None

    return {
        "code": quote["code"],
        "name": quote["name"],
        "type": " / ".join(types),
        "sector": quote["industry"] or "未分类",
        "pct": round(today["pct"], 2),
        "recentGainPct": round(recent_gain, 2),
        "maSpreadPct": round(today_spread, 2),
        "maRangeYuan": round(today_range, 2),
        "volumeRatio": round(volume_ratio, 2),
        "amount": amount_yi(today["amount"] or quote["amount"]),
        "close": round(today["close"], 3),
        "ma5": round(today_ma["ma5"], 3),
        "ma10": round(today_ma["ma10"], 3),
        "ma15": round(today_ma["ma15"], 3),
        "ma20": round(today_ma["ma20"], 3),
        "note": build_note(today, today_ma, today_spread, today_range, volume_ratio, recent_gain),
    }


def build_rows(report, report_date, max_workers=24):
    cache_file = CACHE_DIR / f"ma_convergence_{report_date}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        cache_matches = (
            cached.get("cacheVersion") == FILTER_CACHE_VERSION
            and cached.get("maPeriods") == list(MA_PERIODS)
            and cached.get("maRangeLimitYuan") == MA_RANGE_LIMIT_YUAN
            and cached.get("maxDailyPct") == MAX_DAILY_PCT
            and cached.get("mainBoardOnly") is True
        )
        if cache_matches:
            return cached.get("rows", []), cached.get("quoteCount", 0), cached.get("quoteSource", "全A主板股票池")

    quote_source = "全A主板股票池"
    try:
        quotes = fetch_all_a_quotes()
    except Exception as exc:
        print(f"Full A quote list failed, fallback to report stock pool: {exc}")
        quotes = fallback_quotes_from_report(report)
        quote_source = "当日报告主板样本池"
    rows = []
    checked = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(evaluate_quote, quote, report_date): quote for quote in quotes}
        for future in as_completed(futures):
            quote = futures[future]
            checked += 1
            try:
                row = future.result()
            except Exception as exc:
                if checked % 300 == 0:
                    print(f"Skip {quote['code']} {quote['name']}: {exc}")
                continue
            if row:
                rows.append(row)
            if checked % 500 == 0:
                print(f"Checked {checked}/{len(quotes)}, matched {len(rows)}")

    rows.sort(
        key=lambda item: (
            0 if "放量突破" in item["type"] else 1,
            0 if "多头发散" in item["type"] else 1,
            -item["pct"],
            -item["volumeRatio"],
            item.get("maRangeYuan", item["maSpreadPct"]),
        )
    )
    rows = rows[:180]
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {
                    "date": report_date,
                    "quoteCount": len(quotes),
                    "quoteSource": quote_source,
                    "cacheVersion": FILTER_CACHE_VERSION,
                    "maPeriods": list(MA_PERIODS),
                    "maRangeLimitYuan": MA_RANGE_LIMIT_YUAN,
                    "maxDailyPct": MAX_DAILY_PCT,
                    "mainBoardOnly": True,
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"Cache write skipped: {exc}")
    return rows, len(quotes), quote_source


def build_output(report_date=None, max_workers=24):
    data = load_reports()
    report = find_report(data, report_date)
    target = report["date"]
    result = build_rows(report, target, max_workers=max_workers)
    if len(result) == 2:
        rows, quote_count = result
        quote_source = "全A主板股票池"
    else:
        rows, quote_count, quote_source = result
    scope = (
        f"筛选口径：{quote_source}{quote_count}只，使用前复权日K计算5日、10日、15日、20日均线；"
        "只要四条均线最高值与最低值落在5元价格区间内即可进入筛选，不要求完全黏合；同时剔除当日涨幅超过10%的股票，仅保留主板观察样本。"
        "类型包含均线区间内观察、均线区间内偏强、均线黏合+放量突破、黏合后均线多头发散，黏合前、黏合中和黏合后均可入表。"
        f"本次命中{len(rows)}只。"
    )
    return target, rows, quote_count, scope


def update_report(report_date=None, max_workers=24):
    data = load_reports()
    report = find_report(data, report_date)
    target, rows, quote_count, scope = build_output(report_date, max_workers=max_workers)
    report["maConvergenceScope"] = (
        scope
    )
    report["maConvergenceStocks"] = rows
    data["updatedAt"] = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +08:00")
    REPORTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows, REPORTS


def main():
    parser = argparse.ArgumentParser(description="Update MA convergence candidates in reports.json")
    parser.add_argument("--report-date", help="Report date such as 2026-05-28. Defaults to latest report.")
    parser.add_argument("--max-workers", type=int, default=24)
    parser.add_argument("--output-json", help="Write calculated rows to this JSON file without updating reports.json.")
    args = parser.parse_args()
    if args.output_json:
        target, rows, quote_count, scope = build_output(args.report_date, max_workers=args.max_workers)
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {"date": target, "quoteCount": quote_count, "scope": scope, "rows": rows},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {output_path}")
        print(f"Saved MA convergence rows: {len(rows)}")
        return

    rows, path = update_report(args.report_date, max_workers=args.max_workers)
    print(f"Updated {path}")
    print(f"Saved MA convergence rows: {len(rows)}")
    for row in rows[:40]:
        print(row["code"], row["name"], row["type"], row["sector"], row["pct"], row["recentGainPct"], row["volumeRatio"])


if __name__ == "__main__":
    main()
