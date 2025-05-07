import sqlite3
from typing import List, Dict
from datetime import datetime

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                site_login TEXT,
                site_password TEXT,
                tests_completed INTEGER DEFAULT 0,
                average_score REAL DEFAULT 0
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score INTEGER,
                correct_answers INTEGER,
                total_questions INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS requisites (
                card_number TEXT,
                sbp TEXT,
                bank TEXT,
                holder_name TEXT
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                subscription_type TEXT
            )
        """)
        self.conn.commit()
    
    def save_user_credentials(self, user_id: int, login: str, password: str):
        self.cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, site_login, site_password)
            VALUES (?, ?, ?)
        """, (user_id, login, password))
        self.conn.commit()
    
    def get_user_credentials(self, user_id: int) -> tuple:
        self.cursor.execute("""
            SELECT site_login, site_password FROM users WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchone()
    
    def save_test_result(self, user_id: int, score: int, correct: int, total: int):
        self.cursor.execute("""
            INSERT INTO test_results (user_id, score, correct_answers, total_questions)
            VALUES (?, ?, ?, ?)
        """, (user_id, score, correct, total))
        self.conn.commit()
    
    def get_user_statistics(self, user_id: int) -> dict:
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_tests,
                AVG(score) as average_score,
                MAX(score) as best_score,
                MAX(test_date) as last_test_date
            FROM test_results 
            WHERE user_id = ?
        """, (user_id,))
        
        row = self.cursor.fetchone()
        return {
            "total_tests": row[0],
            "average_score": round(row[1] or 0, 2),
            "best_score": round(row[2] or 0, 2),
            "last_test_date": row[3] or "Нет данных"
        }
    
    def save_requisites(self, card_number: str, sbp: str, bank: str, holder_name: str):
        self.cursor.execute("DELETE FROM requisites")  # Удаляем старые реквизиты
        self.cursor.execute("""
            INSERT INTO requisites (card_number, sbp, bank, holder_name)
            VALUES (?, ?, ?, ?)
        """, (card_number, sbp, bank, holder_name))
        self.conn.commit()

    def get_requisites(self) -> tuple:
        self.cursor.execute("SELECT card_number, sbp, bank, holder_name FROM requisites")
        return self.cursor.fetchone() or (None, None, None, None)

    def add_subscription(self, user_id: int, days: int, subscription_type: str):
        self.cursor.execute("""
            INSERT OR REPLACE INTO subscriptions (user_id, end_date, subscription_type)
            VALUES (?, datetime('now', '+' || ? || ' days'), ?)
        """, (user_id, days, subscription_type))
        self.conn.commit()

    def get_subscription(self, user_id: int) -> dict:
        self.cursor.execute("""
            SELECT end_date, subscription_type FROM subscriptions
            WHERE user_id = ? AND end_date > datetime('now')
        """, (user_id,))
        row = self.cursor.fetchone()
        return {"active": bool(row), "end_date": row[0] if row else None, "type": row[1] if row else None}

    def get_subscription_details(self, user_id: int) -> dict:
        self.cursor.execute("""
            SELECT end_date, subscription_type 
            FROM subscriptions 
            WHERE user_id = ? AND end_date > datetime('now')
        """, (user_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return {"active": False, "end_date": None, "type": None, "time_left": None}
            
        end_date = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
        time_left = end_date - datetime.now()
        
        return {
            "active": True,
            "end_date": end_date,
            "type": row[1],
            "time_left": time_left
        }
