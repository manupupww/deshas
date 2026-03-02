import modal
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Modal app
app = modal.App("binance-data-dashboard")
image = modal.Image.debian_slim().pip_install("pandas", "requests", "python-dateutil", "ccxt")


def download_vision_zips(base_url, data_type, clean_symbol, start_dt, end_dt, klines_tf=None):
    """
    Universal Binance Vision downloader.
    Downloads monthly archives first, then fills gaps with daily archives.
    Works for: aggTrades, liquidationOrders, klines/{tf}
    """
    all_dfs = []

    # Build the path segment
    if klines_tf:
        path_segment = f"klines/{clean_symbol}/{klines_tf}"
        file_prefix = f"{clean_symbol}-{klines_tf}"
    else:
        path_segment = f"{data_type}/{clean_symbol}"
        file_prefix = f"{clean_symbol}-{data_type}"

    # 1) Monthly archives
    monthly_done = []
    current_month = start_dt.replace(day=1)
    while current_month <= end_dt.replace(day=1):
        next_month = current_month + relativedelta(months=1)
        if next_month <= datetime.now().replace(day=1):
            m_str = current_month.strftime("%Y-%m")
            url = f"{base_url}/monthly/{path_segment}/{file_prefix}-{m_str}.zip"
            try:
                res = requests.get(url, timeout=30)
                if res.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                        with z.open(z.namelist()[0]) as f:
                            df = pd.read_csv(f, header=None)
                            if not str(df.iloc[0, 0]).isdigit():
                                df = df.iloc[1:].reset_index(drop=True)
                            all_dfs.append(df)
                            monthly_done.append(current_month)
                            print(f"  [OK] Month {m_str}: {len(df)} rows")
                else:
                    print(f"  [SKIP] Month {m_str}: HTTP {res.status_code}")
            except Exception as e:
                print(f"  [ERR] Month {m_str}: {e}")
        current_month = next_month

    # 2) Daily archives for uncovered days
    temp_date = start_dt
    while temp_date <= end_dt:
        is_covered = any(
            m_dt <= temp_date < (m_dt + relativedelta(months=1))
            for m_dt in monthly_done
        )
        if not is_covered and temp_date < datetime.now():
            d_str = temp_date.strftime("%Y-%m-%d")
            url = f"{base_url}/daily/{path_segment}/{file_prefix}-{d_str}.zip"
            try:
                res = requests.get(url, timeout=15)
                if res.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                        with z.open(z.namelist()[0]) as f:
                            df = pd.read_csv(f, header=None)
                            if not str(df.iloc[0, 0]).isdigit():
                                df = df.iloc[1:].reset_index(drop=True)
                            all_dfs.append(df)
            except:
                pass
        temp_date += timedelta(days=1)

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


# ============================================================
# CLOUD FUNCTIONS
# ============================================================

@app.function(image=image, timeout=7200, cpu=2.0, memory=8192)
def fetch_klines_cloud(symbol: str, timeframe: str, start_date: str, end_date: str):
    """Download Klines (OHLCV) in the cloud."""
    print(f"[CLOUD] Klines: {symbol} {timeframe} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    raw = download_vision_zips(base_url, "klines", clean_symbol, start_dt, end_dt, klines_tf=timeframe)
    if raw.empty:
        return {"success": False, "message": "Duomenu nerasta."}

    raw = raw.iloc[:, :6]
    raw.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    raw['timestamp'] = pd.to_datetime(pd.to_numeric(raw['timestamp']), unit='ms')
    raw = raw[(raw['timestamp'] >= pd.to_datetime(start_dt)) &
              (raw['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
    raw = raw.sort_values('timestamp').reset_index(drop=True)

    print(f"[CLOUD] Klines done: {len(raw)} rows")
    csv_string = raw.to_csv(index=False)
    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string}


@app.function(image=image, timeout=7200, cpu=2.0, memory=8192)
def fetch_aggtrades_cloud(symbol: str, start_date: str, end_date: str):
    """Download AggTrades in the cloud."""
    print(f"[CLOUD] AggTrades: {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    raw = download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt)
    if raw.empty:
        return {"success": False, "message": "Duomenu nerasta."}

    raw.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
    raw['timestamp'] = pd.to_datetime(pd.to_numeric(raw['timestamp']), unit='ms')
    raw = raw[(raw['timestamp'] >= pd.to_datetime(start_dt)) &
              (raw['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
    raw = raw.sort_values('timestamp').reset_index(drop=True)

    print(f"[CLOUD] AggTrades done: {len(raw)} rows")
    csv_string = raw.to_csv(index=False)
    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string}


@app.function(image=image, timeout=7200, cpu=2.0, memory=8192)
def fetch_liquidations_cloud(symbol: str, start_date: str, end_date: str):
    """Download Liquidations in the cloud."""
    print(f"[CLOUD] Liquidations: {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    raw = download_vision_zips(base_url, "liquidationOrders", clean_symbol, start_dt, end_dt)
    if raw.empty:
        return {"success": False, "message": "Duomenu nerasta."}

    raw.columns = ['symbol', 'side', 'order_type', 'time_in_force', 'original_quantity', 'price',
                   'average_price', 'order_status', 'last_fill_quantity', 'accumulated_fill_quantity', 'timestamp']
    raw['timestamp'] = pd.to_datetime(pd.to_numeric(raw['timestamp']), unit='ms')
    raw = raw[(raw['timestamp'] >= pd.to_datetime(start_dt)) &
              (raw['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
    raw = raw.sort_values('timestamp').reset_index(drop=True)

    print(f"[CLOUD] Liquidations done: {len(raw)} rows")
    csv_string = raw.to_csv(index=False)
    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string}


@app.function(image=image, timeout=7200, cpu=2.0, memory=8192)
def fetch_dollar_bars_cloud(symbol: str, start_date: str, end_date: str, threshold: float = 1_000_000):
    """Download AggTrades and generate Dollar Bars in the cloud."""
    print(f"[CLOUD] Dollar Bars: {symbol} | {start_date} -> {end_date} | Threshold: {threshold}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    raw = download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt)
    if raw.empty:
        return {"success": False, "message": "AggTrades nerasta, Dollar Bars sugeneruoti nepavyko."}

    raw.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
    raw['timestamp'] = pd.to_datetime(pd.to_numeric(raw['timestamp']), unit='ms')
    raw = raw[(raw['timestamp'] >= pd.to_datetime(start_dt)) &
              (raw['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
    raw = raw.sort_values('timestamp').reset_index(drop=True)
    raw['price'] = pd.to_numeric(raw['price'])
    raw['quantity'] = pd.to_numeric(raw['quantity'])
    raw['dollar_value'] = raw['price'] * raw['quantity']

    print(f"[CLOUD] AggTrades loaded: {len(raw)} rows. Generating Dollar Bars...")

    # Generate Dollar Bars
    bars = []
    current_sum = 0.0
    b_open, b_high, b_low, b_vol, b_ts = None, -float('inf'), float('inf'), 0.0, None

    for _, row in raw.iterrows():
        if b_open is None:
            b_open = row['price']
            b_ts = row['timestamp']
        b_high = max(b_high, row['price'])
        b_low = min(b_low, row['price'])
        b_vol += row['quantity']
        current_sum += row['dollar_value']

        if current_sum >= threshold:
            bars.append({
                'timestamp': b_ts, 'open': b_open, 'high': b_high,
                'low': b_low, 'close': row['price'], 'volume': b_vol,
                'dollar_volume': current_sum
            })
            current_sum = 0.0
            b_open, b_high, b_low, b_vol = None, -float('inf'), float('inf'), 0.0

    result_df = pd.DataFrame(bars)
    print(f"[CLOUD] Dollar Bars done: {len(result_df)} bars")
    csv_string = result_df.to_csv(index=False)
    preview = result_df.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(result_df), "preview": preview, "csv_data": csv_string}


@app.local_entrypoint()
def main(symbol="BTCUSDT", timeframe="15m", start="2024-01-01", end="2024-02-01"):
    result = fetch_klines_cloud.remote(symbol, timeframe, start, end)
    if result.get("success"):
        filename = f"{symbol}_{timeframe}_{start}_{end}.csv"
        with open(filename, "w") as f:
            f.write(result["csv_data"])
        print(f"File saved: {filename} ({result['row_count']} rows)")
    else:
        print(f"Error: {result.get('message')}")
