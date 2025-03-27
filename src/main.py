import logging
from tqdm import tqdm
import pandas as pd
import argparse
import re
from datetime import datetime
import os
from database import CompanyDB

def get_default_log_filename():
    """Generate default log filename with timestamp and process ID"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pid = os.getpid()
    return f"kvk_scraper_{timestamp}_pid{pid}.log"

def setup_logging(level=logging.INFO, log_file=None):
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Console handler - for main module
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    # Only show main module logs in console
    console_handler.addFilter(lambda record: record.name == "__main__")
    root_logger.addHandler(console_handler)
    
    # File handler - for scraper module with DEBUG level
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # Ensure debug messages are captured
        # Only save scraper module logs to file
        scraper_logger = logging.getLogger('scraper')
        scraper_logger.addHandler(file_handler)
        scraper_logger.setLevel(logging.DEBUG)
    
    # Quiet noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def clean_kvk_number(kvk):
    """Clean and standardize KvK number format.
    Handles floats, ints and strings, ensures 8-digit format."""
    try:
        # Handle float inputs first
        if isinstance(kvk, float):
            kvk = int(kvk)
        
        # Convert to string
        kvk_str = str(kvk)
        
        # Extract only digits
        digits = re.sub(r'\D', '', kvk_str)
        
        # Convert to integer to remove any leading zeros
        number = int(digits)
        
        # Format back to 8-digit string
        cleaned = f"{number:08d}"
        
        # Validate length
        if len(cleaned) != 8:
            logger.warning(f"Invalid KvK number length after cleaning: {kvk} -> {cleaned}")
            return None
            
        return cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning KvK number {kvk}: {str(e)}")
        return None

from scraper import CompanyScraper

def create_big_company_database(input_file, db_path="companies.db", limit=None):
    """
    Process companies and store results in SQL database
    Args:
        input_file: Path to input CSV file
        db_path: Path to SQLite database
        limit: Optional maximum number of rows to process
    """
    logger.info(f"Reading input file: {input_file}")
    df = pd.read_csv(input_file)
    if limit:
        logger.info(f"Limiting to first {limit} rows")
        df = df.head(limit)
    
    total_companies = len(df)
    logger.info(f"Processing {total_companies} companies")
    
    scraper = CompanyScraper()
    db = CompanyDB(db_path)
    
    with tqdm(total=total_companies, desc="Processing companies", unit="company") as pbar:
        for _, row in df.iterrows():
            kvk = clean_kvk_number(row['kvk_number'])
            company_name = row['company_name']
            
            if kvk is None:
                logger.warning(f"Skipping invalid KvK number: {row['kvk_number']}")
                pbar.update(1)
                continue
                
            # Skip if already checked
            if db.has_been_checked(kvk):
                logger.debug(f"Already processed {company_name} (KvK {kvk})")
                pbar.update(1)
                continue
            
            # Process and store immediately
            result = scraper.check_company_size(company_name, kvk)
            if result is not None:
                db.store_result(company_name, kvk, result)
            pbar.update(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process companies and store results in database')
    parser.add_argument('input_file', type=str, help='Path to input CSV file with kvk_number and company_name columns')
    parser.add_argument('--db-path', type=str, default='companies.db', help='SQLite database path (default: companies.db)')
    parser.add_argument('--limit', type=int, help='Only process the first N rows of the input file')
    parser.add_argument('--log-file', type=str, default=get_default_log_filename(), 
                       help='Save logs to specified file')
    
    args = parser.parse_args()
    setup_logging(log_file=args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting company processing")
    create_big_company_database(args.input_file, args.db_path, args.limit)
    logger.info("Processing complete")
