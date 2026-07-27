# -*- coding: utf-8 -*-
"""
sync_from_neon.py — KÉO NGƯỢC dữ liệu từ Neon Postgres (Cloud) về SQLite gốc (local).

Chiều đồng bộ: CLOUD  ->  LOCAL   (ngược với sync_neon.py là LOCAL -> CLOUD).
Chế độ: MIRROR — cloud là chuẩn, ghi đè dữ liệu local. Trước khi ghi luôn backup
        file operational_data.db sang thư mục backups/ (kèm timestamp).

Cách chạy tay:
    cd tools/web_portal
    python sync_from_neon.py

Chuỗi kết nối Neon (DATABASE_URL) đọc theo thứ tự ưu tiên:
    1) Biến môi trường DATABASE_URL
    2) File .env cạnh script này  (DATABASE_URL=postgresql://...)

Script tự khớp cột chung giữa Neon và SQLite nên không vỡ khi schema lệch nhau.
"""
import os
import sys
import shutil
import sqlite3
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("❌ Thiếu thư viện psycopg2. Chạy: pip install psycopg2-binary")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'operational_data.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
ENV_PATH = os.path.join(BASE_DIR, '.env')

# Các bảng vận hành web ghi vào — sẽ mirror cloud -> local.
TABLES = [
    'tb_stores',
    'tb_asms',
    'tb_store_employees',
    'tb_store_headcount_targets',
    'tb_employee_probation',
    'tb_hr_lifecycle_tickets',
    'tb_store_support_staff',
    'tb_store_shift_config',
    'tb_traffic',
    'tb_contracts',
    'tb_unsigned_contracts',
    'tb_operational_details',
    'tb_support_requests',
]


def load_database_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        return url.strip()
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                if key.strip() == 'DATABASE_URL':
                    return val.strip().strip('"').strip("'")
    return None


def backup_local_db():
    if not os.path.exists(DB_PATH):
        print(f"⚠️  Không thấy {DB_PATH} — sẽ tạo mới khi ghi.")
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(BACKUP_DIR, f'operational_data_{ts}.db')
    shutil.copy2(DB_PATH, dst)
    print(f"💾 Đã backup local DB -> {dst}")
    return dst


def sqlite_tables(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {r[0] for r in cur.fetchall()}


def sqlite_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def pg_columns(pg_cur, table):
    pg_cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    )
    return {r[0] for r in pg_cur.fetchall()}


def mirror_table(pg_conn, sq_conn, table):
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    local_tables = sqlite_tables(sq_cur)
    if table not in local_tables:
        print(f"  ⏭️  {table}: bỏ qua (không có ở local)")
        return 0

    local_cols = sqlite_columns(sq_cur, table)
    try:
        remote_cols = pg_columns(pg_cur, table)
    except Exception as e:
        pg_conn.rollback()
        print(f"  ⏭️  {table}: bỏ qua (không có trên Neon: {e})")
        return 0
    if not remote_cols:
        print(f"  ⏭️  {table}: bỏ qua (Neon không có bảng này)")
        return 0

    # Cột chung, giữ thứ tự theo local để INSERT ổn định.
    common = [c for c in local_cols if c in remote_cols]
    if not common:
        print(f"  ⚠️  {table}: không có cột chung — bỏ qua")
        return 0

    col_list = ', '.join(f'"{c}"' for c in common)
    pg_cur.execute(f'SELECT {col_list} FROM "{table}"')
    rows = pg_cur.fetchall()

    placeholders = ', '.join(['?'] * len(common))
    insert_sql = f"INSERT INTO {table} ({', '.join(common)}) VALUES ({placeholders})"

    # Mirror trong 1 transaction: xoá rồi nạp lại.
    try:
        sq_cur.execute("BEGIN")
        sq_cur.execute(f"DELETE FROM {table}")
        sq_cur.executemany(insert_sql, rows)
        sq_conn.commit()
    except Exception as e:
        sq_conn.rollback()
        print(f"  ❌ {table}: LỖI ghi local, đã rollback bảng này — {e}")
        return 0

    print(f"  ✅ {table}: {len(rows)} dòng (cột: {len(common)}/{len(local_cols)})")
    return len(rows)


def main():
    print("=" * 64)
    print("  ĐỒNG BỘ NGƯỢC: Neon Cloud  ->  SQLite gốc (MIRROR)")
    print("=" * 64)

    url = load_database_url()
    if not url:
        print("❌ Không tìm thấy DATABASE_URL.")
        print("   -> Tạo file .env cạnh script với dòng:")
        print("      DATABASE_URL=postgresql://<user>:<pass>@<host>/<db>?sslmode=require")
        print("   -> Hoặc set biến môi trường DATABASE_URL.")
        sys.exit(1)

    try:
        pg_conn = psycopg2.connect(url, connect_timeout=30)
    except Exception as e:
        print(f"❌ Không kết nối được Neon: {e}")
        sys.exit(1)

    backup_local_db()
    sq_conn = sqlite3.connect(DB_PATH, timeout=30.0)

    total = 0
    print("\n📥 Đang mirror các bảng:")
    for t in TABLES:
        try:
            total += mirror_table(pg_conn, sq_conn, t)
        except Exception as e:
            print(f"  ❌ {t}: lỗi ngoài dự kiến — {e}")

    sq_conn.close()
    pg_conn.close()
    print(f"\n🎉 HOÀN TẤT — tổng {total} dòng đã kéo về local.")
    print(f"   Thời điểm: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
