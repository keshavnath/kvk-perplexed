import logging
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Create module-level logger
logger = logging.getLogger('scraper')
logger.setLevel(logging.DEBUG)

class RateLimitException(Exception):
    """Raised when rate limiting is detected"""
    pass

class CompanyScraper:
    def __init__(self):
        self.base_url = "https://opencorporates.com/companies/nl/"
        self.setup_browser()
        
    def setup_browser(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920x1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def check_company_size(self, company_name, kvk_number):
        try:
            url = f"{self.base_url}{kvk_number}"
            logger.debug(f"Requesting URL: {url}")
            
            self.driver.get(url)
            time.sleep(2)
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'title')))
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Rate limit detection based on actual response page
            message_div = soup.find('div', id='message')
            if message_div and any(phrase in message_div.get_text().lower() for phrase in [
                'higher than expected rate',
                'accessing opencorporates at a higher than expected rate',
                'ip address may be accessing opencorporates at a higher'
            ]):
                logger.error(f"Rate limit detected while processing {company_name} (KvK {kvk_number})")
                raise RateLimitException("Rate limit detected")
            
            # Verify we're on a company page
            title = soup.find('title')
            if not title or 'OpenCorporates' not in title.text:
                logger.warning(f"Not a valid OpenCorporates page for KvK {kvk_number}")
                return False
            
            # Branch detection checks
            branch_section = soup.find('div', id='data-table-branch_relationship_subject')
            similar_companies = soup.find('div', {'class': 'sidebar-item', 'id': 'similarly_named'})
            branch_table = soup.find('table', {'class': 'company-data-object'})
            
            # Combined check for branches
            has_branches = bool(branch_section) or (
                similar_companies and any('branch' in li.get_text().lower() 
                                       for li in similar_companies.find_all('li'))
            ) or (
                branch_table and 'branch' in branch_table.get_text().lower()
            )
            
            logger.info(f"{company_name} (KvK {kvk_number}): {'Has branches' if has_branches else 'No branches detected'}")
            return has_branches
            
        except RateLimitException:
            logger.error(f"Stopping processing due to rate limit for {company_name} (KvK {kvk_number})")
            return None
        except Exception as e:
            logger.error(f"Error processing {company_name} (KvK {kvk_number}): {str(e)}")
            return None
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
