import modal
import pandas as pd
import requests
import io
import zipfile
import os
import gc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Modal app
app = modal.App("binance-data-dashboard")
image = modal.Image.debian_slim().pip_install("pandas", "requests", "python-dateutil", "ccxt", "huggingface_hub")

# Persistent volume for resuming tasks
app_volume = modal.Volume.from_name("binance-data-volume", create_if_missing=True)

def upload_to_hf(file_path, filename, repo_id, token):
    """Uploads a file directly to Hugging Face repository from disk."""
    from huggingface_hub import HfApi
    
    try:
        api = HfApi(token=token)
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except:
            pass
            
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=filename,
            repo_id=repo_id,
            repo_type="dataset"
        )
        print(f"  [HF] Successfully uploaded {filename} to {repo_id}")
        return True, f"https://huggingface.co/datasets/{repo_id}/blob/main/{filename}"
    except Exception as e:
        print(f"  [HF] Upload failed: {e}")
        return False, str(e)


def download_vision_zips(base_url, data_type, clean_symbol, start_dt, end_dt, klines_tf=None):
    """
    Universal Binance Vision downloader (Generator).
    Yields monthly/daily DataFrames one by one to save RAM.
    """
    if klines_tf:
        path_segment = f"klines/{clean_symbol}/{klines_tf}"
        file_prefix = f"{clean_symbol}-{klines_tf}"
    else:
        path_segment = f"{data_type}/{clean_symbol}"
        file_prefix = f"{clean_symbol}-{data_type}"

    monthly_done = []
    current_month = start_dt.replace(day=1)
    while current_month <= end_dt.replace(day=1):
        next_month = current_month + relativedelta(months=1)
        if next_month <= datetime.now().replace(day=1):
            m_str = current_month.strftime("%Y-%m")
            # Skip check should be done by the caller (fetch functions)
            url = f"{base_url}/monthly/{path_segment}/{file_prefix}-{m_str}.zip"
            try:
                res = requests.get(url, timeout=30)
                if res.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                        with z.open(z.namelist()[0]) as f:
                            df = pd.read_csv(f, header=None)
                            if not str(df.iloc[0, 0]).isdigit():
                                df = df.iloc[1:].reset_index(drop=True)
                            yield df, current_month, "monthly"
                            monthly_done.append(current_month)
                            print(f"  [OK] Month {m_str}: {len(df)} rows yielded")
                            del df
                            gc.collect()
                else:
                    print(f"  [SKIP] Month {m_str}: HTTP {res.status_code}")
            except Exception as e:
                print(f"  [ERR] Month {m_str}: {e}")
        current_month = next_month

    temp_date = start_dt
    while temp_date <= end_dt:
        is_covered = any(m_dt <= temp_date < (m_dt + relativedelta(months=1)) for m_dt in monthly_done)
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
                            yield df, temp_date, "daily"
                            print(f"  [OK] Day {d_str}: {len(df)} rows yielded")
                            del df
                            gc.collect()
            except:
                pass
        temp_date += timedelta(days=1)


# ============================================================
# CLOUD FUNCTIONS
# ============================================================

@app.function(image=image, timeout=86400, cpu=1.0, memory=51200, volumes={"/data": app_volume}, retries=0)
def fetch_klines_cloud(symbol: str, timeframe: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download Klines with Persistent Resume logic."""
    print(f"[CLOUD] Klines (Resume): {symbol} {timeframe} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    task_id = f"klines_{clean_symbol}_{timeframe}_{start_date}_{end_date}"
    output_path = f"/data/{task_id}.csv"
    progress_path = f"/data/{task_id}.progress"
    
    last_processed = None
    if os.path.exists(progress_path):
        with open(progress_path, "r") as pf:
            last_processed = datetime.strptime(pf.read().strip(), "%Y-%m-%d")
        print(f"  [RESUME] Found progress. Resuming after {last_processed.date()}")

    first = not os.path.exists(output_path)
    row_count = 0
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    for chunk, current_dt, period_type in download_vision_zips(base_url, "klines", clean_symbol, start_dt, end_dt, klines_tf=timeframe):
        # Resume Check
        if last_processed and current_dt <= last_processed:
            print(f"  [SKIP] {current_dt.date()} (already processed)")
            continue

        chunk = chunk.iloc[:, :6]
        chunk.columns = cols
        chunk['timestamp'] = pd.to_numeric(chunk['timestamp'])
        
        chunk.to_csv(output_path, mode='a' if not first else 'w', index=False, header=first)
        row_count += len(chunk)
        first = False
        
        # Checkpoint
        with open(progress_path, "w") as pf:
            pf.write(current_dt.strftime("%Y-%m-%d"))
        app_volume.commit()
        
        del chunk
        gc.collect()

    if not os.path.exists(output_path): return {"success": False, "message": "Duomenu nerasta."}

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{timeframe}_{start_date}_{end_date}_klines.csv"
        success, url_or_err = upload_to_hf(output_path, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err
    
    return {"success": True, "hf_url": hf_url, "checkpointed": True}


@app.function(image=image, timeout=86400, cpu=1.0, memory=51200, volumes={"/data": app_volume}, retries=0)
def fetch_aggtrades_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download AggTrades with Persistent Resume logic."""
    print(f"[CLOUD] AggTrades (Resume): {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    task_id = f"agg_{clean_symbol}_{start_date}_{end_date}"
    output_path = f"/data/{task_id}.csv"
    progress_path = f"/data/{task_id}.progress"
    
    last_processed = None
    if os.path.exists(progress_path):
        with open(progress_path, "r") as pf:
            last_processed = datetime.strptime(pf.read().strip(), "%Y-%m-%d")
        print(f"  [RESUME] Found progress. Resuming after {last_processed.date()}")

    first = not os.path.exists(output_path)
    row_count = 0
    cols = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']

    for chunk, current_dt, period_type in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        if last_processed and current_dt <= last_processed:
            continue

        chunk.columns = cols
        chunk.to_csv(output_path, mode='a' if not first else 'w', index=False, header=first)
        row_count += len(chunk)
        first = False
        
        with open(progress_path, "w") as pf:
            pf.write(current_dt.strftime("%Y-%m-%d"))
        app_volume.commit()
        
        del chunk
        gc.collect()

    if not os.path.exists(output_path): return {"success": False, "message": "Duomenu nerasta."}

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_aggTrades.csv"
        success, url_or_err = upload_to_hf(output_path, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err
    
    return {"success": True, "hf_url": hf_url, "checkpointed": True}


@app.function(image=image, timeout=86400, cpu=1.0, memory=51200, volumes={"/data": app_volume}, retries=0)
def fetch_liquidations_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
    """Download Liquidations with Persistent Resume logic."""
    print(f"[CLOUD] Liquidations (Resume): {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    task_id = f"liq_{clean_symbol}_{start_date}_{end_date}"
    output_path = f"/data/{task_id}.csv"
    progress_path = f"/data/{task_id}.progress"
    
    last_processed = None
    if os.path.exists(progress_path):
        with open(progress_path, "r") as pf:
            last_processed = datetime.strptime(pf.read().strip(), "%Y-%m-%d")
        print(f"  [RESUME] Found progress. Resuming after {last_processed.date()}")

    first = not os.path.exists(output_path)
    row_count = 0
    cols = ['symbol', 'side', 'order_type', 'time_in_force', 'original_quantity', 'price',
            'average_price', 'order_status', 'last_fill_quantity', 'accumulated_fill_quantity', 'timestamp']

    for chunk, current_dt, period_type in download_vision_zips(base_url, "liquidationOrders", clean_symbol, start_dt, end_dt):
        if last_processed and current_dt <= last_processed:
            continue

        chunk.columns = cols
        chunk.to_csv(output_path, mode='a' if not first else 'w', index=False, header=first)
        row_count += len(chunk)
        first = False
        
        with open(progress_path, "w") as pf:
            pf.write(current_dt.strftime("%Y-%m-%d"))
        app_volume.commit()
        
        del chunk
        gc.collect()

    if not os.path.exists(output_path): return {"success": False, "message": "Duomenu nerasta."}

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_liquidations.csv"
        success, url_or_err = upload_to_hf(output_path, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    return {"success": True, "hf_url": hf_url, "checkpointed": True}


@app.function(image=image, timeout=86400, cpu=2.0, memory=51200, volumes={"/data": app_volume}, retries=0)
def fetch_dollar_bars_cloud(symbol: str, start_date: str, end_date: str, threshold: float = 1_000_000, hf_repo: str = None, hf_token: str = None):
    """Vectorized Dollar Bar generation with Persistent Resume logic."""
    print(f"[CLOUD] Dollar Bars (Resume): {symbol} | {start_date} -> {end_date} | Threshold: {threshold}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    task_id = f"dbars_{clean_symbol}_{start_date}_{end_date}_{int(threshold)}"
    output_path = f"/data/{task_id}.csv"
    progress_path = f"/data/{task_id}.progress"
    state_path = f"/data/{task_id}.state"
    
    last_processed = None
    # We will store leftover rows in a DataFrame
    leftovers = pd.DataFrame()
    
    if os.path.exists(progress_path):
        # Force reset if old format (6 columns) detected in output file
        if os.path.exists(output_path):
            try:
                # Check column count of the first line
                with open(output_path, 'r') as f:
                    first_line = f.readline().strip().split(',')
                
                # If it has 6 columns (old) or is missing headers we expect, we reset
                if len(first_line) != 7:
                    print(f"  [RESET] Old format detected ({len(first_line)} columns). Wiping stale data...")
                    os.remove(output_path)
                    if os.path.exists(progress_path): os.remove(progress_path)
                    if os.path.exists(state_path): os.remove(state_path)
                else:
                    with open(progress_path, "r") as pf:
                        last_processed = datetime.strptime(pf.read().strip(), "%Y-%m-%d")
                    if os.path.exists(state_path):
                        leftovers = pd.read_csv(state_path)
                    print(f"  [RESUME] Resuming Dollar Bars after {last_processed.date()}")
            except Exception as e:
                print(f"  [RESET] Error checking format: {e}. Starting fresh.")
                if os.path.exists(output_path): os.remove(output_path)
        else:
            os.remove(progress_path)
            if os.path.exists(state_path):
                os.remove(state_path)
            print("  [RESET] Progress file found but output missing. Starting fresh.")

    first = not os.path.exists(output_path)
    
    for chunk, current_dt, _ in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        if last_processed and current_dt <= last_processed: continue
        
        chunk.columns = ['id', 'price', 'quantity', 'f', 'l', 'timestamp', 's']
        chunk['price'] = pd.to_numeric(chunk['price'], errors='coerce')
        chunk['quantity'] = pd.to_numeric(chunk['quantity'], errors='coerce')
        chunk = chunk.dropna(subset=['price', 'quantity'])
        
        chunk = chunk[['timestamp', 'price', 'quantity']]
        
        if not leftovers.empty:
            chunk = pd.concat([leftovers, chunk], ignore_index=True)
            leftovers = pd.DataFrame()
            
        chunk['dollar_value'] = chunk['price'] * chunk['quantity']
        chunk['cum_dollar'] = chunk['dollar_value'].cumsum()
        
        # Group by integer thresholds
        chunk['bar_id'] = chunk['cum_dollar'] // threshold
        
        max_bar_id = chunk['bar_id'].max()
        # The last group might not complete the threshold. Keep it as leftovers.
        is_last_group = (chunk['bar_id'] == max_bar_id)
        
        completed_bars_df = chunk[~is_last_group]
        leftovers_df = chunk[is_last_group]
        
        if not completed_bars_df.empty:
            grouped = completed_bars_df.groupby('bar_id')
            
            bars = grouped.agg(
                timestamp=('timestamp', 'first'),
                open=('price', 'first'),
                high=('price', 'max'),
                low=('price', 'min'),
                close=('price', 'last'),
                volume=('quantity', 'sum'),
                dollar_volume=('dollar_value', 'sum')
            ).reset_index(drop=True)
            
            # Convert timestamp to human readable datetime
            bars['timestamp'] = pd.to_datetime(bars['timestamp'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]
            
            # Select specific final columns to guarantee correct output format without headers
            final_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume']
            bars = bars[final_cols]
            
            bars.to_csv(output_path, mode='a' if not first else 'w', index=False, header=first)
            first = False
            
        leftovers = leftovers_df[['timestamp', 'price', 'quantity', 'dollar_value']].copy()
        
        # Checkpoint
        with open(progress_path, "w") as pf:
            pf.write(current_dt.strftime("%Y-%m-%d"))
        
        leftovers.to_csv(state_path, index=False)
        
        app_volume.commit()
        del chunk, completed_bars_df, leftovers_df
        if 'bars' in locals():
            del bars
        gc.collect()

    if not os.path.exists(output_path): return {"success": False, "message": "No bars generated."}

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_dollarBars_{int(threshold)}.csv"
        success, url_or_err = upload_to_hf(output_path, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    return {"success": True, "hf_url": hf_url, "checkpointed": True}


@app.function(image=image, timeout=86400, cpu=2.0, memory=51200, volumes={"/data": app_volume}, retries=0)
def fetch_vpin_cloud(symbol: str, start_date: str, end_date: str, buckets_per_day: int = 50, hf_repo: str = None, hf_token: str = None):
    """Vectorized VPIN toxicity calculation with Persistent Resume logic."""
    print(f"[CLOUD] VPIN (Resume): {symbol} | {start_date} -> {end_date}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    task_id = f"vpin_{clean_symbol}_{start_date}_{end_date}_{buckets_per_day}"
    output_path = f"/data/{task_id}.csv"
    progress_path = f"/data/{task_id}.progress"
    state_path = f"/data/{task_id}.state"
    
    bucket_size = None
    last_processed = None
    v_ts, v_open, v_high, v_low, v_vol, v_buy, v_sell = None, None, -1.0, float('inf'), 0.0, 0.0, 0.0

    if os.path.exists(progress_path):
        with open(progress_path, "r") as pf:
            last_processed = datetime.strptime(pf.read().strip(), "%Y-%m-%d")
        if os.path.exists(state_path):
            import json
            with open(state_path, "r") as sf:
                state = json.load(sf)
                bucket_size = state.get('bs')
                v_ts, v_open, v_high, v_low = state.get('ts'), state.get('o'), state.get('h'), state.get('l')
                v_vol, v_buy, v_sell = state.get('v', 0.0), state.get('b', 0.0), state.get('s', 0.0)
        print(f"  [RESUME] Resuming VPIN after {last_processed.date()}")

    # 1) Bucket size discovery (if not resumed)
    if bucket_size is None:
        print("  [VPIN] Calculating total volume for bucket size...")
        total_vol = 0.0
        for chunk, _, _ in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
            total_vol += pd.to_numeric(chunk.iloc[:, 2]).sum()
            del chunk
            gc.collect()
        if total_vol == 0: return {"success": False, "message": "No data found."}
        bucket_size = total_vol / (max(1, (end_dt - start_dt).days + 1) * buckets_per_day)
        print(f"  [VPIN] New Bucket Size: {bucket_size:.2f} units")

    # 2) VPIN calculation
    first = not os.path.exists(output_path)
    for chunk, current_dt, _ in download_vision_zips(base_url, "aggTrades", clean_symbol, start_dt, end_dt):
        if last_processed and current_dt <= last_processed: continue
        
        chunk.columns = ['id', 'price', 'qty', 'f', 'l', 'ts', 'side']
        chunk['price'] = pd.to_numeric(chunk['price'])
        chunk['qty'] = pd.to_numeric(chunk['qty'])
        chunk['side'] = chunk['side'].astype(str).str.strip().str.lower() == 'true'
        
        buckets = []
        for _, row in chunk.iterrows():
            if v_open is None:
                v_open, v_ts = row['price'], row['ts']
            
            v_high = max(v_high, row['price'])
            v_low = min(v_low, row['price'])
            v_vol += row['qty']
            if row['side']: v_sell += row['qty']
            else: v_buy += row['qty']

            if v_vol >= bucket_size:
                buckets.append([v_ts, v_open, v_high, v_low, row['price'], v_vol, v_buy, v_sell, abs(v_buy - v_sell)])
                v_ts, v_open, v_high, v_low, v_vol, v_buy, v_sell = None, None, -1.0, float('inf'), 0.0, 0.0, 0.0

        if buckets:
            df = pd.DataFrame(buckets, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'buy_vol', 'sell_vol', 'imb'])
            df.to_csv(output_path, mode='a' if not first else 'w', index=False, header=first)
            first = False

        # Checkpoint
        with open(progress_path, "w") as pf:
            pf.write(current_dt.strftime("%Y-%m-%d"))
        import json
        with open(state_path, "w") as sf:
            json.dump({'bs': bucket_size, 'ts': v_ts, 'o': v_open, 'h': v_high, 'l': v_low, 'v': v_vol, 'b': v_buy, 's': v_sell}, sf)
        
        app_volume.commit()
        del chunk
        gc.collect()

    if not os.path.exists(output_path): return {"success": False, "message": "No data processed."}

    # Final VPIN calculation (optional: this part might require reading the full output_path 
    # to apply the rolling window correctly, but that's memory intensive. 
    # For now, we'll keep the raw buckets on Volume and skip complex rolling in cloud if RAM is tight).
    
    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_VPIN_buckets.csv"
        success, url_or_err = upload_to_hf(output_path, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    return {"success": True, "hf_url": hf_url, "checkpointed": True}



@app.local_entrypoint()
def main(symbol="BTCUSDT", start="2021-01-01", end="2021-02-01"):
    res = fetch_vpin_cloud.remote(symbol, start, end)
    print(res)
