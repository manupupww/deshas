import os
import sys

# Force UTF-8 stdout encoding for Windows terminal compatibility
sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ccxt
from typing import Optional
from dotenv import load_dotenv

# Load .env variables (MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)
load_dotenv()

# Import Modal cloud functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modal

app = FastAPI(title="Binance Data Dashboard API")

# CORS
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

class DownloadRequest(BaseModel):
    symbol: str
    interval: str
    data_type: str
    start_date: str
    end_date: str
    threshold: Optional[float] = 1_000_000
    agg_mode: Optional[str] = "Standard (Klines + Liq)"
    datasetType: Optional[str] = None

@app.get("/api/symbols")
def get_symbols():
    try:
        markets = binance.load_markets()
        symbols = sorted(list(markets.keys()))
        return {"symbols": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    
    try:
        # Reference the deployed Modal app
        modal_app = modal.App.lookup("binance-data-dashboard")
        
        if request.data_type == 'Klines (OHLCV)':
            print("[CLOUD] Calling fetch_klines_cloud...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_klines_cloud")
            result = fn.remote(request.symbol, request.interval, request.start_date, request.end_date)
            
        elif request.data_type == 'Liquidations':
            print("[CLOUD] Calling fetch_liquidations_cloud...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_liquidations_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date)

        elif request.data_type == 'AggTrades':
            print("[CLOUD] Calling fetch_aggtrades_cloud...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_aggtrades_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date)

        elif request.data_type == 'Dollar Bars (ML Ready)':
            print(f"[CLOUD] Calling fetch_dollar_bars_cloud (threshold: {request.threshold})...")
            fn = modal.Function.from_name("binance-data-dashboard", "fetch_dollar_bars_cloud")
            result = fn.remote(request.symbol, request.start_date, request.end_date, request.threshold)

        else:
            raise HTTPException(status_code=400, detail="Unknown data type.")

        print(f"[CLOUD] Result received: success={result.get('success')}, rows={result.get('row_count', 0)}")
        return result
            
    except Exception as e:
        print(f"KLAIDA: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Run with: uvicorn backend.api:app --reload
