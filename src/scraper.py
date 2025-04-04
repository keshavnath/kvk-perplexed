import logging
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from proxy_manager import ProxyManager

# Create module-level logger
logger = logging.getLogger('scraper')
logger.setLevel(logging.DEBUG)

class RateLimitException(Exception):
    """Raised when rate limiting is detected"""
    pass

class CompanyScraper:
    @staticmethod
    def is_rate_limited(html_content):
        """Check if HTML content indicates rate limiting"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Critical: Check title first as it's the most reliable indicator
            title = soup.find('title')
            if title and 'Too many requests' in title.text:
                logger.error(f"Rate limit detected in title: '{title.text}'")
                return True
            
            # Fallback checks
            message_div = soup.find('div', id='message')
            if message_div:
                message_text = message_div.get_text()
                logger.debug(f"Found message: '{message_text}'")
                if any(phrase in message_text.lower() for phrase in [
                    'higher than expected rate',
                    'too many requests',
                    'rate limit'
                ]):
                    logger.error(f"Rate limit detected in message: '{message_text}'")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False  # Don't raise on parse errors

    def __init__(self):
        self.base_url = "https://opencorporates.com/companies/nl/"
        self.proxy_manager = ProxyManager()
        self.setup_browser()
    
    def setup_browser(self, proxy=None):
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920x1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')
        
        if hasattr(self, 'driver'):
            self.driver.quit()
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def check_company_size(self, company_name, kvk_number, max_retries=3):
        """Primary entry point for checking company size"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    proxy = self.proxy_manager.get_proxy()
                    if not proxy:
                        raise RateLimitException("No working proxies available")
                    logger.info(f"Attempt {attempt + 1}: Using proxy {proxy}")
                    self.setup_browser(proxy)

                result = self._check_company_size_impl(company_name, kvk_number)
                return result

            except RateLimitException as e:
                logger.error(f"Rate limit on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("All retries exhausted")
                    raise  # Re-raise on final attempt
                continue  # Try next proxy

    def _check_company_size_impl(self, company_name, kvk_number):
        """Implementation that does the actual check"""
        try:
            url = f"{self.base_url}{kvk_number}"
            logger.debug(f"Requesting {url}")
            
            self.driver.get(url)
            time.sleep(2)  # Allow page to load
            
            page_source = self.driver.page_source
            
            # Check rate limit before any processing
            if self.is_rate_limited(page_source):
                raise RateLimitException(f"Rate limit hit for {company_name} (KvK {kvk_number})")
            
            # Only continue if not rate limited
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Verify we're on a company page
            title = soup.find('title')
            if not title:
                logger.error(f"No title element found for {kvk_number}")
                return None
                
            title_text = title.text.lower()
            # logger.debug(f"Page title: {title_text}")
            
            if 'opencorporates' not in title_text:
                logger.error(f"Not on OpenCorporates page for {kvk_number}")
                raise RateLimitException("Redirected from OpenCorporates - likely rate limited")

            has_branches = False
            
            branch_section = soup.find('div', id='data-table-branch_relationship_subject')
            if branch_section:
                logger.debug(f"Found branch section for {kvk_number}")
                has_branches = True
            
            similar_companies = soup.find('div', {'class': 'sidebar-item', 'id': 'similarly_named'})
            if similar_companies and any('branch' in li.get_text().lower() 
                                      for li in similar_companies.find_all('li')):
                logger.debug(f"Found branch in similar companies for {kvk_number}")
                has_branches = True
            
            branch_table = soup.find('table', {'class': 'company-data-object'})
            if branch_table and 'branch' in branch_table.get_text().lower():
                logger.debug(f"Found branch in company data table for {kvk_number}")
                has_branches = True
            
            # Log clear outcome
            if has_branches:
                logger.info(f"{company_name} (KvK {kvk_number}): Has branches")
            else:
                logger.info(f"{company_name} (KvK {kvk_number}): Confirmed no branches")
            
            return has_branches  # Will be False if no branch indicators found
        
        except RateLimitException:
            raise  # Always re-raise rate limit exceptions
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
