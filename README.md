# Job Alert Agent

Monitors LinkedIn, Naukri, and Indeed for new job postings every hour.
Uses Gemini AI to match jobs to your skills and emails you instantly.
Runs 24/7 on GitHub Actions — completely free, no laptop needed.

---

## Files in this project

```
job_agent.py                        ← main script
.github/
  workflows/
    job_alert.yml                   ← GitHub Actions scheduler
seen_jobs.json                      ← auto-created, tracks seen jobs
```

---

## One-time setup (do this once)

### Step 1 — Create a GitHub repository

1. Go to https://github.com and sign in
2. Click the **+** icon → **New repository**
3. Name it: `job-alert-agent`
4. Set it to **Private**
5. Click **Create repository**

### Step 2 — Upload the files

Upload these two files to your new repo:
- `job_agent.py`
- `.github/workflows/job_alert.yml`

You can drag-and-drop them in the GitHub web interface.
Make sure `.github/workflows/job_alert.yml` is in that exact folder path.

### Step 3 — Edit your profile in job_agent.py

Open `job_agent.py` and update:
- `MY_SKILLS` — your actual skills
- `MY_PREFERENCES` — your job preferences
- `JOB_KEYWORDS` — search terms to use
- `LOCATION` — your city
- `MATCH_THRESHOLD` — minimum score to trigger alert (default: 7)

### Step 4 — Add your secrets

In your GitHub repo, go to:
**Settings → Secrets and variables → Actions → New repository secret**

Add these 4 secrets:

| Secret name     | Value                          |
|-----------------|-------------------------------|
| GEMINI_API_KEY  | Your Gemini API key (AIza...) |
| GMAIL_SENDER    | your.email@gmail.com          |
| GMAIL_PASSWORD  | Your 16-char Gmail App Password |
| GMAIL_RECEIVER  | your.email@gmail.com          |

### Step 5 — Allow Actions to write to repo

In your GitHub repo, go to:
**Settings → Actions → General → Workflow permissions**
Select **Read and write permissions** → Save

### Step 6 — Test it manually

Go to **Actions** tab in your repo → Click **Job Alert Agent** → Click **Run workflow**

Watch the logs to confirm it runs without errors.

---

## How it works

1. GitHub Actions triggers the script on a schedule (Mon–Fri, every 2 hours, 9 AM–9 PM IST)
2. Script scrapes LinkedIn, Naukri, and Indeed for your keywords
3. Each new job is sent to Gemini AI for scoring against your profile
4. Jobs scoring 7/10 or above trigger an instant email to you
5. Seen jobs are saved back to the repo so you never get duplicate alerts

---

## Customisation tips

**Change how often it runs:**
Edit the `cron` line in `job_alert.yml`.
Example — every hour: `'30 * * * 1-5'`

**Change match sensitivity:**
Lower `MATCH_THRESHOLD` to 6 for more alerts, raise to 8 for stricter matches.

**Add more job sites:**
Add a new `scrape_xxx()` function in `job_agent.py` and call it inside `fetch_all_jobs()`.

---

## Cost

| Service        | Cost   |
|----------------|--------|
| GitHub Actions | Free (2000 min/month — uses ~5 min/run) |
| Gemini API     | Free (1500 requests/day)                |
| Gmail SMTP     | Free                                    |
| **Total**      | **$0/month**                            |
