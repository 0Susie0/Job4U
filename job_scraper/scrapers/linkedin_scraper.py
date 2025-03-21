"""
LinkedIn job scraper implementation.
"""

import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import List, Dict, Any, Optional

from job_scraper.scrapers.base_scraper import BaseScraper
from job_scraper.utils.utils import Utils

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job listings."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """Initialize LinkedIn scraper."""
        super().__init__(config, logger)
        self.domain = "www.linkedin.com"
        self.user_agent = config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    def get_search_urls(self, keywords: List[str], location: str, num_pages: int = 1) -> List[str]:
        """
        Generate search URLs for LinkedIn.
        
        Args:
            keywords: List of search terms
            location: Job location
            num_pages: Number of pages to search
            
        Returns:
            List of search URLs
        """
        urls = []
        for keyword in keywords:
            for page in range(1, num_pages + 1):
                # LinkedIn uses 'start' parameter for pagination, with 25 jobs per page
                start = (page - 1) * 25
                url = f"https://{self.domain}/jobs/search/?keywords={keyword.replace(' ', '%20')}&location={location.replace(' ', '%20')}&start={start}"
                urls.append(url)
        
        self.logger.info(f"Generated {len(urls)} search URLs for LinkedIn")
        return urls
        
    def extract_job_urls(self, search_url: str) -> List[str]:
        """
        Extract job URLs from a LinkedIn search results page.
        
        Args:
            search_url: URL of the search results page
            
        Returns:
            List of job URLs
        """
        job_urls = []
        
        # Check if scraping is allowed
        if not self.check_site_allowed(self.domain):
            self.logger.warning(f"Scraping not allowed for {self.domain} according to robots.txt")
            return job_urls
            
        # LinkedIn requires JavaScript, so we need to use Selenium
        driver = None
        try:
            driver = self.get_driver()
            self.logger.info(f"Navigating to {search_url}")
            
            # Add random delay to avoid getting blocked
            self.add_random_delay()
            
            driver.get(search_url)
            
            # Get job container selector from configuration
            job_container = self.config.get('linkedin_job_container', 'base-search-card')
            
            # Wait for job listings to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, job_container))
            )
            
            # Get job cards
            job_cards = driver.find_elements(By.CLASS_NAME, job_container)
            
            if not job_cards:
                self.logger.warning(f"No job elements found on page {search_url}")
                return job_urls
                
            for job_card in job_cards:
                try:
                    link_element = job_card.find_element(By.TAG_NAME, "a")
                    if link_element and link_element.get_attribute("href"):
                        job_url = link_element.get_attribute("href")
                        job_urls.append(job_url)
                except Exception as e:
                    self.logger.error(f"Error extracting job URL: {str(e)}")
                    
            self.logger.info(f"Found {len(job_urls)} job URLs on {search_url}")
            
        except Exception as e:
            self.logger.error(f"Error extracting job URLs from {search_url}: {str(e)}")
            
        finally:
            if driver:
                driver.quit()
                
        return job_urls
    
    def scrape(self, search_terms, location, num_pages=None):
        """
        Scrape job listings from LinkedIn.
        
        Args:
            search_terms (list): List of job titles or keywords to search
            location (str): Location to search for jobs
            num_pages (int): Number of pages to scrape
            
        Returns:
            list: Job listings
        """
        if num_pages is None:
            num_pages = self.config.get('max_pages', 3)
        
        # Check if scraping is allowed
        if not self.check_site_allowed(self.domain):
            self.logger.warning(f"Scraping not allowed for {self.domain} according to robots.txt")
            return self.job_listings
        
        self.logger.info(f"Scraping LinkedIn for {search_terms} in {location}...")
        
        # Get selectors from configuration
        job_container = self.config.get('linkedin_job_container', 'base-search-card')
        title_selector = self.config.get('linkedin_title', 'base-search-card__title')
        company_selector = self.config.get('linkedin_company', 'base-search-card__subtitle')
        location_selector = self.config.get('linkedin_location', 'job-search-card__location')
        
        jobs_before = len(self.job_listings)
        
        for search_term in search_terms:
            for page in range(0, num_pages * 25, 25):  # LinkedIn uses 25 jobs per page
                url = f"https://{self.domain}/jobs/search/?keywords={search_term.replace(' ', '%20')}&location={location.replace(' ', '%20')}&start={page}"
                
                # Add random delay
                self.add_random_delay()
                
                try:
                    driver = self.get_driver()
                    driver.get(url)
                    
                    try:
                        # Wait for job container to load
                        WebDriverWait(driver, self.config.get('timeout', 10)).until(
                            EC.presence_of_element_located((By.CLASS_NAME, job_container))
                        )
                        
                        # Scroll to load all jobs (dynamic loading)
                        for _ in range(5):
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1)
                        
                        job_elements = driver.find_elements(By.CLASS_NAME, job_container)
                        
                        if not job_elements:
                            self.logger.warning(f"No job elements found on page {page//25 + 1} for {search_term}. Selector might need updating.")
                            driver.quit()
                            continue
                        
                        for job in job_elements:
                            try:
                                # Use utility for safer element text extraction
                                title = Utils.safe_get_element_text(job, By.CLASS_NAME, title_selector, "No title")
                                company = Utils.safe_get_element_text(job, By.CLASS_NAME, company_selector, "No company")
                                location = Utils.safe_get_element_text(job, By.CLASS_NAME, location_selector, "No location")
                                
                                # Get link - LinkedIn usually has a reliable link class
                                try:
                                    link_element = job.find_element(By.CLASS_NAME, "base-card__full-link")
                                    link = link_element.get_attribute("href")
                                except NoSuchElementException:
                                    # Fallback to find any link
                                    links = job.find_elements(By.TAG_NAME, "a")
                                    link = next((l.get_attribute("href") for l in links if l.get_attribute("href")), "")
                                
                                # Create job data dictionary
                                job_data = {
                                    'title': title,
                                    'company': company,
                                    'location': location,
                                    'link': link,
                                    'source': 'LinkedIn'
                                }
                                
                                # Add job to results
                                self.job_listings.append(job_data)
                                
                            except Exception as e:
                                self.logger.error(f"Error parsing job: {e}", exc_info=True)
                    
                    except TimeoutException:
                        self.logger.warning(f"Timeout waiting for LinkedIn jobs to load on page {page//25 + 1} for {search_term}")
                    
                    finally:
                        driver.quit()
                
                except Exception as e:
                    self.logger.error(f"Error scraping page {page//25 + 1} for {search_term}: {e}", exc_info=True)
                    if 'driver' in locals():
                        driver.quit()
        
        linkedin_jobs_count = len(self.job_listings) - jobs_before
        self.logger.info(f"Found {linkedin_jobs_count} job listings on LinkedIn")
        return self.job_listings
    
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific job from LinkedIn.
        
        Args:
            job_url: URL of the job listing
            
        Returns:
            Job details as a dictionary
        """
        try:
            self.logger.info(f"Getting job details for: {job_url}")
            
            # Get the job page
            driver = self.get_driver()
            
            try:
                # Add random delay to avoid getting blocked
                self.add_random_delay()
                
                driver.get(job_url)
                
                # Wait for the page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Extract job details
                title = ""
                company = ""
                location = ""
                description = ""
                
                # Get job title
                try:
                    title_element = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title")
                    title = title_element.text.strip()
                except NoSuchElementException:
                    self.logger.warning(f"Could not find job title for {job_url}")
                
                # Get company name
                try:
                    company_element = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__company-name")
                    company = company_element.text.strip()
                except NoSuchElementException:
                    self.logger.warning(f"Could not find company name for {job_url}")
                
                # Get location
                try:
                    location_element = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__bullet")
                    location = location_element.text.strip()
                except NoSuchElementException:
                    self.logger.warning(f"Could not find location for {job_url}")
                
                # Get description
                description_selector = self.config.get('linkedin_description', 'show-more-less-html__markup')
                try:
                    # Wait for description to load (LinkedIn is a SPA, so needs explicit wait)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, description_selector))
                    )
                    description_element = driver.find_element(By.CLASS_NAME, description_selector)
                    description = description_element.text.strip()
                except (TimeoutException, NoSuchElementException):
                    # Try alternative method - LinkedIn sometimes uses different selectors
                    try:
                        # Alternative: sometimes job descriptions are in specific sections
                        job_description_sections = driver.find_elements(By.CSS_SELECTOR, ".description__text section p")
                        if job_description_sections:
                            description = "\n".join([elem.text for elem in job_description_sections])
                        else:
                            # Another fallback
                            job_description_div = driver.find_element(By.CSS_SELECTOR, ".description__text")
                            description = job_description_div.text.strip()
                    except NoSuchElementException:
                        self.logger.warning(f"Could not extract job description using selector")
                
                # Create job details dictionary
                job_details = {
                    'title': title,
                    'company': company,
                    'location': location,
                    'description': description,
                    'link': job_url,
                    'source': 'LinkedIn'
                }
                
                return job_details
                
            finally:
                driver.quit()
                
        except Exception as e:
            self.logger.error(f"Error getting job details for {job_url}: {str(e)}")
            return {
                'title': 'Unknown',
                'company': 'Unknown',
                'location': 'Unknown',
                'description': '',
                'link': job_url,
                'source': 'LinkedIn',
                'error': str(e)
            } 