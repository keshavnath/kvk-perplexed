import logging
from tqdm import tqdm
import pandas as pd
import argparse
import re
from datetime import datetime
import os
from database import CompanyDB
from pathlib import Path
from scraper import CompanyScraper, RateLimitException, TimeoutException, ProxyConnectionException

def get_default_log_directory():
    """Generate default log directory with timestamp and process ID"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pid = os.getpid()
    logs_dir = Path('./logs') / f"kvk_scraper_{timestamp}_pid{pid}"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def setup_logging(level=logging.INFO, log_dir=None):
    if log_dir:
        log_dir = Path(log_dir)
    else:
        log_dir = get_default_log_directory()

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
    console_handler.addFilter(lambda record: record.name == "__main__")
    root_logger.addHandler(console_handler)
    
    # Configure module loggers
    modules = {
        'scraper': 'scraper.log',
        'database': 'database.log',
        'proxy': 'proxy.log'
    }
    
    # Add error logger for fatal errors
    error_logger = logging.getLogger('error')
    error_handler = logging.FileHandler(log_dir / 'fatal_errors.log')
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    
    for module, filename in modules.items():
        logger = logging.getLogger(module)
        logger.setLevel(logging.DEBUG)
        
        file_handler = logging.FileHandler(log_dir / filename)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    
    # Quiet noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return error_logger  # Return error logger for fatal errors

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

def create_big_company_database(input_file, db_path="companies.db", start_index=None, end_index=None, retry_failed=False, retry_small=False):
    """
    Process companies and store results in SQL database
    Args:
        input_file: Path to input CSV file
        db_path: Path to SQLite database
        start_index: Optional starting index for processing (inclusive)
        end_index: Optional ending index for processing (exclusive)
        retry_failed: If True, retry companies that previously returned None (-1)
        retry_small: If True, retry companies that were marked as having no branches (0)
    """
    logger.info(f"Reading input file: {input_file}")
    df = pd.read_csv(input_file)
    
    # Handle index bounds
    if start_index is not None or end_index is not None:
        start = start_index if start_index is not None else 0
        end = end_index if end_index is not None else len(df)
        logger.info(f"Processing rows {start} to {end}")
        df = df.iloc[start:end]
    
    total_companies = len(df)
    logger.info(f"Processing {total_companies} companies")
    
    scraper = CompanyScraper()
    db = CompanyDB(db_path)
    
    # Add statistics counters
    stats = {
        'total': total_companies,
        'skipped_invalid_kvk': 0,
        'skipped_already_checked': 0,
        'none_results': 0,
        'stored_true': 0,
        'stored_false': 0
    }
    
    current_index = start if start_index is not None else 0
    error_logger = logging.getLogger('error')
    
    try:
        with tqdm(total=total_companies, desc="Processing companies", unit="company") as pbar:
            for idx, (_, row) in enumerate(df.iterrows()):
                current_index = idx + (start_index if start_index is not None else 0)
                kvk = clean_kvk_number(row['kvk_number'])
                company_name = row['company_name']
                
                if kvk is None:
                    stats['skipped_invalid_kvk'] += 1
                    logger.warning(f"Skipping invalid KvK number: {row['kvk_number']}")
                    pbar.update(1)
                    continue
                    
                # Skip if already checked, unless we want to retry
                if db.has_been_checked(kvk):
                    should_retry = (retry_failed and db.is_failed_result(kvk)) or \
                                 (retry_small and db.is_no_branches_result(kvk))
                    if should_retry:
                        logger.debug(f"Retrying {company_name} (KvK {kvk})")
                    else:
                        stats['skipped_already_checked'] += 1
                        logger.debug(f"Already processed {company_name} (KvK {kvk})")
                        pbar.update(1)
                        continue
                
                try:
                    logger.debug(f"Processing company {company_name} ({kvk})")
                    result = scraper.check_company_size(company_name, kvk)
                    
                    if result is not None:  # Valid response (True/False)
                        stats['stored_true' if result else 'stored_false'] += 1
                        db.store_result(company_name, kvk, result)
                        logger.debug(f"Stored valid result: {result}")
                    else:  # Error occurred (None)
                        stats['none_results'] += 1
                        db.store_result(company_name, kvk, -1)
                        logger.debug("Stored error result (-1)")
                    pbar.update(1)
                    
                except (RateLimitException, TimeoutException, ProxyConnectionException) as e:
                    error_msg = f"Connection error at index {current_index}. Last company: {company_name} (KvK {kvk}). Error: {str(e)}"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    raise  # Re-raise to exit processing
                    
                except Exception as e:
                    if 'invalid session id' in str(e):
                        error_msg = f"Browser session disconnected at index {current_index}. Last company: {company_name} (KvK {kvk})"
                        logger.error(error_msg)
                        error_logger.error(error_msg)
                        raise
                    logger.error(f"Unexpected error: {str(e)}")
                    stats['none_results'] += 1
                    db.store_result(company_name, kvk, -1)
                    pbar.update(1)
    
    except RateLimitException:
        error_logger.error(f"Exiting due to rate limit at index {current_index}")
    except Exception as e:
        if 'invalid session id' in str(e):
            error_logger.error(f"Exiting due to browser disconnection at index {current_index}")
        else:
            error_logger.error(f"Fatal error at index {current_index}: {str(e)}")
    finally:
        # Log statistics to both main and error loggers
        stats_message = f"Processing statistics (up to index {current_index}):"
        for key, value in stats.items():
            stats_message += f"\n  {key}: {value}"
        
        logger.info(stats_message)
        error_logger.error(stats_message)  # Include in fatal errors log

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process companies and store results in database')
    parser.add_argument('input_file', type=str, help='Path to input CSV file with kvk_number and company_name columns')
    parser.add_argument('--db-path', type=str, default='./db/companies.db', help='SQLite database path (default: ./db/companies.db)')
    parser.add_argument('--start-index', type=int, help='Starting row index to process (inclusive)')
    parser.add_argument('--end-index', type=int, help='Ending row index to process (exclusive)')
    parser.add_argument('--log-dir', type=str, default=None,
                       help='Directory to store log files (default: ./logs/kvk_scraper_TIMESTAMP_pidNUM/)')
    parser.add_argument('--retry-failed', action='store_true', 
                       help='Retry processing companies that previously failed (-1)')
    parser.add_argument('--retry-small', action='store_true',
                       help='Retry processing companies previously marked as having no branches (0)')
    
    args = parser.parse_args()
    error_logger = setup_logging(log_dir=args.log_dir)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting company processing")
    create_big_company_database(args.input_file, args.db_path, args.start_index, args.end_index, args.retry_failed, args.retry_small)
    logger.info("Processing complete")
