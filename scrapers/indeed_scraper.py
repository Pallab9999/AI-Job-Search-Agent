import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

def scrape_indeed(keyword: str, location: str, max_results: int = 50) -> List[Dict]:
    """Scrape job listings from Indeed."""
    logger.info(f"Scraping Indeed for '{keyword}' in '{location}'...")
    jobs = []
    start = 0
    
    while len(jobs) < max_results:
        url = f"https://www.indeed.com/jobs?q={requests.utils.quote(keyword)}&l={requests.utils.quote(location)}&start={start}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        try:
            # Note: Indeed heavily blocks automated requests. This is a basic implementation.
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            if not job_cards:
                logger.warning("No job cards found on Indeed. May be blocked.")
                break
                
            for card in job_cards:
                if len(jobs) >= max_results:
                    break
                    
                title_elem = card.find('h2', class_='jobTitle')
                title = title_elem.text.strip() if title_elem else "Unknown"
                
                company_elem = card.find('span', {'data-testid': 'company-name'})
                company = company_elem.text.strip() if company_elem else "Unknown"
                
                location_elem = card.find('div', {'data-testid': 'text-location'})
                loc = location_elem.text.strip() if location_elem else "Unknown"
                
                snippet_elem = card.find('div', class_='job-snippet')
                snippet = snippet_elem.text.strip() if snippet_elem else ""
                
                link_elem = title_elem.find('a') if title_elem else None
                href = f"https://www.indeed.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else ""
                
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "description": snippet,
                    "url": href,
                    "date_posted": "Recent",
                    "source": "Indeed"
                })
                
            start += 10
            time.sleep(random.uniform(1.0, 3.0))
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping Indeed: {e}")
            break
            
    return jobs
