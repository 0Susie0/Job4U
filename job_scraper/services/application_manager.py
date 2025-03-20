"""
Job application manager module for managing job applications.
"""

import os
import json
import time
import logging
import re
import random
import datetime
import webbrowser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)
from contextlib import contextmanager
from typing import Optional, Dict, Any

from .constants import Constants
from .utils import Utils, validate_job_data, validate_resume_data, sanitize_file_path, ValidationError
from .ai_letter_generator import AILetterGenerator

logger = logging.getLogger(__name__)

class RetryableError(Exception):
    """Exception that can be retried."""
    pass

class ApplicationError(Exception):
    """Base exception for application errors."""
    pass

class WebDriverManager:
    """Context manager for handling Selenium WebDriver resources."""
    
    def __init__(self, options=None):
        self.options = options or Options()
        self.driver = None
        
    def __enter__(self):
        try:
            self.driver = webdriver.Chrome(options=self.options)
            return self.driver
        except WebDriverException as e:
            logging.error(f"Failed to initialize WebDriver: {str(e)}")
            raise ApplicationError("Failed to initialize browser")
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.error(f"Error while closing WebDriver: {str(e)}")

class JobApplicationManager:
    """
    Class for managing job applications.
    """
    
    def __init__(self, resume_path, cover_letter_template_path, config_manager):
        """
        Initialize the job application manager.
        
        Args:
            resume_path (str): Path to the resume file
            cover_letter_template_path (str): Path to the cover letter template file
            config_manager: Configuration manager instance
        """
        logger.info("Initializing JobApplicationManager")
        self.resume_path = resume_path
        self.config = config_manager
        self.applications_log_path = Constants.APPLICATIONS_LOG
        self.applied_jobs = self._load_applied_jobs()
        
        # Initialize AI letter generator
        api_key = self.config.get_config('openai_api_key', '')
        self.ai_letter_generator = AILetterGenerator(api_key=api_key)
        
        # Load cover letter template
        try:
            with open(cover_letter_template_path, 'r', encoding='utf-8') as file:
                self.cover_letter_template = file.read()
            logger.debug("Cover letter template loaded")
        except Exception as e:
            logger.error(f"Error loading cover letter template: {e}", exc_info=True)
            self.cover_letter_template = """
[CURRENT_DATE]

Dear Hiring Manager,

I am writing to express my interest in the [JOB_TITLE] position at [COMPANY_NAME]. I was excited to see this opportunity as it aligns perfectly with my skills and career goals.

[BODY_CONTENT]

I am confident that my skills and experience make me a strong candidate for this position. I would welcome the opportunity to discuss how I can contribute to your team.

Thank you for your consideration.

Sincerely,
[YOUR_NAME]
[YOUR_EMAIL]
[YOUR_PHONE]
            """
            logger.warning("Using default cover letter template")
        
        # Configure Chrome options for Selenium
        self.chrome_options = Options()
        # Not using headless mode as we need to see the application forms
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
    
    def _load_applied_jobs(self):
        """
        Load previously applied jobs from log file.
        
        Returns:
            dict: Dictionary of applied jobs
        """
        logger.debug(f"Loading applied jobs from {self.applications_log_path}")
        if os.path.exists(self.applications_log_path):
            try:
                with open(self.applications_log_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except Exception as e:
                logger.error(f"Error loading applied jobs log: {e}", exc_info=True)
                return {}
        return {}
    
    def _save_applied_jobs(self):
        """Save applied jobs to log file."""
        logger.debug(f"Saving applied jobs to {self.applications_log_path}")
        try:
            with open(self.applications_log_path, 'w', encoding='utf-8') as file:
                json.dump(self.applied_jobs, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving applied jobs log: {e}", exc_info=True)
    
    def show_job_details(self, job_data):
        """
        Show detailed job information.
        
        Args:
            job_data (dict): Job data
        """
        logger.debug(f"Showing job details for {job_data.get('title', 'Unknown')}")
        # Print job details to console
        print("\n" + "="*60)
        print(f"Job Title: {job_data.get('title', 'Unknown')}")
        print(f"Company: {job_data.get('company', 'Unknown')}")
        print(f"Location: {job_data.get('location', 'Unknown')}")
        print(f"Source: {job_data.get('source', 'Unknown')}")
        
        if 'match_score' in job_data:
            print(f"Match Score: {job_data['match_score']}%")
        
        if 'missing_skills' in job_data and job_data['missing_skills']:
            print("\nMissing Skills:")
            for skill in job_data['missing_skills']:
                print(f"- {skill}")
        else:
            print("\nYour resume matches all the required skills!")
        
        print("\nDescription Preview:")
        if 'description' in job_data and job_data['description']:
            description_preview = job_data['description'][:500] + "..." if len(job_data['description']) > 500 else job_data['description']
            print(description_preview)
        else:
            print("No description available")
        
        print("\nJob Link:")
        print(job_data.get('link', 'No link available'))
        print("="*60 + "\n")
    
    def ask_for_application_decision(self, job_data):
        """
        Ask user whether to apply for a job.
        
        Args:
            job_data (dict): Job data
            
        Returns:
            bool: True if user wants to apply, False otherwise
        """
        # Check if already applied
        job_id = f"{job_data.get('company', '')}_{job_data.get('title', '')}"
        if job_id in self.applied_jobs:
            print(f"\nYou've already applied to this job on {self.applied_jobs[job_id]['applied_date']}")
            return False
        
        # Show job details
        self.show_job_details(job_data)
        
        # Ask for decision
        while True:
            decision = input("\nDo you want to apply for this job? (y/n): ").lower().strip()
            if decision in ['y', 'yes']:
                return True
            elif decision in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'.")
    
    def generate_cover_letter(self, job_data):
        """
        Generate a customized cover letter.
        
        Args:
            job_data (dict): Job data
            
        Returns:
            str: Customized cover letter
        """
        logger.debug(f"Generating cover letter for {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
        # Prepare data for AI generation
        resume_data = {
            'name': self.config.get_config('name', 'Your Name'),
            'email': self.config.get_config('email', 'your.email@example.com'),
            'phone': self.config.get_config('phone', '555-555-5555'),
            'current_date': datetime.datetime.now().strftime('%B %d, %Y'),
            'skills': self.config.get_config('skills', []),
            'work_experience': self.config.get_config('experience', []),
            'education': self.config.get_config('education', []),
            'job_title': job_data.get('title', 'the position'),
            'company_name': job_data.get('company', 'your company')
        }
        
        job_description = job_data.get('description', '')
        
        # Use AI to generate personalized cover letter content
        try:
            return self.ai_letter_generator.generate_cover_letter(
                resume_data, 
                job_description, 
                self.cover_letter_template
            )
        except Exception as e:
            logger.error(f"Error generating cover letter with AI: {str(e)}")
            
            # Fallback to old method if AI fails
            return self._fallback_generate_cover_letter(job_data)
    
    def _fallback_generate_cover_letter(self, job_data):
        """
        Generate a cover letter for a job using basic template replacement (fallback method).
        
        Args:
            job_data (dict): Job data
            
        Returns:
            str: Customized cover letter
        """
        # Create a copy of the template
        letter = self.cover_letter_template
        
        # Replace placeholders
        letter = letter.replace('[COMPANY_NAME]', job_data.get('company', 'the Company'))
        letter = letter.replace('[JOB_TITLE]', job_data.get('title', 'the position'))
        letter = letter.replace('[JOB_ID]', str(job_data.get('id', '')))
        letter = letter.replace('[CURRENT_DATE]', datetime.datetime.now().strftime('%B %d, %Y'))
        
        # Add personal info
        letter = letter.replace('[YOUR_NAME]', self.config.get_config('name', 'Your Name'))
        letter = letter.replace('[YOUR_EMAIL]', self.config.get_config('email', 'your.email@example.com'))
        letter = letter.replace('[YOUR_PHONE]', self.config.get_config('phone', '555-555-5555'))
        
        # Create a basic custom paragraph based on skills
        skills = self.config.get_config('skills', [])
        if skills:
            skills_text = ', '.join(skills[:5])  # Use first 5 skills
            custom_paragraph = f"""
            I am excited to apply for the {job_data.get('title', 'the position')} position at {job_data.get('company', 'your company')}. 
            Based on my review of the job description, I believe my skills in {skills_text} 
            make me a strong candidate for this role. My previous experience has prepared me 
            to contribute effectively to your team from day one. I am particularly interested 
            in this position because it aligns well with my career goals and skillset.
            """
        else:
            custom_paragraph = """
            I am excited to apply for this position and believe my skills and experiences
            make me a strong candidate. I am eager to contribute to your team and am
            confident that I can make a positive impact in this role.
            """
        
        # Replace body content
        letter = letter.replace('[BODY_CONTENT]', custom_paragraph)
        
        return letter
    
    def save_cover_letter(self, job_data, cover_letter):
        """
        Save cover letter to file.
        
        Args:
            job_data (dict): Job data
            cover_letter (str): Customized cover letter
            
        Returns:
            str: Path to saved cover letter file
        """
        logger.debug(f"Saving cover letter for {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
        # Create output directory if it doesn't exist
        output_dir = Constants.COVER_LETTERS_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename using sanitized company name and job title
        company_name = Utils.sanitize_filename(job_data.get('company', 'company'))
        job_title = Utils.sanitize_filename(job_data.get('title', 'job'))
        filename = f"{output_dir}/cover_letter_{company_name}_{job_title}.txt"
        
        # Save cover letter
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(cover_letter)
            logger.info(f"Cover letter saved to {filename}")
            print(f"Cover letter saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving cover letter: {e}", exc_info=True)
            return None
    
    def apply_to_job(self, job_data):
        """
        Apply to a job.
        
        Args:
            job_data (dict): Job data
            
        Returns:
            bool: True if application successful, False otherwise
        """
        logger.info(f"Applying to job: {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
        
        # Generate cover letter
        cover_letter = self.generate_cover_letter(job_data)
        cover_letter_path = self.save_cover_letter(job_data, cover_letter)
        
        if not cover_letter_path:
            logger.error("Failed to save cover letter")
            return False
        
        # Open job application page
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(job_data.get('link', ''))
            
            print(f"\nOpening application page for {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
            print("Please complete the application manually.")
            print(f"Use the cover letter saved at: {cover_letter_path}")
            print(f"Use the resume at: {self.resume_path}")
            
            # Wait for manual completion
            input("\nPress Enter when you have completed the application or want to exit...")
            
            # Log the application
            job_id = f"{job_data.get('company', '')}_{job_data.get('title', '')}"
            self.applied_jobs[job_id] = {
                'title': job_data.get('title', 'Unknown'),
                'company': job_data.get('company', 'Unknown'),
                'link': job_data.get('link', ''),
                'applied_date': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_applied_jobs()
            
            logger.info(f"Application to {job_data.get('company', '')} completed")
            driver.quit()
            return True
        
        except Exception as e:
            logger.error(f"Error applying to job: {e}", exc_info=True)
            if 'driver' in locals():
                driver.quit()
            return False
    
    def get_applied_job_stats(self):
        """
        Get statistics about applied jobs.
        
        Returns:
            dict: Statistics about applied jobs
        """
        total_applied = len(self.applied_jobs)
        
        # Count by company
        company_counts = {}
        for job_id, job_data in self.applied_jobs.items():
            company = job_data.get('company', 'Unknown')
            company_counts[company] = company_counts.get(company, 0) + 1
        
        # Get top companies
        top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Get application dates
        dates = [job_data.get('applied_date', '').split(' ')[0] for job_data in self.applied_jobs.values()]
        date_counts = {}
        for date in dates:
            if date:
                date_counts[date] = date_counts.get(date, 0) + 1
        
        # Sort by date
        application_trend = sorted(date_counts.items())
        
        return {
            'total_applied': total_applied,
            'top_companies': top_companies,
            'application_trend': application_trend
        }
    
    def show_applied_jobs(self):
        """Show list of applied jobs."""
        if not self.applied_jobs:
            print("\nYou haven't applied to any jobs yet.")
            return
        
        print("\n" + "="*60)
        print(f"Applied Jobs: {len(self.applied_jobs)}")
        print("="*60)
        
        for i, (job_id, job_data) in enumerate(sorted(self.applied_jobs.items(), 
                                                    key=lambda x: x[1].get('applied_date', ''), 
                                                    reverse=True), 1):
            print(f"{i}. {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
            print(f"   Applied on: {job_data.get('applied_date', 'Unknown date')}")
            print(f"   Link: {job_data.get('link', 'No link')}")
            print()
        
        # Show statistics
        stats = self.get_applied_job_stats()
        print("\nApplication Statistics:")
        print(f"Total applications: {stats['total_applied']}")
        
        if stats['top_companies']:
            print("\nTop companies:")
            for company, count in stats['top_companies']:
                print(f"- {company}: {count} applications")
        
        print("="*60 + "\n") 