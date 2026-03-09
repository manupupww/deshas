import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ccxt
from typing import Optional
import modal

app = FastAPI(title="Binance Data Dashboard API")

# CORS - allow all origins for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Binance client for symbol list only
try:
    binance = ccxt.binance()
except Exception as e:
    print(f"Warning: Could not init Binance client: {e}")
    binance = None

class DownloadRequest(BaseModel):
    symbol: str
    interval: str
    data_type: str
    start_date: str
    end_date: str
    threshold: Optional[float] = 1_000_000
    agg_mode: Optional[str] = "Standard (Klines + Liq)"
    datasetType: Optional[str] = None

@app.get("/")
def health():
    return {"status": "ok", "message": "Binance Data Dashboard API on Hugging Face"}

@app.get("/api/symbols")
def get_symbols():
    try:
        if binance is None:
            raise Exception("Binance client not initialized")
        markets = binance.load_markets()
        symbols = sorted(list(markets.keys()))
        return {"symbols": symbols}
    except Exception as e:
        print(f"Warning: Binance API blocked or error: {e}. Using fallback symbols.")
        # Fallback symbols if Binance blocks the IP (common on HF Spaces)
        fallback = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
            "LINK/USDT", "LTC/USDT", "BCH/USDT", "NEAR/USDT", "UNI/USDT"
        ]
        return {"symbols": sorted(fallback)}

@app.post("/api/download")
def download_data(request: DownloadRequest):
    print(f"\n{'='*60}")
    print(f"[CLOUD] Download request:")
    print(f"   Symbol: {request.symbol}")
    print(f"   Interval: {request.interval}")
    print(f"   Data Type: {request.data_type}")
    print(f"   Start: {request.start_date}")
    print(f"   End: {request.end_date}")
    print(f"   Threshold: {request.threshold}")
    print(f"{'='*60}")
    
    # HF Upload settings
    hf_repo = os.environ.get("HF_REPO", "Vycka12/Base")
    hf_token = os.environ.get("HF_TOKEN")
    
    try:
        if request.data_type == 'Klines (OHLCV)':
            print("[CLOUD] Calling fetch_klines_cloud...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_klines_cloud")
            result = fn.remote(request.symbol, request.interval, request.start_date, request.end_date, hf_repo, hf_token)
            
        elif request.data_type == 'Liquidations':
            print("[CLOUD] Calling fetch_liquidations_cloud...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_liquidations_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, hf_repo, hf_token)

        elif request.data_type == 'AggTrades':
            print("[CLOUD] Calling fetch_aggtrades_cloud...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_aggtrades_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, hf_repo, hf_token)

        elif request.data_type == 'Dollar Bars (ML Ready)':
            print(f"[CLOUD] Calling fetch_dollar_bars_cloud (threshold: {request.threshold})...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_dollar_bars_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, request.threshold, hf_repo, hf_token)

        elif request.data_type == 'Volume Bars (ML Ready)':
            print(f"[CLOUD] Calling fetch_volume_bars_cloud (threshold: {request.threshold})...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_volume_bars_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, request.threshold, hf_repo, hf_token)

        elif request.data_type == 'VPIN (Flow Toxicity)':
            buckets = int(request.threshold) if request.threshold else 50
            print(f"[CLOUD] Calling fetch_vpin_cloud (buckets/day: {buckets})...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_vpin_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, buckets, hf_repo, hf_token)

        elif request.data_type == 'CDF Table (Flow Toxicity)':
            buckets = int(request.threshold) if request.threshold else 50
            print(f"[CLOUD] Calling fetch_flow_toxicity_cloud (buckets/day: {buckets})...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_flow_toxicity_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, buckets, 50, hf_repo, hf_token)

        else:
            raise HTTPException(status_code=400, detail="Unknown data type.")


        if result.get("hf_url"):
            print(f"[CLOUD] Result uploaded to HF: {result['hf_url']}")
            
        print(f"[CLOUD] Result received: success={result.get('success')}, rows={result.get('row_count', 0)}")
        return result
            
    except Exception as e:
        print(f"KLAIDA: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
