from config import OWNERSHIP_GROUPS, UNIVERSE_MOVE_THRESHOLD, UNIVERSE_LAGGARD_THRESHOLD


def _daily_change(df):
    close = df["Close"]
    if len(close) < 2:
        return None
    return float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2])


def screen(prices, target_date=None):
    """Kalau mayoritas satu grup pemilik bergerak tapi satu anggota masih diam, flag anggota itu."""
    signals = []
    for group_name, tickers in OWNERSHIP_GROUPS.items():
        changes = {t: _daily_change(prices[t]) for t in tickers if t in prices}
        changes = {t: c for t, c in changes.items() if c is not None}
        if len(changes) < 2:
            continue

        movers = {t: c for t, c in changes.items() if abs(c) >= UNIVERSE_MOVE_THRESHOLD}
        if not movers:
            continue

        for ticker, change in changes.items():
            if ticker in movers:
                continue
            if abs(change) <= UNIVERSE_LAGGARD_THRESHOLD:
                signals.append({
                    "ticker": ticker,
                    "algo": "universe",
                    "group": group_name,
                    "laggard_change_pct": round(change * 100, 2),
                    "movers": {t: round(c * 100, 2) for t, c in movers.items()},
                })
    return signals
