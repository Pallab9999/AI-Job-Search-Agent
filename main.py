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

# Ensure required directories exist
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)
Path("output/cover_letters").mkdir(parents=True, exist_ok=True)

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

def load_email_queue(filepath: str = "data/email_queue.json") -> list:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_email_queue(queue: list, filepath: str = "data/email_queue.json"):
    try:
        Path("data").mkdir(exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save email queue: {e}")

def process_email_queue(config: dict, dry_run: bool):
    from utils.cli_ui import ui, MASCOT_SUCCESS
    queue = load_email_queue()
    if not queue:
        ui.log_activity("Email queue is empty. No new jobs to send.", style="yellow")
        return 0

    batch_size = config.get("email_batch_size", 10)
    to_send = queue[:batch_size]
    remaining = queue[batch_size:]

    ui.show_phase(f"✉️  Phase 3: Sending Notifications ({len(to_send)} jobs)", mascot=MASCOT_SUCCESS, style="bold green")

    # Reconstruct matched_jobs tuple format: (job, score, cv_type)
    matched_jobs = [(item["job"], item["score"], item["cv_type"]) for item in to_send]
    
    recipient = config.get("recipient_email")
    if config.get("email_notifications") and not dry_run and matched_jobs:
        logger.info(f"Sending email with {len(matched_jobs)} matches...")
        ui.log_activity(f"Emailing batch of {len(matched_jobs)} to {recipient}...", style="green")
        send_daily_digest(matched_jobs, recipient)
    elif dry_run:
        logger.info("[Dry Run] Skipping email notifications.")
        ui.log_activity(f"[Dry Run] Skipping email batch of {len(matched_jobs)}.", style="yellow")

    if not dry_run:
        save_email_queue(remaining)
        ui.log_activity(f"Queue updated. {len(remaining)} jobs left in queue.", style="cyan")

    return len(matched_jobs)

def run_scraper_iteration(config: dict, dry_run: bool, target_cv_type: str = None):
    """Run a single iteration of the scraping and matching process."""
    from utils.cli_ui import ui, MASCOT_SEARCHING, MASCOT_MATCHING, MASCOT_SUCCESS

    logger.info("Starting new scraping iteration...")
    ui.show_phase("🔍  Phase 1: Scraping Job Boards", mascot=MASCOT_SEARCHING, style="bold yellow")
    
    try:
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
                    ui.show_scraping_progress(keyword, location, "Indeed")
                    try:
                        all_jobs.extend(scrape_indeed(keyword, location, max_results))
                    except Exception as e:
                        logger.error(f"Indeed scraper failed: {e}")
                if "linkedin" in sites:
                    ui.show_scraping_progress(keyword, location, "LinkedIn")
                    try:
                        all_jobs.extend(scrape_linkedin(keyword, location, max_results))
                    except Exception as e:
                        logger.error(f"LinkedIn scraper failed: {e}")
                if "academic" in sites:
                    ui.show_scraping_progress(keyword, location, "Academic Boards")
                    try:
                        all_jobs.extend(scrape_academic_jobs(keyword, max_results))
                    except Exception as e:
                        logger.error(f"Academic scraper failed: {e}")
                if "ddg" in sites:
                    ui.show_scraping_progress(keyword, location, "DuckDuckGo Deep Search")
                    try:
                        all_jobs.extend(scrape_ddg(keyword, location, max_results))
                    except Exception as e:
                        logger.error(f"DDG scraper failed: {e}")
                    
        logger.info(f"Total raw jobs scraped: {len(all_jobs)}")
        ui.log_activity(f"Total raw jobs scraped: {len(all_jobs)}", style="green")
        
        # Deduplicate within this run
        unique_jobs = deduplicate_jobs(all_jobs)
        
        # Filter out previously seen jobs
        new_jobs = filter_seen_jobs(unique_jobs)
        logger.info(f"New unique jobs to process: {len(new_jobs)}")
        ui.log_activity(f"After deduplication & filtering: {len(new_jobs)} new jobs", style="green")
        
        if not new_jobs:
            ui.log_activity("No new jobs found this round.", style="yellow")
            ui.show_completion(0, dry_run)
            return
        
        # ── Phase 2: Matching ──────────────────────────────────────────
        ui.show_phase("📊  Phase 2: Matching Against Your CVs", mascot=MASCOT_MATCHING, style="bold magenta")
        
        try:
            matched_jobs = get_matching_jobs(new_jobs, config)
        except Exception as e:
            logger.error(f"Error during job matching: {e}")
            matched_jobs = []
        
        # Filter by user requested cv_type if specified
        if target_cv_type:
            matched_jobs = [m for m in matched_jobs if m[2] == target_cv_type]
            
        logger.info(f"Jobs meeting minimum score threshold: {len(matched_jobs)}")
        ui.log_activity(f"Jobs above threshold: {len(matched_jobs)}", style="green")

        # Show the match table
        ui.show_match_table(matched_jobs)
        
        # Process matches
        for job, score, cv_type in matched_jobs:
            if not running:
                return
                
            logger.info(f"Match found: {job.get('title')} at {job.get('company')} (Score: {score:.2f}, CV: {cv_type})")
            
            # Cover Letter Generation
            if config.get("auto_generate_cover_letter"):
                ui.log_activity(f"Generating cover letter for: {job.get('title', 'N/A')[:40]}...", style="cyan")
                cv = load_cv(cv_type)
                api_key = os.environ.get("BEDROCK_API_KEY") or os.environ.get("MISTRAL_API_KEY")
                letter = generate_ai_cover_letter(job, cv, api_key)
                job['cover_letter_path'] = save_cover_letter(letter, job)
        
        # ── Phase 3: Notifications ─────────────────────────────────────
        # Instead of emailing immediately, add to queue and process it
        if matched_jobs:
            queue = load_email_queue()
            # Convert tuples to dicts for JSON
            for job, score, cv_type in matched_jobs:
                queue.append({"job": job, "score": score, "cv_type": cv_type})
            
            # Sort queue by score descending
            queue = sorted(queue, key=lambda x: x["score"], reverse=True)
            save_email_queue(queue)
            
        # Process queue to send batch
        emailed_count = process_email_queue(config, dry_run)
            
        # Save matches to recent_matches.json for Lovable.dev website integration
        if not dry_run and matched_jobs:
            try:
                Path("data").mkdir(exist_ok=True)
                matches_to_save = [{"job": job, "score": score, "cv_type": cv_type} for job, score, cv_type in matched_jobs]
                with open("data/recent_matches.json", "w") as f:
                    json.dump(matches_to_save, f, indent=2)
                ui.log_activity("Saved recent_matches.json for website integration.", style="green")
            except Exception as e:
                logger.error(f"Failed to save recent_matches.json: {e}")
                ui.log_activity(f"Failed to save matches: {e}", style="red")
            
        # Save seen jobs at the end of successful run
        if not dry_run:
            save_seen_jobs(new_jobs)

        # ── Final Summary ──────────────────────────────────────────────
        ui.show_stats_summary(len(all_jobs), len(new_jobs), len(matched_jobs))
        ui.show_completion(len(matched_jobs), dry_run)

    except Exception as e:
        logger.error(f"Critical error during scraper iteration: {e}", exc_info=True)
        ui.show_error(f"Iteration failed: {e}")

def main():
    from utils.cli_ui import ui
    
    parser = argparse.ArgumentParser(description="AI-HUNTER: Job and PhD Search Agent")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--send-next", action="store_true", help="Skip scraping and send the next batch from the queue")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--cv-type", type=str, choices=["intern", "phd"], help="Filter by cv type")
    parser.add_argument("--dry-run", action="store_true", help="Don't send emails or save state")
    
    args = parser.parse_args()
    
    # Show branded startup
    ui.show_banner()
    
    config = load_config(args.config)
    if not config:
        logger.error("Exiting due to missing or invalid config.")
        ui.show_error("Failed to load configuration.")
        return
    
    # Show config summary
    ui.show_config_summary(config)

    if args.dry_run:
        ui.log_activity("Running in DRY RUN mode (no emails, no state saved)", style="yellow")
        
    if args.send_next:
        ui.log_activity("Processing next batch from email queue without scraping...", style="cyan")
        process_email_queue(config, args.dry_run)
        logger.info("Agent shut down successfully.")
        ui.log_activity("Agent shut down successfully. Goodbye! 👋", style="bold green")
        return

    if args.once:
        run_scraper_iteration(config, args.dry_run, args.cv_type)
    else:
        ui.log_activity(f"Continuous mode. Interval: {config.get('check_interval_hours', 24)} hours.", style="cyan")
        while running:
            run_scraper_iteration(config, args.dry_run, args.cv_type)
            
            if not running:
                break
                
            sleep_hours = config.get('check_interval_hours', 24)
            ui.show_sleep(sleep_hours)
            
            # Sleep in smaller chunks to be responsive to Ctrl+C
            sleep_seconds = sleep_hours * 3600
            slept = 0
            while slept < sleep_seconds and running:
                time.sleep(1)
                slept += 1

    logger.info("Agent shut down successfully.")
    ui.log_activity("Agent shut down successfully. Goodbye! 👋", style="bold green")

if __name__ == "__main__":
    main()
