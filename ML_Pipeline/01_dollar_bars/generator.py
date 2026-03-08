import pandas as pd
import numpy as np
import os
import argparse

def generate_dollar_bars(input_csv, output_csv, threshold):
    """
    Transforms Binance AggTrades OR Klines CSV into Dollar Bars (OHLCV format).
    """
    print(f"Processing: {input_csv}")
    print(f"Dollar Threshold: ${threshold:,.2f}")

    try:
        df = pd.read_csv(input_csv)
        
        # Detect Format
        is_klines = 'open' in df.columns and 'close' in df.columns and 'volume' in df.columns
        
        if is_klines:
            print("Detected Klines (OHLCV) format.")
            df['price'] = df['close']
            df['quantity'] = df['volume']
            if not np.issubdtype(df['timestamp'].dtype, np.number):
                df['timestamp'] = pd.to_datetime(df['timestamp']).view('int64') // 10**6
        else:
            if len(df.columns) == 7 and not isinstance(df.columns[0], str):
                df.columns = ['agg_trade_id', 'price', 'quantity', 'first_trade_id', 'last_trade_id', 'timestamp', 'is_buyer_maker']
            
        required_cols = ['price', 'quantity', 'timestamp']
        if not all(col in df.columns for col in required_cols):
            print(f"Error: CSV must contain these columns: {required_cols}")
            return

        df['price'] = pd.to_numeric(df['price'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        df['dollar_value'] = df['price'] * df['quantity']

        bars = []
        cur_sum = 0.0
        b_open, b_high, b_low = None, -float('inf'), float('inf')
        b_vol, b_ts = 0.0, None

        for _, row in df.iterrows():
            if b_open is None:
                b_open = row['open'] if is_klines else row['price']
                b_ts = row['timestamp']
            
            b_high = max(b_high, row['high'] if is_klines else row['price'])
            b_low = min(b_low, row['low'] if is_klines else row['price'])
            b_vol += row['quantity']
            cur_sum += row['dollar_value']

            if cur_sum >= threshold:
                bars.append({
                    'timestamp': b_ts,
                    'open': b_open,
                    'high': b_high,
                    'low': b_low,
                    'close': row['close'] if is_klines else row['price'],
                    'volume': b_vol,
                    'dollar_volume': cur_sum
                })
                cur_sum = 0.0
                b_open = None
                b_high, b_low, b_vol = -float('inf'), float('inf'), 0.0

        result_df = pd.DataFrame(bars)
        
        if not result_df.empty:
            result_df['datetime'] = pd.to_datetime(result_df['timestamp'], unit='ms')

        # Filter until 2022-12-03 if needed (user request)
        cutoff = pd.to_datetime('2022-12-04')
        result_df = result_df[result_df['datetime'] < cutoff]

        result_df.to_csv(output_csv, index=False)
        print(f"Success! Created {len(result_df)} Dollar Bars.")
        print(f"Saved to: {output_csv}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Critical Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Dollar Bars Generator")
    parser.add_argument("--input", type=str, required=True, help="Path to AggTrades CSV file")
    parser.add_argument("--threshold", type=float, default=1000000, help="Dollar amount per bar (default: 1,000,000)")
    parser.add_argument("--output", type=str, help="Output path (default: auto-generated)")

    args = parser.parse_args()

    out_path = args.output
    if not out_path:
        base, ext = os.path.splitext(args.input)
        out_path = f"{base}_dollar_bars_{int(args.threshold)}.csv"

    generate_dollar_bars(args.input, out_path, args.threshold)
