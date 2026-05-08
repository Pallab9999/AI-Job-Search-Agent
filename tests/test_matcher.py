import pytest
from utils.cv_matcher import determine_cv_type, calculate_match_score

def test_determine_cv_type():
    assert determine_cv_type("Software Engineering Intern", "Looking for a student") == "intern"
    assert determine_cv_type("Postdoc Researcher", "NLP lab") == "phd"
    assert determine_cv_type("Data Scientist", "General role") == "intern" # Default

def test_calculate_match_score():
    job = {
        "title": "Machine Learning Engineer",
        "description": "We need someone with Python, PyTorch, and deep learning experience. Remote work allowed.",
        "location": "Remote"
    }
    
    cv_good = {
        "skills": ["Python", "PyTorch", "Deep Learning"],
        "education": [{"degree": "M.S. Computer Science"}],
        "experience": [{"role": "ML Intern"}],
        "location_preference": "Remote"
    }
    
    cv_poor = {
        "skills": ["Java", "SQL"],
        "education": [{"degree": "B.A. English"}],
        "experience": [],
        "location_preference": "New York"
    }
    
    score_good = calculate_match_score(job, cv_good)
    score_poor = calculate_match_score(job, cv_poor)
    
    assert score_good > score_poor
    assert score_good > 0.5
    assert score_poor < 0.5

def test_empty_cv_and_job():
    job = {}
    cv = {}
    assert calculate_match_score(job, cv) == 0.0
