"""
Main module for the job scraper application.
"""

import os
import sys
import logging
import argparse
from typing import List, Optional, Dict, Any, Union

from .config import ConfigManager
from .database import DatabaseManager
from .utils import Utils
from .scrapers.seek_scraper import SeekScraper
from .scrapers.indeed_scraper import IndeedScraper
from .scrapers.linkedin_scraper import LinkedInScraper
from .resume_parser import ResumeParser
from .job_matcher import JobMatcher
from .application_manager import JobApplicationManager

logger = logging.getLogger(__name__)

class JobScraperApp:
    """
    Main class for the job scraper application.
    
    This class coordinates the different components of the application,
    including scrapers, resume parsing, job matching, and applications.
    """
    
    def __init__(self):
        """Initialize the job scraper application."""
        # Set up logging
        Utils.setup_logging()
        logger.info("Initializing JobScraperApp")
        
        # Set up configuration
        self.config = ConfigManager()
        
        # Set up database
        self.db = DatabaseManager()
        
        # Initialize scrapers
        self.seek_scraper = SeekScraper(self.config, self.db)
        self.indeed_scraper = IndeedScraper(self.config, self.db)
        self.linkedin_scraper = LinkedInScraper(self.config, self.db)
        
        # Initialize other components as needed
        self.resume_parser = None
        self.job_matcher = None
        self.application_manager = None
        
        # Job listings
        self.job_listings = []
        self.matched_jobs = []
    
    def scrape_jobs(self, search_terms: List[str], country: str = None, city: str = None, 
                   sites: List[str] = None, num_pages: int = None) -> List[Dict[str, Any]]:
        """
        Scrape job listings from selected sites.
        
        Args:
            search_terms (list): List of job titles or keywords to search
            country (str): Country to search for jobs
            city (str): City to search for jobs
            sites (list): List of job sites to scrape (seek, indeed, linkedin)
            num_pages (int): Number of pages to scrape per site
            
        Returns:
            list: Job listings
        """
        # Format the location string based on provided country and city
        location = ""
        if city and country:
            location = f"{city}, {country}"
        elif city:
            location = city
        elif country:
            location = country
        else:
            location = "Australia"  # Default location
        
        logger.info(f"Starting job scraping for {search_terms} in {location}")
        
        if sites is None:
            sites = ['seek', 'indeed', 'linkedin']
        
        if 'seek' in sites:
            logger.info("Scraping Seek.com.au")
            seek_jobs = self.seek_scraper.scrape(search_terms, location, num_pages)
            self.job_listings.extend(seek_jobs)
        
        if 'indeed' in sites:
            logger.info("Scraping Indeed.com.au")
            indeed_jobs = self.indeed_scraper.scrape(search_terms, location, num_pages)
            self.job_listings.extend(indeed_jobs)
        
        if 'linkedin' in sites:
            logger.info("Scraping LinkedIn")
            linkedin_jobs = self.linkedin_scraper.scrape(search_terms, location, num_pages)
            self.job_listings.extend(linkedin_jobs)
        
        logger.info(f"Completed scraping. Found {len(self.job_listings)} jobs.")
        return self.job_listings
    
    def get_job_details(self, max_jobs: int = 10) -> List[Dict[str, Any]]:
        """
        Get detailed job descriptions.
        
        Args:
            max_jobs (int): Maximum number of jobs to get details for
            
        Returns:
            list: Job listings with detailed descriptions
        """
        logger.info(f"Getting job details for up to {max_jobs} jobs")
        
        jobs_with_details = []
        jobs_to_process = self.job_listings[:max_jobs]
        
        for i, job in enumerate(jobs_to_process):
            logger.debug(f"Processing job {i+1}/{len(jobs_to_process)}: {job.get('title', 'Unknown')}")
            
            # Skip if job already has a description
            if job.get('description'):
                jobs_with_details.append(job)
                continue
            
            # Get job details based on source
            source = job.get('source')
            description = None
            
            if source == 'Seek':
                description = self.seek_scraper.get_job_details(job)
            elif source == 'Indeed':
                description = self.indeed_scraper.get_job_details(job)
            elif source == 'LinkedIn':
                description = self.linkedin_scraper.get_job_details(job)
            
            if description:
                job['description'] = description
                
                # Extract deadline from description
                if source == 'Seek':
                    deadline = self.seek_scraper.extract_deadline(description)
                elif source == 'Indeed':
                    deadline = self.indeed_scraper.extract_deadline(description)
                elif source == 'LinkedIn':
                    deadline = self.linkedin_scraper.extract_deadline(description)
                else:
                    deadline = None
                
                if deadline:
                    job['deadline'] = deadline
                
                # Update job in database
                self.db.insert_job(job)
                
                jobs_with_details.append(job)
        
        logger.info(f"Got detailed descriptions for {len(jobs_with_details)} jobs")
        return jobs_with_details
    
    def check_expired_jobs(self) -> int:
        """
        Check for expired jobs and mark them as such.
        
        Returns:
            int: Number of jobs marked as expired
        """
        logger.info("Checking for expired jobs")
        count = self.db.check_and_mark_expired_jobs()
        if count > 0:
            logger.info(f"Marked {count} job(s) as expired")
        else:
            logger.info("No expired jobs found")
        return count
    
    def delete_expired_jobs(self, older_than_days: int = 30) -> int:
        """
        Delete expired jobs older than the specified number of days.
        
        Args:
            older_than_days (int): Number of days since expiration to keep jobs
            
        Returns:
            int: Number of jobs deleted
        """
        logger.info(f"Deleting expired jobs older than {older_than_days} days")
        count = self.db.delete_expired_jobs(older_than_days)
        if count > 0:
            logger.info(f"Deleted {count} expired job(s)")
        else:
            logger.info("No jobs to delete")
        return count
    
    def show_expiring_jobs(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Show jobs that will expire within the specified number of days.
        
        Args:
            days (int): Number of days to check for expiring jobs
            
        Returns:
            list: List of expiring jobs
        """
        logger.info(f"Finding jobs expiring within {days} days")
        conn = self.db.connect()
        cursor = conn.cursor()
        
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        
        cursor.execute('''
        SELECT id, title, company, location, source, deadline 
        FROM jobs 
        WHERE deadline IS NOT NULL 
        AND deadline >= ? 
        AND deadline <= ?
        AND is_expired = 0
        ORDER BY deadline ASC
        ''', (today, expiry_date))
        
        expiring_jobs = [dict(job) for job in cursor.fetchall()]
        
        if expiring_jobs:
            print("\n" + "="*60)
            print(f"Jobs expiring within {days} days:")
            print("="*60)
            
            for job in expiring_jobs:
                print(f"{job['title']} at {job['company']} ({job['source']})")
                print(f"Location: {job['location']}")
                print(f"Deadline: {job['deadline']}")
                print("-"*40)
            
            print("="*60 + "\n")
        else:
            print(f"No jobs found that expire within {days} days.")
        
        return expiring_jobs
    
    def parse_resume(self, resume_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse resume and extract information.
        
        Args:
            resume_path (str): Path to resume file
            
        Returns:
            dict: Parsed resume data or None if error
        """
        logger.info(f"Parsing resume: {resume_path}")
        
        if not os.path.exists(resume_path):
            logger.error(f"Resume file not found: {resume_path}")
            return None
        
        self.resume_parser = ResumeParser()
        resume_data = self.resume_parser.parse_resume(resume_path)
        
        if resume_data:
            logger.info(f"Resume parsed successfully with {len(resume_data.get('skills', []))} skills")
        else:
            logger.error("Failed to parse resume")
        
        return resume_data
    
    def match_jobs(self, resume_data: Dict[str, Any], 
                  job_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match jobs with resume.
        
        Args:
            resume_data (dict): Parsed resume data
            job_listings (list): List of job listings
            
        Returns:
            list: Job listings with match scores
        """
        logger.info("Matching jobs with resume")
        
        if not resume_data:
            logger.error("No resume data provided for matching")
            return []
        
        self.job_matcher = JobMatcher(resume_data)
        self.matched_jobs = self.job_matcher.match_jobs(job_listings)
        
        logger.info(f"Matched {len(self.matched_jobs)} jobs")
        return self.matched_jobs
    
    def setup_application_manager(self, resume_path: str, 
                                cover_letter_path: str) -> bool:
        """
        Set up the application manager.
        
        Args:
            resume_path (str): Path to resume file
            cover_letter_path (str): Path to cover letter template
            
        Returns:
            bool: True if setup successful, False otherwise
        """
        logger.info("Setting up application manager")
        
        if not os.path.exists(resume_path):
            logger.error(f"Resume file not found: {resume_path}")
            return False
        
        if not os.path.exists(cover_letter_path):
            logger.error(f"Cover letter template not found: {cover_letter_path}")
            return False
        
        self.application_manager = JobApplicationManager(resume_path, cover_letter_path, self.config)
        return True
    
    def apply_to_jobs(self, matched_jobs: List[Dict[str, Any]], 
                     top_n: int = 10) -> int:
        """
        Apply to top matching jobs.
        
        Args:
            matched_jobs (list): List of matched job listings
            top_n (int): Number of top matches to consider
            
        Returns:
            int: Number of successful applications
        """
        logger.info(f"Starting job application process for top {top_n} matches")
        
        if not self.application_manager:
            logger.error("Application manager not set up")
            return 0
        
        successful_applications = 0
        jobs_to_apply = matched_jobs[:min(top_n, len(matched_jobs))]
        
        for job in jobs_to_apply:
            if self.application_manager.ask_for_application_decision(job):
                if self.application_manager.apply_to_job(job):
                    successful_applications += 1
                
                # Ask whether to continue
                continue_choice = input("\nContinue with next job? (y/n): ").lower().strip()
                if continue_choice in ['n', 'no']:
                    break
        
        logger.info(f"Completed {successful_applications} job applications")
        return successful_applications
    
    def show_job_stats(self):
        """Show statistics about jobs in the database."""
        all_jobs = self.db.get_all_jobs()
        
        print("\n" + "="*60)
        print(f"Job Statistics")
        print("="*60)
        
        print(f"Total jobs in database: {len(all_jobs)}")
        
        # Count by source
        sources = {}
        for job in all_jobs:
            source = job.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print("\nJobs by source:")
        for source, count in sources.items():
            print(f"- {source}: {count}")
        
        # Count by location
        locations = {}
        for job in all_jobs:
            location = job.get('location', 'Unknown')
            locations[location] = locations.get(location, 0) + 1
        
        print("\nTop locations:")
        top_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]
        for location, count in top_locations:
            print(f"- {location}: {count}")
        
        # Count by expiry status
        expired_count = sum(1 for job in all_jobs if job.get('is_expired', 0) == 1)
        active_count = len(all_jobs) - expired_count
        
        print(f"\nActive jobs: {active_count}")
        print(f"Expired jobs: {expired_count}")
        
        print("="*60 + "\n")
    
    def close(self):
        """Close database connection and release resources."""
        logger.info("Closing resources")
        if self.db:
            self.db.close()


def main():
    """Main entry point for the job scraper application."""
    parser = argparse.ArgumentParser(description='Job Scraper Tool')
    
    parser.add_argument('--search', '-s', type=str, nargs='+', required=False,
                        help='Search terms or job titles to look for')
    
    parser.add_argument('--country', type=str, default='Australia',
                        help='Country to search for jobs (default: Australia)')
    
    parser.add_argument('--city', type=str, default=None,
                        help='City to search for jobs (e.g., Sydney, Melbourne)')
    
    parser.add_argument('--location', '-l', type=str, default=None,
                        help='Full location string (alternative to --country and --city)')
    
    parser.add_argument('--sites', type=str, choices=['seek', 'indeed', 'linkedin', 'all'],
                        default='all', help='Job sites to scrape (default: all)')
    
    parser.add_argument('--pages', '-p', type=int, default=2,
                        help='Number of pages to scrape per site (default: 2)')
    
    parser.add_argument('--details', '-d', type=int, default=10,
                        help='Number of jobs to get detailed descriptions for (default: 10)')
    
    parser.add_argument('--resume', '-r', type=str,
                        help='Path to resume file (PDF, DOCX, or TXT)')
    
    parser.add_argument('--cover-letter', '-c', type=str,
                        help='Path to cover letter template')
    
    parser.add_argument('--matches', '-m', type=int, default=10,
                        help='Number of top matching jobs to show (default: 10)')
    
    parser.add_argument('--apply', '-a', action='store_true',
                        help='Apply to jobs (requires --resume and --cover-letter)')
    
    parser.add_argument('--check-expired', action='store_true',
                        help='Check for and mark expired jobs')
    
    parser.add_argument('--delete-expired', type=int, metavar='DAYS', nargs='?', const=30,
                        help='Delete expired jobs older than specified days (default: 30)')
    
    parser.add_argument('--show-expiring', type=int, metavar='DAYS', nargs='?', const=7,
                        help='Show jobs expiring within specified days (default: 7)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    Utils.setup_logging(level=log_level)
    
    # Convert sites argument to list
    if args.sites == 'all':
        sites = ['seek', 'indeed', 'linkedin']
    else:
        sites = [args.sites]
    
    app = JobScraperApp()
    
    try:
        # Check if any maintenance operations are requested
        maintenance_performed = False
        
        # Process expired jobs
        if args.check_expired:
            app.check_expired_jobs()
            maintenance_performed = True
        
        # Delete expired jobs
        if args.delete_expired is not None:
            app.delete_expired_jobs(args.delete_expired)
            maintenance_performed = True
        
        # Show expiring jobs
        if args.show_expiring is not None:
            app.show_expiring_jobs(args.show_expiring)
            maintenance_performed = True
        
        # If only maintenance was performed, exit
        if maintenance_performed and not args.search:
            app.show_job_stats()
            app.close()
            return 0
        
        # If search terms are not provided and no maintenance operations were performed,
        # print usage info and exit
        if not args.search:
            parser.print_help()
            print("\nError: Missing required argument --search/-s")
            return 1
        
        # Determine location parameters
        country = None
        city = None
        
        if args.location:
            # Use the legacy location parameter if provided
            location = args.location
            # Try to split it into city and country if it contains a comma
            if ',' in location:
                parts = [part.strip() for part in location.split(',')]
                if len(parts) >= 2:
                    city = parts[0]
                    country = parts[1]
                else:
                    country = location
            else:
                country = location
        else:
            # Use the new country and city parameters
            country = args.country
            city = args.city
        
        # Scrape job listings
        app.scrape_jobs(args.search, country, city, sites, args.pages)
        
        if not app.job_listings:
            print("No jobs found. Try different search terms or location.")
            app.close()
            return 1
        
        # Get detailed descriptions
        if args.details > 0:
            app.get_job_details(max_jobs=args.details)
        
        # Check for expired jobs after scraping
        app.check_expired_jobs()
        
        # Match with resume if provided
        if args.resume:
            resume_data = app.parse_resume(args.resume)
            
            if resume_data:
                matched_jobs = app.match_jobs(resume_data, app.job_listings)
                
                # Show top matches
                print(f"\nTop {min(args.matches, len(matched_jobs))} matching jobs:")
                for i, job in enumerate(matched_jobs[:args.matches], 1):
                    deadline_info = f" (Deadline: {job.get('deadline', 'Unknown')})" if job.get('deadline') else ""
                    print(f"{i}. {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')} - " +
                          f"Match: {job.get('match_score', 0)}%{deadline_info}")
                
                # Apply to jobs if requested
                if args.apply and args.cover_letter:
                    if app.setup_application_manager(args.resume, args.cover_letter):
                        app.apply_to_jobs(matched_jobs, args.matches)
                
            else:
                print("Could not parse resume. Job matching and application not available.")
        
        # Show overall statistics
        app.show_job_stats()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        return 1
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
        
    finally:
        app.close()


if __name__ == "__main__":
    sys.exit(main()) 