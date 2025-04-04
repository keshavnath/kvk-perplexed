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
            
            # First check title for rate limit page
            title = soup.find('title')
            if title:
                title_text = title.text.strip()
                logger.debug(f"Page title: '{title_text}'")
                if 'too many requests' in title_text.lower() or '429' in title_text:
                    logger.warning(f"Rate limit detected in title: {title_text}")
                    return True
            
            # Then check for rate limit message
            message_div = soup.find('div', id='message')
            if message_div:
                message_text = message_div.get_text().lower()
                logger.debug(f"Found message div: '{message_text}'")
                
                rate_limit_phrases = [
                    'higher than expected rate',
                    'accessing opencorporates at a higher than expected rate',
                    'ip address may be accessing opencorporates at a higher',
                    'rate limit',
                    'too many requests'
                ]
                
                for phrase in rate_limit_phrases:
                    if phrase in message_text:
                        logger.warning(f"Rate limit detected with phrase: '{phrase}'")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error in rate limit check: {str(e)}")
            logger.debug(f"HTML content: {html_content[:500]}...")
            return False

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
        """Check company size with proxy rotation and rate limit handling"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:  # On retry, get new proxy
                    proxy = self.proxy_manager.get_proxy()
                    if not proxy:
                        logger.error("No working proxies available")
                        raise RateLimitException("No working proxies available")
                    logger.info(f"Retrying with new proxy: {proxy}")
                    self.setup_browser(proxy)
                
                return self._check_company_size_impl(company_name, kvk_number)
                
            except RateLimitException as e:
                last_exception = e
                logger.warning(f"Rate limit with current proxy (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error("Rate limit persists after all retries")
                continue
            
            except Exception as e:
                last_exception = e
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                break
        
        if isinstance(last_exception, RateLimitException):
            raise last_exception
        return None
    
    def _check_company_size_impl(self, company_name, kvk_number):
        """Implementation of the actual check"""
        try:
            url = f"{self.base_url}{kvk_number}"
            logger.debug(f"Requesting URL: {url}")
            
            self.driver.get(url)
            time.sleep(2)
            
            page_source = self.driver.page_source
            logger.debug(f"Got response for {kvk_number}, length: {len(page_source)}")
            
            # Check rate limit BEFORE any other processing
            if self.is_rate_limited(page_source):
                logger.error(f"Rate limit detected for {kvk_number}")
                raise RateLimitException(f"Rate limit detected for {kvk_number}")
            
            # Only continue if not rate limited
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Verify we're on a company page
            title = soup.find('title')
            if not title:
                logger.error(f"No title element found for {kvk_number}")
                return None
                
            title_text = title.text.lower()
            logger.debug(f"Page title: {title_text}")
            
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
        
        except RateLimitException as e:
            logger.error(f"Rate limit caught: {str(e)}")
            raise  # Re-raise to ensure it's caught by check_company_size
        except Exception as e:
            logger.error(f"Error in branch check: {str(e)}")
            return None
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
