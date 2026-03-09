# VPIN (Volume-Synchronized Probability of Informed Trading) Strategy

This directory contains an implementation of a Bitcoin trading strategy based on order flow toxicity.

## Strategy Background
- **Source**: "Bitcoin wild moves: Evidence from order flow toxicity and price jumps" (ScienceDirect, 2026).
- **Core Concept**: VPIN measures "order flow toxicity" — the probability that informed traders are active. High toxicity predicts upcoming price jumps.
- **Direction**: In this implementation, we use an SMA (Simple Moving Average) filter to determine the jump direction (Uptrend = Buy, Downtrend = Stay out).

## Implementation Details
Since BTC tick-level data (Level 2/3) is extremely large and not always available for historical backtesting, we use the **Bulk Volume Classification (BVC)** method:
1. **Buy/Sell Estimation**: Uses a Normal CDF to estimate the probability of buy vs sell volume within each bar based on the (Close - Open) price move.
2. **VPIN Calculation**: Periodically calculates the order imbalance (Buy - Sell) relative to total volume over a rolling window.
3. **Data Source**: Local `BTCUSDT_2020-2025dollarBars_.csv` (100M Dollar Bars).

## Files
- `vpin_strategy.py`: Initial version using `yfinance` daily data.
- `vpin_dollar_bars.py`: High-precision version using local dollar bars.
- `vpin_results.json`: Latest backtest metrics (generated after run).
- `vpin_dollar_bars.html`: Interactive chart with VPIN indicator.

## What's Missing / Future Work
To reach the precision of the actual research paper:
1. **Tick Data**: Replace BVC estimation with actual trade-by-trade buy/sell (Aggressor) data.
2. **L4/Order ID**: Filter volume by Order ID to identify institutional "herding" behavior vs retail noise.
3. **Z-Score Thresholds**: Instead of a fixed VPIN threshold (e.g., 0.6), use a rolling Z-score to detect *unusual* toxicity spikes.
4. **On-Chain Signals**: Incorporate live whale movements as an additional toxicity filter.

## How to Run
```bash
# Run the dollar bars backtest
py vpin_dollar_bars.py
```
Check `vpin_results.json` and the `.html` file for results.
