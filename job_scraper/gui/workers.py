#!/usr/bin/env python3
"""
Worker threads for background operations in the job scraper GUI.
"""

import os
import sys
import time
import logging
import threading
import webbrowser
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal


class ApplyToJobWorker(QThread):
    """Worker thread for applying to jobs."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def __init__(self, app, job_data, cover_letter_path):
        """Initialize the worker.
        
        Args:
            app: Application instance
            job_data: Job data dictionary
            cover_letter_path: Path to cover letter file
        """
        super().__init__()
        self.app = app
        self.job_data = job_data
        self.cover_letter_path = cover_letter_path
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Applying to job...")
            
            # Save cover letter if not already saved
            if not os.path.exists(self.cover_letter_path):
                self.progress.emit("Saving cover letter...")
                dir_path = os.path.dirname(self.cover_letter_path)
                os.makedirs(dir_path, exist_ok=True)
                with open(self.cover_letter_path, 'w', encoding='utf-8') as f:
                    f.write(self.job_data.get('cover_letter', ''))
                    
            # Log the application
            self.progress.emit("Logging application...")
            self.app.db_manager.log_application(
                self.job_data.get('id'),
                self.cover_letter_path,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Open job URL in browser
            self.progress.emit("Opening job URL in browser...")
            job_url = self.job_data.get('url')
            if job_url:
                webbrowser.open(job_url)
                
            self.progress.emit("Job application process completed")
            self.completed.emit(True)
            
        except Exception as e:
            error_msg = f"Error applying to job: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.completed.emit(False)
            

class GenerateAICoverLetterWorker(QThread):
    """Worker thread for generating AI cover letters."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, app, resume_data, job_data):
        """Initialize the worker.
        
        Args:
            app: Application instance
            resume_data: Resume data dictionary
            job_data: Job data dictionary
        """
        super().__init__()
        self.app = app
        self.resume_data = resume_data
        self.job_data = job_data
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Generating AI cover letter...")
            
            # Check if API key is set
            api_key = self.app.config_manager.get_openai_api_key()
            if not api_key:
                raise ValueError("OpenAI API key is not set")
                
            # Generate cover letter
            cover_letter = self.app.ai_generator.generate_cover_letter(
                self.resume_data,
                self.job_data
            )
            
            self.progress.emit("Cover letter generated")
            self.completed.emit(cover_letter)
            
        except Exception as e:
            error_msg = f"Error generating cover letter: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            

class ParseResumeWorker(QThread):
    """Worker thread for parsing resumes."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, app, resume_path):
        """Initialize the worker.
        
        Args:
            app: Application instance
            resume_path: Path to resume file
        """
        super().__init__()
        self.app = app
        self.resume_path = resume_path
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Parsing resume...")
            
            # Parse resume
            resume_data = self.app.resume_parser.parse_resume(self.resume_path)
            
            self.progress.emit("Resume parsed successfully")
            self.completed.emit(resume_data)
            
        except Exception as e:
            error_msg = f"Error parsing resume: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            

class MatchJobsWorker(QThread):
    """Worker thread for matching jobs with resume."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, app, resume_data, top_n=10):
        """Initialize the worker.
        
        Args:
            app: Application instance
            resume_data: Resume data dictionary
            top_n: Number of top matches to return
        """
        super().__init__()
        self.app = app
        self.resume_data = resume_data
        self.top_n = top_n
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Loading jobs from database...")
            
            # Get all jobs from database
            jobs = self.app.db_manager.get_jobs()
            
            if not jobs:
                self.progress.emit("No jobs found in database")
                self.completed.emit([])
                return
                
            self.progress.emit(f"Matching {len(jobs)} jobs with resume...")
            
            # Match jobs with resume
            matched_jobs = self.app.job_matcher.match_jobs(
                self.resume_data,
                jobs,
                self.top_n
            )
            
            self.progress.emit(f"Found {len(matched_jobs)} matching jobs")
            self.completed.emit(matched_jobs)
            
        except Exception as e:
            error_msg = f"Error matching jobs: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            

class ScrapeJobsWorker(QThread):
    """Worker thread for scraping jobs."""
    
    progress = pyqtSignal(str, int, int)
    job_found = pyqtSignal(dict)
    completed = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, app, keywords, location, sites, pages_per_site, detailed_count):
        """Initialize the worker.
        
        Args:
            app: Application instance
            keywords: List of keywords to search for
            location: Location to search in
            sites: List of job sites to scrape
            pages_per_site: Number of pages to scrape per site
            detailed_count: Number of jobs to get detailed information for
        """
        super().__init__()
        self.app = app
        self.keywords = keywords
        self.location = location
        self.sites = sites
        self.pages_per_site = pages_per_site
        self.detailed_count = detailed_count
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Starting job search...", 0, 100)
            
            # Initialize scraper manager
            scraper_settings = {
                "sites": self.sites,
                "pages_per_site": self.pages_per_site,
                "detailed_count": self.detailed_count
            }
            
            # Scrape jobs
            jobs = self.app.scraper_manager.search_jobs(
                self.keywords,
                self.location
            )
            
            # Add jobs to database and emit signals
            for job in jobs:
                job_id = self.app.db_manager.add_job(job)
                if job_id:
                    job['id'] = job_id
                    self.job_found.emit(job)
                    
            self.progress.emit(f"Found {len(jobs)} jobs", 100, 100)
            self.completed.emit(jobs)
            
        except Exception as e:
            error_msg = f"Error scraping jobs: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            

class LoadJobsWorker(QThread):
    """Worker thread for loading jobs from database."""
    
    progress = pyqtSignal(str)
    job_loaded = pyqtSignal(dict)
    completed = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, app, filter_status=None, min_match_score=0):
        """Initialize the worker.
        
        Args:
            app: Application instance
            filter_status: Filter jobs by status (None for all jobs)
            min_match_score: Minimum match score for filtering
        """
        super().__init__()
        self.app = app
        self.filter_status = filter_status
        self.min_match_score = min_match_score
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Loading jobs from database...")
            
            # Get jobs from database
            jobs = self.app.db_manager.get_jobs(
                status=self.filter_status,
                min_match_score=self.min_match_score
            )
            
            self.progress.emit(f"Loaded {len(jobs)} jobs")
            
            # Emit signals for each job
            for job in jobs:
                self.job_loaded.emit(job)
                
            self.completed.emit(jobs)
            
        except Exception as e:
            error_msg = f"Error loading jobs: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            

class CheckExpiredJobsWorker(QThread):
    """Worker thread for checking expired jobs."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, app):
        """Initialize the worker.
        
        Args:
            app: Application instance
        """
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit("Checking for expired jobs...")
            
            # Check expired jobs
            count = self.app.check_expired_jobs()
            
            self.progress.emit(f"Found {count} expired jobs")
            self.completed.emit(count)
            
        except Exception as e:
            error_msg = f"Error checking expired jobs: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            

class DeleteExpiredJobsWorker(QThread):
    """Worker thread for deleting expired jobs."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, app, days=30):
        """Initialize the worker.
        
        Args:
            app: Application instance
            days: Delete jobs older than this many days
        """
        super().__init__()
        self.app = app
        self.days = days
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Run the worker thread."""
        try:
            self.progress.emit(f"Deleting expired jobs older than {self.days} days...")
            
            # Delete expired jobs
            count = self.app.delete_expired_jobs(self.days)
            
            self.progress.emit(f"Deleted {count} expired jobs")
            self.completed.emit(count)
            
        except Exception as e:
            error_msg = f"Error deleting expired jobs: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg) 