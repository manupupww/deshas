import pandas as pd

# Mock data dataframe that mimics what the script receives
data = {
    'timestamp': [1640995200194, 1640995201194, 1640995202194],
    'price': [46210.57, 46210.57, 46210.57],
    'quantity': [10.0, 10.0, 10.0],
    'dollar_value': [462105.7, 462105.7, 462105.7],
    'bar_id': [1, 1, 1]
}
completed_bars_df = pd.DataFrame(data)

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

final_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume']
bars = bars[final_cols]
print(bars.to_csv(index=False, header=True))
