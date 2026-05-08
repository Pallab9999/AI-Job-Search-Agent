import logging
from duckduckgo_search import DDGS
from typing import List, Dict

logger = logging.getLogger(__name__)

def scrape_ddg(keyword: str, location: str, max_results: int = 20) -> List[Dict]:
    """Scrapes jobs using DuckDuckGo search API."""
    jobs = []
    
    # We will formulate a deep search query targeting common ATS and job boards
    query = f'"{keyword}" "{location}" (site:lever.co OR site:greenhouse.io OR site:workday.com OR site:jobs.ashbyhq.com)'
    
    logger.info(f"Scraping DuckDuckGo for: {query}")
    
    try:
        results = DDGS().text(query, max_results=max_results)
        for r in results:
            jobs.append({
                "title": r.get("title", ""),
                "company": "See Link (via DDG)",
                "location": location,
                "url": r.get("href", ""),
                "description": r.get("body", "")
            })
    except Exception as e:
        logger.error(f"Error scraping DuckDuckGo: {e}")
        
    return jobs
