import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

def load_cv(cv_type: str) -> dict:
    """Load CV data from JSON file."""
    cv_path = Path(f"cvs/{cv_type}_cv.json")
    if not cv_path.exists():
        logger.error(f"CV file not found: {cv_path}")
        return {}
        
    try:
        with open(cv_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading CV {cv_path}: {e}")
        return {}

def determine_cv_type(job_title: str, job_description: str) -> str:
    """Determine whether to use intern or phd CV based on job text."""
    text = (job_title + " " + job_description).lower()
    if "intern" in text or "internship" in text or "student" in text:
        return "intern"
    if "phd" in text or "postdoc" in text or "research assistant" in text or "scientist" in text:
        return "phd"
    return "intern" # Default to intern

def calculate_match_score(job: Dict, cv: Dict) -> float:
    """Calculate match score between job and CV. Returns 0.0 to 1.0"""
    score = 0.0
    text = (job.get('title', '') + " " + job.get('description', '')).lower()
    
    # Skills match (40%)
    raw_skills = cv.get('skills', [])
    flat_skills = []
    if isinstance(raw_skills, dict):
        for category, item_list in raw_skills.items():
            if isinstance(item_list, list):
                flat_skills.extend(item_list)
    elif isinstance(raw_skills, list):
        flat_skills = raw_skills
        
    skills_matched = sum(1 for skill in flat_skills if isinstance(skill, str) and skill.lower() in text)
    if flat_skills:
        score += (skills_matched / len(flat_skills)) * 0.4
        
    # Education match (20%)
    edu_score = 0.0
    for edu in cv.get('education', []):
        if "phd" in text and "phd" in edu.get('degree', '').lower():
            edu_score = 0.2
            break
        elif "master" in text and "m.s." in edu.get('degree', '').lower():
            edu_score = 0.2
            break
        else:
            edu_score = 0.1 # Base score for having education listed
    score += edu_score
    
    # Experience match (25%)
    exp_score = 0.0
    if cv.get('experience') or cv.get('publications'):
        exp_score = 0.25
    score += exp_score
    
    # Location match (15%)
    loc_pref = cv.get('location_preference', '').lower()
    job_loc = job.get('location', '').lower()
    if loc_pref and loc_pref in job_loc:
        score += 0.15
    elif "remote" in job_loc:
        score += 0.15
        
    return min(1.0, score)

def get_matching_jobs(jobs: List[Dict], config: Dict) -> List[Tuple[Dict, float, str]]:
    """Match jobs against CVs and filter by min score."""
    results = []
    for job in jobs:
        cv_type = determine_cv_type(job.get('title', ''), job.get('description', ''))
        cv = load_cv(cv_type)
        if not cv:
            continue
            
        score = calculate_match_score(job, cv)
        if score >= config.get('min_match_score', 0.5):
            results.append((job, score, cv_type))
            
    # Sort by score descending
    return sorted(results, key=lambda x: x[1], reverse=True)
