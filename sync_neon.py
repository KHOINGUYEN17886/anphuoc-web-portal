import sqlite3
import os
import psycopg2

db_path = r'C:\All_Report\8_RETAIL_COMMANDER\tools\web_portal\operational_data.db'
conn_sqlite = sqlite3.connect(db_path)
cur_sqlite = conn_sqlite.cursor()

cur_sqlite.execute('SELECT employee_code, store_code, full_name, position, gender, dob, appointment_date, avatar_url, status, created_at FROM tb_store_employees')
rows = cur_sqlite.fetchall()
print(f"SQLite has {len(rows)} employee records.")

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    try:
        with open(r'C:\All_Report\8_RETAIL_COMMANDER\tools\web_portal\app.py', encoding='utf-8') as f:
            text = f.read()
        import re
        match = re.search(r'postgresql://[^\s"\']+', text)
        if match:
            DATABASE_URL = match.group(0)
    except Exception:
        pass

if DATABASE_URL:
    try:
        print("Connecting to Neon Postgres...")
        conn_pg = psycopg2.connect(DATABASE_URL)
        cur_pg = conn_pg.cursor()
        cur_pg.execute("TRUNCATE TABLE tb_store_employees")
        for r in rows:
            cur_pg.execute("""
                INSERT INTO tb_store_employees (employee_code, store_code, full_name, position, gender, dob, appointment_date, avatar_url, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, r)
        conn_pg.commit()
        print(f"SYNCED {len(rows)} EMPLOYEES TO NEON POSTGRESQL CLOUD DB SUCCESSFULLY!")
    except Exception as e:
        print("Postgres Sync Error:", e)
else:
    print("DATABASE_URL not found.")
