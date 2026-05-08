import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
except ImportError:
    MistralClient = None

logger = logging.getLogger(__name__)

def generate_template_cover_letter(job: Dict, cv: Dict) -> str:
    """Generate a template-based cover letter."""
    name = cv.get('name', 'Applicant')
    skills = ", ".join(cv.get('skills', [])[:3])
    company = job.get('company', 'your company')
    title = job.get('title', 'the open position')
    
    template = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {title} position at {company}. 
With my background and skills in {skills}, I am confident in my ability to contribute effectively to your team.

My experience aligns well with the requirements of this role, and I am eager to bring my expertise to {company}.
Please find my resume attached for your consideration.

Sincerely,
{name}
"""
    return template

def generate_ai_cover_letter(job: Dict, cv: Dict, api_key: str = None) -> str:
    """Generate a cover letter using Mistral AI or fallback to template."""
    if not api_key or not MistralClient:
        logger.info("No Mistral API key or library found. Using template.")
        return generate_template_cover_letter(job, cv)
        
    try:
        client = MistralClient(api_key=api_key)
        
        prompt = f"""Write a professional, concise cover letter for the following job:
Title: {job.get('title')}
Company: {job.get('company')}
Description snippet: {job.get('description')}

Using the following candidate information:
Name: {cv.get('name')}
Skills: {", ".join(cv.get('skills', []))}
Experience/Projects: Highlight relevant points from this CV snippet: {str(cv)[:500]}

Keep it under 300 words.
"""
        messages = [ChatMessage(role="user", content=prompt)]
        chat_response = client.chat(
            model="mistral-small-latest",
            messages=messages,
        )
        return chat_response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating AI cover letter: {e}")
        return generate_template_cover_letter(job, cv)

def save_cover_letter(letter: str, job: Dict, output_dir: str = "output/cover_letters/"):
    """Save the cover letter to text and markdown files."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    company = job.get('company', 'Company').replace(" ", "_").replace("/", "_")
    title = job.get('title', 'Job').replace(" ", "_").replace("/", "_")
    date_str = datetime.now().strftime("%Y%m%d")
    
    base_filename = f"{company}_{title}_{date_str}"
    
    try:
        with open(Path(output_dir) / f"{base_filename}.txt", "w", encoding='utf-8') as f:
            f.write(letter)
            
        with open(Path(output_dir) / f"{base_filename}.md", "w", encoding='utf-8') as f:
            f.write(f"# Cover Letter for {job.get('title')} at {job.get('company')}\n\n{letter}")
            
        logger.info(f"Saved cover letters for {job.get('company')} in {output_dir}")
    except Exception as e:
        logger.error(f"Error saving cover letter: {e}")
