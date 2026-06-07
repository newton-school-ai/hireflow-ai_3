# HireFlow AI - Development Guide

NST Engineering - HireFlow
Framework: Build, Understand, Defend

This document explains how the development process works from your first day to final deployment. Read this before touching any code.

---

## The Development Philosophy

Context before concept. Experience before explanation. Demonstration before discussion.

Every issue in this project is written so you understand WHY something exists before you build it. You will run things, break things, and see the output before you are asked to explain the theory. The Q&A sessions that follow each milestone are not tests - they are conversations between people who built something together.

---

## Branch Strategy

```
main
 |
 +-- dev  (all features merge here first)
      |
      +-- feature/issue-1-dev-environment
      +-- feature/issue-3-db-schema
      +-- feature/issue-6-lever-scraper
      ...
```

**main** - stable, production-ready code only. Nothing goes here directly. Only dev merges into main at the end of a milestone, after the Maintainer and faculty have reviewed the full integration.

**dev** - the working integration branch. All feature branches are created from dev and merge back into dev. This is where the project lives during active development.

**feature/issue-N-short-name** - your personal working branch. One branch per issue. Created from dev, merged back to dev via PR.

### Why not work directly on main?

Imagine 4 contributors each pushing broken code directly to main. Every time someone pulls, they get someone else's half-finished work. The project breaks constantly. Nobody can run the full pipeline. This is why real teams use a staging branch (dev) and only promote stable, reviewed code to main.

---

## Setup Before You Clone (Do This Once)

These steps happen on your machine before any project code is involved.

### Step 1 - Install Python 3.11

```bash
# Check if you already have it
python3 --version

# Mac - install via Homebrew if needed
brew install python@3.11
```

### Step 2 - Install Node.js 18 or higher (for frontend)

```bash
node --version   # check existing
# Install from https://nodejs.org if needed
```

### Step 3 - Install PostgreSQL

```bash
# Mac
brew install postgresql@16
brew services start postgresql@16

# Verify
psql --version
```

### Step 4 - Install Docker (optional for now, required for deployment)

Download from https://docker.com/desktop

### Step 5 - Install Playwright system dependencies (for scrapers)

```bash
pip install playwright
playwright install chromium
```

---

## Cloning and First Setup

### Step 1 - Clone the repo

```bash
git clone git@github.com:newton-school-ai/hireflow-ai.git
cd hireflow-ai
```

### Step 2 - Switch to dev branch

```bash
git checkout dev
git pull origin dev
```

Always work from dev, never from main.

### Step 3 - Create your virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate       # Mac and Linux
venv\Scripts\activate          # Windows

# Verify you are inside venv - you should see (venv) in your prompt
which python   # should point to venv/bin/python
```

### Step 4 - Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5 - Set up environment variables

```bash
cp .env.example .env
# Open .env and fill in at minimum:
# - LLM_PROVIDER and the corresponding API key (use Groq for free)
# - DATABASE_URL
```

### Step 6 - Create the database

```bash
# Create the database
createdb hireflow

# Run migrations (once migrations exist from M1)
alembic upgrade head
```

### Step 7 - Verify the setup

```bash
uvicorn src.api.main:app --reload
# Should start without errors on http://localhost:8000
# Visit http://localhost:8000/docs to see the API
```

---

## Daily Development Workflow

Every day, before you write any code:

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Pull latest from dev
git checkout dev
git pull origin dev

# 3. Switch to your feature branch (or create one)
git checkout feature/issue-6-lever-scraper
# or create: git checkout -b feature/issue-6-lever-scraper
```

Write your code, then:

```bash
# Run tests before committing
pytest tests/ -v

# Format your code
black src/

# Check for issues
ruff check src/

# Stage and commit
git add .
git commit -m "feat(scrapers): add Lever scraper with pagination support"

# Push
git push origin feature/issue-6-lever-scraper
```

Then open a PR on GitHub from your branch into dev.

---

## Testing at Each Step

Every issue has a "How to test locally" section. Follow it exactly. Here is the general pattern:

### Testing a new API endpoint

```bash
# Start the server
uvicorn src.api.main:app --reload

# Use the interactive docs
open http://localhost:8000/docs

# Or use curl
curl -X POST http://localhost:8000/profile \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "skills": ["Python", "LangChain"]}'
```

### Testing a scraper

```bash
# Run the scraper directly as a script
python -m src.scrapers.lever_scraper --url "https://jobs.lever.co/example"

# Or run its test file
pytest tests/test_scrapers.py -v -k "test_lever"
```

### Testing a pipeline (embedding, scoring)

```bash
pytest tests/test_matcher.py -v
```

### Running all tests

```bash
pytest tests/ -v --tb=short
```

### Checking the database after a run

```bash
psql hireflow
\dt                          # list all tables
SELECT * FROM jobs LIMIT 5;  # check scraped jobs
SELECT * FROM users;         # check user profiles
\q
```

---

## How Dev Merges to Main

At the end of each milestone:

1. All feature branches for that milestone are merged into dev via reviewed PRs
2. Maintainer runs the full integration test on dev
3. Faculty reviews the milestone output
4. Maintainer opens a single PR from dev into main titled "M2: Job Discovery Engine - stable"
5. Faculty approves
6. Merge

This means main always contains only complete, tested, reviewed milestones - never half-built features.

---

## Milestone Q&A Prep

Two to three days after each milestone starts, faculty runs a 15 to 20 minute Q&A. To prepare:

1. Run your own code from scratch in a clean terminal (no cached state)
2. Read the defense questions in your issue
3. Write one-paragraph answers to each question in your own words
4. Be able to explain every file you created: what it does, why it exists, what breaks if you remove it

You do not need to memorize. You need to understand.

---

## Common Issues

**"Module not found" error**
You are probably not inside venv. Run `source venv/bin/activate`.

**Database connection error**
PostgreSQL is not running. Run `brew services start postgresql@16`.

**Playwright browser not found**
Run `playwright install chromium`.

**"Permission denied" on git push**
SSH key is not set up. See the SSH setup section in the main README.

**Alembic migration error**
Your DB schema is out of sync. Run `alembic upgrade head` to apply all pending migrations.

---

NST Engineering - HireFlow
