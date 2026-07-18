import os
import calendar
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import threading
import urllib.request
import urllib.parse
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io
import pandas as pd

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

# Get reporting date (Friday of the current week or previous week if early in the week)
def get_report_date():
    today = date.today()
    if today.weekday() >= 4: # Friday (4), Saturday (5), Sunday (6)
        offset = 4 - today.weekday()
    else: # Monday (0), Tuesday (1), Wednesday (2), Thursday (3)
        offset = -3 - today.weekday()
    return today + timedelta(days=offset)

def async_sync_and_alert(store_code, report_date, support_requests):
    def worker():
        try:
            store_info = query_db("SELECT * FROM tb_stores WHERE store_code = ?", (store_code,), one=True)
            store_name = store_info['store_name'] if store_info else store_code
            asm_name = store_info['asm_name'] if store_info else "QLKD / ASM"
        except Exception as e:
            print(f"Error querying store info in async worker: {e}")
            store_name = store_code
            asm_name = "QLKD / ASM"
            
        for sr in support_requests:
            cat = str(sr.get('category', '')).strip()
            pri = str(sr.get('priority', 'Trung bình')).strip()
            item = str(sr.get('issue_item', '')).strip()
            dl = str(sr.get('deadline', '')).strip()
            
            if not item:
                continue
                
            # 1. Sync to Google Sheets if APPS_SCRIPT_URL is configured
            gs_url = os.environ.get('GOOGLE_SHEET_WEBAPP_URL')
            if gs_url:
                payload = {
                    'store_code': store_code,
                    'store_name': store_name,
                    'asm_name': asm_name,
                    'report_date': report_date,
                    'category': cat,
                    'priority': pri,
                    'issue_item': item,
                    'deadline': dl,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                try:
                    req = urllib.request.Request(
                        gs_url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'},
                        method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        response.read()
                    print(f"✅ Synced support request for {store_code} to Google Sheets.")
                except Exception as e:
                    print(f"❌ Error syncing to Google Sheets: {e}")
            else:
                print(f"ℹ️ Google Sheets URL not set. Support request logged locally: {item}")
                
            # 2. Send email via SMTP if user/pass is configured
            smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('SMTP_PORT', 587))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASSWORD')
            
            email_asm = os.environ.get('ALERT_EMAIL_ASM', 'asm_khoi@anphuoc.com.vn')
            email_tech = os.environ.get('ALERT_EMAIL_TECH', 'technical_support@anphuoc.com.vn')
            
            # Format Email Content
            subject = f"[Retail Commander - Su Co] Cua hang {store_name} yeu cau ho tro"
            body = f"""Kinh gui ASM {asm_name} va bo phan Ky thuat,

He thong Retail Commander vua ghi nhan yeu cau ho tro ky thuat tu cua hang:
- Cua hang: {store_name} ({store_code})
- ASM quan ly: {asm_name}
- Ky bao cao: {report_date}
- Phan loai su co: {cat}
- Muc do uu tien: {pri}
- Han xu ly mong muon: {dl}

Noi dung chi tiet su co:
--------------------------------------------------
{item}
--------------------------------------------------

Vui long kiem tra va xu ly su co kip thoi.

Tran trong,
He thong Tu dong hoa Retail Commander."""

            if smtp_user and smtp_pass:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_user
                    msg['To'] = f"{email_asm}, {email_tech}"
                    msg['Subject'] = subject
                    msg.attach(MIMEText(body, 'plain', 'utf-8'))
                    
                    server = smtplib.SMTP(smtp_host, smtp_port)
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [email_asm, email_tech], msg.as_string())
                    server.quit()
                    print(f"✅ SMTP Email sent successfully to {email_asm}, {email_tech}")
                except Exception as e:
                    print(f"❌ SMTP Error: {e}")
            else:
                # Fallback to local files for testing
                print("ℹ️ SMTP credentials not set. Saving email content to local file.")
                sent_dir = r"C:\All_Report\8_RETAIL_COMMANDER\tools\web_portal\sent_emails"
                os.makedirs(sent_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"incident_{store_code}_{timestamp}.txt"
                filepath = os.path.join(sent_dir, filename)
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"Subject: {subject}\n")
                        f.write(f"To: {email_asm}, {email_tech}\n")
                        f.write(f"SMTP Host: {smtp_host}:{smtp_port}\n")
                        f.write("="*50 + "\n")
                        f.write(body)
                    print(f"✅ Local email draft saved to: {filepath}")
                except Exception as e:
                    print(f"❌ Error writing local email file: {e}")

    threading.Thread(target=worker, daemon=True).start()

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
    store_code = request.args.get('store_code')
    try:
        if store_code:
            row = query_db("SELECT store_code, store_name, brand, asm_name FROM tb_stores WHERE store_code = ?", (store_code,), one=True)
            return jsonify({'ok': True, 'store': row})
        
        if not asm or asm == 'all' or asm == 'ADMIN':
            rows = query_db("SELECT store_code, store_name, brand, asm_name FROM tb_stores ORDER BY store_name")
        else:
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
    
    # Handle Admin validation
    if store_code == 'ADMIN':
        master_pin = os.environ.get('MASTER_PIN', '8888')
        if pin == master_pin:
            return jsonify({'ok': True, 'valid': True, 'role': 'admin'})
        return jsonify({'ok': True, 'valid': False, 'error': 'Mã PIN ADMIN không đúng'})
        
    # Handle ASM validation
    if store_code.startswith("ASM_"):
        asm_name = store_code[4:]
        try:
            asm = query_db("SELECT * FROM tb_asms WHERE asm_name = ?", (asm_name,), one=True)
            valid_pin = asm['passcode'] if asm else '9999'
            if pin == valid_pin:
                return jsonify({'ok': True, 'valid': True, 'role': 'asm', 'asm_name': asm_name})
            return jsonify({'ok': True, 'valid': False, 'error': 'Mã PIN ASM không đúng'})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)})
    
    try:
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if store:
            return jsonify({'ok': True, 'valid': True, 'role': 'store'})
            
        # Fallback for default pin if store not configured with one
        store_exists = query_db("SELECT * FROM tb_stores WHERE store_code = ?", (store_code,), one=True)
        if store_exists and pin == '1234':
            return jsonify({'ok': True, 'valid': True, 'role': 'store'})
            
        return jsonify({'ok': True, 'valid': False, 'error': 'Mã PIN không đúng'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ──────────────────────────────────────────────────────────────────────────────
# NEW API: DAILY TRAFFIC ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/get_daily_traffic', methods=['GET'])
def get_daily_traffic():
    store_code = request.args.get('store_code')
    year = request.args.get('year')
    month = request.args.get('month')
    pin = request.args.get('pin')
    
    if not store_code or not year or not month or not pin:
        return jsonify({'ok': False, 'error': 'Thiếu tham số bắt buộc'})
        
    try:
        # Validate PIN
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if not store and pin != '1234':
            return jsonify({'ok': False, 'error': 'Mã PIN không đúng'})
            
        # Query daily traffic and bills for this store and month
        prefix = f"{year}-{int(month):02d}-%"
        rows = query_db("SELECT traffic_date, traffic_val, bills_val, company_online_bills, store_online_bills FROM tb_traffic WHERE store_code = ? AND traffic_date LIKE ?", (store_code, prefix))
        
        traffic_map = {
            r['traffic_date']: {
                'traffic': r['traffic_val'],
                'bills': r['bills_val'] or 0,
                'company_online_bills': r['company_online_bills'] or 0,
                'store_online_bills': r['store_online_bills'] or 0
            } for r in rows
        }
        return jsonify({'ok': True, 'traffic': traffic_map})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/submit_daily_traffic', methods=['POST'])
def submit_daily_traffic():
    data = request.json or {}
    store_code = data.get('store_code')
    pin = data.get('pin')
    traffic_data = data.get('traffic_data', {})
    
    if not store_code or not pin:
        return jsonify({'ok': False, 'error': 'Thiếu store_code hoặc pin'})
        
    try:
        # Validate PIN
        master_pin = os.environ.get('MASTER_PIN', '8888')
        if pin != master_pin:
            store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
            if not store and pin != '1234':
                return jsonify({'ok': False, 'error': 'Mã PIN không đúng'})
            
        # Upsert each day
        for date_str, day_data in traffic_data.items():
            traffic_str = day_data.get('traffic', '') if isinstance(day_data, dict) else ''
            bills_str = day_data.get('bills', '') if isinstance(day_data, dict) else ''
            co_str = day_data.get('company_online_bills', '') if isinstance(day_data, dict) else ''
            so_str = day_data.get('store_online_bills', '') if isinstance(day_data, dict) else ''
            
            if (traffic_str is None or str(traffic_str).strip() == '') and (bills_str is None or str(bills_str).strip() == ''):
                # Delete record if cleared
                execute_db("DELETE FROM tb_traffic WHERE store_code = ? AND traffic_date = ?", (store_code, date_str))
            else:
                try:
                    trf_val = int(traffic_str) if (traffic_str is not None and str(traffic_str).strip() != '') else 0
                    bil_val = int(bills_str) if (bills_str is not None and str(bills_str).strip() != '') else 0
                    co_val = int(co_str) if (co_str is not None and str(co_str).strip() != '') else 0
                    so_val = int(so_str) if (so_str is not None and str(so_str).strip() != '') else 0
                    
                    if trf_val < 0 or bil_val < 0 or co_val < 0 or so_val < 0:
                        continue
                    if DATABASE_URL:
                        execute_db("""
                        INSERT INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val, company_online_bills, store_online_bills)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT (store_code, traffic_date) DO UPDATE SET 
                            traffic_val = EXCLUDED.traffic_val,
                            bills_val = EXCLUDED.bills_val,
                            company_online_bills = EXCLUDED.company_online_bills,
                            store_online_bills = EXCLUDED.store_online_bills
                        """, (store_code, date_str, trf_val, bil_val, co_val, so_val))
                    else:
                        execute_db("""
                        INSERT OR REPLACE INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val, company_online_bills, store_online_bills)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (store_code, date_str, trf_val, bil_val, co_val, so_val))
                except ValueError:
                    continue
                    
        return jsonify({'ok': True, 'message': 'Đã cập nhật Traffic thành công!'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ──────────────────────────────────────────────────────────────────────────────
# NEW API: OPERATIONAL DETAILS (EDIT MECHANISM)
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/get_operational_report', methods=['GET'])
def get_operational_report():
    store_code = request.args.get('store_code')
    report_date = request.args.get('report_date')
    pin = request.args.get('pin')
    
    if not store_code or not report_date or not pin:
        return jsonify({'ok': False, 'error': 'Thiếu tham số bắt buộc'})
        
    try:
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if not store and pin != '1234':
            return jsonify({'ok': False, 'error': 'Mã PIN không đúng'})
            
        # Query contracts (Section 3.1)
        contracts = query_db("SELECT contract_number, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason FROM tb_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        
        # Query unsigned contracts (Section 3.2)
        unsigned = query_db("SELECT prev_year_value, expected_signing_time, product_category, quantity, status, reason FROM tb_unsigned_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        
        # Query operational details (Section 4.1 - 4.4)
        details = query_db("SELECT * FROM tb_operational_details WHERE store_code = ? AND report_date = ?", (store_code, report_date), one=True)
        
        # Query support requests (Section 4.5)
        support = query_db("SELECT category, priority, issue_item, deadline, person_in_charge FROM tb_support_requests WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        
        # Get traffic and bills for this specific Friday (report_date) if nộp in weekly
        traffic_row = query_db("SELECT traffic_val, bills_val, company_online_bills, store_online_bills FROM tb_traffic WHERE store_code = ? AND traffic_date = ?", (store_code, report_date), one=True)
        traffic_val = traffic_row['traffic_val'] if traffic_row else ''
        bills_val = traffic_row['bills_val'] if traffic_row else ''
        co_val = traffic_row['company_online_bills'] if traffic_row else 0
        so_val = traffic_row['store_online_bills'] if traffic_row else 0
        
        return jsonify({
            'ok': True,
            'traffic': traffic_val,
            'bills': bills_val,
            'company_online_bills': co_val,
            'store_online_bills': so_val,
            'contracts': contracts,
            'unsigned_contracts': unsigned,
            'details': details or {},
            'support_requests': support
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ──────────────────────────────────────────────────────────────────────────────
# SUBMIT & EXPORT ENHANCEMENTS (INCLUDES PART 4 & 5)
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/submit', methods=['POST'])
def submit_data():
    data = request.json or {}
    store_code = data.get('store_code')
    pin = data.get('pin')
    report_date = data.get('report_date')
    traffic_val = data.get('traffic')
    bills_val = data.get('bills')
    contracts = data.get('contracts', [])
    unsigned_contracts = data.get('unsigned_contracts', [])
    details = data.get('details', {})
    support_requests = data.get('support_requests', [])
    
    if not store_code or not report_date:
        return jsonify({'ok': False, 'error': 'Store code and report date are required'})
        
    try:
        # 1. Validate PIN
        master_pin = os.environ.get('MASTER_PIN', '8888')
        if pin != master_pin:
            store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
            if not store and pin != '1234':
                return jsonify({'ok': False, 'error': 'Mã PIN không hợp lệ'})
            
        # 2. Save Traffic (Save for report_date as daily record)
        if traffic_val is not None and str(traffic_val).strip() != '':
            execute_db("DELETE FROM tb_traffic WHERE store_code = ? AND traffic_date = ?", (store_code, report_date))
            trf_int = int(traffic_val)
            bil_int = int(bills_val) if (bills_val is not None and str(bills_val).strip() != '') else 0
            co_int = int(data.get('company_online_bills', 0))
            so_int = int(data.get('store_online_bills', 0))
            
            if DATABASE_URL:
                execute_db("""
                INSERT INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val, company_online_bills, store_online_bills) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (store_code, traffic_date) DO UPDATE SET 
                    traffic_val = EXCLUDED.traffic_val,
                    bills_val = EXCLUDED.bills_val,
                    company_online_bills = EXCLUDED.company_online_bills,
                    store_online_bills = EXCLUDED.store_online_bills
                """, (store_code, report_date, trf_int, bil_int, co_int, so_int))
            else:
                execute_db("INSERT OR REPLACE INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val, company_online_bills, store_online_bills) VALUES (?, ?, ?, ?, ?, ?)", 
                           (store_code, report_date, trf_int, bil_int, co_int, so_int))
            
        # 3. Save Contracts (Section 3.1)
        execute_db("DELETE FROM tb_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        for c in contracts:
            contract_num = str(c.get('contract_number', '')).strip() or 'Đang GD'
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
                (store_code, report_date, contract_number, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (store_code, report_date, contract_num, val, cat, qty, dep, inst2, status, reason))
                
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
                
        # 5. Save Operational Details (Section 4.1 - 4.4)
        execute_db("DELETE FROM tb_operational_details WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        execute_db("""
        INSERT INTO tb_operational_details (
            store_code, report_date, 
            op_open_close_status, op_open_close_note,
            op_uniform_status, op_uniform_note,
            op_greet_status, op_greet_note,
            op_feedback_status, op_feedback_note,
            op_other_status, op_other_note,
            hr_target, hr_actual, hr_guard,
            hr_resigned_note, hr_leave_note, hr_absent_note,
            inv_stock_status, inv_info_goods, inv_return_warehouse, inv_proposal,
            market_product_feedback, market_missing_products, market_competitors, market_other_feedback
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """, (
            store_code, report_date,
            details.get('op_open_close_status', 'Đạt'), details.get('op_open_close_note', ''),
            details.get('op_uniform_status', 'Đạt'), details.get('op_uniform_note', ''),
            details.get('op_greet_status', 'Đạt'), details.get('op_greet_note', ''),
            details.get('op_feedback_status', 'Đạt'), details.get('op_feedback_note', ''),
            details.get('op_other_status', 'Đạt'), details.get('op_other_note', ''),
            int(details.get('hr_target', 0) or 0), int(details.get('hr_actual', 0) or 0), int(details.get('hr_guard', 0) or 0),
            details.get('hr_resigned_note', ''), details.get('hr_leave_note', ''), details.get('hr_absent_note', ''),
            details.get('inv_stock_status', ''), details.get('inv_info_goods', ''), details.get('inv_return_warehouse', ''), details.get('inv_proposal', ''),
            details.get('market_product_feedback', ''), details.get('market_missing_products', ''), details.get('market_competitors', ''), details.get('market_other_feedback', '')
        ))
        
        # 6. Save Support Requests (Section 4.5)
        execute_db("DELETE FROM tb_support_requests WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        for sr in support_requests:
            cat = str(sr.get('category', '')).strip()
            pri = str(sr.get('priority', 'Trung bình')).strip()
            item = str(sr.get('issue_item', '')).strip()
            dl = str(sr.get('deadline', '')).strip()
            pic = str(sr.get('person_in_charge', 'QLKD / ASM')).strip()
            
            if item:
                execute_db("""
                INSERT INTO tb_support_requests (store_code, report_date, category, priority, issue_item, deadline, person_in_charge)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (store_code, report_date, cat, pri, item, dl, pic))
        
        if support_requests:
            async_sync_and_alert(store_code, report_date, support_requests)
            
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
        # Pull daily traffic records for the week ending on report_date (Saturday to Friday)
        # We also pull all daily traffic for this month to calculate MTD
        rep_dt = datetime.strptime(report_date, '%Y-%m-%d').date()
        week_start = rep_dt - timedelta(days=6)
        month_start = rep_dt.replace(day=1)
        
        daily_traffic = query_db("""
            SELECT store_code, traffic_date, traffic_val, bills_val FROM tb_traffic 
            WHERE traffic_date >= ? AND traffic_date <= ?
        """, (month_start.strftime('%Y-%m-%d'), report_date))
        
        contracts = query_db("SELECT store_code, contract_number, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason FROM tb_contracts WHERE report_date = ?", (report_date,))
        unsigned = query_db("SELECT store_code, prev_year_value, expected_signing_time, product_category, quantity, status, reason FROM tb_unsigned_contracts WHERE report_date = ?", (report_date,))
        details = query_db("SELECT * FROM tb_operational_details WHERE report_date = ?", (report_date,))
        support = query_db("SELECT store_code, category, priority, issue_item, deadline, person_in_charge FROM tb_support_requests WHERE report_date = ?", (report_date,))
        
        return jsonify({
            'ok': True,
            'report_date': report_date,
            'daily_traffic': daily_traffic,
            'contracts': contracts,
            'unsigned_contracts': unsigned,
            'operational_details': details,
            'support_requests': support
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/submission_status', methods=['GET'])
def get_submission_status():
    report_date = request.args.get('report_date') or get_report_date().strftime('%Y-%m-%d')
    asm = request.args.get('asm')
    try:
        # Get stores (filtered by ASM if provided)
        if asm:
            stores = query_db("SELECT store_code, store_name, region, asm_name FROM tb_stores WHERE asm_name = ? ORDER BY region, store_name", (asm,))
        else:
            stores = query_db("SELECT store_code, store_name, region, asm_name FROM tb_stores ORDER BY region, store_name")
            
        # Get submitted operational details
        submitted = query_db("SELECT DISTINCT store_code FROM tb_operational_details WHERE report_date = ?", (report_date,))
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

@app.route('/api/get_support_requests', methods=['GET'])
def get_support_requests():
    report_date = request.args.get('report_date') or get_report_date().strftime('%Y-%m-%d')
    asm = request.args.get('asm')
    try:
        if asm:
            rows = query_db("""
                SELECT s.store_name, r.category, r.priority, r.issue_item, r.deadline, r.person_in_charge 
                FROM tb_support_requests r
                JOIN tb_stores s ON r.store_code = s.store_code
                WHERE r.report_date = ? AND s.asm_name = ?
                ORDER BY s.store_name, r.priority DESC
            """, (report_date, asm))
        else:
            rows = query_db("""
                SELECT s.store_name, r.category, r.priority, r.issue_item, r.deadline, r.person_in_charge 
                FROM tb_support_requests r
                JOIN tb_stores s ON r.store_code = s.store_code
                WHERE r.report_date = ?
                ORDER BY s.store_name, r.priority DESC
            """, (report_date,))
            
        results = []
        for r in rows:
            results.append({
                'store_name': r['store_name'],
                'category': r['category'],
                'priority': r['priority'],
                'issue_item': r['issue_item'],
                'deadline': r['deadline'],
                'person_in_charge': r['person_in_charge']
            })
        return jsonify({'ok': True, 'requests': results})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ──────────────────────────────────────────────────────────────────────────────
# NEW API: ASM TRAFFIC REMINDERS SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/asm_traffic_summary', methods=['GET'])
def get_asm_traffic_summary():
    asm = request.args.get('asm')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if not start_date_str or not end_date_str:
        return jsonify({'ok': False, 'error': 'Thiếu tham số bắt buộc'})
        
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Limit end_date to yesterday
        yesterday = date.today() - timedelta(days=1)
        if end_date > yesterday:
            end_date = yesterday
            
        # Get list of all dates in range
        delta = end_date - start_date
        all_dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(delta.days + 1)]
        
        # Get all stores for this ASM or all stores
        if asm and asm != 'ALL' and asm != 'undefined' and asm != '':
            stores = query_db("SELECT store_code, store_name FROM tb_stores WHERE asm_name = ? ORDER BY store_name", (asm,))
        else:
            stores = query_db("SELECT store_code, store_name FROM tb_stores ORDER BY store_name")
        
        # Get all traffic entries in range
        rows = query_db("""
            SELECT store_code, traffic_date FROM tb_traffic 
            WHERE traffic_date >= ? AND traffic_date <= ?
        """, (start_date_str, end_date_str))
        
        # Map store_code -> set of filled dates
        filled_map = {}
        for r in rows:
            code = r['store_code']
            dt = r['traffic_date']
            if code not in filled_map:
                filled_map[code] = set()
            filled_map[code].add(dt)
            
        results = []
        for s in stores:
            code = s['store_code']
            name = s['store_name']
            filled = filled_map.get(code, set())
            
            missing_dates = [d for d in all_dates if d not in filled]
            # Convert YYYY-MM-DD to DD/MM
            missing_formatted = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in missing_dates]
            
            results.append({
                'store_code': code,
                'store_name': name,
                'total_filled': len(filled),
                'total_required': len(all_dates),
                'missing_dates': missing_formatted
            })
            
        return jsonify({'ok': True, 'summary': results})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/get_all_passcodes', methods=['GET'])
def get_all_passcodes():
    admin_pin = request.args.get('admin_pin')
    master_pin = os.environ.get('MASTER_PIN', '8888')
    if admin_pin != master_pin:
        return jsonify({'ok': False, 'error': 'Không có quyền truy cập'}), 401
        
    try:
        asms = query_db("SELECT asm_name, passcode FROM tb_asms ORDER BY asm_name")
        stores = query_db("SELECT store_code, store_name, asm_name, passcode FROM tb_stores ORDER BY store_code")
        return jsonify({'ok': True, 'asms': asms, 'stores': stores})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/update_passcode', methods=['POST'])
def update_passcode():
    data = request.json or {}
    user_type = data.get('user_type') # 'store' or 'asm'
    user_id = data.get('user_id') # store_code or asm_name
    new_pin = data.get('new_pin')
    old_pin = data.get('old_pin')
    admin_pin = data.get('admin_pin')
    
    if not user_type or not user_id or not new_pin:
        return jsonify({'ok': False, 'error': 'Thiếu tham số bắt buộc'})
        
    new_pin = str(new_pin).strip()
    if len(new_pin) < 4:
        return jsonify({'ok': False, 'error': 'Mã PIN phải có ít nhất 4 ký tự'})
        
    master_pin = os.environ.get('MASTER_PIN', '8888')
    is_admin = (admin_pin == master_pin)
    
    try:
        if user_type == 'asm':
            # Check authorization if not admin
            if not is_admin:
                asm = query_db("SELECT * FROM tb_asms WHERE asm_name = ? AND passcode = ?", (user_id, old_pin), one=True)
                if not asm:
                    return jsonify({'ok': False, 'error': 'Mật khẩu cũ không chính xác'})
            
            # Update
            execute_db("UPDATE tb_asms SET passcode = ? WHERE asm_name = ?", (new_pin, user_id))
            return jsonify({'ok': True, 'message': 'Đã đổi mã PIN ASM thành công!'})
            
        elif user_type == 'store':
            # Check authorization if not admin
            if not is_admin:
                store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (user_id, old_pin), one=True)
                # Fallback default PIN
                if not store and old_pin == '1234':
                    store_exists = query_db("SELECT * FROM tb_stores WHERE store_code = ?", (user_id,), one=True)
                    if store_exists:
                        store = store_exists
                if not store:
                    return jsonify({'ok': False, 'error': 'Mật khẩu cũ không chính xác'})
            
            # Update
            execute_db("UPDATE tb_stores SET passcode = ? WHERE store_code = ?", (new_pin, user_id))
            return jsonify({'ok': True, 'message': 'Đã đổi mã PIN cửa hàng thành công!'})
            
        else:
            return jsonify({'ok': False, 'error': 'Loại người dùng không hợp lệ'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

def style_sheet(ws, title, subtitle, date_range_str, role_str):
    # Enable grid lines explicitly
    ws.views.sheetView[0].showGridLines = True
    
    # 1. Title Block (Rows 1 to 3)
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    navy_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    
    # Merge cells for Title on Row 1
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ws.max_column)
    title_cell = ws.cell(row=1, column=1)
    title_cell.value = title.upper()
    title_cell.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    title_cell.fill = navy_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28
    
    # Merge cells for Subtitle on Row 2 (Date Range & Target)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ws.max_column)
    sub_cell = ws.cell(row=2, column=1)
    sub_cell.value = f"Tuần báo cáo: {date_range_str}  |  Đối tượng: {role_str}"
    sub_cell.font = Font(name="Segoe UI", size=9, italic=True, color="FFFFFF")
    sub_cell.fill = navy_fill
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18
    
    # Merge cells for Metadata on Row 3 (Export info)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=ws.max_column)
    meta_cell = ws.cell(row=3, column=1)
    from datetime import datetime
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    meta_cell.value = f"Ngày xuất báo cáo: {now_str}  |  Hệ thống Retail Commander"
    meta_cell.font = Font(name="Segoe UI", size=9, italic=True, color="FFFFFF")
    meta_cell.fill = navy_fill
    meta_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 18
    
    # Empty Spacer Row 4
    ws.row_dimensions[4].height = 12
    
    # Table Header Row 5
    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )
    
    # Format Headers
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=5, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[5].height = 24
    
    # Format Data Rows (Row 6 onwards)
    data_font = Font(name="Segoe UI", size=10)
    zebra_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    for row in range(6, ws.max_row + 1):
        is_even = (row % 2 == 0)
        row_fill = zebra_fill if is_even else white_fill
        ws.row_dimensions[row].height = 18
        
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = data_font
            if cell.fill.fill_type is None:
                cell.fill = row_fill
            cell.border = thin_border
            
            # Auto-align and format number cells
            val = cell.value
            col_name = ws.cell(row=5, column=col).value or ""
            
            if isinstance(val, (int, float)):
                if "%" in col_name or "Tỷ Lệ" in col_name:
                    cell.number_format = '0.0"%"'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif "Giá Trị" in col_name or "Số Tiền" in col_name or "Cọc" in col_name or "Đợt 2" in col_name or "HĐ" in col_name:
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
            elif val == "Chưa nộp" or val == "Chưa nhập" or val == "N/A":
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
    # Auto-adjust column widths
    from openpyxl.utils import get_column_letter
    for col in ws.columns:
        max_len = 0
        col_idx = col[0].column
        col_letter = get_column_letter(col_idx)
        for cell in col:
            if cell.row < 5:
                continue
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        header_val = ws.cell(row=5, column=col_idx).value
        if header_val:
            max_len = max(max_len, len(str(header_val)))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

def style_input_traffic_sheet(ws):
    ws.views.sheetView[0].showGridLines = True
    
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    
    red_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    peach_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    gray_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    zebra_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    white_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    red_bold_font = Font(name="Segoe UI", size=12, bold=True, color="C00000")
    bold_font = Font(name="Segoe UI", size=10, bold=True)
    normal_font = Font(name="Segoe UI", size=10)
    italic_gray_font = Font(name="Segoe UI", size=10, italic=True, color="7F7F7F")
    
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )
    
    # --- Row 1 ---
    cell_a1 = ws.cell(row=1, column=1)
    cell_a1.value = "Nhập đúng tên CH trên file M\n(chỉ thêm đúng CH mình quản lý)"
    cell_a1.font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
    cell_a1.fill = red_fill
    cell_a1.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    ws.merge_cells(start_row=1, start_column=2, end_row=1, end_column=7)
    title_cell = ws.cell(row=1, column=2)
    title_cell.value = "Nhập traffic cửa hàng vào đây"
    title_cell.font = red_bold_font
    title_cell.fill = peach_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    
    for col in range(3, 8):
        ws.cell(row=1, column=col).fill = peach_fill
        
    ws.row_dimensions[1].height = 35
    
    # --- Row 2 (Total) ---
    ws.cell(row=2, column=1).value = "Total"
    ws.cell(row=2, column=1).font = bold_font
    ws.cell(row=2, column=1).fill = gray_fill
    ws.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=2, column=1).border = thin_border
    
    max_row = ws.max_row
    for col in range(2, 8):
        col_letter = get_column_letter(col)
        cell = ws.cell(row=2, column=col)
        cell.value = f"=SUM({col_letter}4:{col_letter}{max_row})"
        cell.font = bold_font
        cell.fill = gray_fill
        cell.alignment = Alignment(horizontal="right", vertical="center")
        cell.number_format = '#,##0'
        cell.border = thin_border
        
    ws.row_dimensions[2].height = 20
    
    # --- Row 3 (Headers) ---
    headers = [
        "Cửa Hàng", "Traffic Tuần Này", "Traffic Tuần Trước", 
        "Traffic Tuần cùng kỳ", "Traffic Tháng Này", "Traffic Tháng Trước", 
        "Traffic Tháng cùng kỳ"
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col)
        cell.value = h
        cell.font = white_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        
    ws.row_dimensions[3].height = 25
    
    # --- Row 4+ (Data) ---
    for row in range(4, max_row + 1):
        is_even = (row % 2 == 0)
        row_fill = zebra_fill if is_even else white_fill
        ws.row_dimensions[row].height = 20
        
        cell_name = ws.cell(row=row, column=1)
        cell_name.font = normal_font
        cell_name.fill = row_fill
        cell_name.border = thin_border
        cell_name.alignment = Alignment(horizontal="left", vertical="center")
        
        for col in range(2, 8):
            cell = ws.cell(row=row, column=col)
            val = cell.value
            cell.border = thin_border
            cell.fill = row_fill
            
            if val == "Không có dữ liệu":
                cell.font = italic_gray_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.font = normal_font
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = '#,##0'
                
    ws.column_dimensions['A'].width = 32
    for col in range(2, 8):
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].width = 20

@app.route('/api/export_excel', methods=['GET'])
def export_excel():
    report_date = request.args.get('report_date')
    asm = request.args.get('asm')
    role = request.args.get('role') # 'asm' or 'admin'
    pin = request.args.get('pin')
    
    if not report_date:
        return "Thiếu ngày báo cáo", 400
        
    master_pin = os.environ.get('MASTER_PIN', '8888')
    is_authorized = False
    if role == 'admin' and pin == master_pin:
        is_authorized = True
    elif role == 'asm':
        asm_record = query_db("SELECT * FROM tb_asms WHERE asm_name = ? AND passcode = ?", (asm, pin), one=True)
        if asm_record:
            is_authorized = True
            
    if not is_authorized:
        return "Không có quyền xuất báo cáo", 401
        
    try:
        filter_asm = None
        if role == 'asm':
            filter_asm = asm
        elif role == 'admin' and asm:
            filter_asm = asm
            
        # 1. Fetch data
        if filter_asm:
            stores = query_db("SELECT store_code, store_name, region, asm_name FROM tb_stores WHERE asm_name = ? ORDER BY store_code", (filter_asm,))
        else:
            stores = query_db("SELECT store_code, store_name, region, asm_name FROM tb_stores ORDER BY store_code")
            
        store_codes = [s['store_code'] for s in stores]
        if not store_codes:
            return "Không tìm thấy dữ liệu cửa hàng", 404
            
        placeholders = ",".join(["?"] * len(store_codes))
        
        # Get start and end date of the week (Saturday to Friday)
        rep_dt = datetime.strptime(report_date, '%Y-%m-%d')
        start_date = (rep_dt - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = report_date
        
        # Calculate other date ranges for Input_Traffic comparison
        # 1. This Week
        w_curr_start = start_date
        w_curr_end = end_date
        
        # 2. Last Week
        w_prev_start = (rep_dt - timedelta(days=13)).strftime('%Y-%m-%d')
        w_prev_end = (rep_dt - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # 3. Same Week LY (364 days ago)
        w_ly_start = (rep_dt - timedelta(days=370)).strftime('%Y-%m-%d')
        w_ly_end = (rep_dt - timedelta(days=364)).strftime('%Y-%m-%d')
        
        # 4. This Month
        m_curr_start = rep_dt.replace(day=1).strftime('%Y-%m-%d')
        m_curr_end = report_date
        
        # 5. Last Month
        m_prev_end_dt = rep_dt.replace(day=1) - timedelta(days=1)
        m_prev_start = m_prev_end_dt.replace(day=1).strftime('%Y-%m-%d')
        m_prev_end = m_prev_end_dt.strftime('%Y-%m-%d')
        
        # 6. Same Month LY
        try:
            ly_rep_dt = rep_dt.replace(year=rep_dt.year - 1)
        except ValueError:
            ly_rep_dt = rep_dt.replace(year=rep_dt.year - 1, day=28)
        m_ly_start = ly_rep_dt.replace(day=1).strftime('%Y-%m-%d')
        m_ly_end = ly_rep_dt.strftime('%Y-%m-%d')
        
        # Query Period 1: Last Year (w_ly_start to max of w_ly_end and m_ly_end)
        ly_max_date = max(w_ly_end, m_ly_end)
        traffic_rows_ly = query_db(f"""
            SELECT store_code, traffic_date, traffic_val FROM tb_traffic
            WHERE traffic_date >= ? AND traffic_date <= ? AND store_code IN ({placeholders})
        """, [w_ly_start, ly_max_date] + store_codes)
        
        # Query Period 2: This Year (min of w_prev_start and m_prev_start to w_curr_end)
        ty_min_date = min(w_prev_start, m_prev_start)
        traffic_rows_ty = query_db(f"""
            SELECT store_code, traffic_date, traffic_val FROM tb_traffic
            WHERE traffic_date >= ? AND traffic_date <= ? AND store_code IN ({placeholders})
        """, [ty_min_date, w_curr_end] + store_codes)
        
        # Combine all traffic rows for comparison
        all_traffic_rows = traffic_rows_ly + traffic_rows_ty
        
        # Load Traffic records for the entire week
        traffic_rows = query_db(f"""
            SELECT store_code, traffic_date, traffic_val, bills_val, company_online_bills, store_online_bills 
            FROM tb_traffic 
            WHERE traffic_date >= ? AND traffic_date <= ? AND store_code IN ({placeholders})
            ORDER BY store_code, traffic_date
        """, [start_date, end_date] + store_codes)
        
        # Load Contracts (Section 3.1) with contract_number
        contract_rows = query_db(f"""
            SELECT store_code, contract_number, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason 
            FROM tb_contracts 
            WHERE report_date = ? AND store_code IN ({placeholders})
        """, [report_date] + store_codes)
        
        # Load Unsigned (Section 3.2)
        unsigned_rows = query_db(f"""
            SELECT store_code, prev_year_value, expected_signing_time, product_category, quantity, status, reason 
            FROM tb_unsigned_contracts 
            WHERE report_date = ? AND store_code IN ({placeholders})
        """, [report_date] + store_codes)
        
        # Load Details (Section 4)
        detail_rows = query_db(f"""
            SELECT * FROM tb_operational_details 
            WHERE report_date = ? AND store_code IN ({placeholders})
        """, [report_date] + store_codes)
        
        # Load Support Requests (Section 4.5)
        support_rows = query_db(f"""
            SELECT store_code, category, priority, issue_item, deadline, person_in_charge 
            FROM tb_support_requests 
            WHERE report_date = ? AND store_code IN ({placeholders})
        """, [report_date] + store_codes)
        
        store_map = {s['store_code']: s for s in stores}
        
        # Group traffic rows by store_code
        from collections import defaultdict
        store_traffic_map = defaultdict(list)
        for r in traffic_rows:
            store_traffic_map[r['store_code']].append(r)
            
        # 2. Process dataframes using pandas
        # Sheet 1: Tổng Hợp Traffic & CR
        traffic_summary_data = []
        for code, s in store_map.items():
            s_traffic = store_traffic_map.get(code, [])
            has_submitted = len(s_traffic) > 0
            
            if not has_submitted:
                traffic_summary_data.append({
                    'Mã Cửa Hàng': code,
                    'Tên Cửa Hàng': s['store_name'],
                    'Khu Vực': s['region'],
                    'ASM Quản Lý': s['asm_name'],
                    'Tổng Traffic': 'Chưa nộp',
                    'Tổng Bill Bán Lẻ': 'Chưa nộp',
                    'Tổng Bill OL Công Ty': 0,
                    'Tổng Bill OL Cửa Hàng': 0,
                    'Tỷ Lệ CR tại quầy (%)': 'N/A'
                })
            else:
                tot_trf = sum(r['traffic_val'] for r in s_traffic if r['traffic_val'] is not None)
                tot_bil = sum(r['bills_val'] for r in s_traffic if r['bills_val'] is not None)
                tot_co = sum(r['company_online_bills'] for r in s_traffic if r['company_online_bills'] is not None)
                tot_so = sum(r['store_online_bills'] for r in s_traffic if r['store_online_bills'] is not None)
                
                bill_for_cr = tot_bil - tot_co
                cr = (bill_for_cr / tot_trf * 100) if tot_trf > 0 else 0.0
                
                traffic_summary_data.append({
                    'Mã Cửa Hàng': code,
                    'Tên Cửa Hàng': s['store_name'],
                    'Khu Vực': s['region'],
                    'ASM Quản Lý': s['asm_name'],
                    'Tổng Traffic': tot_trf,
                    'Tổng Bill Bán Lẻ': tot_bil,
                    'Tổng Bill OL Công Ty': tot_co,
                    'Tổng Bill OL Cửa Hàng': tot_so,
                    'Tỷ Lệ CR tại quầy (%)': cr
                })
        df_traffic = pd.DataFrame(traffic_summary_data)
        
        # Sheet 2: Traffic Chi Tiết Theo Ngày
        daily_detail_data = []
        weekday_vn = {
            5: "Thứ Bảy",
            6: "Chủ Nhật",
            0: "Thứ Hai",
            1: "Thứ Ba",
            2: "Thứ Tư",
            3: "Thứ Năm",
            4: "Thứ Sáu"
        }
        
        for code, s in store_map.items():
            s_traffic = store_traffic_map.get(code, [])
            s_traffic_dict = {r['traffic_date']: r for r in s_traffic}
            
            for i in range(7):
                curr_date = rep_dt - timedelta(days=(6 - i))
                curr_date_str = curr_date.strftime('%Y-%m-%d')
                curr_day_vn = weekday_vn[curr_date.weekday()]
                
                r = s_traffic_dict.get(curr_date_str)
                
                if r is None:
                    daily_detail_data.append({
                        'Mã Cửa Hàng': code,
                        'Tên Cửa Hàng': s['store_name'],
                        'Khu Vực': s['region'],
                        'ASM Quản Lý': s['asm_name'],
                        'Ngày': curr_date.strftime('%d/%m/%Y'),
                        'Thứ': curr_day_vn,
                        'Traffic (Lượt Khách)': 'Chưa nhập',
                        'Số Bill Bán Lẻ': 'Chưa nhập',
                        'Bill Online Công Ty': 0,
                        'Bill Online Cửa Hàng': 0,
                        'Tỷ Lệ CR tại quầy (%)': 'N/A'
                    })
                else:
                    trf_val = r['traffic_val']
                    bil_val = r['bills_val']
                    co_val = r['company_online_bills'] or 0
                    so_val = r['store_online_bills'] or 0
                    
                    bill_for_cr = (bil_val or 0) - co_val
                    cr = (bill_for_cr / trf_val * 100) if (trf_val and trf_val > 0) else 0.0
                    
                    daily_detail_data.append({
                        'Mã Cửa Hàng': code,
                        'Tên Cửa Hàng': s['store_name'],
                        'Khu Vực': s['region'],
                        'ASM Quản Lý': s['asm_name'],
                        'Ngày': curr_date.strftime('%d/%m/%Y'),
                        'Thứ': curr_day_vn,
                        'Traffic (Lượt Khách)': trf_val if trf_val is not None else 'Chưa nhập',
                        'Số Bill Bán Lẻ': bil_val if bil_val is not None else 'Chưa nhập',
                        'Bill Online Công Ty': co_val,
                        'Bill Online Cửa Hàng': so_val,
                        'Tỷ Lệ CR tại quầy (%)': cr if trf_val is not None else 'N/A'
                    })
        df_daily_detail = pd.DataFrame(daily_detail_data)
        
        # Process Input_Traffic sheet data
        store_traffic_all_map = defaultdict(list)
        for r in all_traffic_rows:
            store_traffic_all_map[r['store_code']].append(r)
            
        def get_range_sum(rows, start, end):
            matching_vals = [r['traffic_val'] for r in rows if start <= r['traffic_date'] <= end and r['traffic_val'] is not None]
            if not matching_vals:
                return None
            return sum(matching_vals)
            
        input_traffic_data = []
        for code, s in store_map.items():
            rows = store_traffic_all_map.get(code, [])
            
            val_w_curr = get_range_sum(rows, w_curr_start, w_curr_end)
            val_w_prev = get_range_sum(rows, w_prev_start, w_prev_end)
            val_w_ly = get_range_sum(rows, w_ly_start, w_ly_end)
            val_m_curr = get_range_sum(rows, m_curr_start, m_curr_end)
            val_m_prev = get_range_sum(rows, m_prev_start, m_prev_end)
            val_m_ly = get_range_sum(rows, m_ly_start, m_ly_end)
            
            input_traffic_data.append({
                'Cửa Hàng': s['store_name'],
                'Traffic Tuần Này': val_w_curr if val_w_curr is not None else 'Không có dữ liệu',
                'Traffic Tuần Trước': val_w_prev if val_w_prev is not None else 'Không có dữ liệu',
                'Traffic Tuần cùng kỳ': val_w_ly if val_w_ly is not None else 'Không có dữ liệu',
                'Traffic Tháng Này': val_m_curr if val_m_curr is not None else 'Không có dữ liệu',
                'Traffic Tháng Trước': val_m_prev if val_m_prev is not None else 'Không có dữ liệu',
                'Traffic Tháng cùng kỳ': val_m_ly if val_m_ly is not None else 'Không có dữ liệu'
            })
            
        input_traffic_data.sort(key=lambda x: x['Cửa Hàng'])
        df_input_traffic = pd.DataFrame(input_traffic_data)
        
        # Sheet 3: HĐ Đang Đàm Phán 3.1
        contracts_data = []
        for c in contract_rows:
            s = store_map.get(c['store_code'], {})
            contracts_data.append({
                'Mã Cửa Hàng': c['store_code'],
                'Tên Cửa Hàng': s.get('store_name', ''),
                'Khu Vực': s.get('region', ''),
                'Số Hợp Đồng': c['contract_number'] or 'Đang GD',
                'Giá Trị HĐ (Tr.đ)': c['contract_value'],
                'Chủng Loại': c['product_category'],
                'Số Lượng': c['quantity'],
                'Số Tiền Đã Cọc': c['deposit_paid'],
                'Số Tiền Đợt 2': c['installment_2'],
                'Trạng Thái': c['status'],
                'Lý Do / Chi Tiết': c['reason']
            })
        df_contracts = pd.DataFrame(contracts_data) if contracts_data else pd.DataFrame(columns=['Mã Cửa Hàng', 'Tên Cửa Hàng', 'Khu Vực', 'Số Hợp Đồng', 'Giá Trị HĐ (Tr.đ)', 'Chủng Loại', 'Số Lượng', 'Số Tiền Đã Cọc', 'Số Tiền Đợt 2', 'Trạng Thái', 'Lý Do / Chi Tiết'])
        
        # Sheet 4: Unsigned Contracts 3.2
        unsigned_data = []
        for u in unsigned_rows:
            s = store_map.get(u['store_code'], {})
            unsigned_data.append({
                'Mã Cửa Hàng': u['store_code'],
                'Tên Cửa Hàng': s.get('store_name', ''),
                'Khu Vực': s.get('region', ''),
                'Giá Trị Năm Ngoái (Tr.đ)': u['prev_year_value'],
                'Thời Gian Dự Kiến Ký': u['expected_signing_time'],
                'Chủng Loại': u['product_category'],
                'Số Lượng': u['quantity'],
                'Trạng Thái': u['status'],
                'Lý Do / Chi Tiết': u['reason']
            })
        df_unsigned = pd.DataFrame(unsigned_data) if unsigned_data else pd.DataFrame(columns=['Mã Cửa Hàng', 'Tên Cửa Hàng', 'Khu Vực', 'Giá Trị Năm Ngoái (Tr.đ)', 'Thời Gian Dự Kiến Ký', 'Chủng Loại', 'Số Lượng', 'Trạng thái', 'Lý Do / Chi Tiết'])
        
        # Sheet 5: Chi Tiết Vận Hành 4
        details_data = []
        for d in detail_rows:
            s = store_map.get(d['store_code'], {})
            details_data.append({
                'Mã Cửa Hàng': d['store_code'],
                'Tên Cửa Hàng': s.get('store_name', ''),
                'Khu Vực': s.get('region', ''),
                'Mở Cửa / Đóng Cửa': d['op_open_close_status'],
                'Ghi Chú Mở/Đóng': d['op_open_close_note'],
                'Đồng Phục & Diện Mạo': d['op_uniform_status'],
                'Ghi Chú Đồng Phục': d['op_uniform_note'],
                'Chào Hỏi Khách Hàng': d['op_greet_status'],
                'Ghi Chú Chào Hỏi': d['op_greet_note'],
                'Ý Kiến Phản Hồi Khách': d['op_feedback_status'],
                'Ghi Chú Phản Hồi': d['op_feedback_note'],
                'Vấn Đề Vận Hành Khác': d['op_other_status'],
                'Ghi Chú Vấn Đề Khác': d['op_other_note'],
                'Chỉ Tiêu Nhân Sự': d['hr_target'],
                'Thực Tế Nhân Sự': d['hr_actual'],
                'Bảo Vệ Ca Trực': d['hr_guard'],
                'Nghỉ Việc/Tuyển Dụng': d['hr_resigned_note'],
                'Nghỉ Phép/Ối/Đau': d['hr_leave_note'],
                'Tự Ý Nghỉ Việc': d['hr_absent_note'],
                'Phản Hồi Tồn Kho': d['inv_stock_status'],
                'Hàng Thiếu/Đứt Size': d['inv_info_goods'],
                'Hàng Trả Kho': d['inv_return_warehouse'],
                'Đề Xuất/Kiến Nghị': d['inv_proposal']
            })
        df_details = pd.DataFrame(details_data) if details_data else pd.DataFrame(columns=['Mã Cửa Hàng', 'Tên Cửa Hàng', 'Khu Vực'])
        
        # Sheet 6: Yêu Cầu Hỗ Trợ 4.5
        support_data = []
        for sp in support_rows:
            s = store_map.get(sp['store_code'], {})
            support_data.append({
                'Mã Cửa Hàng': sp['store_code'],
                'Tên Cửa Hàng': s.get('store_name', ''),
                'Khu Vực': s.get('region', ''),
                'Danh Mục Hỗ Trợ': sp['category'],
                'Độ Ưu Tiên': sp['priority'],
                'Nội Dung Sự Việc Cụ Thể': sp['issue_item'],
                'Thời Hạn Hoàn Thành': sp['deadline'],
                'Người Chịu Trách Nhiệm': sp['person_in_charge']
            })
        df_support = pd.DataFrame(support_data) if support_data else pd.DataFrame(columns=['Mã Cửa Hàng', 'Tên Cửa Hàng', 'Khu Vực', 'Danh Mục Hỗ Trợ', 'Độ Ưu Tiên', 'Nội Dung Sự Việc Cụ Thể', 'Thời Hạn Hoàn Thành', 'Người Chịu Trách Nhiệm'])
        
        # 3. Create Excel File in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_traffic.to_excel(writer, sheet_name='Tổng Hợp Traffic & CR', index=False, startrow=4)
            df_daily_detail.to_excel(writer, sheet_name='Traffic Chi Tiết Theo Ngày', index=False, startrow=4)
            df_input_traffic.to_excel(writer, sheet_name='Input_Traffic', index=False, startrow=2)
            df_contracts.to_excel(writer, sheet_name='HĐ Đang Đàm Phán 3.1', index=False, startrow=4)
            df_unsigned.to_excel(writer, sheet_name='HĐ Chưa Ký 3.2', index=False, startrow=4)
            df_details.to_excel(writer, sheet_name='Chi Tiết Vận Hành 4', index=False, startrow=4)
            df_support.to_excel(writer, sheet_name='Yêu Cầu Hỗ Trợ 4.5', index=False, startrow=4)
            
            # Access workbook and apply corporate styling
            workbook = writer.book
            date_range_str = f"Từ {datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y')} đến {datetime.strptime(end_date, '%Y-%m-%d').strftime('%d/%m/%Y')}"
            role_str = f"ASM {filter_asm}" if filter_asm else "Toàn Hệ Thống"
            
            style_sheet(workbook['Tổng Hợp Traffic & CR'], "Báo Cáo Tổng Hợp Traffic & CR Tuần", "Tổng hợp kết quả chuyển đổi", date_range_str, role_str)
            style_sheet(workbook['Traffic Chi Tiết Theo Ngày'], "Báo Cáo Chi Tiết Traffic Ngày-Qua-Ngày", "Nhật ký nhập traffic hàng ngày của tuần", date_range_str, role_str)
            style_input_traffic_sheet(workbook['Input_Traffic'])
            style_sheet(workbook['HĐ Đang Đàm Phán 3.1'], "Danh Sách Hợp Đồng Đang Đàm Phán (3.1)", "Theo dõi tiến độ thương thảo hợp đồng", date_range_str, role_str)
            style_sheet(workbook['HĐ Chưa Ký 3.2'], "Danh Sách Hợp Đồng Cùng Kỳ Chưa Ký (3.2)", "Hợp đồng trễ hạn chưa tái ký", date_range_str, role_str)
            style_sheet(workbook['Chi Tiết Vận Hành 4'], "Báo Cáo Chi Tiết Vận Hành - Nhân Sự - Hàng Hóa", "Đánh giá chất lượng dịch vụ & nhân sự tại quầy", date_range_str, role_str)
            style_sheet(workbook['Yêu Cầu Hỗ Trợ 4.5'], "Danh Sách Yêu Cầu Hỗ Trợ Kỹ Thuật / Vận Hành (4.5)", "Tiếp nhận và xử lý yêu cầu phát sinh từ cửa hàng", date_range_str, role_str)
            
        output.seek(0)
        
        # Format filename
        filename = f"BaoCao_RetailCommander_{report_date}.xlsx"
        if filter_asm:
            filename = f"BaoCao_RetailCommander_{filter_asm}_{report_date}.xlsx"
            
        encoded_filename = urllib.parse.quote(filename)
        
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return f"Lỗi xuất file Excel: {str(e)}", 500

if __name__ == '__main__':
    # Default port 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
