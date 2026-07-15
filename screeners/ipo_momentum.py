from config import IPO_WATCH


def screen(prices, target_date=None):
    """Cek saham IPO_WATCH udah nyampe berapa % dari target 100%/200% akumulasi.

    ponytail: accum_price diisi manual di config.py karena deteksi otomatis butuh data
    broker-summary (sama kayak bdmtool) yang belum ada sumbernya. Upgrade: sambungin ke
    data broker-summary buat auto-isi accum_price begitu ada sumbernya.
    """
    signals = []
    for entry in IPO_WATCH:
        ticker = entry["ticker"]
        accum_price = entry["accum_price"]
        if ticker not in prices:
            continue

        last = float(prices[ticker]["Close"].iloc[-1])
        pct_of_target = (last - accum_price) / accum_price

        if pct_of_target >= 0.5:  # udah gerak minimal separuh jalan ke target 100%
            signals.append({
                "ticker": ticker,
                "algo": "ipo_momentum",
                "last_price": round(last, 2),
                "accum_price": accum_price,
                "pct_of_target": round(pct_of_target * 100, 1),
            })
    return signals
