import modal
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Modal app
app = modal.App("binance-data-dashboard")
image = modal.Image.debian_slim().pip_install("pandas", "requests", "python-dateutil", "ccxt", "huggingface_hub")

def upload_to_hf(csv_content, filename, repo_id, token):
    """Uploads CSV content directly to Hugging Face repository."""
    from huggingface_hub import HfApi
    import io
    
    try:
        api = HfApi(token=token)
        # Create repo if not exists (as dataset)
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except:
            pass
            
        api.upload_file(
            path_or_fileobj=io.BytesIO(csv_content.encode('utf-8')),
            path_in_repo=filename,
            repo_id=repo_id,
            repo_type="dataset"
        )
        print(f"  [HF] Successfully uploaded to {repo_id}/{filename}")
        return True, f"https://huggingface.co/datasets/{repo_id}/blob/main/{filename}"
    except Exception as e:
        print(f"  [HF] Upload failed: {e}")
        return False, str(e)


def download_vision_zips(base_url, data_type, clean_symbol, start_dt, end_dt, klines_tf=None):
    """
    Universal Binance Vision downloader (Generator).
    Yields monthly/daily DataFrames one by one to save RAM.
    """
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
                            yield df
                            monthly_done.append(current_month)
                            print(f"  [OK] Month {m_str}: {len(df)} rows yielded")
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
                            yield df
                            print(f"  [OK] Day {d_str}: {len(df)} rows yielded")
            except:
                pass
        temp_date += timedelta(days=1)


# ============================================================
# CLOUD FUNCTIONS
# ============================================================

@app.function(image=image, timeout=86400, cpu=1.0, memory=51200)
def fetch_klines_cloud(symbol: str, timeframe: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download Klines (OHLCV) in the cloud."""
    print(f"[CLOUD] Klines: {symbol} {timeframe} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Use generator to save RAM
    all_chunks = []
    for chunk in download_vision_zips(base_url, "klines", clean_symbol, start_dt, end_dt, klines_tf=timeframe):
        # Basic filtering to reduce size immediately
        chunk = chunk.iloc[:, :6]
        chunk.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        chunk['timestamp'] = pd.to_datetime(pd.to_numeric(chunk['timestamp']), unit='ms')
        chunk = chunk[(chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                      (chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
        all_chunks.append(chunk)

    if not all_chunks:
        return {"success": False, "message": "Duomenu nerasta."}

    raw = pd.concat(all_chunks, ignore_index=True)
    raw = raw.sort_values('timestamp').reset_index(drop=True)

    print(f"[CLOUD] Klines done: {len(raw)} rows")
    csv_string = raw.to_csv(index=False)
    
    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{timeframe}_{start_date}_{end_date}_klines.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=996400, cpu=1.0, memory=31200)
def fetch_aggtrades_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download AggTrades in the cloud."""
    print(f"[CLOUD] AggTrades: {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Use generator to save RAM
    all_chunks = []
    for chunk in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        chunk.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
        chunk['timestamp'] = pd.to_datetime(pd.to_numeric(chunk['timestamp']), unit='ms')
        chunk = chunk[(chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                      (chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
        all_chunks.append(chunk)

    if not all_chunks:
        return {"success": False, "message": "Duomenu nerasta."}

    raw = pd.concat(all_chunks, ignore_index=True)
    raw = raw.sort_values('timestamp').reset_index(drop=True)

    print(f"[CLOUD] AggTrades done: {len(raw)} rows")
    csv_string = raw.to_csv(index=False)

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_aggTrades.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400, cpu=1.0, memory=51200)
def fetch_liquidations_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download Liquidations in the cloud."""
    print(f"[CLOUD] Liquidations: {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Use generator to save RAM
    all_chunks = []
    for chunk in download_vision_zips(base_url, "liquidationOrders", clean_symbol, start_dt, end_dt):
        chunk.columns = ['symbol', 'side', 'order_type', 'time_in_force', 'original_quantity', 'price',
                       'average_price', 'order_status', 'last_fill_quantity', 'accumulated_fill_quantity', 'timestamp']
        chunk['timestamp'] = pd.to_datetime(pd.to_numeric(chunk['timestamp']), unit='ms')
        chunk = chunk[(chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                      (chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
        all_chunks.append(chunk)

    if not all_chunks:
        return {"success": False, "message": "Duomenu nerasta."}

    raw = pd.concat(all_chunks, ignore_index=True)
    raw = raw.sort_values('timestamp').reset_index(drop=True)

    print(f"[CLOUD] Liquidations done: {len(raw)} rows")
    csv_string = raw.to_csv(index=False)

    import gc
    del all_chunks
    gc.collect()

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_liquidations.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400, cpu=1.0, memory=51200)
def fetch_dollar_bars_cloud(symbol: str, start_date: str, end_date: str, threshold: float = 1_000_000, hf_repo: str = None, hf_token: str = None):
    """Download AggTrades and generate Dollar Bars in the cloud."""
    print(f"[CLOUD] Dollar Bars: {symbol} | {start_date} -> {end_date} | Threshold: {threshold}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Generate Dollar Bars using generator for RAM efficiency
    bars = []
    current_sum = 0.0
    b_open, b_high, b_low, b_vol, b_ts = None, -float('inf'), float('inf'), 0.0, None

    import gc
    for chunk in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        chunk.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
        chunk['timestamp'] = pd.to_datetime(pd.to_numeric(chunk['timestamp']), unit='ms')
        chunk = chunk[(chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                      (chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
        if chunk.empty: continue
        
        chunk = chunk.sort_values('timestamp')
        chunk['price'] = pd.to_numeric(chunk['price'])
        chunk['quantity'] = pd.to_numeric(chunk['quantity'])
        chunk['dollar_value'] = chunk['price'] * chunk['quantity']

        for _, row in chunk.iterrows():
            if b_open is None:
                b_open = row['price']
                b_ts = row['timestamp']
            
            b_high = max(b_high, row['price'])
            b_low = min(b_low, row['price'])
            b_vol += row['quantity']
            current_sum += row['dollar_value']

            if current_sum >= threshold:
                bars.append({
                    'timestamp': b_ts,
                    'open': b_open,
                    'high': b_high,
                    'low': b_low,
                    'close': row['price'],
                    'volume': b_vol
                })
                # Reset for next bar
                current_sum = 0.0
                b_open, b_high, b_low, b_vol, b_ts = None, -float('inf'), float('inf'), 0.0, None

        del chunk
        gc.collect()

    if not bars:
        return {"success": False, "message": "Barai nesugeneruoti (per mazas volumenas)."}

    raw = pd.DataFrame(bars)
    print(f"[CLOUD] Dollar Bars done: {len(raw)} bars")
    csv_string = raw.to_csv(index=False)
    
    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_dollarBars_{int(threshold)}.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400, cpu=1.0, memory=51200)
def fetch_vpin_cloud(symbol: str, start_date: str, end_date: str, buckets_per_day: int = 50, hf_repo: str = None, hf_token: str = None):
    """
    Download AggTrades and calculate VPIN (Volume-Synchronized Probability of Informed Trading).
    Reference: AFML Chapter 3.
    """
    print(f"[CLOUD] VPIN: {symbol} | {start_date} -> {end_date} | Buckets/Day: {buckets_per_day}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Calculate VPIN using streaming generator for RAM efficiency
    # 1) First pass: Calculate total volume to determine bucket size
    print("[CLOUD] Calculating total volume for bucket size...")
    total_vol = 0
    total_days = (end_dt - start_dt).days + 1
    
    for chunk in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        total_vol += pd.to_numeric(chunk.iloc[:, 2]).sum()
        del chunk

    if total_vol == 0:
        return {"success": False, "message": "AggTrades nerasta, VPIN paskaiciuoti nepavyko."}

    bucket_size = total_vol / (max(1, total_days) * buckets_per_day)
    print(f"[CLOUD] Bucket size: {bucket_size:.2f} units. Starting VPIN calculation...")

    vpin_data = []
    curr_b_vol, curr_b_buy, curr_b_sell = 0, 0, 0
    curr_b_open, curr_b_high, curr_b_low, curr_b_ts = None, -float('inf'), float('inf'), None

    import gc
    for chunk in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        chunk.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
        chunk['timestamp'] = pd.to_datetime(pd.to_numeric(chunk['timestamp']), unit='ms')
        chunk = chunk[(chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                      (chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
        if chunk.empty: continue
        
        chunk = chunk.sort_values('timestamp')
        chunk['price'] = pd.to_numeric(chunk['price'])
        chunk['quantity'] = pd.to_numeric(chunk['quantity'])
        
        # Proper is_buyer_maker conversion
        chunk['is_buyer_maker'] = chunk['is_buyer_maker'].astype(str).str.strip().str.lower() == 'true'
        chunk['buy_vol'] = chunk['quantity'].where(~chunk['is_buyer_maker'], 0.0)
        chunk['sell_vol'] = chunk['quantity'].where(chunk['is_buyer_maker'], 0.0)

        for _, row in chunk.iterrows():
            if curr_b_open is None:
                curr_b_open = row['price']
                curr_b_ts = row['timestamp']
            
            curr_b_high = max(curr_b_high, row['price'])
            curr_b_low = min(curr_b_low, row['price'])
            curr_b_vol += row['quantity']
            curr_b_buy += row['buy_vol']
            curr_b_sell += row['sell_vol']

            if curr_b_vol >= bucket_size:
                vpin_data.append({
                    'timestamp': curr_b_ts, 'open': curr_b_open, 'high': curr_b_high,
                    'low': curr_b_low, 'close': row['price'], 'volume': curr_b_vol,
                    'buy_vol': curr_b_buy, 'sell_vol': curr_b_sell, 
                    'imbalance': abs(curr_b_buy - curr_b_sell)
                })
                curr_b_vol, curr_b_buy, curr_b_sell = 0, 0, 0
                curr_b_open, curr_b_high, curr_b_low = None, -float('inf'), float('inf')
        
        del chunk
        gc.collect()

    df_vpin = pd.DataFrame(vpin_data)
    
    # VPIN formula: EMA of (|Buy - Sell|) / BucketSize
    # We'll use a 50-bucket window for the VPIN average toxicity
    df_vpin['vpin'] = df_vpin['imbalance'].rolling(window=buckets_per_day).mean() / bucket_size
    
    print(f"[CLOUD] VPIN done: {len(df_vpin)} buckets.")
    csv_string = df_vpin.to_csv(index=False)

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_VPIN.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = df_vpin.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(df_vpin), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.local_entrypoint()
def main(symbol="BTCUSDT", timeframe="15m", start="2024-01-01", end="2024-02-01"):
    # result = fetch_klines_cloud.remote(symbol, timeframe, start, end)
    result = fetch_vpin_cloud.remote(symbol, start, end)
    if result.get("success"):
        filename = f"{symbol}_vpin_{start}_{end}.csv"
        with open(filename, "w") as f:
            f.write(result["csv_data"])
        print(f"File saved: {filename} ({result['row_count']} rows)")
    else:
        print(f"Error: {result.get('message')}")
