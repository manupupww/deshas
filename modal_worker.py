import modal
import pandas as pd
import requests
import io
import zipfile
import gc
import os
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Modal app
app = modal.App("binance-data-dashboard")
image = modal.Image.debian_slim().pip_install("pandas", "requests", "python-dateutil", "ccxt", "huggingface_hub", "numpy")

def upload_to_hf(content_or_path, filename, repo_id, token, is_file=False):
    """Uploads content or a file directly to Hugging Face repository."""
    from huggingface_hub import HfApi
    import io
    
    try:
        api = HfApi(token=token)
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except:
            pass
            
        if is_file:
            api.upload_file(
                path_or_fileobj=content_or_path,
                path_in_repo=filename,
                repo_id=repo_id,
                repo_type="dataset"
            )
        else:
            api.upload_file(
                path_or_fileobj=io.BytesIO(content_or_path.encode('utf-8')),
                path_in_repo=filename,
                repo_id=repo_id,
                repo_type="dataset"
            )
        print(f"  [HF] Successfully uploaded to {repo_id}/{filename}")
        return True, f"https://huggingface.co/datasets/{repo_id}/blob/main/{filename}"
    except Exception as e:
        print(f"  [HF] Upload failed: {e}")
        return False, str(e)


def yield_vision_zips(base_url, data_type, clean_symbol, start_dt, end_dt, klines_tf=None, usecols=None):
    """
    Generator that yields monthly DataFrames one by one.
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
                    if len(res.content) < 100:
                        print(f"  [SKIP] {url}: File too small ({len(res.content)} bytes)")
                        continue
                    try:
                        with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                            namelist = z.namelist()
                            if not namelist:
                                print(f"  [SKIP] {url}: No files inside ZIP")
                                continue
                            with z.open(namelist[0]) as f:
                                df = pd.read_csv(f, header=None, usecols=usecols)
                                if not df.empty and not str(df.iloc[0, 0]).isdigit():
                                    df = df.iloc[1:].reset_index(drop=True)
                                yield df, m_str
                                monthly_done.append(current_month)
                                print(f"  [OK] Month {m_str}: {len(df)} rows")
                    except zipfile.BadZipFile:
                        print(f"  [ERR] {url}: Invalid ZIP file content")
                else:
                    print(f"  [SKIP] Month {m_str}: HTTP {res.status_code}")
            except Exception as e:
                print(f"  [ERR] Month {m_str}: {e}")
        current_month = next_month

    # 2) Daily archives
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
                            df = pd.read_csv(f, header=None, usecols=usecols)
                            if not str(df.iloc[0, 0]).isdigit():
                                df = df.iloc[1:].reset_index(drop=True)
                            yield df, d_str
            except:
                pass
        temp_date += timedelta(days=1)


def download_vision_zips(base_url, data_type, clean_symbol, start_dt, end_dt, klines_tf=None):
    """Backwards compatibility for simple downloads."""
    all_dfs = []
    for df, label in yield_vision_zips(base_url, data_type, clean_symbol, start_dt, end_dt, klines_tf):
        all_dfs.append(df)
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


# ============================================================
# CLOUD FUNCTIONS
# ============================================================

@app.function(image=image, timeout=7200, cpu=1.0, memory=51200)
def fetch_klines_cloud(symbol: str, timeframe: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download Klines (OHLCV) in the cloud with chunked processing."""
    print(f"[CLOUD] Klines (Chunked): {symbol} {timeframe} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    all_csv_chunks = []
    total_rows = 0
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    for df_chunk, label in yield_vision_zips(base_url, "klines", clean_symbol, start_dt, end_dt, klines_tf=timeframe, usecols=[0,1,2,3,4,5]):
        df_chunk.columns = cols
        df_chunk['timestamp'] = pd.to_datetime(pd.to_numeric(df_chunk['timestamp']), unit='ms')
        df_chunk = df_chunk[(df_chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                          (df_chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
        
        if not df_chunk.empty:
            all_csv_chunks.append(df_chunk.to_csv(index=False, header=(total_rows == 0)))
            total_rows += len(df_chunk)
        del df_chunk
        gc.collect()

    if total_rows == 0:
        return {"success": False, "message": "Klines nerasta."}

    csv_string = "".join(all_csv_chunks)
    print(f"[CLOUD] Klines done: {total_rows} rows")

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{timeframe}_{start_date}_{end_date}_klines.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    last_df = pd.read_csv(io.StringIO(all_csv_chunks[-1]))
    preview = last_df.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": total_rows, "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=7200, cpu=1.0, memory=51200)
def fetch_aggtrades_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download AggTrades in the cloud with strict memory management."""
    print(f"[CLOUD] AggTrades (Disk-Backed): {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    temp_path = f"/tmp/{clean_symbol}_aggtrades.csv"
    total_rows = 0
    cols = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
    
    with open(temp_path, "w") as f:
        for df_chunk, label in yield_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
            df_chunk.columns = cols
            df_chunk['timestamp'] = pd.to_datetime(pd.to_numeric(df_chunk['timestamp']), unit='ms')
            df_chunk = df_chunk[(df_chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                              (df_chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
            
            if not df_chunk.empty:
                df_chunk.to_csv(f, index=False, header=(total_rows == 0))
                total_rows += len(df_chunk)
            
            # Strict Cleanup
            del df_chunk
            gc.collect()

    if total_rows == 0:
        if os.path.exists(temp_path): os.remove(temp_path)
        return {"success": False, "message": "AggTrades nerasta."}

    print(f"[CLOUD] AggTrades done: {total_rows} rows. Saved to disk.")

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_aggTrades.csv"
        success, url_or_err = upload_to_hf(temp_path, filename, hf_repo, hf_token, is_file=True)
        if success: hf_url = url_or_err

    # Preview
    preview_df = pd.read_csv(temp_path).tail(100)
    preview = preview_df.to_dict(orient="records")
    
    # Return limited data as string for immediate use, or signal to use HF
    with open(temp_path, "r") as f:
        # We only return the CSV string if it's reasonably small, otherwise use HF
        # But per user req "csv_data" is usually expected.
        # However, for huge files (>50MB), returning as string might crash the client.
        csv_data = f.read() if os.path.getsize(temp_path) < 50_000_000 else "FILE_TOO_LARGE_USE_HF"

    if os.path.exists(temp_path): os.remove(temp_path)
    return {"success": True, "row_count": total_rows, "preview": preview, "csv_data": csv_data, "hf_url": hf_url}


@app.function(image=image, timeout=7200, cpu=1.0, memory=51200)
def fetch_liquidations_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download Liquidations in the cloud with strict memory management."""
    print(f"[CLOUD] Liquidations (Disk-Backed): {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    temp_path = f"/tmp/{clean_symbol}_liquidations.csv"
    total_rows = 0
    cols = ['symbol', 'side', 'order_type', 'time_in_force', 'original_quantity', 'price',
            'average_price', 'order_status', 'last_fill_quantity', 'accumulated_fill_quantity', 'timestamp']

    with open(temp_path, "w") as f:
        for df_chunk, label in yield_vision_zips(base_url, "liquidationOrders", clean_symbol, start_dt, end_dt):
            df_chunk.columns = cols
            df_chunk['timestamp'] = pd.to_datetime(pd.to_numeric(df_chunk['timestamp']), unit='ms')
            df_chunk = df_chunk[(df_chunk['timestamp'] >= pd.to_datetime(start_dt)) &
                              (df_chunk['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
            
            if not df_chunk.empty:
                df_chunk.to_csv(f, index=False, header=(total_rows == 0))
                total_rows += len(df_chunk)
            
            del df_chunk
            gc.collect()

    if total_rows == 0:
        if os.path.exists(temp_path): os.remove(temp_path)
        return {"success": False, "message": "Liquidations nerasta."}

    print(f"[CLOUD] Liquidations done: {total_rows} rows. Saved to disk.")

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_liquidations.csv"
        success, url_or_err = upload_to_hf(temp_path, filename, hf_repo, hf_token, is_file=True)
        if success: hf_url = url_or_err

    preview_df = pd.read_csv(temp_path).tail(100)
    preview = preview_df.to_dict(orient="records")
    
    with open(temp_path, "r") as f:
        csv_data = f.read() if os.path.getsize(temp_path) < 50_000_000 else "FILE_TOO_LARGE_USE_HF"

    if os.path.exists(temp_path): os.remove(temp_path)
    return {"success": True, "row_count": total_rows, "preview": preview, "csv_data": csv_data, "hf_url": hf_url}


@app.function(image=image, timeout=7200, cpu=1.0, memory=51200)
def fetch_dollar_bars_cloud(symbol: str, start_date: str, end_date: str, threshold: float = 1_000_000, hf_repo: str = None, hf_token: str = None):
    """Download AggTrades and generate Dollar Bars with chunked processing."""
    print(f"[CLOUD] Dollar Bars (Chunked): {symbol} | {start_date} -> {end_date} | Threshold: {threshold}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    bars = []
    # State tracking
    s = {
        'current_sum': 0.0, 'b_open': None, 'b_high': -float('inf'),
        'b_low': float('inf'), 'b_vol': 0.0, 'b_ts': None
    }

    for df_chunk, label in yield_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        print(f"  [DBARS] Processing {label}...")
        df_chunk.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
        df_chunk['timestamp'] = pd.to_datetime(pd.to_numeric(df_chunk['timestamp']), unit='ms')
        df_chunk['price'] = pd.to_numeric(df_chunk['price'])
        df_chunk['quantity'] = pd.to_numeric(df_chunk['quantity'])
        df_chunk['dollar_value'] = df_chunk['price'] * df_chunk['quantity']

        for _, row in df_chunk.iterrows():
            if s['b_open'] is None:
                s['b_open'] = row['price']
                s['b_ts'] = row['timestamp']
            s['b_high'] = max(s['b_high'], row['price'])
            s['b_low'] = min(s['b_low'], row['price'])
            s['b_vol'] += row['quantity']
            s['current_sum'] += row['dollar_value']

            if s['current_sum'] >= threshold:
                bars.append({
                    'timestamp': s['b_ts'], 'open': s['b_open'], 'high': s['b_high'],
                    'low': s['b_low'], 'close': row['price'], 'volume': s['b_vol'],
                    'dollar_volume': s['current_sum']
                })
                s['current_sum'] = 0.0
                s['b_open'], s['b_high'], s['b_low'], s['b_vol'] = None, -float('inf'), float('inf'), 0.0
        del df_chunk
        gc.collect()

    if not bars:
        return {"success": False, "message": "Dollar Bars nebuvo sugeneruoti."}

    result_df = pd.DataFrame(bars)
    print(f"[CLOUD] Dollar Bars done: {len(result_df)} bars")
    csv_string = result_df.to_csv(index=False)

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_dollarBars_{int(threshold)}.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = result_df.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(result_df), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=7200, cpu=1.0, memory=51200)
def fetch_vpin_cloud(symbol: str, start_date: str, end_date: str, buckets_per_day: int = 50, hf_repo: str = None, hf_token: str = None):
    """
    Download AggTrades and calculate VPIN.
    Strictly sequential processing: one month at a time.
    """
    print(f"[CLOUD] VPIN (Strict Sequential): {symbol} | {start_date} -> {end_date} | Buckets/Day: {buckets_per_day}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1

    # To avoid the slow AggTrades pre-scan, we use 1m Klines *only* for the volume estimate
    # because bucket_size must be fixed for the indicator to be valid across time.
    print("  [VPIN] Step 1: Sequential Volume Estimation (Fast 1m Klines)...")
    total_vol = 0
    for df_k, label in yield_vision_zips(base_url, "klines", clean_symbol, start_dt, end_dt, timeframe="1m", usecols=[5]):
        total_vol += pd.to_numeric(df_k.iloc[:, 0]).sum()
        del df_k
        gc.collect()

    if total_vol == 0:
        return {"success": False, "message": "Volume data not found."}
    
    bucket_size = total_vol / (total_days * buckets_per_day)
    print(f"  [VPIN] Step 2: Sequential AggTrades processing | Target Bucket: {bucket_size:,.2f}")

    vpin_results = []
    # Persistent state for VPIN calculation across months
    state = {
        'residual_vol': 0.0, 'residual_buy': 0.0, 'residual_sell': 0.0,
        'current_bucket_id': 0,
        'recent_imbalances': [] # Rolling window of imbalances
    }

    for df_chunk, label in yield_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        row_count = len(df_chunk)
        print(f"  [VPIN] Processing {label} ({row_count:,.0f} rows)...")
        
        # 1. Prepare data (Columns: 1=Price, 2=Qty, 5=TS, 6=IsMaker)
        prices = pd.to_numeric(df_chunk.iloc[:, 1]).values
        quants = pd.to_numeric(df_chunk.iloc[:, 2]).values
        times = pd.to_numeric(df_chunk.iloc[:, 5]).values
        is_maker = df_chunk.iloc[:, 6].values
        
        # Buy/Sell classification
        buys = np.where(~is_maker, quants, 0.0)
        sells = np.where(is_maker, quants, 0.0)
        
        # 2. Vectorized Bucket Assignment
        cum_vol = np.cumsum(quants) + state['residual_vol']
        bucket_ids = (cum_vol // bucket_size).astype(int)
        
        # 3. Aggregate by Bucket using Pandas (Vectorized & Fast)
        df_work = pd.DataFrame({
            'bid': bucket_ids, 'p': prices, 'q': quants, 
            't': times, 'b': buys, 's': sells
        })
        
        # Group by Bucket ID
        grouped = df_work.groupby('bid')
        aggs = grouped.agg({
            't': 'first', 'p': ['first', 'max', 'min', 'last'],
            'q': 'sum', 'b': 'sum', 's': 'sum'
        })
        aggs.columns = ['ts', 'open', 'high', 'low', 'close', 'vol', 'buy', 'sell']
        
        # 4. Handle Partial Buckets at month boundaries
        # The last bucket ID in this chunk might be incomplete
        last_bid = bucket_ids[-1]
        is_complete = (grouped.size().index < last_bid).values
        complete_buckets = aggs[is_complete].copy()
        
        # Process complete buckets
        if not complete_buckets.empty:
            for _, row in complete_buckets.iterrows():
                imbalance = abs(row['buy'] - row['sell'])
                state['recent_imbalances'].append(imbalance)
                if len(state['recent_imbalances']) > buckets_per_day:
                    state['recent_imbalances'].pop(0)
                
                vpin_val = None
                if len(state['recent_imbalances']) == buckets_per_day:
                    vpin_val = sum(state['recent_imbalances']) / (buckets_per_day * bucket_size)
                
                vpin_results.append({
                    'timestamp': pd.to_datetime(row['ts'], unit='ms'),
                    'open': row['open'], 'high': row['high'], 'low': row['low'],
                    'close': row['close'], 'volume': row['vol'], 'vpin': vpin_val
                })

        # Save residue for next month
        # Residue is the data from the last (incomplete) bucket ID
        residue_mask = (bucket_ids == last_bid)
        state['residual_vol'] = quants[residue_mask].sum()
        state['residual_buy'] = buys[residue_mask].sum()
        state['residual_sell'] = sells[residue_mask].sum()
        # Note: Open/High/Low for residue would need more state if we wanted perfect OHLC accuracy
        # but for VPIN the volumes are the primary concern.

        # Heartbeat log to show activity
        print(f"    [OK] Finished {label}. Buckets formed: {len(complete_buckets)}. Cumulative Buckets: {len(vpin_results)}")

        # Immediate cleanup
        del df_chunk, df_work, grouped, aggs, complete_buckets
        gc.collect()

    if not vpin_results:
        return {"success": False, "message": "Buckets were not formed."}

    df_final = pd.DataFrame(vpin_results)
    print(f"[CLOUD] VPIN Complete: {len(df_final)} buckets.")
    csv_string = df_final.to_csv(index=False)

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_VPIN.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    return {"success": True, "row_count": len(df_final), "preview": vpin_results[-100:], "csv_data": csv_string, "hf_url": hf_url}


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
