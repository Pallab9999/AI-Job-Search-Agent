import requests
from bs4 import BeautifulSoup
import logging
import urllib.parse
from typing import List, Dict

logger = logging.getLogger(__name__)

def scrape_academic_jobs(keyword: str, max_results: int = 50) -> List[Dict]:
    """Scrape academic jobs (placeholder for academicjobsonline or similar).
    For demonstration, we use a simple generic scraper against nature careers as an example.
    """
    logger.info(f"Scraping Academic jobs for '{keyword}'...")
    jobs = []
    
    url = f"https://www.nature.com/naturecareers/job-search?keywords={urllib.parse.quote(keyword)}"
    headers = {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        job_cards = soup.find_all('div', class_='c-job-card')
        
        for card in job_cards[:max_results]:
            title_elem = card.find('h3', class_='c-job-card__title')
            title = title_elem.text.strip() if title_elem else "Unknown"
            
            company_elem = card.find('li', class_='c-job-card__company')
            company = company_elem.text.strip() if company_elem else "Unknown"
            
            location_elem = card.find('li', class_='c-job-card__location')
            loc = location_elem.text.strip() if location_elem else "Unknown"
            
            link_elem = title_elem.find('a') if title_elem else None
            href = f"https://www.nature.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else ""
            
            jobs.append({
                "title": title,
                "company": company,
                "location": loc,
                "description": "",
                "url": href,
                "date_posted": "Recent",
                "source": "Academic"
            })
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error scraping Academic jobs: {e}")
        
    return jobs
