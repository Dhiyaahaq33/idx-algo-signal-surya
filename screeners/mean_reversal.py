from config import MEAN_REVERSAL_LOOKBACK_DAYS, MEAN_REVERSAL_DROP_THRESHOLD


def screen(prices, target_date=None):
    """Flag saham yang turun jauh dari rolling high dan mulai nunjukin reversal (2 hari terakhir naik)."""
    signals = []
    for ticker, df in prices.items():
        if len(df) < MEAN_REVERSAL_LOOKBACK_DAYS + 2:
            continue

        close = df["Close"]
        rolling_high = close.rolling(MEAN_REVERSAL_LOOKBACK_DAYS).max().iloc[-1]
        last = close.iloc[-1]
        drop_pct = (rolling_high - last) / rolling_high

        reversing = close.iloc[-1] > close.iloc[-2] > close.iloc[-3] if len(close) >= 3 else False

        if drop_pct >= MEAN_REVERSAL_DROP_THRESHOLD and reversing:
            signals.append({
                "ticker": ticker,
                "algo": "mean_reversal",
                "last_price": round(float(last), 2),
                "rolling_high": round(float(rolling_high), 2),
                "drop_pct": round(float(drop_pct) * 100, 1),
            })
    return signals
