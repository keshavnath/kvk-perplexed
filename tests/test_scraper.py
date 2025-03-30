import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scraper import CompanyScraper, RateLimitException

class TestCompanyScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = CompanyScraper()
        
    def tearDown(self):
        self.scraper.driver.quit()
        
    @patch('selenium.webdriver.Chrome')
    def test_rate_limit_detection(self, mock_chrome):
        # Mock the webdriver response with rate limit page
        with open('html-samples/html_rate_limited.html', 'r') as f:
            rate_limit_html = f.read()
            
        mock_driver = Mock()
        mock_driver.page_source = rate_limit_html
        mock_chrome.return_value = mock_driver
        
        self.scraper.driver = mock_driver
        
        with self.assertRaises(RateLimitException):
            self.scraper._check_company_size_impl("Test Company", "12345678")
            
    def test_branch_detection(self):
        # Test cases with different HTML structures
        test_cases = [
            {
                'html': '<div id="data-table-branch_relationship_subject">Branch data</div>',
                'expected': True
            },
            {
                'html': '<div class="sidebar-item" id="similarly_named"><li>branch office</li></div>',
                'expected': True
            },
            {
                'html': '<table class="company-data-object">No branch info</table>',
                'expected': False
            }
        ]
        
        for case in test_cases:
            mock_driver = Mock()
            mock_driver.page_source = case['html']
            self.scraper.driver = mock_driver
            
            result = self.scraper._check_company_size_impl("Test Company", "12345678")
            self.assertEqual(result, case['expected'])

if __name__ == '__main__':
    unittest.main()
