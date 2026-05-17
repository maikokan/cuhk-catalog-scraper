from playwright.sync_api import sync_playwright
import pandas as pd
import re
import yaml
import numpy as np
import cv2
import sys
from pathlib import Path
from datetime import datetime
import time

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def load_config():
    """Load configuration from config.yaml."""
    if not CONFIG_FILE.exists():
        default_config = {
            "course_subject": "FINA",
            "course_nbr_start": 5000,
            "course_nbr_end": 9999,
            "enrollment": "MSc Finance",
            "captcha_max_attempts": 10,
        }
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(default_config, f)
        raise SystemExit("Please edit config.yaml and run again.")

    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


config = load_config()
CATALOG_URL = 'https://rgsntl.rgs.cuhk.edu.hk/aqs_prd_applx/Public/tt_dsp_crse_catalog.aspx'
COURSE_SUBJECT = config["course_subject"]
COURSE_NBR_START = config.get("course_nbr_start", 0)
COURSE_NBR_END = config.get("course_nbr_end", 9999)
ENROLLMENT_FILTER = config.get("enrollment", "").strip()
CAPTCHA_MAX_ATTEMPTS = config.get("captcha_max_attempts", 10)

if not DDDDOCR_AVAILABLE:
    raise SystemExit("ddddocr is required. Install with: pip install ddddocr")

# =============================================================================
# ASCII ART
# =============================================================================

HEADER = r"""===============================================================================
  ___ _   _ _  _ _  __     ___  ___ ___    _   ___ ___ ___ 
 / __| | | | || | |/ /    / __|/ __| _ \  /_\ | _ \ __| _ \
| (__| |_| | __ | ' <     \__ \ (__|   / / _ \|  _/ _||   /
 \___|\___/|_||_|_|\_\    |___/\___|_|_\/_/ \_\_| |___|_|_\

==============================================================================="""


# =============================================================================
# CAPTCHA SOLVING
# =============================================================================

def sanitize(text):
    """Keep only uppercase letters and numbers, limit to 4 chars."""
    return re.sub(r'[^A-Z0-9]', '', text.upper())[:4]


def preprocess_opencv(image_bytes):
    """Preprocess image for better OCR accuracy using OpenCV."""
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, output = cv2.imencode('.png', binary)
    return output.tobytes()


def solve_captcha(page, ocr, max_attempts=10):
    """Solve CAPTCHA using local ddddocr + OpenCV."""
    for attempt in range(1, max_attempts + 1):
        captcha_name = page.locator("#hf_Captcha").get_attribute("value")
        img_url = f"https://rgsntl.rgs.cuhk.edu.hk/aqs_prd_applx/Public/BuildCaptcha.aspx?captchaname={captcha_name}&len=4"
        response = page.request.get(img_url)
        image_bytes = response.body()

        result1 = ocr.classification(image_bytes)
        sol1 = sanitize(result1)

        processed = preprocess_opencv(image_bytes)
        result2 = ocr.classification(processed) if processed else ""
        sol2 = sanitize(result2)

        solution = sol1 if len(sol1) == 4 else (sol2 if len(sol2) == 4 else None)

        if not solution:
            page.click("#btn_refresh")
            continue

        page.fill("#txt_captcha", solution)
        page.click("#btn_search")
        page.wait_for_timeout(1500)

        error_text = page.locator("#lbl_error").inner_text() if page.locator("#lbl_error").count() > 0 else ""
        if not error_text or "Invalid" not in error_text:
            return solution

        page.click("#btn_refresh")

    raise Exception("Failed to solve CAPTCHA")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_text(page, selector):
    """Helper function to safely extract text if the element exists."""
    loc = page.locator(selector)
    if loc.count() > 0:
        return loc.first.inner_text().strip()
    return "N/A"


def format_time(seconds):
    """Format seconds to readable time."""
    if seconds < 10:
        return f"{int(seconds)}s"
    elif seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def update_progress(current, total, matches, start_time):
    """Update progress bar on same line."""
    bar_len = 25
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_len - filled)
    progress = int(current / total * 100) if total > 0 else 0
    matches_str = str(matches).rjust(2)
    elapsed_str = format_time(time.time() - start_time)
    line = f"[{bar}] {progress:3d}% | {matches_str} matches | {elapsed_str}"
    sys.stdout.write(f"\r\x1b[K{line}")
    sys.stdout.flush()


# =============================================================================
# MAIN SCRAPER
# =============================================================================

def run_scraper():
    start_time = time.time()
    matched_courses = []

    # Print header
    print(HEADER)
    print()

    # Print config info
    print(f"Subject: {COURSE_SUBJECT}")
    print(f"Course Number Range: {COURSE_NBR_START} - {COURSE_NBR_END}")
    print(f"Enrollment: {ENROLLMENT_FILTER or 'All'}")
    print()
    print("✓ Initializing...")
    print("✓ Solving Captcha...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        ocr = ddddocr.DdddOcr(show_ad=False)

        page.goto(CATALOG_URL)
        page.select_option("#ddl_subject", COURSE_SUBJECT)

        solve_captcha(page, ocr, CAPTCHA_MAX_ATTEMPTS)
        print("✓ Captcha Solved!")

        page.wait_for_selector("table#gv_detail")

        # First pass: collect filtered course indices
        rows_locator = page.locator("table#gv_detail tr:not(.normalGridViewHeaderStyle)")
        total_rows = rows_locator.count()

        filtered_indices = []
        for i in range(total_rows):
            row = rows_locator.nth(i)
            nbr_element = row.locator("a[id$='lbtn_course_nbr']")
            if nbr_element.count() == 0:
                continue

            nbr_text = nbr_element.inner_text().strip()
            course_nbr_str = re.sub(r'\D', '', nbr_text)

            if not course_nbr_str:
                continue

            course_num = int(course_nbr_str)
            if COURSE_NBR_START <= course_num <= COURSE_NBR_END:
                filtered_indices.append(i)

        total_courses = len(filtered_indices)
        print(f"✓ Scraping {total_courses} Courses...")
        print()  # newline before progress bar

        # Initial progress
        update_progress(0, total_courses, 0, start_time)

        last_update = start_time

        # Process filtered courses
        for idx, row_idx in enumerate(filtered_indices):
            rows = page.locator("table#gv_detail tr:not(.normalGridViewHeaderStyle)")
            row = rows.nth(row_idx)

            nbr_element = row.locator("a[id$='lbtn_course_nbr']")
            nbr_text = nbr_element.inner_text().strip()
            course_nbr_str = re.sub(r'\D', '', nbr_text)

            title_link = row.locator("a[id$='lbtn_course_title']")
            course_title = title_link.inner_text().strip()

            # Update progress every second
            if time.time() - last_update >= 1:
                update_progress(idx + 1, total_courses, len(matched_courses), start_time)
                last_update = time.time()

            # Enter Course Detail
            with page.expect_navigation():
                title_link.click()

            req_element = page.locator("#uc_course_tc_enrl_requirement")
            enrollment_text = req_element.inner_text().strip() if req_element.count() > 0 else ""

            matches_filter = (not ENROLLMENT_FILTER) or (ENROLLMENT_FILTER.lower() in enrollment_text.lower())

            if matches_filter:
                course_data = {
                    "Course Number": course_nbr_str,
                    "Course Title": course_title,
                    "Description": get_text(page, "#uc_course_lbl_crse_descrlong"),
                    "Course Schedule": get_text(page, "#uc_course_gv_sched")
                }

                with page.expect_navigation():
                    page.locator("#btn_course_outcome").click()

                course_data["Learning Outcome"] = get_text(page, "#uc_course_outcome_lbl_learning_outcome")
                course_data["Course Syllabus"] = get_text(page, "#uc_course_outcome_lbl_course_syllabus")
                course_data["Assessment Type"] = get_text(page, "#uc_course_outcome_gv_ast")
                course_data["Required Readings"] = get_text(page, "#uc_course_outcome_lbl_req_reading")
                course_data["Recommended Readings"] = get_text(page, "#uc_course_outcome_lbl_rec_reading")

                matched_courses.append(course_data)

                with page.expect_navigation():
                    page.locator("#btn_course_outcome_return").click()

            with page.expect_navigation():
                page.locator("#btn_course_return").click()

        browser.close()

    # Final progress update
    update_progress(total_courses, total_courses, len(matched_courses), start_time)
    print()  # newline after progress bar

    total_time = time.time() - start_time
    print(f"✓ Done! ({len(matched_courses)} matches, {format_time(total_time)})")

    # Export to Excel
    if matched_courses:
        df = pd.DataFrame(matched_courses)
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        output_file = f"CUHK_{COURSE_SUBJECT}_{timestamp}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"✓ Saved to \"{output_file}\"")

    print()
    print("=" * 80)


if __name__ == "__main__":
    run_scraper()