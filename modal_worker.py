import modal
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Modal konfigūracija
app = modal.App("binance-data-aggregator")
image = modal.Image.debian_slim().pip_install("pandas", "requests", "python-dateutil", "ccxt")

@app.function(image=image, timeout=3600, cpu=2.0, memory=4096)
def process_binance_data(symbol, timeframe, start_date, end_date):
    """
    Pagrindinė funkcija, kuri veikia Modal debesyje.
    Surenka Klines, Liquidations arba AggTrades ir sugeneruoja Dollar Bars.
    """
    print(f"🚀 Pradedamas apdorojimas: {symbol} | {timeframe} | {start_date} iki {end_date}")
    
    clean_symbol = symbol.replace("/", "").replace(":", "")
    base_url = "https://data.binance.vision/data/futures/um"
    
    def get_vision_csv(data_type, s_dt, e_dt):
        all_dfs = []
        curr = s_dt
        while curr <= e_dt:
            m_str = curr.strftime("%Y-%m")
            m_url = f"{base_url}/monthly/{data_type}/{clean_symbol}/{clean_symbol}-{data_type}-{m_str}.zip"
            try:
                res = requests.get(m_url)
                if res.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                        with z.open(z.namelist()[0]) as f:
                            df = pd.read_csv(f, header=None)
                            all_dfs.append(df)
                    curr += relativedelta(months=1)
                    continue
            except: pass

            d_str = curr.strftime("%Y-%m-%d")
            d_url = f"{base_url}/daily/{data_type}/{clean_symbol}/{clean_symbol}-{data_type}-{d_str}.zip"
            try:
                res = requests.get(d_url)
                if res.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                        with z.open(z.namelist()[0]) as f:
                            df = pd.read_csv(f, header=None)
                            all_dfs.append(df)
            except: pass
            curr += timedelta(days=1)
        
        return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    print("⏳ Siunčiami likvidavimai...")
    liq_raw = get_vision_csv('liquidationOrders', start_dt, end_dt)
    if not liq_raw.empty:
        liq_raw.columns = ['symbol', 'side', 'type', 'tif', 'qty', 'price', 'avg_price', 'status', 'last_fill_qty', 'acc_fill_qty', 'timestamp']
        liq_raw['timestamp'] = pd.to_datetime(liq_raw['timestamp'], unit='ms')
        liq_raw['liq_long_vol'] = liq_raw.apply(lambda x: x['qty'] * x['price'] if x['side'] == 'SELL' else 0, axis=1)
        liq_raw['liq_short_vol'] = liq_raw.apply(lambda x: x['qty'] * x['price'] if x['side'] == 'BUY' else 0, axis=1)
        liq_grouped = liq_raw.set_index('timestamp').resample(timeframe).agg({'liq_long_vol': 'sum', 'liq_short_vol': 'sum'})
    else:
        liq_grouped = pd.DataFrame()

    if timeframe == "Dollar Bars":
        print("⏳ Siunčiami AggTrades Dollar Bars kūrimui...")
        agg_trades = get_vision_csv('aggTrades', start_dt, end_dt)
        if not agg_trades.empty:
            print("⚙️ Generuojami Dollar Bars...")
            # Supaprastinta Dollar Bars logika cloud'ui (dideliems kiekiems)
            agg_trades.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
            agg_trades['price'] = pd.to_numeric(agg_trades['price'])
            agg_trades['quantity'] = pd.to_numeric(agg_trades['quantity'])
            agg_trades['dollar_value'] = agg_trades['price'] * agg_trades['quantity']
            
            bars = []
            current_sum = 0
            # Slenkstis perduodamas per timeframe pavadinimą arba numatytas (pvz. 1mln)
            threshold = 1_000_000 
            
            b_open, b_high, b_low = None, -float('inf'), float('inf')
            b_vol, b_ts = 0, None
            
            for _, row in agg_trades.iterrows():
                if b_open is None:
                    b_open, b_ts = row['price'], row['timestamp']
                b_high, b_low = max(b_high, row['price']), min(b_low, row['price'])
                b_vol += row['quantity']
                current_sum += row['dollar_value']
                
                if current_sum >= threshold:
                    bars.append({'timestamp': b_ts, 'open': b_open, 'high': b_high, 'low': b_low, 'close': row['price'], 'volume': b_vol})
                    current_sum, b_open = 0, None
                    b_high, b_low, b_vol = -float('inf'), float('inf'), 0
            
            return pd.DataFrame(bars).to_csv(index=False)
        return "Klaida: AggTrades nerasta."

    print("⏳ Siunčiamos žvakės (Klines)...")
    klines_raw = get_vision_csv(f'klines/{timeframe}', start_dt, end_dt)
    if not klines_raw.empty:
        klines_raw = klines_raw.iloc[:, :6]
        klines_raw.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        klines_raw['timestamp'] = pd.to_datetime(klines_raw['timestamp'], unit='ms')
        klines_raw = klines_raw.set_index('timestamp')
        final_df = klines_raw.join(liq_grouped, how='left').fillna(0)
        return final_df.reset_index().to_csv(index=False)
    
    return "Klaida: Duomenų nepavyko sugeneruoti."

@app.local_entrypoint()
def main(symbol="BTCUSDT", timeframe="15m", start="2024-01-01", end="2024-02-01"):
    csv_data = process_binance_data.remote(symbol, timeframe, start, end)
    filename = f"{symbol}_{timeframe}_Aggregated_{start}_{end}.csv"
    with open(filename, "w") as f:
        f.write(csv_data)
    print(f"✅ Failas paruoštas: {filename}")
