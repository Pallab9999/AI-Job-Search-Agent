import json
import os
import argparse
from pathlib import Path
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using PyPDF2."""
    if not PdfReader:
        print("PyPDF2 is not installed. Please install it using 'pip install PyPDF2'.")
        return ""
        
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def convert_to_json_format(text: str, default_type: str = "internship") -> dict:
    """
    Naively parse the text into a JSON dictionary structure expected by the system.
    This is a basic heuristic; you may need to manually adjust the output JSON.
    """
    data = {
        "name": "Extracted from PDF",
        "email": "",
        "phone": "",
        "skills": [],
        "experience": [],
        "education": [],
        "job_type": default_type
    }
    
    # Very basic parsing (you would likely use an LLM for better parsing in a real scenario)
    lines = text.split('\n')
    for line in lines:
        lower_line = line.lower()
        if "@" in line and not data["email"]:
            data["email"] = line.strip()
        elif "skills" in lower_line:
            data["skills"].append(line.replace("Skills", "").replace(":", "").strip())
        # Just putting all text into an experience block as a fallback
        
    data["experience"].append({"role": "Parsed text block", "company": "Various", "duration": "", "description": text[:500] + "..."})
    
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF CV to JSON")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output", help="Output JSON file path", default="output.json")
    parser.add_argument("--type", help="CV type (internship or phd)", default="internship")
    
    args = parser.parse_args()
    
    print(f"Extracting text from {args.pdf_path}...")
    extracted_text = extract_text_from_pdf(args.pdf_path)
    
    if extracted_text:
        print("Converting to JSON format...")
        json_data = convert_to_json_format(extracted_text, args.type)
        
        with open(args.output, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"Saved to {args.output}. Please review and manually refine the JSON structure.")
