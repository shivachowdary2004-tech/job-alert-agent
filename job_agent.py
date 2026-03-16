"""
Job Alert AI Agent
==================
Monitors LinkedIn, Naukri, and Indeed for new job postings.
Uses Gemini AI to match jobs against your skill profile.
Sends instant Gmail alerts when a match is found.
Runs 24/7 on GitHub Actions — no laptop needed.
"""

import os
import json
import hashlib
import smtplib
import logging
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────
#  YOUR PROFILE  ← Edit this before deploying
# ─────────────────────────────────────────────────────────────

MY_SKILLS = """
CANDIDATE: Shiva Alaparthi
Location: Chennai, Tamil Nadu
Email: alaparthishiva123@gmail.com

EDUCATION:
- B.E. Computer Science and Engineering, Sathyabama Institute of Science and Technology,
  Chennai (2022–2026), CGPA: 8.32/10
- Class XII, Sri Chaitanya Junior College, Andhra Pradesh (2020–2022), 88.6%
- Class X, QIS Public School (2019–2020), 53%

PROGRAMMING LANGUAGES:
- Java (primary language)
- Python
- C
- HTML, CSS, JavaScript

FRAMEWORKS & BACKEND:
- Spring Boot (primary framework)
- Spring Security, JWT Authentication
- RESTful APIs
- JSP, Servlets

DATABASE:
- MySQL (primary database)
- JPA / Hibernate ORM

DEVELOPER TOOLS:
- Git, GitHub
- Postman
- VS Code, Eclipse

CORE CONCEPTS:
- Data Structures and Algorithms
- Object-Oriented Programming (OOP)
- MVC Architecture

PROJECTS:
- Personal Carbon Footprint Tracking App (Java, Spring Boot, MySQL, JWT)
- Food Ordering Web Application (Java, Servlets, JSP, MySQL)
- E-Commerce Web Application (team lead, backend + Git)

CERTIFICATIONS:
- Java Development Course – Infosys Springboard
- Programming in Java – NPTEL
- Database Management Systems – NPTEL

EXPERIENCE LEVEL: Fresher / Entry-level (Final year student, graduating 2026)
"""

MY_PREFERENCES = """
- Target roles: Java Developer, Software Engineer, Backend Developer,
  Full Stack Developer, Spring Boot Developer, Junior Software Engineer,
  Fresher Java Developer, Entry Level Developer
- Experience level: Fresher / Entry-level (0–1 year)
- Preferred locations: Chennai, Bangalore, Hyderabad, Remote (India)
- Job type: Full-time
- Preferred stack: Java, Spring Boot, MySQL, REST APIs
"""

# Keywords to search across all job sites
JOB_KEYWORDS = [
    "java developer fresher chennai",
    "spring boot fresher chennai",
    "java fresher 2026 chennai",
    "junior java developer chennai",
    "java developer fresher bangalore",
    "spring boot fresher bangalore",
    "java fresher 2026 bangalore",
    "junior java developer bangalore",
    "java developer fresher hyderabad",
    "spring boot fresher hyderabad",
    "java fresher 2026 hyderabad",
    "junior java developer hyderabad",
    "java developer fresher remote india",
    "spring boot developer fresher remote",
]

LOCATION = "India"

# Only alert if AI match score >= this (out of 10)
MATCH_THRESHOLD = 7

# ─────────────────────────────────────────────────────────────
#  SECRETS — loaded from environment (GitHub Actions secrets)
# ─────────────────────────────────────────────────────────────

GMAIL_SENDER    = os.environ.get("GMAIL_SENDER", "")    # your Gmail address
GMAIL_PASSWORD  = os.environ.get("GMAIL_PASSWORD", "")  # Gmail App Password
GMAIL_RECEIVER  = os.environ.get("GMAIL_RECEIVER", "")  # where to send alerts

# ─────────────────────────────────────────────────────────────
#  INTERNALS
# ─────────────────────────────────────────────────────────────

SEEN_JOBS_FILE = Path("seen_jobs.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Seen-jobs tracker ─────────────────────────────────────────

def load_seen_jobs() -> set:
    if SEEN_JOBS_FILE.exists():
        try:
            return set(json.loads(SEEN_JOBS_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen_jobs(seen: set):
    SEEN_JOBS_FILE.write_text(json.dumps(list(seen), indent=2))


def job_id(job: dict) -> str:
    key = f"{job.get('title','').lower()}-{job.get('company','').lower()}"
    return hashlib.md5(key.encode()).hexdigest()


# ── Scrapers ──────────────────────────────────────────────────

def scrape_linkedin(keyword: str, location: str) -> list:
    jobs = []
    url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={requests.utils.quote(keyword)}"
        f"&location={requests.utils.quote(location)}"
        "&sortBy=DD&f_TPR=r86400"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup.select("div.base-card")[:8]:
            title   = card.select_one("h3.base-search-card__title")
            company = card.select_one("h4.base-search-card__subtitle")
            loc     = card.select_one("span.job-search-card__location")
            link    = card.select_one("a.base-card__full-link")
            if not title:
                continue
            jobs.append({
                "source":   "LinkedIn",
                "title":    title.get_text(strip=True),
                "company":  company.get_text(strip=True) if company else "N/A",
                "location": loc.get_text(strip=True) if loc else location,
                "url":      link["href"] if link else url,
                "description": "",
            })
        log.info(f"LinkedIn: found {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        log.warning(f"LinkedIn scrape error: {e}")
    return jobs


def scrape_indeed(keyword: str, location: str) -> list:
    jobs = []
    url = (
        "https://in.indeed.com/jobs"
        f"?q={requests.utils.quote(keyword)}"
        f"&l={requests.utils.quote(location)}"
        "&sort=date&fromage=1"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup.select("div.job_seen_beacon")[:8]:
            title   = card.select_one("h2.jobTitle span")
            company = card.select_one("span.companyName")
            loc     = card.select_one("div.companyLocation")
            link    = card.select_one("h2.jobTitle a")
            desc    = card.select_one("div.job-snippet")
            if not title:
                continue
            jobs.append({
                "source":      "Indeed",
                "title":       title.get_text(strip=True),
                "company":     company.get_text(strip=True) if company else "N/A",
                "location":    loc.get_text(strip=True) if loc else location,
                "url":         "https://in.indeed.com" + link["href"] if link else url,
                "description": desc.get_text(strip=True) if desc else "",
            })
        log.info(f"Indeed: found {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        log.warning(f"Indeed scrape error: {e}")
    return jobs


def scrape_naukri(keyword: str, location: str) -> list:
    jobs = []
    slug = keyword.replace(" ", "-")
    loc  = location.lower()
    url  = f"https://www.naukri.com/{slug}-jobs-in-{loc}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup.select("article.jobTuple, div.jobTuple")[:8]:
            title   = card.select_one("a.title")
            company = card.select_one("a.subTitle, .companyInfo a")
            loc_el  = card.select_one("li.location, .locWdth")
            desc    = card.select_one("div.job-description, .job-desc")
            if not title:
                continue
            jobs.append({
                "source":      "Naukri",
                "title":       title.get_text(strip=True),
                "company":     company.get_text(strip=True) if company else "N/A",
                "location":    loc_el.get_text(strip=True) if loc_el else location,
                "url":         title.get("href", url),
                "description": desc.get_text(strip=True) if desc else "",
            })
        log.info(f"Naukri: found {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        log.warning(f"Naukri scrape error: {e}")
    return jobs


def fetch_all_jobs() -> list:
    all_jobs = []
    for keyword in JOB_KEYWORDS:
        all_jobs.extend(scrape_linkedin(keyword, LOCATION))
        all_jobs.extend(scrape_indeed(keyword, LOCATION))
        all_jobs.extend(scrape_naukri(keyword, LOCATION))
        time.sleep(2)  # polite delay between requests
    return all_jobs


# ── Keyword Matcher (no API needed) ──────────────────────────

# Jobs matching ANY of these keywords in title will trigger an alert
MATCH_KEYWORDS = [
    "java", "spring", "spring boot", "backend", "full stack",
    "fullstack", "software engineer", "python", "mysql", "rest api",
    "j2ee", "microservices", "hibernate", "servlet",
]

# Jobs containing these words will be SKIPPED (senior/irrelevant roles)
SKIP_KEYWORDS = [
    "senior", "lead", "manager", "director", "architect",
    "10+ years", "8+ years", "7+ years",
]

def score_job(job: dict) -> dict:
    """Score job using keyword matching — no API needed, always works."""
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    combined = title + " " + description

    # Skip senior/irrelevant roles
    for skip in SKIP_KEYWORDS:
        if skip in combined:
            job["score"]      = 0
            job["reason"]     = f"Skipped — contains '{skip}'"
            job["highlights"] = []
            log.info(f"Skipped '{job['title']}' — senior/irrelevant role")
            return job

    # Score based on keyword matches
    matched = [kw for kw in MATCH_KEYWORDS if kw in combined]
    score = min(10, len(matched) * 2 + 3)  # base score 3, +2 per keyword match

    job["score"]      = score
    job["reason"]     = f"Matched keywords: {', '.join(matched)}" if matched else "No keywords matched"
    job["highlights"] = matched[:4]
    log.info(f"Scored '{job['title']}': {score}/10 — matched: {matched}")
    return job


# ── Email Sender ──────────────────────────────────────────────

def send_email_alert(matched_jobs: list):
    """Send a single email listing all matched jobs."""
    if not matched_jobs:
        return

    subject = f"[Job Alert] {len(matched_jobs)} new matching job(s) found!"

    # Build HTML email body
    job_blocks = ""
    for job in matched_jobs:
        highlights = "".join(
            f"<li style='margin:2px 0'>{h}</li>" for h in job.get("highlights", [])
        )
        job_blocks += f"""
        <div style="border:1px solid #e0e0e0; border-radius:8px; padding:16px; margin-bottom:16px;">
          <h3 style="margin:0 0 4px; color:#1a1a1a">{job['title']}</h3>
          <p style="margin:0 0 8px; color:#555">{job['company']} &bull; {job['location']} &bull; {job['source']}</p>
          <div style="background:#f0faf4; border-radius:4px; padding:8px; margin-bottom:8px;">
            <strong style="color:#1a7a4a">Match score: {job['score']}/10</strong>
            <p style="margin:4px 0 0; color:#333">{job['reason']}</p>
          </div>
          {'<ul style="margin:4px 0; padding-left:20px; color:#333">' + highlights + '</ul>' if highlights else ''}
          <a href="{job['url']}" style="display:inline-block; margin-top:8px; padding:8px 16px;
             background:#0066cc; color:white; text-decoration:none; border-radius:4px;">
            View Job
          </a>
        </div>"""

    html = f"""
    <html><body style="font-family:sans-serif; max-width:600px; margin:0 auto; padding:20px;">
      <h2 style="color:#1a1a1a">Job Alert — {datetime.now().strftime('%d %b %Y, %I:%M %p')}</h2>
      <p style="color:#555">Found <strong>{len(matched_jobs)}</strong> new job(s) matching your profile:</p>
      {job_blocks}
      <p style="color:#999; font-size:12px; margin-top:24px">
        Sent by your Job Alert Agent &bull; Running on GitHub Actions
      </p>
    </body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = GMAIL_RECEIVER
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())

        log.info(f"Email sent: {len(matched_jobs)} job(s) to {GMAIL_RECEIVER}")
    except Exception as e:
        log.error(f"Email send failed: {e}")


# ── Main ──────────────────────────────────────────────────────

def run():
    log.info("=" * 50)
    log.info("Job Alert Agent started")
    log.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 50)

    seen = load_seen_jobs()
    log.info(f"Loaded {len(seen)} previously seen jobs")

    # 1. Fetch all jobs
    all_jobs = fetch_all_jobs()
    log.info(f"Total jobs fetched: {len(all_jobs)}")

    # 2. Filter out already-seen jobs
    new_jobs = [j for j in all_jobs if job_id(j) not in seen]
    log.info(f"New jobs to evaluate: {len(new_jobs)}")

    if not new_jobs:
        log.info("No new jobs found. Done.")
        return

    # 3. Score each new job with keyword matching
    matched_jobs = []
    for job in new_jobs:
        job = score_job(job)
        seen.add(job_id(job))
        if job["score"] >= MATCH_THRESHOLD:
            matched_jobs.append(job)
            log.info(f"MATCH: '{job['title']}' at {job['company']} — {job['score']}/10")

    # 4. Save updated seen list
    save_seen_jobs(seen)
    log.info(f"Saved {len(seen)} total seen jobs")

    # 5. Send email if there are matches
    if matched_jobs:
        log.info(f"Sending alert for {len(matched_jobs)} matched job(s)...")
        send_email_alert(matched_jobs)
    else:
        log.info("No jobs met the match threshold. No email sent.")

    log.info("Run complete.")


if __name__ == "__main__":
    run()
