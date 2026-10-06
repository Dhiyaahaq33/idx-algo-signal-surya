# IDX Algo Signal Surya

Bot screener saham IDX (Bursa Efek Indonesia) berbasis Python yang menjalankan beberapa algoritma sinyal trading harian, lalu mengirim hasilnya ke Telegram. Bot juga bisa dikendalikan lewat command Telegram (polling), punya mode backfill untuk mengisi histori beberapa hari sekaligus, dan punya utilitas untuk melihat log/riwayat run serta mendeteksi sinyal yang muncul beruntun beberapa hari bursa.

> Nama internal project: `idx-algo-signal-surya`.

## Fitur Utama

Setiap run mengambil data harga (lewat `yfinance`) untuk watchlist saham di `config.py`, lalu menjalankan 5 screener/algoritma berikut (modul di folder `screeners/`):

1. **Mean Reversal** (`screeners/mean_reversal.py`) — Flag saham yang turun jauh (default ≥15%) dari rolling high N hari (default 20 hari bursa) dan mulai menunjukkan tanda reversal (harga naik 2 hari berturut-turut).
2. **Pairs / Universe** (`screeners/universe.py`) — Berdasarkan daftar grup kepemilikan/afiliasi saham (`OWNERSHIP_GROUPS` di `config.py`, mis. grup Barito, Salim, Sinar Mas, Astra, dll). Kalau mayoritas anggota grup bergerak signifikan (default ≥5%) tapi satu anggota masih diam (default ≤1%), anggota yang diam itu di-flag sebagai kandidat "ketinggalan".
3. **Golden Basket / Sector Laggard** (`screeners/sector_basket.py`) — Mencari sektor (berdasarkan peta sektor IDX-IC manual di `SECTOR_MAP`) yang rata-rata pergerakannya paling kompak naik dalam beberapa hari terakhir (default 5 hari), lalu flag saham anggota sektor tersebut yang pergerakannya masih di bawah rata-rata sektor.
4. **Momentum IPO** (`screeners/ipo_momentum.py`) — Memantau saham IPO yang didaftarkan manual di `IPO_WATCH` (ticker + harga akumulasi), lalu flag kalau harga sudah bergerak minimal separuh jalan menuju target kenaikan 100%.
5. **Broker Anomali** (`screeners/broker_flow.py`) — Proxy dari konsep "Sun Reversal": mengambil data broker summary harian dari endpoint publik idx.co.id (level pasar, bukan breakdown per saham) dan flag broker yang nilai transaksinya hari ini jauh di atas (default ≥2x) rata-rata baseline dia sendiri (default 10 hari bursa terakhir, minimal baseline Rp1 miliar).

Fitur pendukung lain:

- **Bot Telegram interaktif** (`bot.py`) — polling command Telegram: `/run [YYYY-MM-DD]`, `/streak`, `/watch`, `/status`, `/help`.
- **Backfill** (`backfill.py`) — jalankan screening untuk N hari bursa terakhir sekaligus (skip weekend/libur otomatis), berguna untuk mengisi histori tanpa spam Telegram (`--notify` opsional).
- **Log & analisis riwayat** (`view_log.py`) — parsing `signal.log` (rotating log) untuk melihat riwayat run, mendeteksi sinyal yang muncul beruntun (streak) di beberapa hari bursa berturut-turut, dan membangun rekomendasi watchlist dari sinyal paling konsisten.

## Sumber Data

- **Harga OHLCV**: [yfinance](https://pypi.org/project/yfinance/), ticker IDX diformat `TICKER.JK`.
- **Data broker summary**: endpoint publik `idx.co.id` (`GetBrokerSummary`), diakses via `curl` (bukan `requests`) karena Cloudflare di depan idx.co.id memblokir fingerprint TLS dari `requests`/urllib3.

Catatan: data broker summary dari IDX hanya level pasar (total transaksi per broker per hari), bukan breakdown broker per saham — jadi screener Broker Anomali hanya mendeteksi broker yang sedang aktif secara tidak biasa, bukan saham spesifik apa yang sedang mereka gerakkan.

## Tech Stack

- Python 3
- [yfinance](https://pypi.org/project/yfinance/) — data harga saham
- [pandas](https://pandas.pydata.org/) — perhitungan rolling/statistik
- [requests](https://pypi.org/project/requests/) — HTTP client (notifikasi Telegram, polling command)
- [python-dotenv](https://pypi.org/project/python-dotenv/) — load konfigurasi dari `.env`
- `curl` (CLI, harus tersedia di PATH) — fetch data broker summary IDX

## Instalasi

```bash
git clone <url-repo-ini>
cd idx-algo-signal-surya
pip install -r requirements.txt
```

Pastikan `curl` tersedia di PATH (dipakai oleh `broker_data.py` untuk mengambil data broker summary IDX).

## Konfigurasi

Salin `.env.example` menjadi `.env` dan isi dengan token bot Telegram kamu sendiri (JANGAN commit file `.env` — sudah masuk `.gitignore`):

```env
TELEGRAM_BOT_TOKEN=isi_token_bot_telegram_kamu
TELEGRAM_CHAT_ID=isi_chat_id_tujuan_notifikasi
```

Jika `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` kosong, hasil screening akan dicetak ke console saja (tidak dikirim ke Telegram).

Watchlist saham, grup kepemilikan, peta sektor, daftar IPO yang dipantau, dan seluruh parameter/threshold algoritma (lookback, ambang drop, ambang anomali, dll) dikonfigurasi manual di `config.py` — sesuaikan sendiri sesuai saham yang ingin dipantau.

## Cara Menjalankan

Jalankan screening sekali untuk data terbaru (dan kirim ke Telegram):

```bash
python main.py
```

Jalankan untuk tanggal tertentu:

```bash
python main.py 2026-06-15
```

Jalankan bot Telegram interaktif (polling command `/run`, `/streak`, `/watch`, `/status`):

```bash
python bot.py
```

Backfill N hari bursa terakhir (default tanpa kirim ke Telegram, tambahkan `--notify` untuk mengirim tiap hari):

```bash
python backfill.py 10
python backfill.py 10 --end-date 2026-06-15 --notify
```

Lihat riwayat run / detail satu run dari log:

```bash
python view_log.py
```

Lihat sinyal yang beruntun (streak) beberapa hari bursa terakhir:

```bash
python view_log.py streak
```

Lihat rekomendasi pantau berdasarkan sinyal paling konsisten:

```bash
python view_log.py watch
```

Jalankan test screener (data harga sintetis, tanpa perlu koneksi internet):

```bash
python test_screeners.py
```

## Jalan Otomatis di GitHub Actions (tanpa PC nyala)

Selain jalan lokal, bot ini bisa dijadwalkan lewat GitHub Actions (`.github/workflows/daily-signal.yml`) — jalan tiap hari bursa jam 16:30 WIB di server GitHub, tidak perlu PC/laptop kamu nyala. Trigger manual juga bisa lewat tab **Actions > Daily IDX Signal Run > Run workflow**.

Setup:

1. Push repo ini ke GitHub (kalau belum).
2. Di **Settings > Secrets and variables > Actions**, tambahkan repository secrets:
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — sama seperti isi `.env` lokal.
   - `GOOGLE_SHEETS_CREDENTIALS_JSON` (opsional) — isi JSON key service account Google Cloud (lihat bagian di bawah).
   - `GOOGLE_SHEET_ID` (opsional) — ID spreadsheet tujuan, diambil dari URL sheet (`.../d/<ID>/edit`).
3. Kalau `GOOGLE_SHEETS_CREDENTIALS_JSON`/`GOOGLE_SHEET_ID` tidak diisi, langkah push-ke-Sheets otomatis di-skip (bot tetap jalan normal, kirim ke Telegram saja).

`signal.log` sengaja tidak ikut ter-commit ke git (lihat `.gitignore`) — di Actions, riwayatnya dipertahankan lewat GitHub Actions cache antar-run, supaya `view_log.py streak`/`watch` tetap punya histori walau runner-nya baru tiap kali.

### Push hasil sinyal ke Google Sheets

Tiap run menambah baris baru ke tab `Signals` di spreadsheet (kolom: `date`, `algo`, `ticker`, `details`). Ini dipakai supaya data sinyal bisa dibaca otomasi lain (mis. Gemini Spark) tanpa perlu akses langsung ke repo/log.

Cara bikin service account:

1. Buat project di [Google Cloud Console](https://console.cloud.google.com/), aktifkan **Google Sheets API**.
2. Buat **Service Account**, generate key JSON.
3. Buat Google Sheet baru, share ke email service account (`...@<project>.iam.gserviceaccount.com`) dengan akses **Editor**.
4. Isi `GOOGLE_SHEETS_CREDENTIALS_JSON` (seluruh isi file JSON, satu baris) dan `GOOGLE_SHEET_ID` (dari URL sheet) di GitHub Secrets (untuk Actions) atau `.env` (untuk lokal).

## Disclaimer

Project ini dibuat untuk keperluan riset dan otomatisasi pribadi. Sinyal yang dihasilkan bersifat teknikal/statistik sederhana berdasarkan data harga historis dan data broker summary publik — **bukan rekomendasi atau saran finansial**. Selalu lakukan riset dan cross-check mandiri sebelum mengambil keputusan investasi/trading. Penggunaan sepenuhnya menjadi tanggung jawab pengguna.
