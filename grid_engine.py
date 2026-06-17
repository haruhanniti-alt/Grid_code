"""
grid_engine.py — Core Grid Backtest Engine (shared)
====================================================
ใช้ร่วมกันทุก pair (BTC/USDT, BTC/THB, future coins)
- โหลดข้อมูลแบบ auto-detect column (csv / csv.gz / feather)
- Grid logic: multi-fill High/Low, Pass1 SELL → Pass2 BUY, initial empty
- Output JSON format เดียวกันสำหรับ HTML dashboard

วิธีใช้: import แล้วเรียก run_pair(config) จาก run_*.py
"""

import pandas as pd
import numpy as np
import json, gzip, glob
from pathlib import Path

SLIPPAGE = 0.0005  # 0.05% (override ได้ใน config)


# ════════════════════════════════════════════════════════════
#  DATA LOADER — auto-detect column structure
# ════════════════════════════════════════════════════════════
def _detect_and_normalize(df):
    """
    รับ DataFrame ดิบ → คืน DataFrame ที่มี index=datetime, cols=[open,high,low,close,volume]
    รองรับหลายรูปแบบ column ที่ exchange ต่างกันใช้
    """
    df = df.copy()
    cols_lower = [str(c).lower().strip() for c in df.columns]
    df.columns = cols_lower

    # ── หา timestamp column (ให้ string date มาก่อน epoch) ──
    ts_candidates = ['datetime', 'date', 'time', 'timestamp', 'open_time', 'ts']
    ts_col = None
    for c in ts_candidates:
        if c in df.columns:
            ts_col = c
            break

    # ถ้าไม่เจอชื่อ ลองดู column แรกว่าเป็น epoch (ตัวเลขใหญ่) หรือ string วันที่ไหม
    if ts_col is None:
        first = df.columns[0]
        sample = pd.to_numeric(df[first], errors='coerce').iloc[0]
        # epoch (s หรือ ms) เป็นตัวเลขใหญ่กว่า 1e9
        if pd.notna(sample) and sample > 1e9:
            ts_col = first
        else:
            try:
                parsed = pd.to_datetime(df[first].iloc[:5], errors='coerce')
                if parsed.notna().all():
                    ts_col = first
            except Exception:
                pass

    if ts_col is None:
        # สมมติ index เป็น timestamp อยู่แล้ว
        df.index = pd.to_datetime(df.index)
    else:
        # แปลง epoch → datetime (auto detect s / ms / us)
        col = pd.to_numeric(df[ts_col], errors='coerce')
        if col.notna().all() and col.iloc[0] > 1e9:
            mx = col.max()
            if   mx > 1e17: unit = 'ns'   # nanoseconds (19 หลัก)
            elif mx > 1e14: unit = 'us'   # microseconds (16 หลัก)
            elif mx > 1e11: unit = 'ms'   # milliseconds (13 หลัก)
            else:           unit = 's'    # seconds (10 หลัก)
            df.index = pd.to_datetime(col, unit=unit)
        else:
            df.index = pd.to_datetime(df[ts_col])
        df = df.drop(columns=[ts_col])

    # ── ลบ time columns อื่นที่เหลือ (เช่นมีทั้ง datetime + timestamp) ──
    for leftover in ['datetime', 'date', 'time', 'timestamp', 'open_time', 'ts', 'exchange']:
        if leftover in df.columns:
            df = df.drop(columns=[leftover])

    # ── map OHLCV columns ──
    rename = {}
    for c in df.columns:
        if c in ('open', 'o'):              rename[c] = 'open'
        elif c in ('high', 'h'):            rename[c] = 'high'
        elif c in ('low', 'l'):             rename[c] = 'low'
        elif c in ('close', 'c', 'last'):   rename[c] = 'close'
        elif c in ('volume', 'vol', 'v', 'basevolume', 'base_volume'): rename[c] = 'volume'
    df = df.rename(columns=rename)

    # ถ้ายังไม่ครบ ใช้ positional (เผื่อ header เป็นเลข index)
    needed = ['open', 'high', 'low', 'close']
    if not all(n in df.columns for n in needed):
        ncol = df.shape[1]
        positional = ['open', 'high', 'low', 'close', 'volume'][:ncol]
        df.columns = positional + list(df.columns[len(positional):])

    # เก็บเฉพาะที่ใช้
    keep = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in df.columns]
    df = df[keep]
    if 'volume' not in df.columns:
        df['volume'] = 0.0

    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    return df


def load_data(path_pattern, start, end):
    """
    โหลดไฟล์ (รองรับ glob หลายไฟล์, csv/csv.gz/feather) แล้วกรองช่วงเวลา
    path_pattern: str หรือ list ของ path (รองรับ wildcard)
    """
    patterns = [path_pattern] if isinstance(path_pattern, str) else list(path_pattern)
    files = []
    for pat in patterns:
        files.extend(sorted(glob.glob(pat)))
    if not files:
        raise FileNotFoundError(f"ไม่พบไฟล์: {patterns}")

    start_dt = pd.Timestamp(start)
    end_dt   = pd.Timestamp(end) + pd.Timedelta(days=1)

    dfs = []
    for fp in files:
        fp = Path(fp)
        print(f"  [load] {fp.name} ...", end="", flush=True)
        try:
            if fp.suffix == '.feather':
                raw = pd.read_feather(fp)
            elif fp.name.endswith('.csv.gz'):
                with gzip.open(fp, 'rt') as f:
                    raw = pd.read_csv(f)
            else:
                raw = pd.read_csv(fp)

            df = _detect_and_normalize(raw)
            df = df[(df.index >= start_dt) & (df.index < end_dt)]
            if len(df):
                dfs.append(df)
                print(f" {len(df):,} rows")
            else:
                print(" (out of range)")
        except Exception as e:
            print(f" ERROR: {e}")

    if not dfs:
        raise ValueError(f"ไม่มีข้อมูลในช่วง {start} → {end}")

    df = pd.concat(dfs).sort_index()
    df = df[~df.index.duplicated(keep='first')]
    print(f"  Total: {len(df):,} rows ({df.index[0]} → {df.index[-1]})")
    return df


# ════════════════════════════════════════════════════════════
#  GRID BACKTEST CORE
# ════════════════════════════════════════════════════════════
def backtest(df, stake, fee, grid_min, grid_max, grid_levels,
             slippage=SLIPPAGE):
    """
    Grid backtest: multi-fill, Pass1 SELL → Pass2 BUY, ทุก slot เริ่มว่าง
    คืน dict ของ metrics + snapshots รายวัน
    """
    step = (grid_max - grid_min) / (grid_levels - 1)
    levels = np.array([grid_min + i * step for i in range(grid_levels)])
    stake_per_slot = stake / grid_levels

    ref_price = float(df['open'].iloc[0])
    wallet = float(stake)
    slots = np.zeros(grid_levels, dtype=bool)
    slot_cost = np.zeros(grid_levels)
    slot_qty  = np.zeros(grid_levels)

    trades = []
    daily_snap = []
    prev_date = None

    for ts, row in df.iterrows():
        hi, lo = row['high'], row['low']
        date_str = ts.strftime("%Y-%m-%d")

        # ── Pass 1: SELL ──
        for i in range(grid_levels - 1):
            sell_level = levels[i + 1]
            if slots[i] and lo <= sell_level <= hi:
                sp = sell_level * (1 - slippage)
                revenue = slot_qty[i] * sp
                fee_paid = revenue * fee
                realized = revenue - fee_paid - slot_cost[i]
                wallet += revenue - fee_paid
                trades.append({'date': date_str, 'side': 'SELL', 'price': sp,
                               'qty': slot_qty[i], 'profit': realized, 'fee': fee_paid})
                slots[i] = False; slot_cost[i] = 0; slot_qty[i] = 0

        # ── Pass 2: BUY ──
        for i in range(grid_levels):
            buy_level = levels[i]
            if not slots[i] and lo <= buy_level <= hi:
                bp = buy_level * (1 + slippage)
                cost = stake_per_slot
                if wallet >= cost:
                    qty = (cost * (1 - fee)) / bp
                    fee_paid = cost * fee
                    wallet -= cost
                    slots[i] = True; slot_cost[i] = cost; slot_qty[i] = qty
                    trades.append({'date': date_str, 'side': 'BUY', 'price': bp,
                                   'qty': qty, 'profit': 0, 'fee': fee_paid})

        # ── Daily snapshot ──
        if date_str != prev_date:
            cp = row['close']
            held_val = sum(slot_qty[i] * cp for i in range(grid_levels) if slots[i])
            total_equity = wallet + held_val
            grid_pct = (total_equity - stake) / stake * 100
            bh_pct   = (cp - ref_price) / ref_price * 100
            daily_snap.append({'date': date_str, 'price': round(cp, 2),
                               'grid_pct': round(grid_pct, 3), 'bh_pct': round(bh_pct, 3)})
            prev_date = date_str

    # ── Summary ──
    sells = [t for t in trades if t['side'] == 'SELL']
    last_price = float(df['close'].iloc[-1])
    coin_held = int(slots.sum())
    held_val  = sum(slot_qty[i] * last_price for i in range(grid_levels) if slots[i])
    held_cost = sum(slot_cost[i] for i in range(grid_levels) if slots[i])
    unrealized = held_val - held_cost
    total_profit = sum(t['profit'] for t in sells)
    total_fee = sum(t['fee'] for t in trades)
    final_equity = wallet + held_val
    net_pnl = total_profit + unrealized

    days = (df.index[-1] - df.index[0]).days + 1
    years = days / 365.25
    months_actual = days / 30.44

    monthly = {}
    for t in sells:
        m = t['date'][:7]
        monthly[m] = monthly.get(m, 0) + t['profit']

    total_vol = sum(t['qty'] * t['price'] for t in trades)
    spacing_pct = step / grid_min * 100

    return {
        "stake_total": stake, "fee": fee,
        "ref_price": round(ref_price, 2), "last_price": round(last_price, 2),
        "grid_min": grid_min, "grid_max": grid_max, "grid_step": round(step, 2),
        "grid_levels": grid_levels, "spacing_pct": round(spacing_pct, 4),
        "profit_per_grid": round(spacing_pct * 2 * fee * 100, 3),
        "actual_min": round(float(df['low'].min()), 2),
        "actual_max": round(float(df['high'].max()), 2),
        "total_trades": len(sells),
        "trades_per_year": round(len(sells) / years) if years else 0,
        "trades_per_month": round(len(sells) / months_actual, 1) if months_actual else 0,
        "wins": len(sells), "win_pct": 100.0,
        "total_profit": round(total_profit, 2),
        "profit_pct": round(total_profit / stake * 100, 2),
        "apy": round((total_profit / stake) / years * 100, 2) if years else 0,
        "total_fee": round(total_fee, 2),
        "volume_per_month": round(total_vol / months_actual, 2) if months_actual else 0,
        "revenue_per_month": round(total_profit / months_actual, 2) if months_actual else 0,
        "total_volume": round(total_vol, 2),
        "final_wallet": round(wallet, 2),
        "coin_slots_held": coin_held,
        "cost_of_held": round(held_cost, 2),
        "unrealized_val": round(held_val, 2),
        "unrealized_pnl": round(unrealized, 2),
        "net_pnl": round(net_pnl, 2),
        "net_pnl_pct": round(net_pnl / stake * 100, 2),
        "final_equity": round(final_equity, 2),
        "monthly_revenue": {k: round(v, 2) for k, v in sorted(monthly.items())},
        "snapshots": daily_snap,
    }


# ════════════════════════════════════════════════════════════
#  RUN ONE PAIR (เรียกจาก run_*.py)
# ════════════════════════════════════════════════════════════
def run_pair(config):
    """
    config = {
      'pair': 'BTC_USDT', 'currency': 'USDT', 'source': 'Binance',
      'data': '/path/to/*.csv', 'start': '2026-01-19', 'end': '2026-06-15',
      'grid_min': 63190, 'grid_max': 126381, 'grid_levels': 82,
      'stake': 94786, 'fees': [0.0025, 0.00125], 'slippage': 0.0005,
    }
    คืน list ของ records (1 record ต่อ fee)
    """
    print(f"\n{'='*55}")
    print(f"  {config['pair']}  ({config.get('source','?')})")
    print(f"  {config['start']} → {config['end']}")
    print(f"  Range: {config['grid_min']:,} → {config['grid_max']:,} {config.get('currency','')}")
    print(f"  Stake: {config['stake']:,} {config.get('currency','')}  ·  Grids: {config['grid_levels']}")
    print(f"{'='*55}")

    df = load_data(config['data'], config['start'], config['end'])

    records = []
    for fee in config['fees']:
        print(f"\n  Running fee={fee*100:.3f}% ...")
        res = backtest(df, config['stake'], fee,
                       config['grid_min'], config['grid_max'], config['grid_levels'],
                       config.get('slippage', SLIPPAGE))
        res['pair'] = config['pair']
        res['currency'] = config.get('currency', 'USDT')
        res['source'] = config.get('source', '')

        records.append({
            "fee": fee, "stake": config['stake'],
            "currency": config.get('currency', 'USDT'),
            "source": config.get('source', ''),
            "backtest_start": config['start'], "backtest_end": config['end'],
            "total_trades": res['total_trades'],
            "total_profit": res['total_profit'],
            "profit_pct": res['profit_pct'],
            "total_fee": res['total_fee'],
            "revenue_per_month": res['revenue_per_month'],
            "pairs": [res],
        })

        print(f"    Trades={res['total_trades']}  APY={res['apy']}%  "
              f"GridProfit={res['total_profit']:,.0f}  "
              f"Net={res['net_pnl']:,.0f} ({res['net_pnl_pct']}%)  "
              f"Slots={res['coin_slots_held']}/{config['grid_levels']}")

    return records


def save_json(records, out_path):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved → {out_path}")
