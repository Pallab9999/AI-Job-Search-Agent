import pytest
from unittest.mock import patch, MagicMock
from scrapers.indeed_scraper import scrape_indeed
from scrapers.academic_scraper import scrape_academic_jobs

@patch('scrapers.indeed_scraper.requests.get')
def test_scrape_indeed_empty(mock_get):
    # Mock empty or blocked response
    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    jobs = scrape_indeed("python", "remote", max_results=10)
    assert len(jobs) == 0

@patch('scrapers.academic_scraper.requests.get')
def test_scrape_academic_success(mock_get):
    mock_html = """
    <html>
        <body>
            <div class="c-job-card">
                <h3 class="c-job-card__title"><a href="/job/123">Postdoc in AI</a></h3>
                <li class="c-job-card__company">University X</li>
                <li class="c-job-card__location">London</li>
            </div>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    jobs = scrape_academic_jobs("AI", max_results=5)
    
    assert len(jobs) == 1
    assert jobs[0]['title'] == "Postdoc in AI"
    assert jobs[0]['company'] == "University X"
    assert jobs[0]['location'] == "London"
    assert jobs[0]['url'] == "https://www.nature.com/job/123"
