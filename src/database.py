import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger('database')
logger.setLevel(logging.DEBUG)

class CompanyDB:
    def __init__(self, db_path="companies.db"):
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    kvk_number TEXT PRIMARY KEY,
                    has_branches BOOLEAN,
                    check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def has_been_checked(self, kvk_number):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT has_branches FROM companies WHERE kvk_number = ?', 
                (kvk_number,)
            )
            result = cursor.fetchone()
            return result is not None

    def store_result(self, kvk_number, has_branches):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO companies (kvk_number, has_branches) VALUES (?, ?)',
                (kvk_number, has_branches)
            )
            conn.commit()
            logger.debug(f"Stored result for KvK {kvk_number}: has_branches={has_branches}")
