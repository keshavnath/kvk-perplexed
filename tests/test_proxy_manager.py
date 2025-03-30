import unittest
from unittest.mock import Mock, patch
import requests
from datetime import datetime
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.proxy_manager import ProxyManager

class TestProxyManager(unittest.TestCase):
    def setUp(self):
        self.proxy_manager = ProxyManager(min_proxies=2)
        
    @patch('requests.get')
    def test_fetch_free_proxies(self, mock_get):
        # Mock proxy list response with realistic HTML structure
        mock_response = Mock()
        mock_response.text = """
        <table class="table table-striped table-bordered">
            <thead>
                <tr><th>IP</th><th>Port</th><th>Code</th><th>Country</th><th>Anonymity</th><th>Google</th><th>Https</th><th>Last Checked</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>192.168.1.1</td>
                    <td>8080</td>
                    <td>NL</td>
                    <td>Netherlands</td>
                    <td>anonymous</td>
                    <td>yes</td>
                    <td>yes</td>
                    <td>1 minute ago</td>
                </tr>
                <tr>
                    <td>192.168.1.2</td>
                    <td>8080</td>
                    <td>NL</td>
                    <td>Netherlands</td>
                    <td>anonymous</td>
                    <td>yes</td>
                    <td>no</td>
                    <td>1 minute ago</td>
                </tr>
            </tbody>
        </table>
        """
        mock_get.return_value = mock_response
        
        proxies = self.proxy_manager._fetch_free_proxies()
        self.assertEqual(len(proxies), 1)
        self.assertEqual(proxies[0], "192.168.1.1:8080")
        
    @patch('requests.get')
    def test_validate_proxies(self, mock_get):
        test_proxies = ["192.168.1.1:8080", "192.168.1.2:8080"]
        
        def mock_request(*args, **kwargs):
            mock_response = Mock()
            # Simulate first proxy working, second failing
            if kwargs['proxies']['http'] == 'http://192.168.1.1:8080':
                mock_response.status_code = 200
            else:
                raise requests.exceptions.RequestException()
            return mock_response
            
        mock_get.side_effect = mock_request
        
        valid_proxies = self.proxy_manager._validate_proxies(test_proxies)
        self.assertEqual(len(valid_proxies), 1)
        self.assertEqual(valid_proxies[0], "192.168.1.1:8080")
        
    def test_proxy_rotation(self):
        # Initialize with test proxies
        self.proxy_manager.proxies = ["192.168.1.1:8080", "192.168.1.2:8080"]
        self.proxy_manager.last_update = datetime.now()  # Ensure last_update is set
        
        proxy1 = self.proxy_manager.get_proxy()
        self.assertIn(proxy1, self.proxy_manager.proxies)

if __name__ == '__main__':
    unittest.main()
