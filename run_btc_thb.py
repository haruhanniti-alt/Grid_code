"""
run_btc_thb.py — BTC/THB (Bitkub)
รัน: docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/run_btc_thb.py
"""
import sys
sys.path.insert(0, '/freqtrade/user_data')
from grid_engine import run_pair, save_json

CONFIG = {
    'pair':        'BTC_THB',
    'currency':    'THB',
    'source':      'Bitkub',
    # โหลดทุกปี (auto-detect column, กรองช่วงเองใน engine)
    'data':        '/freqtrade/user_data/data/bitkub/btc_thb_1m_*.csv.gz',
    'start':       '2026-01-19',
    'end':         '2026-06-15',
    'grid_min':    2_000_000,     # THB
    'grid_max':    4_000_000,     # THB
    'grid_levels': 82,
    'stake':       3_000_000,     # THB
    'fees':        [0.0025, 0.00125],
    'slippage':    0.0005,
}

if __name__ == '__main__':
    records = run_pair(CONFIG)
    save_json(records, '/freqtrade/user_data/results_btc_thb.json')
