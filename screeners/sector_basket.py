from config import SECTOR_MAP, SECTOR_LOOKBACK_DAYS


def _period_change(df, days):
    close = df["Close"]
    if len(close) < days + 1:
        return None
    return float((close.iloc[-1] - close.iloc[-1 - days]) / close.iloc[-1 - days])


def screen(prices, target_date=None):
    """Cari sektor yang lagi paling kompak naik, lalu flag anggotanya yang masih ketinggalan (laggard sektor)."""
    changes = {t: _period_change(df, SECTOR_LOOKBACK_DAYS) for t, df in prices.items() if t in SECTOR_MAP}
    changes = {t: c for t, c in changes.items() if c is not None}
    if not changes:
        return []

    sector_changes = {}
    for ticker, change in changes.items():
        sector = SECTOR_MAP[ticker]
        sector_changes.setdefault(sector, []).append(change)

    sector_avg = {s: sum(v) / len(v) for s, v in sector_changes.items()}
    top_sector = max(sector_avg, key=sector_avg.get)
    if sector_avg[top_sector] <= 0:
        return []

    signals = []
    for ticker, change in changes.items():
        if SECTOR_MAP[ticker] != top_sector:
            continue
        if change < sector_avg[top_sector]:
            signals.append({
                "ticker": ticker,
                "algo": "sector_basket",
                "sector": top_sector,
                "sector_avg_pct": round(sector_avg[top_sector] * 100, 1),
                "ticker_pct": round(change * 100, 1),
            })
    return signals
