import logging
import argparse
import time
from pathlib import Path
from typing import List, Tuple
import sqlite3
from tqdm import tqdm

from database import CompanyDB
from company_details_db import CompanyDetailsDB
from perplexity_client import PerplexityClient
from models import CompanyDetails

logger = logging.getLogger('phase2')
logger.setLevel(logging.DEBUG)

class Phase2Processor:
    def __init__(self, phase1_db_path: str = "./db/companies.db", 
                 phase2_db_path: str = "./db/company_details.db"):
        self.phase1_db_path = Path(phase1_db_path)
        self.phase2_db_path = Path(phase2_db_path)
        
        # Ensure database directories exist
        self.phase1_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.phase2_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize databases and client
        self.phase1_db = CompanyDB(self.phase1_db_path)
        self.phase2_db = CompanyDetailsDB(self.phase2_db_path)
        self.perplexity_client = PerplexityClient()
        
        logger.info("Phase 2 processor initialized")

    def get_companies_with_branches(self) -> List[Tuple[str, str]]:
        """Get companies from Phase 1 DB where has_branches = 1"""
        try:
            with sqlite3.connect(self.phase1_db_path) as conn:
                cursor = conn.execute('''
                    SELECT company_name, kvk_number 
                    FROM companies 
                    WHERE has_branches = 1
                    ORDER BY company_name
                ''')
                companies = cursor.fetchall()
                logger.info(f"Found {len(companies)} companies with branches")
                return companies
        except Exception as e:
            logger.error(f"Error fetching companies with branches: {str(e)}")
            return []

    def get_unprocessed_companies(self) -> List[Tuple[str, str]]:
        """Get companies that haven't been processed in Phase 2 yet"""
        companies_with_branches = self.get_companies_with_branches()
        unprocessed = []
        
        for company_name, kvk_number in companies_with_branches:
            if not self.phase2_db.has_been_processed(kvk_number):
                unprocessed.append((company_name, kvk_number))
        
        logger.info(f"Found {len(unprocessed)} unprocessed companies")
        return unprocessed

    def process_company(self, company_name: str, kvk_number: str) -> bool:
        """Process a single company through Perplexity API"""
        try:
            logger.debug(f"Processing {company_name} (KvK: {kvk_number})")
            
            # Get company details from Perplexity
            details = self.perplexity_client.get_company_details(company_name, kvk_number)
            
            if details is None:
                failure_reason = "No details returned from Perplexity API"
                logger.warning(f"{failure_reason} for {company_name}")
                self.phase2_db.store_failed_attempt(kvk_number, company_name, failure_reason)
                return False
            
            # Store in Phase 2 database regardless of confidence score
            self.phase2_db.store_company_details(kvk_number, company_name, details)
            logger.info(f"Successfully processed {company_name} (confidence: {details.confidence_score})")
            return True
            
        except Exception as e:
            failure_reason = f"Processing error: {str(e)}"
            logger.error(f"Error processing {company_name}: {str(e)}")
            self.phase2_db.store_failed_attempt(kvk_number, company_name, failure_reason)
            return False

    def run_batch_processing(self, max_companies: int = None, delay_seconds: float = 1.0):
        """Run batch processing of companies"""
        unprocessed_companies = self.get_unprocessed_companies()
        
        if max_companies:
            unprocessed_companies = unprocessed_companies[:max_companies]
            
        total_companies = len(unprocessed_companies)
        logger.info(f"Starting batch processing of {total_companies} companies")
        
        if total_companies == 0:
            logger.info("No companies to process")
            return
        
        # Statistics
        stats = {
            'total': total_companies,
            'processed': 0,
            'failed': 0,
            'skipped_low_confidence': 0
        }
        
        try:
            with tqdm(total=total_companies, desc="Processing companies", unit="company") as pbar:
                for idx, (company_name, kvk_number) in enumerate(unprocessed_companies):
                    try:
                        # Process company
                        success = self.process_company(company_name, kvk_number)
                        
                        if success:
                            stats['processed'] += 1
                        else:
                            stats['failed'] += 1
                        
                        pbar.update(1)
                        pbar.set_postfix({
                            'Processed': stats['processed'],
                            'Failed': stats['failed']
                        })
                        
                        # Rate limiting delay
                        if delay_seconds > 0 and idx < total_companies - 1:
                            time.sleep(delay_seconds)
                            
                    except KeyboardInterrupt:
                        logger.info("Processing interrupted by user")
                        break
                    except Exception as e:
                        logger.error(f"Unexpected error processing {company_name}: {str(e)}")
                        stats['failed'] += 1
                        continue
                        
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
        finally:
            # Log final statistics
            logger.info("Processing complete. Statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")

def setup_logging(log_dir: str = None):
    """Setup logging for Phase 2 processing"""
    if log_dir:
        log_dir = Path(log_dir)
    else:
        logs_dir = Path('./logs')
        logs_dir.mkdir(exist_ok=True)
        log_dir = logs_dir
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # File handlers
    phase2_handler = logging.FileHandler(log_dir / 'phase2.log')
    phase2_handler.setFormatter(formatter)
    phase2_handler.setLevel(logging.DEBUG)
    
    perplexity_handler = logging.FileHandler(log_dir / 'perplexity.log')
    perplexity_handler.setFormatter(formatter)
    perplexity_handler.setLevel(logging.DEBUG)
    
    # Setup loggers
    phase2_logger = logging.getLogger('phase2')
    phase2_logger.addHandler(console_handler)
    phase2_logger.addHandler(phase2_handler)
    phase2_logger.setLevel(logging.DEBUG)
    
    perplexity_logger = logging.getLogger('perplexity')
    perplexity_logger.addHandler(perplexity_handler)
    perplexity_logger.setLevel(logging.DEBUG)
    
    company_details_logger = logging.getLogger('company_details')
    company_details_logger.addHandler(phase2_handler)
    company_details_logger.setLevel(logging.DEBUG)

def main():
    parser = argparse.ArgumentParser(description='Phase 2: Process companies with Perplexity API')
    parser.add_argument('--phase1-db', type=str, default='./db/companies.db',
                       help='Path to Phase 1 database')
    parser.add_argument('--phase2-db', type=str, default='./db/company_details.db',
                       help='Path to Phase 2 database')
    parser.add_argument('--max-companies', type=int,
                       help='Maximum number of companies to process')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between API calls in seconds (default: 1.0)')
    parser.add_argument('--log-dir', type=str,
                       help='Directory for log files')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_dir)
    
    try:
        # Initialize processor
        processor = Phase2Processor(args.phase1_db, args.phase2_db)
        
        # Run processing
        processor.run_batch_processing(args.max_companies, args.delay)
        
    except Exception as e:
        logger.error(f"Fatal error in Phase 2 processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()
