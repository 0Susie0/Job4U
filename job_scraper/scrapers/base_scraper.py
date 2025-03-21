"""
Base scraper class definition for job scraping.
"""

import time
import random
import logging
import re
import datetime
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from ..utils import Utils
from ..config import Constants
from ..utils import validate_url

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Base abstract class for all job scrapers.
    
    This class provides common functionality for all job scrapers,
    including driver setup, delay management, and robots.txt checking.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the base scraper.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.max_workers = self.config.get('max_concurrent_requests', 5)
        self.delay = self.config.get('request_delay', 1.0)  # Seconds between requests
        self.timeout = self.config.get('request_timeout', 30)
        self.retry_count = self.config.get('retry_count', 3)
        self.setup_webdriver()
        self.job_listings = []
        
    def setup_webdriver(self):
        """Set up Chrome options for Selenium."""
        self.chrome_options = Options()
        if self.config.get('headless', True):
            self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        # Add user agent to avoid detection
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
    def get_driver(self):
        """Get a new WebDriver instance."""
        return webdriver.Chrome(options=self.chrome_options)
    
    def check_site_allowed(self, domain):
        """
        Check if scraping is allowed for this site according to robots.txt.
        
        Args:
            domain (str): Domain to check
            
        Returns:
            bool: True if allowed, False otherwise
        """
        if self.config.get_boolean('SCRAPING', 'respect_robots_txt', True):
            return Utils.check_robots_txt(domain)
        return True
    
    def add_random_delay(self):
        """Add a random delay between requests to avoid getting blocked."""
        min_delay = self.config.get_float('SCRAPING', 'min_delay', 2)
        max_delay = self.config.get_float('SCRAPING', 'max_delay', 5)
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def extract_deadline(self, text):
        """
        Extract application deadline from job description.
        
        Args:
            text (str): Job description text
            
        Returns:
            str: Deadline date in YYYY-MM-DD format or None if not found
        """
        if not text:
            return None
            
        deadline_patterns = [
            # Common deadline formats
            r"(?:closing|application|apply by|deadline)[:\s].*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(?:closing|application|apply by|deadline)[:\s].*?(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:\s+\d{2,4})?)",
            r"applications?\s+(?:will\s+)?close\s+(?:on|by)?\s+(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:\s+\d{2,4})?)",
            r"apply before (\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:\s+\d{2,4})?)",
            
            # Specific timeframes
            r"applications? close\s+in\s+(\d+)\s+days",
            r"applications? close\s+in\s+(\d+)\s+weeks",
        ]
        
        # Search for deadline patterns
        for pattern in deadline_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                deadline_str = matches.group(1).strip()
                
                # Process timeframes (days/weeks)
                if "days" in pattern or "weeks" in pattern:
                    try:
                        num = int(deadline_str)
                        today = datetime.date.today()
                        if "days" in pattern:
                            deadline_date = today + datetime.timedelta(days=num)
                        else:  # weeks
                            deadline_date = today + datetime.timedelta(weeks=num)
                        return deadline_date.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        continue
                
                # Process date formats
                try:
                    # Try to parse different date formats
                    for date_format in ["%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y", 
                                       "%d/%m/%y", "%d-%m-%y", "%m/%d/%y", "%m-%d-%y"]:
                        try:
                            parsed_date = datetime.datetime.strptime(deadline_str, date_format)
                            return parsed_date.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                    
                    # Try natural language processing for dates like "31st December 2023"
                    # Remove ordinal suffixes
                    deadline_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', deadline_str)
                    
                    # Try common month-name formats
                    for date_format in ["%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
                                       "%d %B", "%d %b", "%B %d", "%b %d"]:
                        try:
                            parsed_date = datetime.datetime.strptime(deadline_str, date_format)
                            # If year is missing, assume current year
                            if "%Y" not in date_format:
                                current_year = datetime.date.today().year
                                parsed_date = parsed_date.replace(year=current_year)
                            return parsed_date.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                    
                except Exception as e:
                    logger.debug(f"Error parsing deadline date '{deadline_str}': {e}")
        
        # Default: assume job posting is valid for 30 days from today if no deadline is found
        default_deadline = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        logger.debug(f"No deadline found, using default (30 days): {default_deadline}")
        return default_deadline
    
    def http_get(self, url: str, use_selenium: bool = False) -> Optional[str]:
        """
        Perform an HTTP GET request with retries and delay.
        
        Args:
            url: URL to fetch
            use_selenium: Whether to use Selenium or requests
            
        Returns:
            Page content as string or None if failed
        """
        for attempt in range(self.retry_count):
            try:
                if use_selenium:
                    driver = self.get_driver()
                    driver.get(url)
                    time.sleep(self.delay)  # Wait for JavaScript to load
                    content = driver.page_source
                    driver.quit()
                    return content
                else:
                    # Use requests for static content (much faster)
                    response = requests.get(
                        url, 
                        timeout=self.timeout,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    )
                    response.raise_for_status()
                    # Add delay between requests to avoid rate limiting
                    time.sleep(self.delay)
                    return response.text
            except Exception as e:
                self.logger.warning(f"Error fetching {url} (attempt {attempt+1}/{self.retry_count}): {str(e)}")
                time.sleep(self.delay * (attempt + 1))  # Exponential backoff
                
        self.logger.error(f"Failed to fetch {url} after {self.retry_count} attempts")
        return None
        
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup."""
        return BeautifulSoup(html_content, 'html.parser')
    
    @abstractmethod
    def scrape(self, search_terms, location, num_pages=None):
        """
        Scrape job listings.
        
        This is an abstract method that must be implemented by subclasses.
        
        Args:
            search_terms (list): List of job titles or keywords to search
            location (str): Location to search for jobs
            num_pages (int): Number of pages to scrape
            
        Returns:
            list: Job listings
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_url: URL of the job listing
            
        Returns:
            Job details as a dictionary
        """
        pass
    
    def get_search_urls(self, keywords: List[str], location: str, num_pages: int = 1) -> List[str]:
        """
        Generate search URLs for the given parameters.
        
        Args:
            keywords: List of search terms
            location: Job location
            num_pages: Number of pages to scrape
            
        Returns:
            List of search URLs
        """
        pass
    
    def search_jobs_concurrent(self, keywords: List[str], location: str, num_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Search for jobs concurrently across multiple pages.
        
        Args:
            keywords: List of search terms
            location: Job location
            num_pages: Number of pages to search
            
        Returns:
            List of job dictionaries
        """
        search_urls = self.get_search_urls(keywords, location, num_pages)
        
        if not search_urls:
            self.logger.warning("No search URLs generated")
            return []
            
        # Get job listings concurrently
        job_urls = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.extract_job_urls, url): url 
                for url in search_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    urls = future.result()
                    if urls:
                        job_urls.extend(urls)
                except Exception as e:
                    self.logger.error(f"Error processing search page {url}: {str(e)}")
                    
        self.logger.info(f"Found {len(job_urls)} job URLs")
        
        # Filter out duplicates while preserving order
        unique_job_urls = []
        seen = set()
        for url in job_urls:
            if url not in seen and validate_url(url):
                seen.add(url)
                unique_job_urls.append(url)
                
        self.logger.info(f"Found {len(unique_job_urls)} unique job URLs")
        
        # Get job details concurrently
        all_jobs = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Limit the number of jobs to process based on config
            max_jobs = self.config.get('max_jobs', 100)
            urls_to_process = unique_job_urls[:max_jobs]
            
            self.logger.info(f"Processing details for {len(urls_to_process)} jobs")
            
            future_to_url = {
                executor.submit(self.get_job_details, url): url 
                for url in urls_to_process
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    job_details = future.result()
                    if job_details:
                        all_jobs.append(job_details)
                except Exception as e:
                    self.logger.error(f"Error getting details for job {url}: {str(e)}")
                    
        return all_jobs
    
    @abstractmethod
    def extract_job_urls(self, search_url: str) -> List[str]:
        """
        Extract job URLs from a search results page.
        
        Args:
            search_url: URL of the search results page
            
        Returns:
            List of job URLs
        """
        pass 