# Grid Trading Backtest Engine

เครื่องมือ backtest กลยุทธ์ **Spot Grid Trading** สำหรับ cryptocurrency  
รองรับหลาย pair และหลาย exchange พร้อม HTML dashboard แสดงผล

**Live Dashboard:** [haruhanniti-alt.github.io/BTC-USDT-BN-vs-BTC-THB-BK-](https://haruhanniti-alt.github.io/BTC-USDT-BN-vs-BTC-THB-BK-/)

---

## ตัวอย่างผล Backtest (2026-01-19 → 2026-06-15, 147 วัน)

| Pair | Exchange | Stake | Grid | Return | Net P&L |
|---|---|---|---|---|---|
| BTC/USDT | Binance | 94,786 USDT | 63,190–126,381 (82) | +2.26% | -4.95% |
| BTC/THB  | Bitkub  | 3,000,000 THB | 2,000,000–4,000,000 (82) | +3.07% | -2.46% |

> Net P&L รวม unrealized PNL (มูลค่า coin ที่ยังถือค้างอยู่)

---

## Grid Logic

```
ทุก slot เริ่มว่าง (ไม่ถือ coin ตั้งแต่ต้น)
แต่ละ candle:
  Pass 1: SELL — slot ที่ถืออยู่ ถ้าราคาผ่าน level บนขึ้น → ขาย
  Pass 2: BUY  — slot ว่าง ถ้าราคาผ่าน level ลง → ซื้อ
Multi-fill: ราคาวิ่งผ่านหลาย level ในแท่งเดียว → fill ทุก level
Slippage: BUY × (1 + 0.05%), SELL × (1 - 0.05%)
```

---

## โครงสร้างไฟล์

```
grid-backtest/
├── grid_engine.py        # Core engine (shared ทุก pair)
├── run_btc_usdt.py       # Config BTC/USDT — Binance
├── run_btc_thb.py        # Config BTC/THB  — Bitkub
├── run_eth_usdt.py       # Config ETH/USDT — Binance
├── run_eth_thb.py        # Config ETH/THB  — Bitkub
├── merge_results.py      # รวม JSON ทุก pair → inject HTML
└── index.html            # Dashboard (GitHub Pages)
```

---

## Requirements

- Python 3.8+
- pandas, numpy

```bash
pip install pandas numpy
```

หรือถ้าใช้ **Freqtrade + Docker** (แนะนำ):
```bash
# ไม่ต้องติดตั้งอะไรเพิ่ม — รันผ่าน docker ได้เลย
```

---

## วิธีใช้งาน

### 1. เตรียมข้อมูล

วางไฟล์ข้อมูลราคา 1m ใน path ที่กำหนดใน config:

| Pair | แหล่งข้อมูล | Format |
|---|---|---|
| BTC/USDT | Binance | `btc_usdt_1m_2026.csv` |
| BTC/THB | Bitkub | `btc_thb_1m_YYYY.csv.gz` |
| ETH/USDT | Binance | `ETH_USDT-1m.feather` |
| ETH/THB | Bitkub | `eth_thb_1m_YYYY.csv.gz` |

**Column format ที่รองรับ (auto-detect):**
- `datetime, timestamp, open, high, low, close, volume` (Binance CSV)
- `timestamp(ms), open, high, low, close, volume` (CCXT/Freqtrade)
- `timestamp(epoch s/ms/μs), open, high, low, close, volume`

### 2. ปรับ Config (ถ้าต้องการ)

แก้ไขตัวเลขใน `run_*.py`:

```python
CONFIG = {
    'pair':        'BTC_USDT',
    'currency':    'USDT',
    'source':      'Binance',
    'data':        '/path/to/btc_usdt_1m.csv',
    'start':       '2026-01-19',
    'end':         '2026-06-15',
    'grid_min':    63_190,      # ราคาต่ำสุดของ grid
    'grid_max':    126_381,     # ราคาสูงสุดของ grid
    'grid_levels': 82,          # จำนวน grid
    'stake':       94_786,      # เงินลงทุน
    'fees':        [0.0025, 0.00125],  # ทดสอบ 2 ค่า fee
    'slippage':    0.0005,      # 0.05%
}
```

### 3. รัน Backtest

**แบบ Docker (Freqtrade):**
```bash
# BTC/USDT
docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/run_btc_usdt.py

# BTC/THB
docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/run_btc_thb.py

# รวมผลและ inject เข้า HTML
docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/merge_results.py
```

**แบบ Python ตรง:**
```bash
python run_btc_usdt.py
python run_btc_thb.py
python merge_results.py
```

### 4. ดูผลลัพธ์

- **Terminal:** ผล summary พิมพ์ออกมาทันที
- **JSON:** ไฟล์ `results_*.json` ใน `user_data/`
- **HTML Dashboard:** เปิด `index.html` หรือ push ขึ้น GitHub Pages

---

## เพิ่ม Pair ใหม่

สร้างไฟล์ `run_xxx_yyy.py` โดย copy จาก template แล้วแก้ config:

```python
CONFIG = {
    'pair':        'SOL_USDT',
    'currency':    'USDT',
    'source':      'Binance',
    'data':        '/path/to/sol_usdt_1m.csv',
    'start':       '2025-01-01',
    'end':         '2026-01-01',
    'grid_min':    100,
    'grid_max':    300,
    'grid_levels': 82,
    'stake':       10_000,
    'fees':        [0.0025, 0.00125],
    'slippage':    0.0005,
}
```

`merge_results.py` จะรวมผลทุก pair เข้า HTML ให้อัตโนมัติ

---

## Output JSON Format

ผลแต่ละ pair มีโครงสร้าง:

```json
{
  "fee": 0.0025,
  "stake": 94786,
  "currency": "USDT",
  "source": "Binance",
  "backtest_start": "2026-01-19",
  "backtest_end": "2026-06-15",
  "total_trades": 382,
  "total_profit": 2144.24,
  "pairs": [{
    "pair": "BTC_USDT",
    "apy": 5.58,
    "total_trades": 382,
    "total_profit": 2144.24,
    "unrealized_pnl": -6838.66,
    "net_pnl": -4694.43,
    "net_pnl_pct": -4.95,
    "coin_slots_held": 36,
    "monthly_revenue": {"2026-01": 120.5, ...},
    "snapshots": [{"date": "2026-01-19", "price": 93365, "grid_pct": -0.007, "bh_pct": -0.329}, ...]
  }]
}
```

---

## ข้อจำกัด / Disclaimer

- Backtest ไม่รับประกันผลในอนาคต
- Unrealized PNL คำนวณจากราคาปิดวันสุดท้าย — ถ้าราคาต่ำกว่า grid_min จะถือ coin ครบเกือบทุก slot
- ไม่รองรับ partial fill, funding rate, หรือ position limit

---

## License

MIT License — ใช้ต่อได้อิสระ ทั้ง personal และ commercial

---

*สร้างด้วย Python + Chart.js | ข้อมูล: Binance, Bitkub*
