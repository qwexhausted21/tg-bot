import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создание таблицы leads, если она ещё не существует."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            comment TEXT,
            date_added TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_lead(user_id: int, username: str | None, name: str, phone: str, comment: str) -> int:
    """Сохранение новой заявки в БД. Возвращает ID созданной записи."""
    conn = get_connection()
    cursor = conn.cursor()
    date_added = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO leads (user_id, username, name, phone, comment, date_added)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, name, phone, comment, date_added))
    conn.commit()
    lead_id = cursor.lastrowid
    conn.close()
    return lead_id


def get_leads_count() -> int:
    """Получение общего количества заявок."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_last_leads(limit: int = 5) -> list[dict]:
    """Получение последних N заявок."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, username, name, phone, comment, date_added
        FROM leads
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_leads() -> list[dict]:
    """Получение всех заявок для выгрузки."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, username, name, phone, comment, date_added
        FROM leads
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]