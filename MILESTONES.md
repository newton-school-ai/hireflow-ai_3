# HireFlow AI - GitHub Issues (M1 to M8)

This file contains the full issue descriptions for all 8 milestones.
Copy each issue into GitHub Issues when setting up the project board.
Each issue maps to the HireFlow Sprint Tracker board, Backlog column.

HireFlow supports two modes: Internship and Job (full-time). All modules must handle both. They differ in sources scraped, stipend vs salary filters, resume tone, and interview prep depth.

---

## M1 - Project Scaffold and User Onboarding

Labels: m1, milestone, infra
Assignees: Maintainer and Contributor 1

### What needs to be built

Set up the complete project foundation: database schema, data models, and the user onboarding flow. A user should be able to select a mode (Internship or Job), upload their resume or fill a profile form, have their skills and experience extracted by an LLM, set a weekly application quota, and have their profile stored in the database.

### Acceptance Criteria

- [ ] PostgreSQL schema created with all 5 tables: users, jobs, applications, prep_guides, weekly_reports (and shortlists for optional module)
- [ ] SQLAlchemy models defined for all tables in src/models/
- [ ] User model includes a `mode` field: "internship" or "job"
- [ ] FastAPI endpoint: POST /profile - accepts PDF resume upload or JSON profile, extracts skills and experience via LLM, saves to DB
- [ ] FastAPI endpoint: GET /profile/{user_id} - returns stored profile
- [ ] .env.example filled with all required keys, .env working locally
- [ ] requirements.txt complete and tested in a fresh venv
- [ ] docker-compose up starts API and PostgreSQL successfully
- [ ] Alembic migration for initial schema
- [ ] Basic README setup instructions work for a fresh clone

### Files Expected

- src/models/user.py
- src/models/job.py
- src/models/application.py
- src/models/prep_guide.py
- src/models/report.py
- src/api/routes/profile.py
- src/config/settings.py
- src/config/database.py
- migrations/

### Defense Questions

1. What is a virtual environment (venv) and why is it non-negotiable in this project? What breaks in CI/CD if you do not use one?
2. Why do we store API keys in .env and never commit them? What happens if you accidentally push a key to a public repo?
3. Walk me through the profile intake flow - what happens from the moment a user uploads their PDF to when the data is stored in the DB?
4. Why did you use Alembic for migrations instead of running raw SQL? What is the advantage in a team setting?
5. The user profile has a `mode` field (internship or job). How does this value flow into later modules?

---

## M2 - Job Discovery Engine

Labels: m2, milestone, scraper
Assignees: Contributor 1

### What needs to be built

Build the job discovery engine that scrapes career pages and portals to build a pool of 100+ relevant listings per cycle. Must handle static pages, JavaScript-rendered SPAs, and API-backed portals. Includes a spam and quality filter.

Internship Mode sources: Internshala, Wellfound, LinkedIn internships, company pages
Job Mode sources: LinkedIn jobs, Naukri, Greenhouse, Lever, company career pages

### Acceptance Criteria

- [ ] Scraper for Lever career pages - extracts all required fields
- [ ] Scraper for Greenhouse career pages - extracts all required fields
- [ ] Generic scraper for custom career pages using Playwright (handles JS-rendered content)
- [ ] BeautifulSoup scraper for static pages
- [ ] All scrapers extract: company_name, role_title, jd_text, skills_required, experience_required, location, stipend_salary, application_url, posting_date, selection_process, source, listing_type (internship or job)
- [ ] Spam and quality filter: flags vague JDs, missing company info, unrealistic claims, saves is_spam=True with spam_confidence score
- [ ] All discovered listings saved to the jobs table
- [ ] Scraper reads `mode` from user profile and targets the correct sources
- [ ] Rate limiting implemented - no more than X requests per second per domain
- [ ] At least 5 test cases in tests/test_scrapers.py

### Files Expected

- src/scrapers/lever_scraper.py
- src/scrapers/greenhouse_scraper.py
- src/scrapers/generic_scraper.py
- src/scrapers/static_scraper.py
- src/agents/spam_filter.py
- tests/test_scrapers.py

### Defense Questions

1. Why Playwright over Selenium for JS-rendered pages? When would Selenium still be the better choice?
2. How do you handle a career page that loads listings via infinite scroll or a "Load More" button?
3. Your spam filter flags a real early-stage startup that has a short, simple JD. How do you reduce false positives?
4. What is your rate limiting strategy? How do you avoid getting IP-banned while scraping?
5. A career page updates its HTML structure overnight and your selectors break. How do you make your scraper resilient to this?
6. How do you distinguish between an internship listing and a full-time job listing in your scraper output?

---

## M3 - Job-Profile Match Scorer

Labels: m3, milestone, agent
Assignees: Contributor 2

### What needs to be built

Build the embedding-based matching engine that scores every discovered listing against the user profile. Output is a ranked list where rank 1 is the best fit, with per-listing skill gap analysis.

Scoring weights:
- Skill Match: 40%
- Role Fit: 20%
- Experience Fit: 15%
- Location Match: 10%
- Stipend or Salary Fit: 10%
- Company Signal: 5%

### Acceptance Criteria

- [ ] Embedding pipeline: generates vector embeddings for both user profile (skills, experience, projects) and each JD
- [ ] FAISS index built from job embeddings, supports similarity search
- [ ] Multi-factor scorer implemented with exact weights above
- [ ] Output per listing: match_score (0 to 1 float), skill_matches, skill_gaps, rank
- [ ] Skill gap extraction: clearly identifies skills in JD that are missing from the user profile
- [ ] Stipend or Salary Fit component uses `stipend_salary` field and compares against user's `min_stipend` (internship mode) or `min_salary` (job mode)
- [ ] Match results saved to applications table (planned status)
- [ ] At least 3 unit tests in tests/test_matcher.py
- [ ] Scoring function is deterministic (same input gives same output)

### Files Expected

- src/pipelines/embedding_pipeline.py
- src/pipelines/match_scorer.py
- tests/test_matcher.py

### Defense Questions

1. What embedding model did you use? Why? How would you evaluate whether it is doing a good job at matching JDs to profiles?
2. Why FAISS over ChromaDB for this use case? When would ChromaDB be a better choice?
3. The skill match weight is 40%. Why not 60%? How did you decide the relative weights?
4. Two listings have the same match score (0.87). How does the system break the tie?
5. What chunk size did you use when embedding JDs? What happens if the JD is only 3 lines long?
6. A user is in Internship Mode with experience_years = 0. How does the experience fit component score them against an internship that says "0 to 1 years preferred"?

---

## M4 - Weekly Quota Selector and Resume Tailoring Engine

Labels: m4, milestone, agent
Assignees: Contributor 2 (quota selector) and Contributor 3 (resume engine)

### What needs to be built

Two connected components: (1) the quota selector that picks the top N listings from the ranked list based on the user weekly limit, and (2) the resume tailoring engine that generates a unique, ATS-optimized resume for each selected listing.

### Acceptance Criteria

Quota Selector:
- [ ] Takes ranked listing list and user weekly_quota, returns top N listings
- [ ] Filters out: already-applied companies, expired listings, user blacklist
- [ ] Always generates a weekly plan and sends it to the user for review before any application is submitted - this is not optional
- [ ] Weekly plan shows: company, role, match score, skill gaps, and the resume that will be used
- [ ] User can confirm the full batch, swap individual listings, or remove any company
- [ ] `confirmation_mode` field in user profile controls granularity: "batch" (confirm all at once) or "individual" (confirm each one separately) - default is "batch"
- [ ] No resume is generated and no application is submitted until the user confirms
- [ ] After confirmation, generates tailored resumes and shows each one to the user before submitting

Resume Tailoring Engine:
- [ ] For each selected listing: extracts required skills from JD, maps to user matching skills and projects
- [ ] Generates tailored resume sections: Summary (role-specific), Skills (JD-priority ordered), Projects (top 2 to 3 most relevant), Experience, Education
- [ ] Resume generated as PDF (LaTeX or ReportLab)
- [ ] Each resume saved at: data/resumes/{user_id}/{job_id}_resume.pdf
- [ ] Application record updated in DB: resume_path, resume_version, status = "planned"
- [ ] Resume tone and summary differ between Internship Mode (fresher, project-focused) and Job Mode (impact-focused, results-driven)
- [ ] At least 2 test cases

### Files Expected

- src/pipelines/quota_selector.py
- src/pipelines/resume_generator.py
- src/templates/resume_latex/base_template.tex
- tests/test_resume.py

### Defense Questions

1. How does the resume tailoring engine decide which 2 to 3 projects to include when the user has 6 projects?
2. Why LaTeX for resume generation? What are the trade-offs vs HTML/CSS to PDF or ReportLab?
3. What happens when a user has zero projects that match the JD requirements?
4. The user weekly quota is 10 but only 7 listings pass the quality threshold. What does the system do?
5. How does the resume summary change between Internship Mode and Job Mode for the same user?
6. The user confirms the weekly plan but then wants to change one company after resumes are already generated. How do you handle this?
7. Why should confirmation always be required even if the user previously said "auto-apply"? What could go wrong if you skip it?

---

## M5 - Application Automation Agent

Labels: m5, milestone, agent
Assignees: Contributor 3

### What needs to be built

Build the Playwright-based automation agent that fills and submits application forms. Must handle multi-step forms, file uploads, free-text questions, rate limiting, CAPTCHA detection, and error recovery. Must work for both internship portals and job portals.

### Acceptance Criteria

- [ ] Agent navigates to application_url for each listing in the weekly plan
- [ ] Fills standard form fields: name, email, phone, education, experience, skills
- [ ] Uploads tailored resume PDF to file upload fields
- [ ] Handles free-text fields (e.g. "Why do you want to work here?") using LLM generation with JD context
- [ ] Multi-step and multi-page form support, resumes from last completed page on failure
- [ ] CAPTCHA detection: flags the application as status = "needs_action", does not attempt to solve
- [ ] Rate limiting: configurable delay between submissions
- [ ] Application status logged: "applied", "failed", or "needs_action"
- [ ] Failure reason recorded in DB for failed applications
- [ ] Handles Internshala internship forms and standard ATS job forms (Lever, Greenhouse)
- [ ] At least 3 test cases with mock pages

### Files Expected

- src/agents/application_agent.py
- src/automation/form_filler.py
- src/automation/captcha_handler.py
- tests/test_automation.py

### Defense Questions

1. How do you handle a multi-page application where page 3 of 4 fails mid-submission?
2. The application portal has a CAPTCHA. What does your agent do, and why is solving it not an option?
3. How do you avoid being detected as a bot? What anti-detection measures did you implement in Playwright?
4. What is your retry strategy? After how many attempts do you mark an application as failed?
5. Internshala forms are structured differently from Greenhouse forms. How does your agent handle both without duplicating all the form-filling logic?

---

## M6 - Preparation Guide Generator

Labels: m6, milestone, agent
Assignees: Contributor 4

### What needs to be built

For every listing applied to, generate a structured interview preparation guide. This includes: predicted interview rounds, topics to prepare (strong, moderate, gap), curated learning resources, mock interview questions, and company intelligence.

Internship interviews are typically shorter (1 to 2 rounds, lighter technical depth). Job interviews are typically longer (3 to 5 rounds, deeper technical and behavioral). The prep guide must reflect this difference.

### Acceptance Criteria

- [ ] Interview round prediction: analyzes JD, company career page, and company stage to predict number of rounds and focus areas
- [ ] Prediction accounts for mode - internship listings get lighter round predictions by default
- [ ] Topic analysis: categorizes user skills into Strong, Moderate, and Gap relative to JD requirements
- [ ] Resource finder: for each gap or key topic, finds 2 to 3 relevant links (docs, tutorials, videos) using Tavily or SerpAPI
- [ ] Mock question generator: generates 5 to 10 JD-specific interview questions (technical, behavioral, design)
- [ ] Company intel scraper: collects company stage, tech stack, recent news, Glassdoor or AmbitionBox interview patterns if available
- [ ] Handles gracefully when company has zero reviews, provides fallback guidance
- [ ] Prep guide saved to prep_guides table and as PDF or HTML in data/reports/
- [ ] Prep guide is distinct per listing, not a generic template repeated 10 times

### Files Expected

- src/agents/prep_guide_agent.py
- src/agents/company_intel_agent.py
- tests/test_prep_guide.py

### Defense Questions

1. How do you predict the number of interview rounds when the JD does not mention a selection process?
2. Your resource finder returns a link that is broken or paywalled. How do you handle this?
3. How do you make sure the mock questions are specific to the JD and company, not generic AI interview questions?
4. The company has zero Glassdoor reviews and no public interview history. What does the company intel module output?
5. Internship interviews are shorter and less formal than job interviews. How does your round prediction account for this?
6. You are generating prep guides for 10 different listings in one weekly cycle. How do you keep them distinct?

---

## M7 - Weekly Report and Hiring Side Module

Labels: m7, milestone, agent
Assignees: Contributor 4 and Maintainer

### What needs to be built

Two components: (1) the weekly report generator that compiles all applications, resumes, and prep guides into a single user-facing email report, and (2) the hiring side agent that takes a company JD and applicant pool and shortlists the top candidates.

### Acceptance Criteria

Weekly Report:
- [ ] Aggregates all applications from the weekly cycle: status, match score, resume used, prep guide
- [ ] Cross-application insights: most in-demand skills this week, user strongest and weakest match categories, skill gap frequency
- [ ] Weekly study plan: prioritized list of skills to learn based on gap frequency across all JDs
- [ ] Report sent via email (SendGrid or Resend) with resume PDFs attached or linked
- [ ] Report saved to weekly_reports table and as HTML or PDF in data/reports/
- [ ] Report clearly separates internship applications from job applications in the summary if the user applied to both

Hiring Side Agent (Optional Module):
- [ ] Accepts: JD (text) and applicant data (CSV or JSON)
- [ ] Parses each applicant: skills, experience, projects, education
- [ ] Scores each applicant against JD using the same scoring engine as M3
- [ ] Produces shortlist of top N candidates (company specifies N)
- [ ] Generates shortlist report: per-candidate summary with match score and key strengths
- [ ] Sends email to hiring team with shortlist attached
- [ ] Saved to shortlists table

### Files Expected

- src/agents/report_generator.py
- src/agents/hiring_shortlist_agent.py
- tests/test_report.py

### Defense Questions

1. The weekly report has 10 prep guides. How do you keep the email readable - do you embed everything or link out?
2. How do you prioritize which skill gap to study first when 10 JDs each have different gaps?
3. For the hiring side: your scoring engine ranks applicants by skill match. How do you prevent it from inadvertently penalizing non-traditional backgrounds (self-taught, bootcamp, non-CS degree)?
4. One application failed due to CAPTCHA. How does the report handle it - what does the user see and what action are they prompted to take?
5. The user applied to both internships and full-time jobs in the same week. Does the report treat them differently?

---

## M8 - Dashboard, Integration and Demo

Labels: m8, milestone, frontend
Assignees: All pod members

### What needs to be built

Build the React frontend dashboard and complete the end-to-end integration of all modules. Every module (M1 to M7) must connect and run as a single pipeline. Includes edge case handling, a demo video, and full project documentation.

### Acceptance Criteria

Frontend Dashboard:
- [ ] Mode switcher: user can toggle between Internship Mode and Job Mode
- [ ] Weekly plan view: shows top N selected listings with match scores, skill gaps, and planned resume - user must confirm before agent proceeds
- [ ] Plan review actions: confirm full batch, swap a listing, remove a company, or edit the resume for a specific listing
- [ ] Resume preview: user can view each tailored resume before it is submitted, with option to edit or reject
- [ ] Application tracker: table of all applications with status (applied, failed, needs action), match score, resume link
- [ ] Prep guide viewer: per-application prep guide display (topics, resources, mock questions, company intel)
- [ ] Resume viewer: list of all tailored resumes with download links
- [ ] Profile page: user can update their master profile, mode, and weekly quota
- [ ] Mobile-responsive layout

Integration:
- [ ] End-to-end flow works: profile upload, mode selection, scrape, score, select, tailor resume, apply, prep guide, report, dashboard
- [ ] All failure states handled: CAPTCHA blocked, scraper error, LLM timeout
- [ ] Handles both modes in the same weekly cycle if needed

Demo and Docs:
- [ ] Demo video (3 to 5 min): walks through the full pipeline from profile upload to weekly report
- [ ] docs/architecture.md: system architecture diagram and module descriptions
- [ ] All README setup instructions tested on a fresh machine
- [ ] At least 10 total tests passing across all modules

### Files Expected

- frontend/src/ (React components - Dashboard, ApplicationTracker, PrepGuideViewer, etc.)
- docs/architecture.md
- docs/demo.md (link to demo video)

### Defense Questions

Maintainer:
1. Walk me through the complete data flow: "user sets quota = 10 in Internship Mode" to "weekly report delivered." Name every function and every DB write.
2. How do agents coordinate in LangGraph? What is the state schema? What happens when the scraper fails mid-pipeline?
3. How would you add support for a new job portal without touching core architecture?

All Contributors:
4. If you had to do your milestone over, what would you build differently?
5. What was the hardest edge case you encountered and how did you handle it?
6. What is one thing about your module that could fail silently in production, and how would you detect it?

---

## GitHub Labels to Create

| Label | Description |
|-------|-------------|
| m1 | Milestone 1 - Scaffold and Onboarding |
| m2 | Milestone 2 - Job Discovery |
| m3 | Milestone 3 - Match Scorer |
| m4 | Milestone 4 - Quota Selector and Resume |
| m5 | Milestone 5 - Application Agent |
| m6 | Milestone 6 - Prep Guide Generator |
| m7 | Milestone 7 - Weekly Report and Hiring |
| m8 | Milestone 8 - Dashboard and Demo |
| agent | LangGraph and agent code |
| scraper | Playwright and BeautifulSoup scrapers |
| frontend | React dashboard |
| infra | Docker, DB, CI/CD |
| milestone | Milestone-level tracking issue |
| good first issue | Good starting point |
| needs-review | PR ready for Maintainer review |

---

## Project Board - HireFlow Sprint Tracker

Columns:

| Column | Purpose |
|--------|---------|
| Backlog | All 8 milestone issues start here |
| In Progress | Issue is actively being worked on |
| In Review | PR raised, waiting for Maintainer review |
| Done | PR merged, issue closed |

Setup: GitHub, Projects, New Project, Board view, add all 8 issues to Backlog.
