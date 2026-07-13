import os
import calendar
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, jsonify
import sqlite3
import threading
import urllib.request
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    offset = 4 - today.weekday()
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
    
    # Handle ASM validation
    if store_code.startswith("ASM_"):
        asm_name = store_code[4:]
        if pin == '9999':
            return jsonify({'ok': True, 'valid': True, 'role': 'asm', 'asm_name': asm_name})
        return jsonify({'ok': True, 'valid': False, 'error': 'Mã PIN ASM không đúng'})
    
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
        rows = query_db("SELECT traffic_date, traffic_val, bills_val FROM tb_traffic WHERE store_code = ? AND traffic_date LIKE ?", (store_code, prefix))
        
        traffic_map = {r['traffic_date']: {'traffic': r['traffic_val'], 'bills': r['bills_val'] or 0} for r in rows}
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
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if not store and pin != '1234':
            return jsonify({'ok': False, 'error': 'Mã PIN không đúng'})
            
        # Upsert each day
        for date_str, day_data in traffic_data.items():
            traffic_str = day_data.get('traffic', '') if isinstance(day_data, dict) else ''
            bills_str = day_data.get('bills', '') if isinstance(day_data, dict) else ''
            
            if (traffic_str is None or str(traffic_str).strip() == '') and (bills_str is None or str(bills_str).strip() == ''):
                # Delete record if cleared
                execute_db("DELETE FROM tb_traffic WHERE store_code = ? AND traffic_date = ?", (store_code, date_str))
            else:
                try:
                    trf_val = int(traffic_str) if (traffic_str is not None and str(traffic_str).strip() != '') else 0
                    bil_val = int(bills_str) if (bills_str is not None and str(bills_str).strip() != '') else 0
                    
                    if trf_val < 0 or bil_val < 0:
                        continue
                    if DATABASE_URL:
                        execute_db("""
                        INSERT INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT (store_code, traffic_date) DO UPDATE SET 
                            traffic_val = EXCLUDED.traffic_val,
                            bills_val = EXCLUDED.bills_val
                        """, (store_code, date_str, trf_val, bil_val))
                    else:
                        execute_db("""
                        INSERT OR REPLACE INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val)
                        VALUES (?, ?, ?, ?)
                        """, (store_code, date_str, trf_val, bil_val))
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
        contracts = query_db("SELECT contract_value, product_category, quantity, deposit_paid, installment_2, status, reason FROM tb_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        
        # Query unsigned contracts (Section 3.2)
        unsigned = query_db("SELECT prev_year_value, expected_signing_time, product_category, quantity, status, reason FROM tb_unsigned_contracts WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        
        # Query operational details (Section 4.1 - 4.4)
        details = query_db("SELECT * FROM tb_operational_details WHERE store_code = ? AND report_date = ?", (store_code, report_date), one=True)
        
        # Query support requests (Section 4.5)
        support = query_db("SELECT category, priority, issue_item, deadline, person_in_charge FROM tb_support_requests WHERE store_code = ? AND report_date = ?", (store_code, report_date))
        
        # Get traffic and bills for this specific Friday (report_date) if nộp in weekly
        traffic_row = query_db("SELECT traffic_val, bills_val FROM tb_traffic WHERE store_code = ? AND traffic_date = ?", (store_code, report_date), one=True)
        traffic_val = traffic_row['traffic_val'] if traffic_row else ''
        bills_val = traffic_row['bills_val'] if traffic_row else ''
        
        return jsonify({
            'ok': True,
            'traffic': traffic_val,
            'bills': bills_val,
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
        store = query_db("SELECT * FROM tb_stores WHERE store_code = ? AND passcode = ?", (store_code, pin), one=True)
        if not store and pin != '1234':
            return jsonify({'ok': False, 'error': 'Mã PIN không hợp lệ'})
            
        # 2. Save Traffic (Save for report_date as daily record)
        if traffic_val is not None and str(traffic_val).strip() != '':
            execute_db("DELETE FROM tb_traffic WHERE store_code = ? AND traffic_date = ?", (store_code, report_date))
            trf_int = int(traffic_val)
            bil_int = int(bills_val) if (bills_val is not None and str(bills_val).strip() != '') else 0
            if DATABASE_URL:
                execute_db("""
                INSERT INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val) VALUES (?, ?, ?, ?)
                ON CONFLICT (store_code, traffic_date) DO UPDATE SET 
                    traffic_val = EXCLUDED.traffic_val,
                    bills_val = EXCLUDED.bills_val
                """, (store_code, report_date, trf_int, bil_int))
            else:
                execute_db("INSERT OR REPLACE INTO tb_traffic (store_code, traffic_date, traffic_val, bills_val) VALUES (?, ?, ?, ?)", 
                           (store_code, report_date, trf_int, bil_int))
            
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
        
        contracts = query_db("SELECT store_code, contract_value, product_category, quantity, deposit_paid, installment_2, status, reason FROM tb_contracts WHERE report_date = ?", (report_date,))
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
    try:
        # Get all stores
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

# ──────────────────────────────────────────────────────────────────────────────
# NEW API: ASM TRAFFIC REMINDERS SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/asm_traffic_summary', methods=['GET'])
def get_asm_traffic_summary():
    asm = request.args.get('asm')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if not asm or not start_date_str or not end_date_str:
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
        
        # Get all stores for this ASM
        stores = query_db("SELECT store_code, store_name FROM tb_stores WHERE asm_name = ? ORDER BY store_name", (asm,))
        
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

if __name__ == '__main__':
    # Default port 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
