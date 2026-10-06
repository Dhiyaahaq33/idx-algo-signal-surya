# Mata-Mata Pasar: Radar Sinyal Saham IDX Otomatis
idx-algo-signal-surya

## Apa Ini?

Ini adalah bot screener (penyaring) saham otomatis untuk Bursa Efek Indonesia (IDX). Setiap hari bot ini mengambil data harga saham, menjalankan lima "algoritma" screening yang berbeda-beda gayanya, lalu mengirim rangkuman sinyal yang ditemukan ke Telegram. Ada juga bot Telegram interaktif yang bisa dipakai untuk memicu screening manual, melihat status, atau minta rekomendasi saham yang perlu dipantau.

Proyek ini murni alat bantu pemantauan/screening — bukan bot yang otomatis eksekusi order beli/jual. Semua sinyal harus dicek ulang manual sebelum dipakai untuk keputusan trading nyata.

Catatan dari pemilik proyek: repo ini awalnya dipakai juga sebagai referensi gaya kode untuk pengembangan modul "bandarmology" (analisis broker summary), tapi pengembangan itu sudah dipindahkan keluar dari sini. Di dalam folder ada sisa worktree Git bernama `bandar-broksum` (`.claude/worktrees/bandar-broksum/`) — itu percobaan lama yang belum dibersihkan, bukan bagian dari alur kerja utama.

## Fitur Utama

- **5 Algoritma Screening berjalan tiap kali screening dieksekusi:**
  1. **Mean Reversal** (`screeners/mean_reversal.py`) — mendeteksi saham yang sudah turun jauh (default >15%) dari harga tertinggi 20 hari terakhir, tapi mulai menunjukkan pembalikan arah (harga naik 2 hari beruntun).
  2. **Universe / Pairs** (`screeners/universe.py`) — mengelompokkan saham berdasarkan grup kepemilikan (misal grup Barito, Salim, Sinar Mas, Lippo, MNC, Astra, dll. — didefinisikan manual di `config.py`). Kalau mayoritas anggota grup bergerak signifikan tapi satu anggota masih diam, saham yang diam itu di-flag sebagai kandidat "ketinggalan" (laggard).
  3. **Golden Basket / Sector** (`screeners/sector_basket.py`) — mencari sektor IDX yang rata-rata pergerakannya paling kompak naik dalam 5 hari terakhir, lalu menandai saham anggota sektor itu yang pergerakannya masih di bawah rata-rata sektor.
  4. **Momentum IPO** (`screeners/ipo_momentum.py`) — memantau daftar saham IPO manual (`IPO_WATCH` di `config.py`) dan mengecek apakah harga sudah bergerak minimal separuh jalan menuju target akumulasi yang diisi manual oleh user.
  5. **Broker Anomali** (`screeners/broker_flow.py`) — pendekatan/proxy dari konsep "Sun Reversal": mendeteksi broker yang nilai transaksi hariannya jauh di atas rata-rata historisnya sendiri (default ≥2x). Catatan penting: data resmi IDX cuma level pasar keseluruhan (total transaksi broker per hari), BUKAN breakdown broker-per-saham, jadi sinyal ini cuma bilang "broker X lagi aktif banget hari ini", bukan "broker X beli saham Y".

- **Notifikasi Telegram** (`notify.py`, `main.py`) — hasil screening diformat rapi per kategori (dengan emoji judul) dan dikirim ke chat Telegram lewat Bot API. Kalau token/chat ID belum diisi di `.env`, pesan hanya dicetak ke console sebagai fallback.

- **Bot Telegram Interaktif** (`bot.py`) — polling command dari Telegram:
  - `/run` — jalankan screening data terbaru
  - `/run YYYY-MM-DD` — jalankan screening untuk tanggal tertentu
  - `/streak` — lihat sinyal yang muncul berturut-turut beberapa hari bursa
  - `/status` — kapan terakhir bot dijalankan
  - `/watch` — rekomendasi saham yang paling konsisten muncul di screening
  - `/start` atau `/help` — tampilkan daftar command
  - Hanya membalas chat ID yang cocok dengan `.env` (`TELEGRAM_CHAT_ID`), command dari chat lain diabaikan.

- **Backfill Historis** (`backfill.py`) — jalankan screening untuk beberapa hari bursa ke belakang sekaligus (otomatis skip weekend/hari libur), berguna untuk mengisi riwayat log tanpa harus menunggu hari demi hari. Secara default tidak mengirim ke Telegram (supaya tidak spam), kecuali pakai flag `--notify`.

- **Log & Riwayat Run** (`view_log.py`, `signal.log`) — semua hasil run dicatat ke `signal.log` (rotating log, otomatis dipotong agar tidak menumpuk tak terbatas). `view_log.py` bisa dipakai untuk:
  - Melihat daftar riwayat run beserta status (OK/gagal)
  - Melihat detail satu run tertentu (by nomor urut atau tanggal)
  - Menghitung "streak" — sinyal yang konsisten muncul berturut-turut di beberapa hari bursa terakhir
  - Membuat rekomendasi watchlist otomatis dari saham yang paling sering muncul beruntun

- **Sumber Data Harga** (`data.py`) — mengambil data OHLCV harian dari Yahoo Finance (`yfinance`), otomatis menambahkan suffix `.JK` untuk ticker IDX.

- **Sumber Data Broker Summary** (`broker_data.py`) — mengambil data ringkasan broker dari endpoint resmi idx.co.id. Karena Cloudflare di depan idx.co.id memblokir fingerprint TLS dari library Python biasa (403 Forbidden), bot ini shell-out ke `curl.exe` yang berhasil lolos, daripada memasang library TLS-impersonation tambahan.

- **Watchlist & Konfigurasi Fleksibel** (`config.py`) — watchlist saham (gabungan contoh manual + seluruh konstituen LQ45 + anggota grup konglomerasi besar), pemetaan grup kepemilikan, pemetaan sektor IDX-IC, serta semua ambang batas (threshold) tiap algoritma bisa diatur di satu file ini.

## Teknologi yang Dipakai

- **Python 3** — bahasa utama seluruh bot
- **yfinance** — ambil data harga saham historis dari Yahoo Finance
- **pandas** — manipulasi data time-series (rolling window, perhitungan persentase, dll.)
- **requests** — panggil Telegram Bot API dan endpoint IDX
- **python-dotenv** — memuat variabel rahasia (token, chat ID) dari file `.env`
- **curl.exe** (dipanggil via `subprocess`) — bypass proteksi Cloudflare di endpoint broker summary idx.co.id
- **Telegram Bot API** — kanal notifikasi dan command interaktif
- **pytest** — untuk `test_screeners.py` (unit test screener)
- Penjadwalan run harian dilakukan lewat **Windows Task Scheduler** (bukan cron, karena ini Windows) — bot menulis log sendiri lewat Python `RotatingFileHandler` karena redirect shell (`> run.log`) terbukti kurang reliable saat dipicu Task Scheduler.

## Cara Instalasi

Laptop ini sudah punya Python 3.11.6 (di `C:\Users\izayy\AppData\Local\Programs\Python\Python311`) dan pip 26.1.1, jadi semua dependency bisa langsung diinstal tanpa perlu tool tambahan.

1. **Masuk ke folder proyek** lewat PowerShell:
   ```powershell
   cd "D:\BOT\MONEY\idx-algo-signal-surya"
   ```

2. **(Disarankan) Buat virtual environment** supaya dependency proyek ini terpisah dari instalasi Python global:
   ```powershell
   py -3.11 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   Jika muncul error izin eksekusi script, jalankan dulu (sekali saja):
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

3. **Install semua dependency** dari `requirements.txt` (berisi: `yfinance`, `pandas`, `requests`, `python-dotenv`):
   ```powershell
   pip install -r requirements.txt
   ```

4. **Siapkan file `.env`** — file `.env` sudah ada di folder ini, tapi cek/lengkapi isinya (lihat `.env.example` sebagai contoh format). Perlu diisi:
   - `TELEGRAM_BOT_TOKEN` — token bot Telegram dari @BotFather
   - `TELEGRAM_CHAT_ID` — ID chat/grup tujuan notifikasi

5. **Pastikan `curl` tersedia** — Windows 11 sudah menyertakan `curl.exe` bawaan sejak beberapa tahun terakhir, jadi biasanya tidak perlu instalasi tambahan. Cek dengan:
   ```powershell
   curl --version
   ```
   Jika belum ada, install lewat winget:
   ```powershell
   winget install cURL.cURL
   ```

## Cara Menjalankan

Jalankan semua perintah dari dalam folder proyek (`D:\BOT\MONEY\idx-algo-signal-surya`), setelah virtual environment (jika dipakai) diaktifkan.

**Screening sekali jalan (data terbaru), kirim ke Telegram:**
```powershell
python main.py
```

**Screening untuk tanggal tertentu:**
```powershell
python main.py 2026-06-15
```

**Backfill screening beberapa hari bursa ke belakang (tanpa spam Telegram):**
```powershell
python backfill.py 10
```
Tambahkan `--notify` di akhir kalau memang ingin tiap hari juga dikirim ke Telegram:
```powershell
python backfill.py 10 --notify
```

**Jalankan bot Telegram interaktif** (polling command `/run`, `/streak`, `/status`, `/watch` — biarkan berjalan terus di terminal/background):
```powershell
python bot.py
```

**Lihat riwayat log run:**
```powershell
python view_log.py
```
atau langsung minta laporan streak/watchlist:
```powershell
python view_log.py streak
python view_log.py watch
```

**Jalankan test:**
```powershell
pytest test_screeners.py
```

**Untuk run otomatis harian**, daftarkan `python main.py` sebagai task terjadwal lewat Windows Task Scheduler (bukan lewat shell redirect `> log.txt`, karena bot ini sudah menulis log sendiri via Python).


## Catatan Penting

- **File `.env` dan `.env.example` berpotensi berisi credential sensitif** (token bot Telegram dan chat ID). Jangan pernah menampilkan, mem-forward, atau meng-commit isi file `.env` ke repository publik. Selalu pastikan `.env` sudah masuk daftar `.gitignore` sebelum push ke GitHub atau platform Git publik manapun — di proyek ini `.gitignore` sudah mengecualikan `.env`, tapi tetap periksa manual sebelum commit besar (`.env.example` boleh dishare karena isinya cuma template kosong).
- Semua sinyal dari screener ini adalah **hasil algoritma otomatis, bukan rekomendasi beli/jual**. Selalu cross-check manual sebelum mengambil keputusan trading, terutama sinyal "Broker Anomali" yang sifatnya proxy/pendekatan, bukan data breakdown broker-per-saham yang sesungguhnya.
- Daftar `OWNERSHIP_GROUPS` (grup kepemilikan konglomerasi) di `config.py` dikurasi manual dan beberapa grup (terutama MNC) ditandai penulis kode sendiri sebagai "kurang yakin lengkap" — verifikasi ulang ke prospektus/berita sebelum dipakai serius.
- Ada folder sisa `.claude/worktrees/bandar-broksum/` di dalam repo ini — itu adalah worktree Git dari eksperimen lama terkait modul bandarmology yang sudah dipindahkan ke proyek terpisah (`bandar-broksum`). Folder ini tidak dipakai oleh alur kerja utama proyek dan aman diabaikan atau dibersihkan jika sudah tidak diperlukan.

## Kebutuhan API LLM

- **Butuh API LLM?** Tidak relevan — proyek ini tidak memproses bahasa alami / tidak butuh LLM sama sekali. Semua 5 screener-nya murni rule-based (perhitungan persentase, rolling window, threshold numerik) di atas data harga dan broker summary — tidak ada langkah yang butuh model bahasa untuk berfungsi.
- **Bisa pakai API Claude (Anthropic)?** Tidak relevan untuk fungsi inti screening. Kalau mau dikembangkan lebih lanjut, Claude API (misalnya Claude Haiku 4.5) bisa opsional ditambahkan sebagai fitur ekstra — misalnya meringkas hasil screening harian jadi narasi yang lebih enak dibaca sebelum dikirim ke Telegram, atau menjawab pertanyaan bebas di bot Telegram interaktif (`bot.py`). Tapi ini murni nice-to-have, bukan kebutuhan dasar bot.

## Instalasi & Eksekusi Offline

- **Bisa instalasi offline?** Sebagian — `pip install -r requirements.txt` WAJIB online pertama kali untuk menarik `yfinance`, `pandas`, `requests`, `python-dotenv` dari PyPI. Setelah pernah terpasang atau ter-cache di pip lokal, instalasi ulang (misalnya di venv baru) bisa dilakukan offline dari cache.
- **Bisa dijalankan offline (setelah terinstall)?** Tidak — bot ini sepenuhnya bergantung pada data live: harga saham dari Yahoo Finance (`yfinance`), data broker summary dari idx.co.id, dan pengiriman notifikasi lewat Telegram Bot API. Tanpa koneksi internet, semua screener (`main.py`, `backfill.py`, `bot.py`) gagal mengambil data terbaru dan tidak bisa mengirim notifikasi.
