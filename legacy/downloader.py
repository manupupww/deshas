import ccxt
import pandas as pd
import time
import requests
import io
import zipfile
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class BinanceDownloader:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.base_vision_url = "https://data.binance.vision/data/futures/um"
        self.data_dir = os.path.normpath("c:/Users/Mr. Perfect/tradingbot/data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_to_csv(self, df, symbol, data_type, timeframe=""):
        """Išsaugo DataFrame į CSV failą data/ aplanke."""
        if df.empty:
            return None
        
        clean_symbol = symbol.replace("/", "_").replace(":", "")
        # Supaprastintas pavadinimas: pvz. BTC_USDT_1m_Klines.csv
        suffix = f"_{timeframe}" if timeframe else ""
        filename = f"{clean_symbol}{suffix}_{data_type}.csv"
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False)
        return filepath

    def fetch_klines(self, symbol, timeframe, start_date, end_date, progress_callback=None):
        """
        Atsisiunčia Klines (OHLCV).
        Dideliems laikotarpiams (>30 dienų) naudoja Binance Vision bulk archyvus.
        Mažiems laikotarpiams naudoja CCXT API.
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days_diff = (end_dt - start_dt).days

        if days_diff > 30:
            print(f"📦 Naudojamas Binance Vision bulk download ({days_diff} dienų)...")
            return self._fetch_vision_klines(symbol, timeframe, start_date, end_date, progress_callback)
        else:
            print(f"🔌 Naudojamas CCXT API ({days_diff} dienų)...")
            return self._fetch_api_klines(symbol, timeframe, start_date, end_date, progress_callback)

    def _fetch_api_klines(self, symbol, timeframe, start_date, end_date, progress_callback=None):
        """Atsisiunčia Klines per CCXT API (mažiems laikotarpiams)."""
        since = self.exchange.parse8601(f"{start_date}T00:00:00Z")
        until = self.exchange.parse8601(f"{end_date}T23:59:59Z")
        
        all_ohlcv = []
        current_since = since
        
        while current_since < until:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, current_since, limit=1000)
                if not ohlcv: break
                
                last_ts = ohlcv[-1][0]
                all_ohlcv.extend(ohlcv)
                current_since = last_ts + 1
                
                if progress_callback:
                    progress_callback(min(len(all_ohlcv) / 10000, 0.95))
                
                if last_ts >= until: break
                time.sleep(self.exchange.rateLimit / 1000)
            except Exception as e:
                print(f"API klaida: {e}")
                break

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
        return df[df['timestamp'] <= pd.to_datetime(until, unit='ms')]

    def _fetch_vision_klines(self, symbol, timeframe, start_date, end_date, progress_callback=None):
        """Atsisiunčia Klines iš Binance Vision bulk archyvų (greitas, dideliems laikotarpiams)."""
        clean_symbol = symbol.replace("/", "").replace(":", "")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_dfs = []
        data_type = "klines"
        
        # 1. Mėnesiniai archyvai
        current_month = start_dt.replace(day=1)
        monthly_done = []
        total_months = 0
        
        while current_month <= end_dt.replace(day=1):
            next_month = current_month + relativedelta(months=1)
            if next_month <= datetime.now().replace(day=1):
                total_months += 1
            current_month = next_month
        
        current_month = start_dt.replace(day=1)
        processed = 0
        
        while current_month <= end_dt.replace(day=1):
            next_month = current_month + relativedelta(months=1)
            
            if next_month <= datetime.now().replace(day=1):
                month_str = current_month.strftime("%Y-%m")
                url = f"{self.base_vision_url}/monthly/{data_type}/{clean_symbol}/{timeframe}/{clean_symbol}-{timeframe}-{month_str}.zip"
                
                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                            with z.open(z.namelist()[0]) as f:
                                # Binance Vision failai kartais turi antraštes, kartais ne
                                df = pd.read_csv(f, header=None)
                                if not str(df.iloc[0, 0]).isdigit():
                                    df = df.iloc[1:].reset_index(drop=True)
                                
                                df = df.iloc[:, :6]
                                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                                df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
                                all_dfs.append(df)
                                monthly_done.append(current_month)
                                print(f"  ✅ Mėnuo {month_str}: {len(df)} eilučių")
                    else:
                        print(f"  ⚠️ Mėnuo {month_str}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"  ❌ Klaida {month_str}: {e}")
                
                processed += 1
                if progress_callback and total_months > 0:
                    progress_callback(min(processed / (total_months + 5), 0.95))
            
            current_month = next_month
        
        # 2. Dieniniai archyvai (tik nepadengtos dienos — dabartinis mėnuo)
        temp_date = start_dt
        while temp_date <= end_dt:
            is_covered = any(
                m_dt <= temp_date < (m_dt + relativedelta(months=1))
                for m_dt in monthly_done
            )
            
            if not is_covered and temp_date < datetime.now():
                date_str = temp_date.strftime("%Y-%m-%d")
                url = f"{self.base_vision_url}/daily/{data_type}/{clean_symbol}/{timeframe}/{clean_symbol}-{timeframe}-{date_str}.zip"
                
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                            with z.open(z.namelist()[0]) as f:
                                df = pd.read_csv(f, header=None)
                                if not str(df.iloc[0, 0]).isdigit():
                                    df = df.iloc[1:].reset_index(drop=True)

                                df = df.iloc[:, :6]
                                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                                df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
                                all_dfs.append(df)
                except Exception as e:
                    pass
            
            temp_date += timedelta(days=1)

        if all_dfs:
            final_df = pd.concat(all_dfs, ignore_index=True)
            final_df = final_df[(final_df['timestamp'] >= pd.to_datetime(start_dt)) & 
                               (final_df['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
            return final_df.sort_values('timestamp').reset_index(drop=True)
        return pd.DataFrame()

    def fetch_vision_data(self, data_type, symbol, start_date, end_date, progress_callback=None):
        """
        Išmanus duomenų siuntimas iš Binance Vision.
        Pirmiausia bando siųsti mėnesinius archyvus, o likusius dienas - iš dieninių.
        """
        clean_symbol = symbol.replace("/", "").replace(":", "")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_dfs = []
        
        # 1. GENERUOJAME MĖNESINIŲ ARCHYVŲ SĄRAŠĄ
        current_month = start_dt.replace(day=1)
        monthly_urls = []
        while current_month <= end_dt.replace(day=1):
            # Tikriname ar visas mėnuo patenka į rėmus
            next_month = current_month + relativedelta(months=1)
            month_str = current_month.strftime("%Y-%m")
            
            # Jei visas mėnuo yra praeityje (ne dabartinis mėnuo), bandom mėnesinį archyvą
            if next_month <= datetime.now().replace(day=1):
                url = f"{self.base_vision_url}/monthly/{data_type}/{clean_symbol}/{clean_symbol}-{data_type}-{month_str}.zip"
                monthly_urls.append((url, 'monthly', current_month))
            current_month = next_month

        # 2. GENERUOJAME DIENINIŲ ARCHYVŲ SĄRAŠĄ (tik toms dienoms, kurios nebuvo mėnesiniuose)
        daily_urls = []
        temp_date = start_dt
        while temp_date <= end_dt:
            # Tikriname ar ši diena jau padengta mėnesiniu archyvu
            is_covered = any(m_dt <= temp_date < (m_dt + relativedelta(months=1)) for _, type, m_dt in monthly_urls)
            
            if not is_covered:
                date_str = temp_date.strftime("%Y-%m-%d")
                url = f"{self.base_vision_url}/daily/{data_type}/{clean_symbol}/{clean_symbol}-{data_type}-{date_str}.zip"
                daily_urls.append((url, 'daily', temp_date))
            temp_date += timedelta(days=1)

        total_tasks = len(monthly_urls) + len(daily_urls)
        processed_tasks = 0

        # 3. SIUNTIMAS
        for url, period_type, dt in (monthly_urls + daily_urls):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        csv_name = z.namelist()[0]
                        with z.open(csv_name) as f:
                            df = pd.read_csv(f, header=None)
                            # Jei pirma eilutė yra antraštė, ją išmetame
                            if not str(df.iloc[0, 0]).isdigit():
                                df = df.iloc[1:].reset_index(drop=True)

                            if data_type == 'liquidationOrders':
                                df.columns = ['symbol', 'side', 'order_type', 'time_in_force', 'original_quantity', 'price', 'average_price', 'order_status', 'last_fill_quantity', 'accumulated_fill_quantity', 'timestamp']
                            else: # aggTrades
                                df.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
                            
                            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
                            # Filtruojame pagal tikslias datas (svarbu mėnesiniams archyvams)
                            df = df[(df['timestamp'] >= pd.to_datetime(start_dt)) & (df['timestamp'] <= pd.to_datetime(end_dt) + timedelta(days=1))]
                            all_dfs.append(df)
                else:
                    print(f"Nerasta: {url} (Status: {response.status_code})")
            except Exception as e:
                print(f"Klaida siunčiant {url}: {e}")
            
            processed_tasks += 1
            if progress_callback:
                progress_callback(processed_tasks / total_tasks)

        if all_dfs:
            final_df = pd.concat(all_dfs, ignore_index=True)
            return final_df.sort_values('timestamp')
        return pd.DataFrame()

    def create_dollar_bars(self, agg_trades_df, threshold=1_000_000):
        """
        Konvertuoja aggTrades DataFrame į Dollar Bars.
        """
        if agg_trades_df.empty:
            return pd.DataFrame()

        df = agg_trades_df.copy()
        df['price'] = pd.to_numeric(df['price'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        df['dollar_value'] = df['price'] * df['quantity']

        bars = []
        current_dollar_sum = 0.0
        bar_open = None
        bar_high = -float('inf')
        bar_low = float('inf')
        bar_volume = 0.0
        bar_start_ts = None

        for _, row in df.iterrows():
            if bar_open is None:
                bar_open = row['price']
                bar_start_ts = row['timestamp']
            
            bar_high = max(bar_high, row['price'])
            bar_low = min(bar_low, row['price'])
            bar_volume += row['quantity']
            current_dollar_sum += row['dollar_value']
            
            if current_dollar_sum >= threshold:
                bars.append({
                    'timestamp': bar_start_ts,
                    'open': bar_open,
                    'high': bar_high,
                    'low': bar_low,
                    'close': row['price'],
                    'volume': bar_volume,
                    'dollar_volume': current_dollar_sum
                })
                current_dollar_sum = 0.0
                bar_open = None
                bar_high = -float('inf')
                bar_low = float('inf')
                bar_volume = 0.0
        
        return pd.DataFrame(bars)

def get_downloader():
    return BinanceDownloader()
