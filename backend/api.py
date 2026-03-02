import os
import sys

# Priverčiame stdout naudoti UTF-8, kad Windows terminalas nelūžtų dėl lietuviškų raidžių
sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional
from dotenv import load_dotenv

# Užkrauname .env kintamuosius
load_dotenv()
# Pridedame legacy katalogą į sys.path, kad galėtume importuoti downloader
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "legacy"))

try:
    from downloader import get_downloader
    import ccxt
except ImportError as e:
    print(f"Nepavyko importuoti modulių: {e}")
    # Jei reikia, inicializuokime downloader lokaliai ar modifikuojant path

app = FastAPI(title="Binance Data Dashboard API")

# Leidžiame CORS (Cross-Origin Resource Sharing), kad frontend galėtų bendrauti su backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Gamyboje pakeisti į specifiškus domenus pvz., "http://localhost:5173"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializuojame Binance klientą per CCXT
try:
    binance = ccxt.binance()
    downloader_instance = get_downloader()
except Exception as e:
    print(f"Klaida inicializuojant Binance klientą: {e}")

class DownloadRequest(BaseModel):
    symbol: str
    interval: str
    data_type: str
    start_date: str
    end_date: str
    threshold: Optional[float] = 1_000_000
    agg_mode: Optional[str] = "Standard (Klines + Liq)"

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
    print(f"Gautas download request:")
    print(f"   Symbol: {request.symbol}")
    print(f"   Interval: {request.interval}")
    print(f"   Data Type: {request.data_type}")
    print(f"   Start: {request.start_date}")
    print(f"   End: {request.end_date}")
    print(f"{'='*60}")
    
    try:
        data = pd.DataFrame()
        
        if request.data_type == 'Klines (OHLCV)':
            print("Pradedamas Klines siuntimas per CCXT API...")
            data = downloader_instance.fetch_klines(
                request.symbol, 
                request.interval, 
                request.start_date, 
                request.end_date
            )
            print(f"Klines rezultatas: {len(data)} eilučių")
        
        elif request.data_type == 'Liquidations':
            print("Pradedamas Liquidations siuntimas iš Binance Vision...")
            data = downloader_instance.fetch_vision_data(
                'liquidationOrders',
                request.symbol,
                request.start_date,
                request.end_date
            )
            print(f"Liquidations rezultatas: {len(data)} eilučių")

        elif request.data_type == 'AggTrades':
            print("Pradedamas AggTrades siuntimas iš Binance Vision...")
            data = downloader_instance.fetch_vision_data(
                'aggTrades',
                request.symbol,
                request.start_date,
                request.end_date
            )
            print(f"AggTrades rezultatas: {len(data)} eilučių")

        elif request.data_type == 'Dollar Bars (ML Ready)':
            print(f"Siunčiami AggTrades ir generuojami Dollar Bars (Threshold: {request.threshold})...")
            agg_trades = downloader_instance.fetch_vision_data(
                'aggTrades',
                request.symbol,
                request.start_date,
                request.end_date
            )
            if not agg_trades.empty:
                data = downloader_instance.create_dollar_bars(agg_trades, threshold=request.threshold)
                print(f"Dollar Bars rezultatas: {len(data)} eilučių")
            else:
                print("AggTrades nerasta, Dollar Bars sugeneruoti nepavyko.")

        elif request.data_type == 'Time-Series Aggregator (Cloud)':
            cmd_tf = request.interval if request.agg_mode == "Standard (Klines + Liq)" else "Dollar Bars"
            return {
                "message": "Modal Cloud processing required.", 
                "command": f"modal run dashboard/modal_worker.py --symbol {request.symbol.replace('/', '')} --timeframe \"{cmd_tf}\" --start {request.start_date} --end {request.end_date}"
            }
        else:
            raise HTTPException(status_code=400, detail="Nežinomas duomenų tipas.")

        if not data.empty:
            print(f"Sėkmingai! Grąžinama {len(data)} eilučių.")
            # Paimti 100 paskutinių eilučių preview
            preview_data = data.tail(100).to_dict(orient="records")
            # Sukuriame vieną CSV failo string masyvą
            csv_string = data.to_csv(index=False)
            
            return {
                "success": True,
                "row_count": len(data),
                "preview": preview_data,
                "csv_data": csv_string
            }
        else:
            print("Duomenų nerasta — tuščias DataFrame grąžintas.")
            return {"success": False, "message": "Duomenų nerasta."}
            
    except Exception as e:
        print(f"KLAIDA: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Paleisti su: uvicorn backend.api:app --reload
