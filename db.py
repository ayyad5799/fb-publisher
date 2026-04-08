"""
نظام قاعدة البيانات - يدعم Supabase (Render) والملفات المحلية (Railway)
يتحول تلقائياً حسب متغير البيئة DATABASE_URL
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', '')

# ===== Supabase Mode =====
_db_conn = None

def get_db():
    global _db_conn
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        if _db_conn is None or _db_conn.closed:
            _db_conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            _db_conn.autocommit = True
        return _db_conn
    except Exception as e:
        logger.error(f"DB connect error: {e}")
        _db_conn = None
        return None

def init_db():
    """إنشاء جداول قاعدة البيانات"""
    db = get_db()
    if not db:
        return False
    try:
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.close()
        logger.info("DB initialized OK")
        return True
    except Exception as e:
        logger.error(f"DB init error: {e}")
        return False

# ===== واجهة موحدة =====
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def _file_path(key):
    """تحويل المفتاح لمسار ملف"""
    safe = key.replace('/', '_').replace(':', '_')
    return os.path.join(DATA_DIR, safe + '.json')

def db_get(key, default=None):
    """جلب قيمة من DB أو ملف"""
    if DATABASE_URL:
        db = get_db()
        if db:
            try:
                cur = db.cursor()
                cur.execute("SELECT value FROM kv_store WHERE key=%s", (key,))
                row = cur.fetchone()
                cur.close()
                if row:
                    return json.loads(row['value'])
            except Exception as e:
                logger.error(f"DB get error [{key}]: {e}")
    # Fallback: ملف محلي
    try:
        fp = _file_path(key)
        if os.path.exists(fp):
            with open(fp, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return default

def db_set(key, value):
    """حفظ قيمة في DB أو ملف"""
    if DATABASE_URL:
        db = get_db()
        if db:
            try:
                cur = db.cursor()
                cur.execute("""
                    INSERT INTO kv_store (key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                """, (key, json.dumps(value, ensure_ascii=False)))
                cur.close()
                return True
            except Exception as e:
                logger.error(f"DB set error [{key}]: {e}")
    # Fallback: ملف محلي
    try:
        fp = _file_path(key)
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"File set error [{key}]: {e}")
        return False

def db_mode():
    return "supabase" if DATABASE_URL else "local"
