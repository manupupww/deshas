# ML Risk Manager Implementation Plan (Meta-Labeling)

This plan outlines the step-by-step process for building an institutional-grade ML Risk Manager based on the principles of **Marcos López de Prado** and the **Hudson & Thames `mlfinlab`** library.

---

## 🎯 Goal
To transition from a primary "alpha" strategy that may have high noise and false positives to a robust system where a secondary ML model (the Risk Manager) filters signals, optimizes position sizing, and protects the portfolio during market stress.

---

## 🚀 Phase 1: Institutional-Grade Data Engineering
Standard time-series data is often non-stationary and noisy. We will transform it into a format suitable for machine learning.

1.  **Event-Based Bars**: Replace time bars (1m, 5m) with **Dollar Bars** or **Volume Bars**.
    -   *Why?* They exhibit better statistical properties (closer to normal distribution) and handle volatility clusters naturally.
    -   *Tool:* `mlfinlab.data_structures.get_dollar_bars`
2.  **Fractional Differentiation (FracDiff)**: Use fractional differentiation instead of standard integer differentiation (first-order returns).
    -   *Why?* Standard returns remove "memory" from the series. FracDiff preserves memory while achieving stationarity.
    -   *Tool:* `mlfinlab.features.fracdiff`
3.  **CUSUM Filter**: Detect structural breaks to identify significant price movements for sampling.
    -   *Tool:* `mlfinlab.filters.cusum_filter`

---

## 🛠️ Phase 2: Primary Model (Alpha Generation)
The "Primary Model" (M1) provides the direction.

1.  **Baseline Strategy**: Implement a simple but logical strategy (e.g., Trend Following via MA Crossover or Mean Reversion via Bollinger Bands).
2.  **Signal Generation**: Produce ternary signals:
    -   `+1`: Long
    -   `-1`: Short
    -   `0`: Neutral
3.  **Baseline Metrics**: Calculate PnL, Sharpe Ratio, and Max Drawdown for the M1 strategy without any risk filtering.

---

## 🏷️ Phase 3: Triple-Barrier Labeling
Standard "up/down" labeling fails to capture the reality of trading (stop-losses and time limits).

1.  **Define Barriers**:
    -   **Upper Barrier**: Profit taking (scaled by volatility, e.g., $1.5 \times \text{ATR}$).
    -   **Lower Barrier**: Stop-loss (scaled by volatility, e.g., $2.0 \times \text{ATR}$).
    -   **Vertical Barrier**: Time limit (e.g., exit after 5 days if neither price barrier is hit).
2.  **Labeling**: If the upper barrier is hit first, label as `1` (Success). If the lower or vertical barrier is hit, label as `0` (Failure/Ignore).
    -   *Tool:* `mlfinlab.labeling.get_events` & `mlfinlab.labeling.get_bins`

---

## 🧠 Phase 4: Secondary Model (ML Risk Manager)
The "Secondary Model" (M2) performs **Meta-Labeling**. It doesn't predict direction; it predicts if the M1 signal will hit its profit target.

1.  **Feature Selection**:
    -   **M1 Meta-Data**: M1 signal strength/probability.
    -   **Market Context**: VIX index, rolling volatility, autocorrelation, market regime detectors.
    -   **Technical Indicators**: RSI, MACD, Volume Profile.
2.  **Model Selection**: Train a binary classifier (Random Forest, XGBoost, or a specialized Neural Network).
3.  **Optimization**: 
    -   Focus on **Precision** (avoiding false positives) and **F1-Score**.
    -   Use **Purged Cross-Validation** to prevent information leakage.
    -   *Tool:* `mlfinlab.cross_validation.purged_k_fold`

---

## 📏 Phase 5: Dynamic Position Sizing (Bet Sizing)
The Risk Manager shouldn't just be an on/off switch; it should scale the "conviction".

1.  **Probabilistic Scaling**: Use the output probability of M2 to determine the position size.
    -   $Size = P(\text{Success}) \times \text{Max Capital Allocation}$
2.  **Averaging In/Out**: Use concurrent bets analysis to manage multiple active signals.
    -   *Tool:* `mlfinlab.bet_sizing.bet_size_probability`

---

## 📊 Phase 6: Verification & Institutional Backtesting
Institutional grade means preventing overfitting and accounting for real-world costs.

1.  **Transaction Costs**: Include slippage and commissions (e.g., 5-10 bps) in the labeling process.
2.  **Backtest Statistics**:
    -   **DSR (Deflated Sharpe Ratio)**: To account for multiple testing bias.
    -   **Information Ratio / Sortino Ratio**.
3.  **Walk-Forward Analysis**: Validate on out-of-sample data continuously.

---

## 📦 Key Resources from `mlfinlab`
-   `labeling`: For Triple-Barrier and Meta-Labeling.
-   `data_structures`: For Tick/Volume/Dollar bars.
-   `features`: For Fractional Differentiation.
-   `cross_validation`: For Purged K-Fold (essential for time-series).
-   `bet_sizing`: For converting ML probabilities into trade sizes.
