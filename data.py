from datetime import date, datetime, timedelta
import yfinance as yf


def fetch_prices(tickers, end_date=None, lookback_days=200):
    """Ambil OHLCV harian buat tiap ticker IDX, sampai end_date (format 'YYYY-MM-DD', default hari ini).
    lookback_days nentuin seberapa jauh ke belakang (200 hari kalender ~cukup buat rolling 20-hari screener).
    Return dict ticker -> DataFrame (index tanggal, kolom Close dll)."""
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
    start_dt = end_dt - timedelta(days=lookback_days)

    jk_tickers = [f"{t}.JK" for t in tickers]
    raw = yf.download(
        jk_tickers, start=start_dt, end=end_dt + timedelta(days=1),
        group_by="ticker", auto_adjust=True, progress=False,
    )

    result = {}
    for ticker, jk in zip(tickers, jk_tickers):
        df = raw[jk] if len(jk_tickers) > 1 else raw
        df = df.dropna(how="all")
        if not df.empty:
            result[ticker] = df
    return result
