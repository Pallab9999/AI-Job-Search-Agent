import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

def create_html_table(jobs: List[Tuple[Dict, float, str]]) -> str:
    """Create HTML table rows for jobs."""
    rows = ""
    for job, score, cv_type in jobs:
        rows += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{job.get('title')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{job.get('company')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{score:.2f}</td>
            <td style="padding: 8px; border: 1px solid #ddd;"><a href="{job.get('url')}">Link</a></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{cv_type}</td>
        </tr>
        """
    return rows

def send_email_alert(jobs_with_scores: List[Tuple[Dict, float, str]], recipient_email: str):
    """Send an email alert with matching jobs."""
    if not jobs_with_scores:
        return
        
    sender = os.environ.get("EMAIL")
    password = os.environ.get("EMAIL_PASSWORD")
    server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", 587))
    
    if not sender or not password:
        logger.warning("Email credentials not found in environment. Skipping email alert.")
        return
        
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Job Agent Alert: {len(jobs_with_scores)} New Matches"
    msg['From'] = sender
    msg['To'] = recipient_email
    
    html = f"""
    <html>
      <body>
        <h2>New Job Matches Found</h2>
        <table style="border-collapse: collapse; width: 100%;">
          <tr style="background-color: #f2f2f2;">
            <th style="padding: 8px; border: 1px solid #ddd;">Title</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Company</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Match Score</th>
            <th style="padding: 8px; border: 1px solid #ddd;">URL</th>
            <th style="padding: 8px; border: 1px solid #ddd;">CV Type</th>
          </tr>
          {create_html_table(jobs_with_scores)}
        </table>
      </body>
    </html>
    """
    
    part = MIMEText(html, 'html')
    msg.attach(part)
    
    try:
        with smtplib.SMTP(server, port) as server_obj:
            server_obj.starttls()
            server_obj.login(sender, password)
            server_obj.send_message(msg)
        logger.info(f"Email alert sent to {recipient_email} with {len(jobs_with_scores)} jobs.")
    except Exception as e:
        logger.error(f"Error sending email: {e}")

def send_daily_digest(all_results: List[Tuple[Dict, float, str]], recipient: str = None):
    """Send a daily digest of all results. Wraps send_email_alert."""
    if not recipient:
        recipient = os.environ.get("EMAIL")
    if recipient:
        send_email_alert(all_results, recipient)
