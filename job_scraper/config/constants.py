#!/usr/bin/env python3
"""
Constants for the Job Scraper and Applicator.
"""

import os
from pathlib import Path

class Constants:
    """Constants used throughout the application."""
    
    # Paths
    APP_DIR = os.path.join(os.path.expanduser("~"), ".job_scraper")
    CONFIG_FILE = os.path.join(APP_DIR, "config.json")
    DB_FILE = os.path.join(APP_DIR, "jobs.db")
    LOGS_DIR = os.path.join(APP_DIR, "logs")
    
    # Output directories
    COVER_LETTERS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Cover Letters")
    APPLICATION_LOGS_DIR = os.path.join(APP_DIR, "applications")
    
    # Default configuration
    DEFAULT_CONFIG = {
        # User information
        "name": "",
        "email": "",
        "phone": "",
        "skills": [],
        
        # Job scraper settings
        "search_terms": [],
        "location": "",
        "job_sites": ["seek", "indeed", "linkedin"],
        "pages_per_site": 2,
        "detailed_job_count": 10,
        
        # Resume settings
        "default_resume_path": "",
        "default_cover_letter_template": "",
        
        # AI settings
        "openai_api_key": "",
        "use_ai_cover_letter": True,
        
        # Application settings
        "auto_apply": False,
        
        # Selenium settings
        "headless": True,
        "timeout": 30,
        "browser": "chrome"
    }
    
    # Default cover letter template
    DEFAULT_COVER_LETTER_TEMPLATE = """[YOUR_NAME]
[YOUR_ADDRESS]
[YOUR_PHONE]
[YOUR_EMAIL]

[DATE]

[COMPANY_NAME]
[COMPANY_ADDRESS]
[COMPANY_CITY, STATE ZIP]

Dear Hiring Manager,

I am writing to express my interest in the [JOB_TITLE] position at [COMPANY_NAME]. With my background in [RELEVANT_BACKGROUND], I am confident in my ability to contribute to your team's success.

[SKILLS_PARAGRAPH]

[EXPERIENCE_PARAGRAPH]

[CLOSING_PARAGRAPH]

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experiences align with your needs for the [JOB_TITLE] position.

Sincerely,

[YOUR_NAME]
"""
    
    # Website selectors
    SEEK_SELECTORS = {
        "search_url": "https://www.seek.com.au/jobs?keywords={keywords}&where={location}&page={page}",
        "job_links": "a[data-automation='jobTitle']",
        "job_title": "h1[data-automation='job-detail-title']",
        "company": "span[data-automation='job-detail-company']",
        "location": "span[data-automation='job-detail-location']",
        "description": "div[data-automation='jobDescription']",
        "deadline": "span[data-automation='job-detail-deadline']"
    }
    
    INDEED_SELECTORS = {
        "search_url": "https://au.indeed.com/jobs?q={keywords}&l={location}&start={start}",
        "job_links": "a.jcs-JobTitle",
        "job_title": "h1.jobsearch-JobInfoHeader-title",
        "company": "div.jobsearch-InlineCompanyRating > div:first-child",
        "location": "div.jobsearch-JobInfoHeader-subtitle > div:nth-child(2)",
        "description": "div#jobDescriptionText",
        "deadline": "div.jobsearch-JobMetadataHeader-item:contains('deadline')"
    }
    
    LINKEDIN_SELECTORS = {
        "search_url": "https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&start={start}",
        "job_links": "a.base-card__full-link",
        "job_title": "h1.top-card-layout__title",
        "company": "a.topcard__org-name-link",
        "location": "span.topcard__flavor--bullet",
        "description": "div.description__text",
        "deadline": "span.job-deadline"
    }
    
    # Default deadline format
    DEFAULT_DEADLINE_FORMAT = "%Y-%m-%d"
    
    # Job status
    JOB_STATUS = {
        "ACTIVE": 0,
        "EXPIRED": 1,
        "APPLIED": 2
    }
    
    # Match thresholds
    MATCH_THRESHOLDS = {
        "EXCELLENT": 80,
        "GOOD": 60,
        "FAIR": 40,
        "POOR": 20
    }
    
    # AI prompts
    AI_COVER_LETTER_PROMPT = """You are an expert career coach and professional cover letter writer. I need you to create a personalized cover letter for a job application based on my resume and the job description.

Resume Information:
{resume_info}

Job Description:
{job_description}

Create a professional, tailored cover letter that:
1. Highlights my relevant skills and experience for this specific job
2. Demonstrates my understanding of the company's needs
3. Shows enthusiasm for the role and company
4. Addresses any potential skill gaps with transferable skills or learning potential
5. Uses a professional but personable tone

Format the cover letter according to standard business letter format.
Be concise, specific, and avoid generic statements that could apply to any job.
Focus on how I can add value to the company rather than just stating what I want from the job.
Limit the cover letter to approximately 350-400 words.
"""

    # Resume parsing patterns
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    PHONE_PATTERN = r"(\+\d{1,3}\s?)?(\(?\d{1,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}"
    NAME_PATTERN = r"^([A-Z][a-z]+([\s-][A-Z][a-z]+)+)$"
    
    # Database tables
    DB_TABLES = {
        "jobs": """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                url TEXT,
                source TEXT,
                deadline TEXT,
                date_scraped TEXT,
                expired INTEGER DEFAULT 0,
                applied INTEGER DEFAULT 0,
                application_date TEXT,
                match_score INTEGER DEFAULT 0
            )
        """
    }

    # Common IT skills list
    IT_SKILLS = [
        "python", "java", "javascript", "c++", "c#", "ruby", "php", "swift", "kotlin", "scala",
        "html", "css", "react", "angular", "vue", "node.js", "express", "django", "flask", "laravel",
        "spring", "hibernate", "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "jenkins", "github actions", "gitlab ci", "sql", "mysql", "postgresql", "mongodb", "oracle",
        "nosql", "redis", "elasticsearch", "hadoop", "spark", "kafka", "rabbitmq", "tensorflow",
        "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib", "power bi", "tableau", "linux",
        "unix", "windows", "networking", "cybersecurity", "penetration testing", "encryption",
        "firewall", "vpn", "dns", "dhcp", "tcp/ip", "agile", "scrum", "kanban", "jira", "confluence",
        "git", "svn", "rest api", "graphql", "soap", "json", "xml", "yaml", "oauth", "jwt", "sso",
        "ldap", "active directory", "selenium", "cypress", "jest", "mocha", "chai", "junit", "testng",
        "ci/cd", "devops", "sre", "infrastructure as code", "cloud computing", "microservices",
        "serverless", "soa", "etl", "data warehousing", "data mining", "machine learning",
        "deep learning", "nlp", "computer vision", "big data", "bioinformatics", "product management",
        "project management", "scrum master", "product owner", "ux/ui", "figma", "sketch", "adobe xd",
        "mobile development", "ios", "android", "flutter", "react native", "xamarin", "unity",
        "game development", "blockchain", "cryptocurrency", "smart contracts", "iot", "embedded systems",
        "robotics", "ar/vr", "data science", "business intelligence", "data analysis", "data visualization"
    ]
    
    # Section headers for resume parsing
    EXPERIENCE_HEADERS = [
        "work experience", "professional experience", "employment history",
        "work history", "experience", "professional background"
    ]
    
    EDUCATION_HEADERS = [
        "education", "academic background", "educational background",
        "academic qualifications", "qualifications"
    ]
    
    # Output directories
    OUTPUT_DIR = "output"
    COVER_LETTERS_DIR = f"{OUTPUT_DIR}/cover_letters"
    
    # Log file for applications
    APPLICATIONS_LOG = f"{OUTPUT_DIR}/applications.json"
    
    # Database configuration
    DB_NAME = "job_scraper.db"
    
    # Delay settings
    MIN_DELAY = 2
    MAX_DELAY = 5 