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

@app.function(image=image, timeout=86400, cpu=1.0, memory=61440)
def fetch_klines_cloud(symbol: str, timeframe: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
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
    
    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{timeframe}_{start_date}_{end_date}_klines.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400, cpu=1.0, memory=61440)
def fetch_aggtrades_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
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

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_aggTrades.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400, cpu=1.0, memory=61440)
def fetch_liquidations_cloud(symbol: str, start_date: str, end_date: str, hf_repo: str = None, hf_token: str = None):
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

    hf_url = None
    if hf_repo and hf_token:
        filename = f"{clean_symbol}_{start_date}_{end_date}_liquidations.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = raw.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(raw), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400, cpu=1.0, memory=51200)
def fetch_dollar_bars_cloud(symbol: str, start_date: str, end_date: str, threshold: float = 1_000_000, hf_repo: str = None, hf_token: str = None, checkpoint_id: str = None):
    """Download AggTrades and generate Dollar Bars with 50GB memory safety and Checkpoints."""
    import gc
    import json
    from huggingface_hub import hf_hub_download
    
    print(f"[CLOUD] Dollar Bars: {symbol} | {start_date} -> {end_date} | Threshold: {threshold}")
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    all_bars = []
    leftover_dollar_sum = 0.0
    b_open, b_high, b_low, b_vol, b_ts = None, -float('inf'), float('inf'), 0.0, None
    current_month = start_dt.replace(day=1)

    # --- CHECKPOINT RESUME ---
    if checkpoint_id and hf_repo and hf_token:
        try:
            state_filename = f".state_{checkpoint_id}.json"
            bars_filename = f".bars_{checkpoint_id}.csv"
            
            state_path = hf_hub_download(repo_id=hf_repo, filename=state_filename, repo_type="dataset", token=hf_token)
            bars_path = hf_hub_download(repo_id=hf_repo, filename=bars_filename, repo_type="dataset", token=hf_token)
            
            with open(state_path, 'r') as f:
                state = json.load(f)
            
            df_existing = pd.read_csv(bars_path)
            all_bars = df_existing.to_dict('records')
            
            leftover_dollar_sum = state['leftover_dollar_sum']
            b_open = state['b_open']
            b_high = state['b_high']
            b_low = state['b_low']
            b_vol = state['b_vol']
            b_ts = state['b_ts']
            if b_ts: b_ts = pd.to_datetime(b_ts)
            
            # Resume from the month AFTER the one saved in state
            last_saved_month = datetime.strptime(state['last_month'], "%Y-%m")
            current_month = last_saved_month + relativedelta(months=1)
            
            print(f"  [RESUME] Found checkpoint. Resuming from {current_month.strftime('%Y-%m')}. Loaded {len(all_bars)} bars.")
        except Exception as e:
            print(f"  [INFO] No checkpoint found or failed to load: {e}")

    # --- MAIN LOOP ---
    while current_month <= end_dt:
        m_str = current_month.strftime("%Y-%m")
        print(f"  [PROCESS] Month {m_str}...")
        
        raw_month = download_vision_zips(base_url, "aggTrades", clean_symbol, current_month, current_month + relativedelta(months=1) - timedelta(days=1))
        
        if not raw_month.empty:
            raw_month.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
            raw_month['timestamp'] = pd.to_datetime(pd.to_numeric(raw_month['timestamp']), unit='ms')
            raw_month['price'] = pd.to_numeric(raw_month['price'])
            raw_month['quantity'] = pd.to_numeric(raw_month['quantity'])
            raw_month['dollar_value'] = raw_month['price'] * raw_month['quantity']
            
            mask = (raw_month['timestamp'] >= pd.to_datetime(start_dt)) & \
                   (raw_month['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))
            chunk = raw_month[mask].sort_values('timestamp')

            if not chunk.empty:
                for _, row in chunk.iterrows():
                    if b_open is None:
                        b_open = row['price']
                        b_ts = row['timestamp']
                    b_high = max(b_high, row['price'])
                    b_low = min(b_low, row['price'])
                    b_vol += row['quantity']
                    leftover_dollar_sum += row['dollar_value']

                    if leftover_dollar_sum >= threshold:
                        all_bars.append({
                            'timestamp': b_ts, 'open': b_open, 'high': b_high,
                            'low': b_low, 'close': row['price'], 'volume': b_vol,
                            'dollar_volume': leftover_dollar_sum
                        })
                        leftover_dollar_sum = 0.0
                        b_open, b_high, b_low, b_vol = None, -float('inf'), float('inf'), 0.0
        
        # --- SAVE CHECKPOINT ---
        if checkpoint_id and hf_repo and hf_token:
            state = {
                "last_month": m_str,
                "leftover_dollar_sum": leftover_dollar_sum,
                "b_open": b_open,
                "b_high": b_high,
                "b_low": b_low,
                "b_vol": b_vol,
                "b_ts": str(b_ts) if b_ts else None
            }
            upload_to_hf(json.dumps(state), f".state_{checkpoint_id}.json", hf_repo, hf_token)
            if all_bars:
                bars_csv = pd.DataFrame(all_bars).to_csv(index=False)
                upload_to_hf(bars_csv, f".bars_{checkpoint_id}.csv", hf_repo, hf_token)
            print(f"  [SAVED] Checkpoint for {m_str}")

        del raw_month
        gc.collect()
        current_month += relativedelta(months=1)

    if not all_bars:
        return {"success": False, "message": "Duomenu nerasta."}

    result_df = pd.DataFrame(all_bars)
    csv_string = result_df.to_csv(index=False)

    hf_url = None
    if hf_repo and hf_token and not checkpoint_id: 
        filename = f"{clean_symbol}_{start_date}_{end_date}_dollarBars_{int(threshold)}.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: hf_url = url_or_err

    preview = result_df.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(result_df), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.function(image=image, timeout=86400)
def fetch_dollar_bars_parallel(symbol: str, start_date: str, end_date: str, threshold: float = 1_000_000, hf_repo: str = None, hf_token: str = None):
    """Orchestrator to split work across 5 containers with Checkpoints."""
    print(f"[ORCHESTRATOR] Scaling Dollar Bars: {symbol} | {start_date} -> {end_date}")
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days
    
    # Split into 5 chunks
    chunks = []
    days_per_chunk = total_days // 5
    for i in range(5):
        c_start = start_dt + timedelta(days=i * days_per_chunk)
        if i == 4:
            c_end = end_dt
        else:
            c_end = c_start + timedelta(days=days_per_chunk - 1)
        
        # Unique ID for each chunk's checkpoint
        chunk_id = f"{symbol.replace('/','-')}_{c_start.strftime('%Y%m%d')}_{c_end.strftime('%Y%m%d')}"
        chunks.append((c_start.strftime("%Y-%m-%d"), c_end.strftime("%Y-%m-%d"), chunk_id))

    print(f"  [PARALLEL] Dispatching 5 workers with Checkpoints.")
    
    results = list(fetch_dollar_bars_cloud.map(
        [symbol]*5, 
        [c[0] for c in chunks], 
        [c[1] for c in chunks], 
        [threshold]*5,
        [hf_repo]*5,
        [hf_token]*5,
        [c[2] for c in chunks] # Pass the ID
    ))

    all_dfs = []
    for i, res in enumerate(results):
        if res.get("success") and res.get("csv_data"):
            df = pd.read_csv(io.StringIO(res["csv_data"]))
            all_dfs.append(df)
        else:
            print(f"  [WARN] Worker {i} failed: {res.get('message')}")

    if not all_dfs:
        return {"success": False, "message": "Visi konteineriai grazino klaida."}

    final_df = pd.concat(all_dfs, ignore_index=True).sort_values("timestamp")
    csv_string = final_df.to_csv(index=False)
    
    hf_url = None
    if hf_repo and hf_token:
        clean_symbol = symbol.replace("/", "").replace(":", "")
        filename = f"{clean_symbol}_{start_date}_{end_date}_dollarBars_PARALLEL_{int(threshold)}.csv"
        success, url_or_err = upload_to_hf(csv_string, filename, hf_repo, hf_token)
        if success: 
            hf_url = url_or_err
            # --- CLEANUP CHECKPOINTS ---
            from huggingface_hub import HfApi
            api = HfApi(token=hf_token)
            for c in chunks:
                try:
                    state_filename = f".state_{c[2]}.json"
                    bars_filename = f".bars_{c[2]}.csv"
                    api.delete_file(path_in_repo=state_filename, repo_id=hf_repo, repo_type="dataset")
                    api.delete_file(path_in_repo=bars_filename, repo_id=hf_repo, repo_type="dataset")
                except: pass

    preview = final_df.tail(100).to_dict(orient="records")
    return {"success": True, "row_count": len(final_df), "preview": preview, "csv_data": csv_string, "hf_url": hf_url}


@app.local_entrypoint()
def main(symbol="BTCUSDT", timeframe="15m", start="2024-01-01", end="2024-02-01"):
    # Testing aggregator
    result = fetch_dollar_bars_parallel.remote(symbol, start, end, 1000000)
    print(result)


