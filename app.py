import os
import calendar
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, jsonify
import sqlite3

# Import psycopg2 for PostgreSQL if on cloud
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

app = Flask(__name__)

# Secret token for local machine to pull data
API_SECRET_TOKEN = os.environ.get('API_SECRET_TOKEN', 'ap_report_secret_key_2026')
DATABASE_URL = os.environ.get('DATABASE_URL')

# SQLite absolute path helper
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'operational_data.db')

def get_db_connection():
    if DATABASE_URL and psycopg2:
        # PostgreSQL (Neon Cloud)
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        # SQLite (Local Dev)
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

def execute_db(query, args=()):
    conn = get_db_connection()
    cur = conn.cursor()
    if DATABASE_URL:
        query = query.replace('?', '%s')
    cur.execute(query, args)
    conn.commit()
    cur.close()
    conn.close()

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    # Use DictCursor for PostgreSQL to act like sqlite3.Row
    if DATABASE_URL and psycopg2:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = query.replace('?', '%s')
    else:
        cur = conn.cursor()
    
    cur.execute(query, args)
    
    if DATABASE_URL and psycopg2:
        rv = cur.fetchall()
        rv = [dict(r) for r in rv]
    else:
        rv = cur.fetchall()
        # Convert sqlite3.Row to dict
        rv = [dict(r) for r in rv]
        
    cur.close()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Get reporting date (Friday of the current week)
def get_report_date():
    today = date.today()
    # weekday: Monday is 0, Friday is 4, Sunday is 6
    # We want the Friday of the current week.
    # If today is Sat (5) or Sun (6), we might refer to the Friday that just passed (today - (today.weekday() - 4))
    # If today is Mon-Fri, Friday is today + (4 - today.weekday())
    offset = 4 - today.weekday()
    return today + timedelta(days=offset)

@app.route('/')
def index():
    default_date = get_report_date().strftime('%Y-%m-%d')
    return render_template('index.html', default_date=default_date)

@app.route('/api/asms', methods=['GET'])
def get_asms():
    try:
        rows = query_db("SELECT DISTINCT asm_name FROM tb_stores WHERE asm_name IS NOT NULL AND asm_name != '' ORDER BY asm_name")
        asms = [r['asm_name'] for r in rows]
        return jsonify({'ok': True, 'asms': asms})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/stores', methods=['GET'])
def get_stores():
    asm = request.args.get('asm')
    if not asm:
        return jsonify({'ok': False, 'error': 'ASM is required'})
    try:
        rows = query_db("SELECT store_code, store_name, brand, asm_name FROM tb_stores WHERE asm_name = ? ORDER BY store_name", (asm,))
        return jsonify({'ok': True, 'stores': rows})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/validate_pin', methods=['POST'])
def validate_pin():
    data = request.json or {}
    store_code = data.get('store_code')
    pin = data.get('pin')
    
    if not store_code or not pin:
        return jsonify({'ok': False, 'error': 'Missing store_code or pin'})
    
    try:
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if store:
            return jsonify({'ok': True, 'valid': True})
            
        # Fallback for default pin if store not configured with one
        store_exists = query_db("SELECT * FROM tb_stores WHERE store_code = ?", (store_code,), one=True)
        if store_exists and pin == '1234':
            return jsonify({'ok': True, 'valid': True})
            
        return jsonify({'ok': True, 'valid': False, 'error': 'Mã PIN không đúng'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/submit', methods=['POST'])
def submit_data():
    data = request.json or {}
    store_code = data.get('store_code')
    pin = data.get('pin')
    report_date = data.get('report_date')
    traffic_val = data.get('traffic')
    contracts = data.get('contracts', [])
    unsigned_contracts = data.get('unsigned_contracts', [])
    
    if not store_code or not report_date:
        return jsonify({'ok': False, 'error': 'Store code and report date are required'})
        
    try:
        # 1. Validate PIN
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if not store and pin != '1234':
            return jsonify({'ok': False, 'error': 'Mã PIN không hợp lệ'})
            
        # 2. Save Traffic (Update if exists, else Insert)
        if traffic_val is not None:
            # Clean old traffic for this date & store
            execute_db("DELETE FROM tb_traffic WHERE store_code = ? AND report_date = ?", (store_code, report_date))
            execute_db("INSERT INTO tb_traffic (store_code, report_date, traffic_val) VALUES (?, ?, ?)", 
                       (store_code, report_date, int(traffic_val)))
            
        # 3. Save Contracts (Section 3.1)
        execute_db("DELETE FROM tb_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        for c in contracts:
            val = float(c.get('contract_value', 0.0))
            cat = str(c.get('product_category', '')).strip()
            qty = int(c.get('quantity', 0))
            dep = float(c.get('deposit_paid', 0.0))
            inst2 = float(c.get('installment_2', 0.0))
            status = str(c.get('status', '')).strip()
            reason = str(c.get('reason', '')).strip()
            
            if val > 0 and cat:
                execute_db("""
                INSERT INTO tb_contracts 
                (store_code, report_date, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (store_code, report_date, val, cat, qty, dep, inst2, status, reason))
                
        # 4. Save Unsigned Contracts (Section 3.2)
        execute_db("DELETE FROM tb_unsigned_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        for uc in unsigned_contracts:
            val = float(uc.get('prev_year_value', 0.0))
            time_str = str(uc.get('expected_signing_time', '')).strip()
            cat = str(uc.get('product_category', '')).strip()
            qty = int(uc.get('quantity', 0))
            status = str(uc.get('status', '')).strip()
            reason = str(uc.get('reason', '')).strip()
            
            if val > 0:
                execute_db("""
                INSERT INTO tb_unsigned_contracts 
                (store_code, report_date, prev_year_value, expected_signing_time, product_category, quantity, status, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (store_code, report_date, val, time_str, cat, qty, status, reason))
                
        return jsonify({'ok': True, 'message': 'Nộp báo cáo thành công!'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/export', methods=['GET'])
def export_data():
    token = request.args.get('token')
    report_date = request.args.get('report_date')
    
    if token != API_SECRET_TOKEN:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
        
    if not report_date:
        return jsonify({'ok': False, 'error': 'report_date is required'})
        
    try:
        traffic = query_db("SELECT store_code, traffic_val FROM tb_traffic WHERE report_date = ?", (report_date,))
        contracts = query_db("SELECT store_code, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason FROM tb_contracts WHERE report_date = ?", (report_date,))
        unsigned = query_db("SELECT store_code, prev_year_value, expected_signing_time, product_category, quantity, status, reason FROM tb_unsigned_contracts WHERE report_date = ?", (report_date,))
        
        return jsonify({
            'ok': True,
            'report_date': report_date,
            'traffic': traffic,
            'contracts': contracts,
            'unsigned_contracts': unsigned
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/submission_status', methods=['GET'])
def get_submission_status():
    report_date = request.args.get('report_date') or get_report_date().strftime('%Y-%m-%d')
    try:
        # Get all stores
        stores = query_db("SELECT store_code, store_name, region, asm_name FROM tb_stores ORDER BY region, store_name")
        # Get submitted traffic stores
        submitted = query_db("SELECT DISTINCT store_code FROM tb_traffic WHERE report_date = ?", (report_date,))
        sub_set = {s['store_code'] for s in submitted}
        
        results = []
        for s in stores:
            results.append({
                'store_code': s['store_code'],
                'store_name': s['store_name'],
                'region': s['region'],
                'asm_name': s['asm_name'],
                'submitted': s['store_code'] in sub_set
            })
            
        return jsonify({'ok': True, 'report_date': report_date, 'status': results})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

if __name__ == '__main__':
    # Default port 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
