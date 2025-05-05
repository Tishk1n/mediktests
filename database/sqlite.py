import sqlite3
from typing import List, Dict

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
