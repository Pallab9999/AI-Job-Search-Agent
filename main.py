import argparse
import json
import time
import os
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger
from scrapers.indeed_scraper import scrape_indeed
from scrapers.linkedin_scraper import scrape_linkedin
from scrapers.academic_scraper import scrape_academic_jobs
from scrapers.ddg_scraper import scrape_ddg
from utils.cv_matcher import get_matching_jobs, load_cv
from utils.cover_letter_gen import generate_ai_cover_letter, save_cover_letter
from utils.email_alerts import send_daily_digest

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger()

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    logger.info("Graceful shutdown initiated...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def load_config(config_path: str) -> dict:
    """Load configuration from JSON."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config {config_path}: {e}")
        return {}

def deduplicate_jobs(jobs: list) -> list:
    """Deduplicate jobs based on URL."""
    seen_urls = set()
    unique_jobs = []
    for job in jobs:
        url = job.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url: # If no url, keep it anyway
            unique_jobs.append(job)
    return unique_jobs

def save_seen_jobs(jobs: list, filepath: str = "data/seen_jobs.json"):
    """Save seen jobs to avoid future duplicates."""
    Path("data").mkdir(exist_ok=True)
    seen_urls = set()
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                seen_urls = set(json.load(f))
        except Exception:
            pass
            
    for job in jobs:
        if job.get('url'):
            seen_urls.add(job.get('url'))
            
    try:
        with open(filepath, 'w') as f:
            json.dump(list(seen_urls), f)
    except Exception as e:
        logger.error(f"Failed to save seen jobs: {e}")

def filter_seen_jobs(jobs: list, filepath: str = "data/seen_jobs.json") -> list:
    """Filter out jobs that have already been seen."""
    if not os.path.exists(filepath):
        return jobs
        
    try:
        with open(filepath, 'r') as f:
            seen_urls = set(json.load(f))
    except Exception:
        return jobs
        
    return [job for job in jobs if job.get('url') not in seen_urls]

def run_scraper_iteration(config: dict, dry_run: bool, target_cv_type: str = None):
    """Run a single iteration of the scraping and matching process."""
    logger.info("Starting new scraping iteration...")
    
    all_jobs = []
    sites = config.get("sites_to_scrape", [])
    keywords = config.get("search_keywords", [])
    locations = config.get("locations", [])
    max_results = config.get("max_results_per_site", 50)
    
    for keyword in keywords:
        for location in locations:
            if not running:
                return
                
            if "indeed" in sites:
                all_jobs.extend(scrape_indeed(keyword, location, max_results))
            if "linkedin" in sites:
                all_jobs.extend(scrape_linkedin(keyword, location, max_results))
            if "academic" in sites:
                # Academic boards might not use location in the same way, but keeping structure
                all_jobs.extend(scrape_academic_jobs(keyword, max_results))
            if "ddg" in sites:
                all_jobs.extend(scrape_ddg(keyword, location, max_results))
                
    logger.info(f"Total raw jobs scraped: {len(all_jobs)}")
    
    # Deduplicate within this run
    unique_jobs = deduplicate_jobs(all_jobs)
    
    # Filter out previously seen jobs
    new_jobs = filter_seen_jobs(unique_jobs)
    logger.info(f"New unique jobs to process: {len(new_jobs)}")
    
    if not new_jobs:
        return
        
    # Match jobs
    matched_jobs = get_matching_jobs(new_jobs, config)
    
    # Filter by user requested cv_type if specified
    if target_cv_type:
        matched_jobs = [m for m in matched_jobs if m[2] == target_cv_type]
        
    logger.info(f"Jobs meeting minimum score threshold: {len(matched_jobs)}")
    
    # Process matches
    for job, score, cv_type in matched_jobs:
        if not running:
            return
            
        logger.info(f"Match found: {job.get('title')} at {job.get('company')} (Score: {score:.2f}, CV: {cv_type})")
        
        # Cover Letter Generation
        if config.get("auto_generate_cover_letter"):
            cv = load_cv(cv_type)
            api_key = os.environ.get("MISTRAL_API_KEY")
            letter = generate_ai_cover_letter(job, cv, api_key)
            save_cover_letter(letter, job)
            
    # Send email
    recipient = config.get("recipient_email")
    if config.get("email_notifications") and not dry_run and matched_jobs:
        logger.info("Sending daily digest...")
        send_daily_digest(matched_jobs, recipient)
    elif dry_run:
        logger.info("[Dry Run] Skipping email notifications.")
        
    # Save matches to recent_matches.json for Lovable.dev website integration
    if not dry_run and matched_jobs:
        try:
            matches_to_save = [{"job": job, "score": score, "cv_type": cv_type} for job, score, cv_type in matched_jobs]
            with open("data/recent_matches.json", "w") as f:
                json.dump(matches_to_save, f)
        except Exception as e:
            logger.error(f"Failed to save recent_matches.json: {e}")
        
    # Save seen jobs at the end of successful run
    if not dry_run:
        save_seen_jobs(new_jobs)

def main():
    parser = argparse.ArgumentParser(description="Job and PhD Search Agent")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--cv-type", type=str, choices=["intern", "phd"], help="Filter by cv type")
    parser.add_argument("--dry-run", action="store_true", help="Don't send emails or save state")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    if not config:
        logger.error("Exiting due to missing or invalid config.")
        return
        
    if args.once:
        run_scraper_iteration(config, args.dry_run, args.cv_type)
    else:
        logger.info(f"Starting agent in continuous mode. Interval: {config.get('check_interval_hours', 24)} hours.")
        while running:
            run_scraper_iteration(config, args.dry_run, args.cv_type)
            
            if not running:
                break
                
            sleep_hours = config.get('check_interval_hours', 24)
            logger.info(f"Sleeping for {sleep_hours} hours. Press Ctrl+C to stop.")
            
            # Sleep in smaller chunks to be responsive to Ctrl+C
            sleep_seconds = sleep_hours * 3600
            slept = 0
            while slept < sleep_seconds and running:
                time.sleep(1)
                slept += 1

    logger.info("Agent shut down successfully.")

if __name__ == "__main__":
    main()
