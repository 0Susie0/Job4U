#!/usr/bin/env python3
"""
Main application module for the Job Scraper and Applicator.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, List, Optional, Any

from .config.constants import Constants
from .config.config_manager import ConfigManager
from .data.database import DatabaseManager
from .scraper import ScraperManager
from .core.resume_parser import ResumeParser
from .core.job_matcher import JobMatcher
from .services.ai_letter_generator import AILetterGenerator
from .services.application_manager import ApplicationManager
from .utils.utils import validate_config, ValidationError


class JobScraperApp:
    """Main application class for Job Scraper and Applicator."""
    
    def __init__(self):
        """Initialize the application components."""
        self._setup_logging()
        self._init_components()
        
    def _setup_logging(self):
        """Set up logging with rotation."""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs(Constants.LOG_DIR, exist_ok=True)
            
            # Configure root logger
            self.logger = logging.getLogger()
            self.logger.setLevel(Constants.LOGGING_SETTINGS["LOG_LEVEL"])
            
            # Create formatters
            file_formatter = logging.Formatter(Constants.LOGGING_SETTINGS["LOG_FORMAT"])
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            
            # Set up file handler with rotation
            log_file = os.path.join(
                Constants.LOG_DIR,
                Constants.LOGGING_SETTINGS["LOG_FILE"]
            )
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=Constants.LOGGING_SETTINGS["MAX_LOG_SIZE"],
                backupCount=Constants.LOGGING_SETTINGS["BACKUP_COUNT"],
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.INFO)
            
            # Set up console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            
            # Add handlers to logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
            self.logger.info("Logging system initialized")
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            sys.exit(1)
            
    def _init_components(self):
        """Initialize application components."""
        try:
            # Initialize configuration manager
            self.config_manager = ConfigManager(self.logger)
            
            # Validate configuration
            config_errors = validate_config(self.config_manager.config)
            if config_errors:
                self.logger.warning(f"Configuration validation errors: {', '.join(config_errors)}")
                
            # Initialize database manager
            self.db_manager = DatabaseManager(
                Constants.DB_FILE,
                self.logger
            )
            
            # Initialize scraper manager
            self.scraper_manager = ScraperManager(
                self.config_manager.get_job_scraper_settings(),
                self.logger
            )
            
            # Initialize resume parser
            self.resume_parser = ResumeParser(
                self.config_manager.get_resume_settings(),
                self.logger
            )
            
            # Initialize job matcher
            self.job_matcher = JobMatcher(
                self.config_manager.get_resume_settings(),
                self.logger
            )
            
            # Initialize AI letter generator
            self.ai_generator = AILetterGenerator(
                self.config_manager.get_openai_api_key(),
                self.logger
            )
            
            # Initialize application manager
            self.application_manager = ApplicationManager(
                self.config_manager,
                self.logger
            )
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {str(e)}")
            raise
            
    def search_jobs(self, keywords: List[str], location: str) -> List[Dict[str, Any]]:
        """Search for jobs using configured sites."""
        try:
            jobs = self.scraper_manager.search_jobs(keywords, location)
            self.logger.info(f"Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            self.logger.error(f"Error searching jobs: {str(e)}")
            return []
            
    def parse_resume(self, resume_path: str) -> Dict[str, Any]:
        """Parse resume to extract information."""
        try:
            resume_data = self.resume_parser.parse_resume(resume_path)
            self.logger.info("Resume parsed successfully")
            return resume_data
        except Exception as e:
            self.logger.error(f"Error parsing resume: {str(e)}")
            return {}
            
    def match_jobs_with_resume(self, resume_data: Dict[str, Any], 
                             jobs: List[Dict[str, Any]], 
                             top_n: int = 10) -> List[Dict[str, Any]]:
        """Match jobs with resume data."""
        try:
            matched_jobs = self.job_matcher.match_jobs(resume_data, jobs, top_n)
            self.logger.info(f"Matched {len(matched_jobs)} jobs with resume")
            return matched_jobs
        except Exception as e:
            self.logger.error(f"Error matching jobs: {str(e)}")
            return []
            
    def generate_cover_letter(self, resume_data: Dict[str, Any], 
                            job_data: Dict[str, Any]) -> str:
        """Generate a cover letter for a job."""
        try:
            cover_letter = self.application_manager.generate_cover_letter(
                resume_data,
                job_data
            )
            self.logger.info("Cover letter generated successfully")
            return cover_letter
        except Exception as e:
            self.logger.error(f"Error generating cover letter: {str(e)}")
            return ""
            
    def apply_to_job(self, job_data: Dict[str, Any]) -> bool:
        """Apply to a job."""
        try:
            success = self.application_manager.apply_to_job(job_data)
            if success:
                self.logger.info(f"Successfully applied to job: {job_data['title']}")
            else:
                self.logger.warning(f"Failed to apply to job: {job_data['title']}")
            return success
        except Exception as e:
            self.logger.error(f"Error applying to job: {str(e)}")
            return False
            
    def check_expired_jobs(self) -> int:
        """Check for expired jobs."""
        try:
            count = self.db_manager.check_expired_jobs()
            self.logger.info(f"Found {count} expired jobs")
            return count
        except Exception as e:
            self.logger.error(f"Error checking expired jobs: {str(e)}")
            return 0
            
    def get_expiring_jobs(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get jobs that are expiring soon."""
        try:
            jobs = self.db_manager.get_expiring_jobs(days)
            self.logger.info(f"Found {len(jobs)} jobs expiring in {days} days")
            return jobs
        except Exception as e:
            self.logger.error(f"Error getting expiring jobs: {str(e)}")
            return []
            
    def delete_expired_jobs(self, days: int = 30) -> int:
        """Delete expired jobs older than specified days."""
        try:
            count = self.db_manager.delete_expired_jobs(days)
            self.logger.info(f"Deleted {count} expired jobs")
            return count
        except Exception as e:
            self.logger.error(f"Error deleting expired jobs: {str(e)}")
            return 0 