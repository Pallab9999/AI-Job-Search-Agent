# Job Agent

An AI-powered job and PhD search agent that automatically scrapes job listings, matches them against your CVs, generates cover letters, and sends email alerts.

## Features

- Scrapes jobs from Indeed, LinkedIn, and academic boards.
- Supports multiple CV profiles (e.g., Intern vs PhD) using JSON templates.
- **PDF Extraction**: Includes a utility to extract text from your PDF CVs into JSON.
- Match scoring based on skills, education, and experience overlap.
- AI Cover letter generation using Mistral AI (or fallback template).
- Email notifications with a daily digest of matches.
- Deduplication of seen jobs.

## Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd job-agent
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Copy the environment template and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
2. Update `config.json` with your preferred keywords, locations, and match thresholds.
3. Add your CV details:
   - Manually edit `cvs/intern_cv.json` and `cvs/phd_cv.json` OR
   - Run the PDF extraction tool:
     ```bash
     python utils/pdf_to_json.py path/to/your/cv.pdf --type internship --output cvs/intern_cv.json
     ```
     *(Be sure to review and refine the output JSON manually)*

## Usage

Run tests:
```bash
pytest tests/
```

Run once (Dry run - no emails sent, state not saved):
```bash
python main.py --once --dry-run
```

Run once (Live - sends emails and saves seen jobs):
```bash
python main.py --once
```

Run continuously (Background process):
```bash
python main.py
```

## Deployment

A GitHub Actions workflow is provided (`.github/workflows/daily_scrape.yml`) to automatically run the scraper every day at 8 AM UTC. Make sure to set the required repository secrets (`EMAIL`, `EMAIL_PASSWORD`, `MISTRAL_API_KEY`, etc.).

## License

MIT
