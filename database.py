import sqlite3
from datetime import datetime, timedelta
import random
import string

conn = sqlite3.connect("locker.db", check_same_thread=False)
c = conn.cursor()

# Locks table
c.execute('''CREATE TABLE IF NOT EXISTS locks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_id TEXT,
    file_type TEXT,
    password TEXT DEFAULT '',
    force_join INTEGER DEFAULT 0,
    one_time INTEGER DEFAULT 0,
    expiry TIMESTAMP,
    delete_code TEXT UNIQUE,
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    premium INTEGER DEFAULT 0
)''')

# Users table
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    referrals INTEGER DEFAULT 0,
    referred_by INTEGER,
    is_premium INTEGER DEFAULT 0
)''')

conn.commit()

def add_user(user_id, username="", referred_by=None):
    c.execute("INSERT OR IGNORE INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
              (user_id, username, referred_by))
    conn.commit()

def get_user(user_id):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        return dict(zip([desc[0] for desc in c.description], row))
    return None

def make_premium(user_id):
    c.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (user_id,))
    conn.commit()

def create_lock(**kwargs):
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    c.execute("""INSERT INTO locks 
                 (user_id, file_id, file_type, password, force_join, one_time, expiry, delete_code, premium)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (kwargs['user_id'], kwargs['file_id'], kwargs['file_type'],
               kwargs.get('password',''), kwargs.get('force_join',0), kwargs.get('one_time',0),
               kwargs.get('expiry'), code, kwargs.get('premium',0)))
    conn.commit()
    return code

def get_lock_by_code(code):
    c.execute("SELECT * FROM locks WHERE delete_code=?", (code,))
    row = c.fetchone()
    if row:
        return dict(zip([desc[0] for desc in c.description], row))
    return None

def increment_views(lock_id):
    c.execute("UPDATE locks SET views = views + 1 WHERE id=?", (lock_id,))

def delete_lock(code):
    c.execute("DELETE FROM locks WHERE delete_code=?", (code,))
    conn.commit()

def get_stats():
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")
    premium = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM locks")
    total_locks = c.fetchone()[0]
    return total_users, premium, total_locks
