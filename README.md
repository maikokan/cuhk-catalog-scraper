# CUHK Catalog Scraper

A Python scraper for extracting course information from the [CUHK Course Catalog](https://rgsntl.rgs.cuhk.edu.hk/aqs_prd_applx/Public/tt_dsp_crse_catalog.aspx).

Features:
- **Local OCR**: Uses `ddddocr` + OpenCV for free CAPTCHA solving (no external services)
- **Configurable**: Edit `config.yaml` to filter by subject, course number range, and enrollment type
- **Clean Output**: Exports to Excel (.xlsx) with course details including descriptions, schedules, and readings

## Requirements

- Python 3.9+
- uv (recommended) or pip

## Installation

```bash
# Clone the repository
git clone https://github.com/maikokan/cuhk-catalog-scraper.git
cd cuhk-catalog-scraper

# Install dependencies (creates .venv automatically)
uv sync

# Or with pip
pip install playwright ddddocr opencv-python pandas pyyaml openpyxl requests
playwright install chromium
```

## Configuration

Edit `config.yaml`:

```yaml
course_subject: "FINA"          # Course subject code (e.g., FINA, ECON, MATH)
course_nbr_start: 5000          # Start of course number range
course_nbr_end: 6999            # End of course number range
enrollment: "MSc Finance"       # Filter by enrollment (leave empty to scrape all)
captcha_max_attempts: 10        # Max CAPTCHA solve attempts
```

**Course Number Ranges:**
- Undergraduate: 0000 - 4999
- Postgraduate: 5000 - 6999

## Usage

```bash
uv run python catalog-scraper.py
# or
python catalog-scraper.py
```

Output is saved as `CUHK_{SUBJECT}_{YYMMDDHHMM}.xlsx`

## Output Columns

| Column | Description |
|--------|-------------|
| Course Number | Course code (e.g., 6203) |
| Course Title | Full course name |
| Description | Course description |
| Course Schedule | Class schedule |
| Learning Outcome | Learning objectives |
| Course Syllabus | Syllabus content |
| Assessment Type | Assessment methods |
| Required Readings | Required reading materials |
| Recommended Readings | Suggested reading materials |

## How It Works

1. Opens the CUHK course catalog in a headless browser
2. Solves the CAPTCHA using local OCR (ddddocr + OpenCV preprocessing)
3. Filters courses by subject and number range
4. Optionally filters by enrollment type (for postgraduate courses)
5. Scrapes detailed information for each matching course
6. Exports results to Excel

## Troubleshooting

**CAPTCHA solving fails repeatedly:**
- Increase `captcha_max_attempts` in config.yaml
- Ensure good internet connection
- The site may be experiencing high load

**No courses found:**
- Verify `course_subject` is correct (check CUHK catalog for valid codes)
- Ensure `course_nbr_start` and `course_nbr_end` cover the desired range

## License

MIT

## Disclaimer

This project is not affiliated with, endorsed by, or supported by The Chinese University of Hong Kong (CUHK). Course data is provided for convenience only. Users should verify details against the official catalog. Use responsibly and avoid running the scraper multiple times in short succession to avoid overloading the server. Ensure your use complies with CUHK's Terms of Service. If CUHK updates their website structure, the scraper may break and will require updates.