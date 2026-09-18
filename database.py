import sqlite3
import os
from datetime import datetime

DB_PATH = 'data/sales_history.db'

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_name TEXT,
            keyword TEXT,
            scraped_content TEXT,
            generated_hook TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_history(target, keyword, content, hook):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO history (target_name, keyword, scraped_content, generated_hook, created_at) VALUES (?, ?, ?, ?, ?)',
              (target, keyword, content, hook, datetime.now()))
    conn.commit()
    conn.close()

def get_recent_targets(limit=5):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT target_name, created_at FROM history ORDER BY created_at DESC LIMIT ?', (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    except:
        return []
