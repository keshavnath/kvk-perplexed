import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import sys
import os
from pathlib import Path
import json
import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scraper import CompanyScraper, RateLimitException, TimeoutException, RetryableError, ProxyConnectionException

class TestRateLimit(unittest.TestCase):
    def setUp(self):
        # Load the actual rate limit HTML sample
        html_path = Path(__file__).parent.parent / 'html-samples' / 'html_rate_limited.html'
        with open(html_path, 'r', encoding='utf-8') as f:
            self.rate_limit_html = f.read()

    @pytest.mark.rate_limit
    def test_rate_limit_detection(self):
        """Test rate limit detection using actual sample HTML"""
        is_rate_limited = CompanyScraper.is_rate_limited(self.rate_limit_html)
        self.assertTrue(is_rate_limited, "Failed to detect rate limit in sample HTML")
        
        # Verify message text contains expected phrase
        soup = BeautifulSoup(self.rate_limit_html, 'html.parser')
        message_div = soup.find('div', id='message')
        self.assertIsNotNone(message_div, "Message div not found")
        self.assertIn('higher than expected rate', message_div.get_text().lower(),
                     "Rate limit phrase not found in message")

    # @pytest.mark.rate_limit
    # def test_rate_limit_false_positive(self):
    #     """Test that normal HTML doesn't trigger rate limit detection"""
    #     normal_html = '<div id="message">Normal message</div>'
    #     self.assertFalse(
    #         CompanyScraper.is_rate_limited(normal_html), 
    #         "False positive in rate limit detection"
    #     )

class TestCompanyScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = CompanyScraper()
        
        # Load test company data
        data_path = Path(__file__).parent / 'data' / 'test_companies.json'
        with open(data_path, 'r', encoding='utf-8') as f:
            self.test_companies = json.load(f)
    
    def tearDown(self):
        if hasattr(self, 'scraper') and hasattr(self.scraper, 'driver'):
            self.scraper.driver.quit()
    
    @pytest.mark.branches
    def test_branch_detection_real_companies(self):
        """Test branch detection with real companies"""
        test_cases = [
            {
                'type': 'has_branches',
                'expected': True
            },
            {
                'type': 'no_branches',
                'expected': False
            }
        ]
        
        for case in test_cases:
            company_data = self.test_companies[case['type']]
            result = self.scraper._check_company_size_impl(
                company_data['company_name'], 
                company_data['kvk_number']
            )
            
            self.assertEqual(
                result, 
                case['expected'],
                f"Failed for {company_data['company_name']} (KvK {company_data['kvk_number']})"
            )

if __name__ == '__main__':
    unittest.main()
