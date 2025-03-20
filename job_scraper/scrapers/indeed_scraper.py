"""
Indeed.com.au job scraper implementation.
"""

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_scraper import BaseScraper
from ..utils import Utils

logger = logging.getLogger(__name__)

class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com.au job listings."""
    
    def __init__(self, config_manager, db_manager):
        """Initialize Indeed scraper."""
        super().__init__(config_manager, db_manager)
        self.domain = "au.indeed.com"
    
    def scrape(self, search_terms, location, num_pages=None):
        """
        Scrape job listings from Indeed.com.au.
        
        Args:
            search_terms (list): List of job titles or keywords to search
            location (str): Location to search for jobs
            num_pages (int): Number of pages to scrape
            
        Returns:
            list: Job listings
        """
        if num_pages is None:
            num_pages = self.config.get_int('SCRAPING', 'max_pages', 3)
        
        # Check if scraping is allowed
        if not self.check_site_allowed(self.domain):
            logger.warning(f"Scraping not allowed for {self.domain} according to robots.txt")
            return self.job_listings
        
        logger.info(f"Scraping Indeed.com.au for {search_terms} in {location}...")
        
        # Get selectors from configuration
        job_container = self.config.get('SELECTORS', 'indeed_job_container', 'job_seen_beacon')
        title_selector = self.config.get('SELECTORS', 'indeed_title', 'jcs-JobTitle')
        company_selector = self.config.get('SELECTORS', 'indeed_company', 'companyName')
        location_selector = self.config.get('SELECTORS', 'indeed_location', 'companyLocation')
        
        jobs_before = len(self.job_listings)
        
        for search_term in search_terms:
            for page in range(0, num_pages * 10, 10):  # Indeed uses 10 jobs per page
                url = f"https://{self.domain}/jobs?q={search_term.replace(' ', '+')}&l={location.replace(' ', '+')}&start={page}"
                
                # Add random delay
                self.add_random_delay()
                
                try:
                    driver = self.get_driver()
                    driver.get(url)
                    
                    try:
                        # Wait for job container to load
                        WebDriverWait(driver, self.config.get_int('SELENIUM', 'timeout', 10)).until(
                            EC.presence_of_element_located((By.CLASS_NAME, job_container))
                        )
                        
                        job_elements = driver.find_elements(By.CLASS_NAME, job_container)
                        
                        if not job_elements:
                            logger.warning(f"No job elements found on page {page//10 + 1} for {search_term}. Selector might need updating.")
                            driver.quit()
                            continue
                        
                        for job in job_elements:
                            try:
                                # Use utility for safer element text extraction
                                title = Utils.safe_get_element_text(job, By.CLASS_NAME, title_selector, "No title")
                                company = Utils.safe_get_element_text(job, By.CLASS_NAME, company_selector, "No company")
                                location = Utils.safe_get_element_text(job, By.CLASS_NAME, location_selector, "No location")
                                
                                # Get link from title element or any link
                                try:
                                    title_element = job.find_element(By.CLASS_NAME, title_selector)
                                    link = title_element.get_attribute("href")
                                    if not link:
                                        # Sometimes the title itself is not the link, but its parent is
                                        parent = title_element.find_element(By.XPATH, "./..")
                                        link = parent.get_attribute("href")
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
                                    'source': 'Indeed'
                                }
                                
                                # Insert into database
                                job_id = self.db.insert_job(job_data)
                                if job_id:
                                    job_data['id'] = job_id
                                    self.job_listings.append(job_data)
                                
                            except Exception as e:
                                logger.error(f"Error parsing job: {e}", exc_info=True)
                    
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for Indeed jobs to load on page {page//10 + 1} for {search_term}")
                    
                    finally:
                        driver.quit()
                
                except Exception as e:
                    logger.error(f"Error scraping page {page//10 + 1} for {search_term}: {e}", exc_info=True)
                    if 'driver' in locals():
                        driver.quit()
        
        indeed_jobs_count = len(self.job_listings) - jobs_before
        logger.info(f"Found {indeed_jobs_count} job listings on Indeed")
        return self.job_listings
    
    def get_job_details(self, job, driver=None):
        """
        Get detailed job description from Indeed.com.au.
        
        Args:
            job (dict): Job data
            driver (WebDriver): Optional existing WebDriver instance
            
        Returns:
            str: Job description
        """
        if job['source'] != 'Indeed':
            logger.warning(f"Cannot get details for non-Indeed job: {job['title']}")
            return None
        
        close_driver = False
        if driver is None:
            driver = self.get_driver()
            close_driver = True
        
        try:
            logger.info(f"Getting job details for: {job['title']} at {job['company']}")
            driver.get(job['link'])
            
            # Add random delay
            self.add_random_delay()
            
            # Get description selector from config
            description_selector = self.config.get('SELECTORS', 'indeed_description', 'jobDescriptionText')
            
            try:
                # First try to get by ID
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, description_selector))
                )
                description_element = driver.find_element(By.ID, description_selector)
                description = description_element.text.strip()
            except (TimeoutException, NoSuchElementException):
                try:
                    # Then try by class name
                    description_element = driver.find_element(By.CLASS_NAME, description_selector)
                    description = description_element.text.strip()
                except (NoSuchElementException, Exception) as e:
                    logger.warning(f"Could not extract job description using selector: {e}")
                    description = "Could not extract job description"
            
            return description
            
        except Exception as e:
            logger.error(f"Error getting job details: {e}", exc_info=True)
            return None
        
        finally:
            if close_driver and driver:
                driver.quit() 