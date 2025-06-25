import sqlite3
import logging
from pathlib import Path
from typing import Optional
from models import CompanyDetails
import json

logger = logging.getLogger('company_details')
logger.setLevel(logging.DEBUG)

class CompanyDetailsDB:
    def __init__(self, db_path="company_details.db"):
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS company_details (
                    kvk_number TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    industries TEXT NOT NULL,  -- JSON array
                    employee_range TEXT NOT NULL,
                    headquarters_location TEXT NOT NULL,
                    business_description TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    homepage_url TEXT DEFAULT '',
                    linkedin_url TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create failed attempts table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS failed_attempts (
                    kvk_number TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    failure_reason TEXT,
                    attempt_count INTEGER DEFAULT 1,
                    first_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            logger.debug("Company details database initialized")

    def has_been_processed(self, kvk_number: str) -> bool:
        """Check if company has already been processed successfully OR failed"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if successfully processed
            cursor = conn.execute(
                'SELECT kvk_number FROM company_details WHERE kvk_number = ?', 
                (kvk_number,)
            )
            if cursor.fetchone() is not None:
                return True
                
            # Check if failed
            cursor = conn.execute(
                'SELECT kvk_number FROM failed_attempts WHERE kvk_number = ?', 
                (kvk_number,)
            )
            return cursor.fetchone() is not None

    def store_company_details(self, kvk_number: str, company_name: str, details: CompanyDetails):
        """Store company details from Perplexity response"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO company_details 
                (kvk_number, company_name, industries, employee_range, 
                 headquarters_location, business_description, confidence_score,
                 homepage_url, linkedin_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                kvk_number,
                company_name,
                json.dumps(details.industries),
                details.employee_range,
                details.headquarters_location,
                details.business_description,
                details.confidence_score,
                details.homepage_url,
                details.linkedin_url
            ))
            conn.commit()
            logger.info(f"Stored details for {company_name} (KvK {kvk_number})")

    def store_failed_attempt(self, kvk_number: str, company_name: str, failure_reason: str):
        """Store a failed processing attempt"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO failed_attempts 
                (kvk_number, company_name, failure_reason, attempt_count, 
                 first_failed_at, last_failed_at)
                VALUES (?, ?, ?, 
                    COALESCE((SELECT attempt_count + 1 FROM failed_attempts WHERE kvk_number = ?), 1),
                    COALESCE((SELECT first_failed_at FROM failed_attempts WHERE kvk_number = ?), CURRENT_TIMESTAMP),
                    CURRENT_TIMESTAMP)
            ''', (kvk_number, company_name, failure_reason, kvk_number, kvk_number))
            conn.commit()
            logger.info(f"Stored failed attempt for {company_name} (KvK {kvk_number}): {failure_reason}")

    def get_failed_attempts(self) -> list:
        """Get all failed attempts"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT kvk_number, company_name, failure_reason, attempt_count,
                       first_failed_at, last_failed_at
                FROM failed_attempts 
                ORDER BY last_failed_at DESC
            ''')
            return cursor.fetchall()

    def get_companies_by_confidence(self, min_confidence: float = 0.0) -> list:
        """Get companies filtered by minimum confidence score"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT kvk_number, company_name, industries, employee_range, 
                       headquarters_location, business_description, confidence_score,
                       homepage_url, linkedin_url
                FROM company_details 
                WHERE confidence_score >= ?
                ORDER BY confidence_score DESC
            ''', (min_confidence,))
            return cursor.fetchall()
