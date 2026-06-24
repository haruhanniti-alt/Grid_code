# Grid Trading Backtest Engine

เครื่องมือ backtest กลยุทธ์ **Spot Grid Trading** สำหรับ cryptocurrency
รองรับหลาย pair และหลาย exchange พร้อม HTML dashboard แสดงผล

**Live Dashboard:** [haruhanniti-alt.github.io/BTC-USDT-BN-vs-BTC-THB-BK-](https://haruhanniti-alt.github.io/BTC-USDT-BN-vs-BTC-THB-BK-/)

---

## ตัวอย่างผล Backtest (2026-01-19 → 2026-06-15, 147 วัน)

| Pair     | Exchange | Stake         | Grid                     | Return | Net P&L |
| -------- | -------- | ------------- | ------------------------ | ------ | ------- |
| BTC/USDT | Binance  | 94,786 USDT   | 63,190–126,381 (82)      | +2.26% | -4.95%  |
| BTC/THB  | Bitkub   | 3,000,000 THB | 2,000,000–4,000,000 (82) | +3.07% | -2.46%  |

> Net P&L รวม unrealized PNL (มูลค่า coin ที่ยังถือค้างอยู่)

---

## Grid Logic

```
ทุก slot เริ่มว่าง (ไม่ถือ coin ตั้งแต่ต้น)
แต่ละ candle:
  Pass 1: SELL — slot ที่ถืออยู่ ถ้า high แตะหรือเกิน sell level → ขาย
                 • ปกติ: ราคาแตะ sell level → ขายที่ราคา sell level
                 • Gap up: ราคากระโดดข้าม sell level (open สูงกว่า level)
                           → ขายที่ราคา "open ของแท่งแรกที่ทะลุ"
                           (ไม่ถือไม้ค้างจนจบ backtest → unrealized ไม่พองลวงตา)
  Pass 2: BUY  — slot ว่าง ถ้าราคาผ่าน level ลง → ซื้อ
Multi-fill: ราคาวิ่งผ่านหลาย level ในแท่งเดียว → fill ทุก level
Slippage: BUY × (1 + 0.05%), SELL × (1 - 0.05%)
```

> **อัปเดต Sell Logic:** เดิม grid จะขายเฉพาะเมื่อ sell level อยู่ในช่วง low–high ของแท่ง
> ทำให้เมื่อราคา**กระโดดทะลุ**กรอบ grid (เช่น เหรียญพุ่งหลายเท่าในตลาดขาขึ้น)
> เหรียญที่ถืออยู่จะ**ขายไม่ออกและค้างยาวจนจบ backtest** → unrealized PNL พองสูงผิดจากความจริง
> เวอร์ชันใหม่แก้ให้ขายที่ราคา open ของแท่งแรกที่ราคาทะลุ sell level
> สะท้อนพฤติกรรม limit order จริง (fill ที่ราคาแรกที่เทรดได้เหนือ level)

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

```
pip install pandas numpy
```

หรือถ้าใช้ **Freqtrade + Docker** (แนะนำ):

```
# ไม่ต้องติดตั้งอะไรเพิ่ม — รันผ่าน docker ได้เลย
```

---

## วิธีใช้งาน

### 1. เตรียมข้อมูล

วางไฟล์ข้อมูลราคา 1m ใน path ที่กำหนดใน config:

| Pair     | แหล่งข้อมูล | Format                   |
| -------- | ----------- | ------------------------ |
| BTC/USDT | Binance     | `btc_usdt_1m_2026.csv`   |
| BTC/THB  | Bitkub      | `btc_thb_1m_YYYY.csv.gz` |
| ETH/USDT | Binance     | `ETH_USDT-1m.feather`    |
| ETH/THB  | Bitkub      | `eth_thb_1m_YYYY.csv.gz` |

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
    'grid_levels': 82,          # จำนวน grid
    'stake':       94_786,      # เงินลงทุน
    'fees':        [0.0025, 0.00125],  # ทดสอบ 2 ค่า fee
    'slippage':    0.0005,      # 0.05%

    # Price range — เลือกอย่างใดอย่างหนึ่ง:
    # (A) auto range จาก open แท่งแรก (ไม่สมมาตรได้)
    'range_low_pct':  0.50,     # grid_min = open × (1 - 0.50) = open × 0.50
    'range_high_pct': 1.00,     # grid_max = open × (1 + 1.00) = open × 2.00
    # (B) หรือกำหนดราคาตรงๆ
    # 'grid_min':    63_190,
    # 'grid_max':    126_381,
}
```

**Price range รองรับ 2 แบบ:**

- `range_low_pct` + `range_high_pct` → auto range จาก open แท่งแรก (ไม่สมมาตรได้ เช่น -50% / +100%)
- `range_pct` → auto range สมมาตร ±range_pct
- `grid_min` + `grid_max` → กำหนดราคาตายตัว

### 3. รัน Backtest

**แบบ Docker (Freqtrade):**

```
# BTC/USDT
docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/run_btc_usdt.py

# BTC/THB
docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/run_btc_thb.py

# รวมผลและ inject เข้า HTML
docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/merge_results.py
```

**แบบ Python ตรง:**

```
python run_btc_usdt.py
python run_btc_thb.py
python merge_results.py
```

**รันหลาย pair / หลายปี แบบขนาน (เร็วขึ้น):**

```
# ใช้ ProcessPoolExecutor กระจายงานลงหลาย CPU แกน
# ปรับจำนวนแกนที่ env MAX_WORKERS (ดีฟอลต์ตามที่ตั้งใน runner)
docker compose run --rm -e MAX_WORKERS=8 --entrypoint python freqtrade /freqtrade/user_data/run_all_parallel.py
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
    'range_low_pct':  0.50,
    'range_high_pct': 1.00,
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
    "range_low_pct": 0.50,
    "range_high_pct": 1.00,
    "monthly_revenue": {"2026-01": 120.5},
    "snapshots": [{"date": "2026-01-19", "price": 93365, "grid_pct": -0.007, "bh_pct": -0.329}]
  }]
}
```

---

## ข้อจำกัด / Disclaimer

- Backtest ไม่รับประกันผลในอนาคต
- Unrealized PNL คำนวณจากราคาปิดวันสุดท้าย — เหลือเฉพาะไม้ชั้นบนสุดของ grid ที่ยังไม่มี level ขายเหนือมัน (ปกติ 1 ไม้ต่อ pair เมื่อราคาทะลุกรอบบน)
- Sell logic ขายที่ราคา open เมื่อราคา gap up ทะลุ level (conservative — ไม่ได้ขายที่ยอดแท่ง)
- ไม่รองรับ partial fill, funding rate, หรือ position limit
- ฝั่ง BUY ยังใช้ logic เดิม (ซื้อเมื่อ level อยู่ในช่วง low–high ของแท่ง) — แก้เฉพาะฝั่ง SELL

---

## License

MIT License — ใช้ต่อได้อิสระ ทั้ง personal และ commercial

---

*สร้างด้วย Python + Chart.js | ข้อมูล: Binance, Bitkub*
