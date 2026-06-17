"""
run_btc_usdt.py — BTC/USDT (Binance)
รัน: docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/run_btc_usdt.py
"""
import sys
sys.path.insert(0, '/freqtrade/user_data')
from grid_engine import run_pair, save_json

CONFIG = {
    'pair':        'BTC_USDT',
    'currency':    'USDT',
    'source':      'Binance',
    'data':        '/freqtrade/user_data/data/btc_usdt_1m_2026.csv',
    'start':       '2026-01-19',
    'end':         '2026-06-15',
    'grid_min':    63_190,
    'grid_max':    126_381,
    'grid_levels': 82,
    'stake':       94_786,        # 3,000,000 THB ÷ 31.65
    'fees':        [0.0025, 0.00125],
    'slippage':    0.0005,
}

if __name__ == '__main__':
    records = run_pair(CONFIG)
    save_json(records, '/freqtrade/user_data/results_btc_usdt.json')
