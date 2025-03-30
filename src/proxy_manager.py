import logging
import requests
from bs4 import BeautifulSoup
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

logger = logging.getLogger('proxy')
logger.setLevel(logging.DEBUG)

class ProxyManager:
    def __init__(self, min_proxies=5):
        self.proxies = []
        self.last_update = datetime.now()  # Initialize with current time
        self.min_proxies = min_proxies
        self.update_interval = timedelta(minutes=30)
    
    def get_proxy(self):
        """Get a random working proxy"""
        if not self.proxies or (datetime.now() - self.last_update > self.update_interval):
            self.update_proxy_list()
        return random.choice(self.proxies) if self.proxies else None
    
    def update_proxy_list(self):
        """Fetch and validate new proxies"""
        raw_proxies = self._fetch_free_proxies()
        valid_proxies = self._validate_proxies(raw_proxies)
        
        if len(valid_proxies) < self.min_proxies:
            logger.warning(f"Found only {len(valid_proxies)} valid proxies")
        
        self.proxies = valid_proxies
        self.last_update = datetime.now()
        logger.info(f"Updated proxy list with {len(self.proxies)} valid proxies")
    
    def _fetch_free_proxies(self):
        """Fetch proxies from multiple free proxy lists"""
        proxies = set()
        
        # Free-Proxy-List.net
        try:
            response = requests.get('https://free-proxy-list.net/')
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for table within specific class or structure
            table = soup.find('table', {'class': 'table table-striped table-bordered'})
            if not table:
                table = soup.find('table')  # Fallback to any table
            
            if table:
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) >= 7:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        https = cols[6].text.strip().lower() == 'yes'
                        if https:
                            proxy = f"{ip}:{port}"
                            proxies.add(proxy)
            else:
                logger.warning("No proxy table found in response")
                
        except Exception as e:
            logger.error(f"Error fetching from free-proxy-list.net: {e}")
        
        return list(proxies)
    
    def _validate_proxies(self, proxy_list, timeout=10):
        """Test proxies in parallel and return working ones"""
        valid_proxies = []
        
        def test_proxy(proxy):
            try:
                proxies = {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }
                response = requests.get(
                    'https://opencorporates.com',
                    proxies=proxies,
                    timeout=timeout
                )
                if response.status_code == 200:
                    return proxy
            except:
                pass
            return None
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(test_proxy, proxy) for proxy in proxy_list]
            for future in as_completed(futures):
                if future.result():
                    valid_proxies.append(future.result())
        
        return valid_proxies
