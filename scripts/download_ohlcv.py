import argparse
import sys
import os
from datetime import datetime, timedelta

# Pridedame dashboard/ aplanką į path, kad galėtume importuoti downloader
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
from downloader import get_downloader

def main():
    parser = argparse.ArgumentParser(description='Binance OHLCV Data Downloader')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Simbolis (pvz. BTC/USDT)')
    parser.add_argument('--interval', type=str, default='1m', help='Laiko intervalas (pvz. 1m, 1h, 1d)')
    parser.add_argument('--start', type=str, default=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), help='Pradžios data (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=datetime.now().strftime('%Y-%m-%d'), help='Pabaigos data (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    downloader = get_downloader()
    
    print(f"🚀 Pradedamas siuntimas: {args.symbol} ({args.interval}) nuo {args.start} iki {args.end}")
    
    try:
        data = downloader.fetch_klines(
            args.symbol,
            args.interval,
            args.start,
            args.end,
            progress_callback=lambda p: print(f"⏳ Progresas: {p*100:.1f}%")
        )
        
        if not data.empty:
            filepath = downloader.save_to_csv(
                data,
                args.symbol,
                'Klines',
                args.interval
            )
            print(f"✅ Sėkmingai atsisiųsta {len(data)} eilučių.")
            print(f"📂 Failas išsaugotas: {filepath}")
        else:
            print("⚠️ Duomenų nerasta.")
            
    except Exception as e:
        print(f"❌ Klaida: {str(e)}")

if __name__ == "__main__":
    main()
