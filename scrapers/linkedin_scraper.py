import time
import logging
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse

logger = logging.getLogger(__name__)

def scrape_linkedin(keyword: str, location: str, max_results: int = 50) -> List[Dict]:
    """Scrape job listings from LinkedIn using Selenium."""
    logger.info(f"Scraping LinkedIn for '{keyword}' in '{location}'...")
    jobs = []
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        url = f"https://www.linkedin.com/jobs/search?keywords={urllib.parse.quote(keyword)}&location={urllib.parse.quote(location)}"
        driver.get(url)
        
        # Scroll to load jobs
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height or len(driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list > li")) >= max_results:
                break
            last_height = new_height
            
        job_cards = driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list > li")
        
        for card in job_cards[:max_results]:
            try:
                title_elem = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title")
                title = title_elem.text.strip()
                
                company_elem = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle")
                company = company_elem.text.strip()
                
                location_elem = card.find_element(By.CSS_SELECTOR, "span.job-search-card__location")
                loc = location_elem.text.strip()
                
                url_elem = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
                href = url_elem.get_attribute("href")
                
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "description": "", # Requires clicking to get full description, keeping it brief
                    "url": href,
                    "date_posted": "Recent",
                    "source": "LinkedIn"
                })
            except Exception as e:
                logger.debug(f"Failed to parse a LinkedIn job card: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scraping LinkedIn: {e}")
    finally:
        if driver:
            driver.quit()
            
    return jobs
