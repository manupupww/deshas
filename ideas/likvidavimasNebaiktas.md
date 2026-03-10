# Option 2: 5-minute data (currently active)
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📥 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

# Data already has proper columns from preprocessing
print(f"✅ Loaded {len(data):,} {timeframe} bars")
print(f"📊 Data columns: {list(data.columns)}")

# Map liquidation columns to match strategy expectations
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
    data['total_liq_volume'] = data['long_liquidations'] + data['short_liquidations']
    data['long_liq_count'] = (data['long_liquidations'] > 0).astype(int)
    data['short_liq_count'] = (data['short_liquidations'] > 0).astype(int)
else:
    print("⚠️ Warning: Liquidation columns not found, creating empty columns")
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0
    data['total_liq_volume'] = 0
    data['long_liq_count'] = 0
    data['short_liq_count'] = 0


class InverseLiquidationSpreadStrategy(Strategy):
    """
    Entry Logic (OPPOSITE of momentum):
    - BUY when long liquidation volume exceeds threshold (fade the cascade, catch bounce)
    - SELL when short liquidation volume exceeds threshold (fade the squeeze, catch reversal)

    Spread Feature:
    - Wait for price to move spread_pct% from liquidation price before entering
    - For longs liquidated: wait for price to DROP spread_pct% then BUY
    - For shorts liquidated: wait for price to RISE spread_pct% then SELL

    Exit Logic:
    - Take profit at X%
    - Stop loss at Y%
    - Time-based exit after max_hold_hours
    """

    # Optimizable parameters
    liquidation_threshold = 975000
    spread_pct = 0.5
    take_profit = 1.0
    stop_loss = 2.0
    max_hold_hours = 2

    # Position sizing
    position_size = 0.95

    def init(self):
        """Initialize strategy indicators"""
        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)
        self.short_liq_volume = self.I(lambda: self.data.short_liq_volume)
        self.net_liq_volume = self.I(lambda: self.data.net_liq_volume)

        self.avg_long_liq = self.I(lambda x: pd.Series(x).rolling(24).mean(), self.long_liq_volume)
        self.avg_short_liq = self.I(lambda x: pd.Series(x).rolling(24).mean(), self.short_liq_volume)

        self.pending_long_signal = False
        self.pending_short_signal = False
        self.long_target_price = 0
        self.short_target_price = 0

    def next(self):
        """Main strategy logic - INVERSE/CONTRARIAN approach with spread"""

        current_long_liq = self.long_liq_volume[-1]
        current_short_liq = self.short_liq_volume[-1]
        current_price = self.data.Close[-1]

        # Check for long liquidation signal → BUY contrarian
        if not self.position:
            if current_long_liq >= self.liquidation_threshold:
                self.long_target_price = current_price * (1 - self.spread_pct / 100)
                self.pending_long_signal = True
                self.pending_short_signal = False

            elif current_short_liq >= self.liquidation_threshold:
                self.short_target_price = current_price * (1 + self.spread_pct / 100)
                self.pending_short_signal = True
                self.pending_long_signal = False

        # Execute pending long entry
        if self.pending_long_signal and current_price <= self.long_target_price:
            sl_price = current_price * (1 - self.stop_loss / 100)
            tp_price = current_price * (1 + self.take_profit / 100)

            self.buy(size=self.position_size, sl=sl_price, tp=tp_price)
            self.pending_long_signal = False
            self.long_target_price = 0

        # Execute pending short entry
        elif self.pending_short_signal and current_price >= self.short_target_price:
            sl_price = current_price * (1 + self.stop_loss / 100)
            tp_price = current_price * (1 - self.take_profit / 100)

            self.sell(size=self.position_size, sl=sl_price, tp=tp_price)
            self.pending_short_signal = False
            self.short_target_price = 0

        # Time-based exit
        else:
            self.pending_long_signal = False
            self.pending_short_signal = False

            if len(self.trades) > 0:
                entry_time = self.trades[-1].entry_time
                current_time = self.data.index[-1]
                hours_held = (current_time - entry_time).total_seconds() / 3600

                if hours_held >= self.max_hold_hours:
                    self.position.close()


# Run baseline backtest
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume',
              'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        InverseLiquidationSpreadStrategy,
        cash=1000000,
        commission=0.001
    )

    baseline_stats = bt.run()

    print(f"\n Moon Dev's BASELINE RESULTS (INVERSE/CONTRARIAN):")
    print(f"Liquidation Threshold: ${InverseLiquidationSpreadStrategy.liquidation_threshold:}")
    print(f"Spread: {InverseLiquidationSpreadStrategy.spread_pct:.2f}%")
    print(f"Take Profit: {InverseLiquidationSpreadStrategy.take_profit:.1f}%")
    print(f"Stop Loss: {InverseLiquidationSpreadStrategy.stop_loss:.1f}%")
    print(f"Max Hold: {InverseLiquidationSpreadStrategy.max_hold_hours} hours")
    print("=" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n FULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)


# Optimization
print("\n" + "="*70)
print("RUNNING OPTIMIZATION - Moon Dev's Parameter Search")
print("="*70)
print("📷 Optimizing parameters... This may take a few minutes...")

try:
    optimization_results = bt.optimize(
        liquidation_threshold=range(100000, 1000000, 25000),
        spread_pct=[0.1, 0.25, 0.5, 0.75, 1.0],
        take_profit=[1.0, 1.5, 2.0],
        stop_loss=[1.0, 1.5, 2.0],
        max_hold_hours=[2, 4],
        maximize='Sharpe Ratio',
        return_heatmap=False
    )

    print("\n✨ Moon Dev's OPTIMIZED RESULTS:")
    print("="*70)
    print(optimization_results)

    print("\n📍 OPTIMIZED PARAMETERS:")
    print("-"*50)
    print(f"Liquidation Threshold: {optimization_results._strategy.liquidation_threshold:,}")
    print(f"Spread: {optimization_results._strategy.spread_pct:.2f}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit:.1f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1f}%")
    print(f"Max Hold Hours: {optimization_results._strategy.max_hold_hours}")

    print("\n📊 IMPROVEMENT SUMMARY:")
    print("-" * 50)
    baseline_return = baseline_stats['Return [%]']

except Exception as e:
    print("❌ Optimization failed:", e)
