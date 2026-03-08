# MA Reversal v1 - AFML Upgraded Strategy

## Overview
This is the **institutional-grade** version of the original "Moon Dev" MA Reversal strategy,
transformed using **Marcos Lopez de Prado's AFML** methodology.

## Original vs Upgraded

| Aspect | Original (Moon Dev) | AFML Upgraded |
|--------|-------------------|---------------|
| Data | Standard OHLCV candles | **Dollar Bars** + Frac Diff |
| Signals | Raw MA crossover | MA as **Primary Model** |
| Risk | Fixed TP/SL | **Meta-Labeling** + Kelly Bet Sizing |
| Validation | Simple backtest | **Purged K-Fold CV** + **DSR** |
| Execution | Full size always | **Dynamic sizing** by confidence |

## Pipeline (Run in order)

```
01_data_engineering.py  -> Downloads data, creates Dollar Bars, applies Frac Diff
02_primary_model.py     -> Generates MA signals, applies Triple-Barrier labels  
03_meta_labeling.py     -> Trains Meta-Model (Random Forest) with Purged CV
04_backtest.py          -> Compares Baseline vs ML Risk Managed + DSR check
```

## Strategy Logic

### Primary Model (MA Reversal)
- **LONG**: Price > SMA(20) AND Price > SMA(40)
- **SHORT**: Price > SMA(20) AND Price < SMA(40)
- **EXIT SHORT**: Price > SMA(40)

### Meta-Model Filter
A Random Forest trained on:
- Distance from SMAs (normalized)
- Momentum (5/10/20 bar returns)
- Volatility regime (short vs long vol ratio)
- Volume trend (current vs SMA)

Only trades with **>55% Meta-Model confidence** are executed.
Position size scales with confidence (Kelly-inspired).

## AFML Principles Applied
- [x] Dollar Bars (Ch. 2)
- [x] Triple-Barrier Labeling (Ch. 3)
- [x] Sample Weights via Uniqueness (Ch. 4)
- [x] Fractional Differentiation (Ch. 5)
- [x] Ensemble Methods - Random Forest (Ch. 6)
- [x] Purged K-Fold Cross-Validation (Ch. 7)
- [x] Bet Sizing via Meta-Labeling (Ch. 10)
- [x] Deflated Sharpe Ratio (Ch. 14)
