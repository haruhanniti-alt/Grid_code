"""
merge_results.py — รวมผล backtest ทุก pair แล้ว inject เข้า index.html
รัน: docker compose run --rm --entrypoint python freqtrade /freqtrade/user_data/merge_results.py

อ่าน results_*.json ทุกไฟล์ → รวมเป็น RAW array → เขียนทับ const RAW ใน index.html
(badge "PENDING REAL DATA" จะถูกลบออกอัตโนมัติเมื่อมีข้อมูลจริง)
"""
import json, glob, re
from pathlib import Path

USER_DATA = Path('/freqtrade/user_data')
HTML_PATH = USER_DATA / 'index.html'

def main():
    # ── รวม JSON ทุก pair ──
    result_files = sorted(glob.glob(str(USER_DATA / 'results_*.json')))
    if not result_files:
        print("ไม่พบไฟล์ results_*.json — รัน run_btc_usdt.py และ run_btc_thb.py ก่อน")
        return

    all_records = []
    for fp in result_files:
        with open(fp, encoding='utf-8') as f:
            recs = json.load(f)
        all_records.extend(recs)
        pairs = {r['pairs'][0]['pair'] for r in recs}
        print(f"  [merge] {Path(fp).name}: {len(recs)} records  {pairs}")

    print(f"\n  รวม {len(all_records)} records")
    raw_js = json.dumps(all_records, indent=2, ensure_ascii=False)

    # ── inject เข้า HTML ──
    if not HTML_PATH.exists():
        # ถ้าไม่มี HTML ใน user_data ก็ save JSON อย่างเดียว
        out = USER_DATA / 'all_results.json'
        with open(out, 'w', encoding='utf-8') as f:
            f.write(raw_js)
        print(f"  ไม่พบ index.html — บันทึก JSON ไว้ที่ {out}")
        print("  นำ JSON นี้ไปแทน const RAW ใน HTML เอง")
        return

    html = HTML_PATH.read_text(encoding='utf-8')

    # แทน const RAW = [...]; ด้วยข้อมูลใหม่
    pattern = re.compile(r'const RAW = \n\[.*?\];', re.DOTALL)
    new_html = pattern.sub(f'const RAW = \n{raw_js};', html, count=1)

    # ลบ badge PENDING REAL DATA (มีข้อมูลจริงแล้ว)
    new_html = new_html.replace(
        "document.getElementById('dataBadge').style.display = '';",
        "document.getElementById('dataBadge').style.display = 'none';"
    )
    # เปลี่ยนข้อความ badge เป็น LIVE DATA
    new_html = new_html.replace('PENDING REAL DATA', 'REAL DATA ✓')
    new_html = new_html.replace(
        'BTC/THB data: estimated (×31.65)',
        'BTC/THB data: Bitkub (real)'
    )

    HTML_PATH.write_text(new_html, encoding='utf-8')
    print(f"  ✓ inject เข้า {HTML_PATH} แล้ว")
    print(f"  upload index.html ขึ้น GitHub ได้เลย")


if __name__ == '__main__':
    main()
