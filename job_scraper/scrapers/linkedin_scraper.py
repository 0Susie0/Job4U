"""
LinkedIn job scraper implementation.
"""

import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_scraper import BaseScraper
from ..utils import Utils

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job listings."""
    
    def __init__(self, config_manager, db_manager):
        """Initialize LinkedIn scraper."""
        super().__init__(config_manager, db_manager)
        self.domain = "www.linkedin.com"
    
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
            num_pages = self.config.get_int('SCRAPING', 'max_pages', 3)
        
        # Check if scraping is allowed
        if not self.check_site_allowed(self.domain):
            logger.warning(f"Scraping not allowed for {self.domain} according to robots.txt")
            return self.job_listings
        
        logger.info(f"Scraping LinkedIn for {search_terms} in {location}...")
        
        # Get selectors from configuration
        job_container = self.config.get('SELECTORS', 'linkedin_job_container', 'base-search-card')
        title_selector = self.config.get('SELECTORS', 'linkedin_title', 'base-search-card__title')
        company_selector = self.config.get('SELECTORS', 'linkedin_company', 'base-search-card__subtitle')
        location_selector = self.config.get('SELECTORS', 'linkedin_location', 'job-search-card__location')
        
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
                        WebDriverWait(driver, self.config.get_int('SELENIUM', 'timeout', 10)).until(
                            EC.presence_of_element_located((By.CLASS_NAME, job_container))
                        )
                        
                        # Scroll to load all jobs (dynamic loading)
                        for _ in range(5):
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1)
                        
                        job_elements = driver.find_elements(By.CLASS_NAME, job_container)
                        
                        if not job_elements:
                            logger.warning(f"No job elements found on page {page//25 + 1} for {search_term}. Selector might need updating.")
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
                                
                                # Insert into database
                                job_id = self.db.insert_job(job_data)
                                if job_id:
                                    job_data['id'] = job_id
                                    self.job_listings.append(job_data)
                                
                            except Exception as e:
                                logger.error(f"Error parsing job: {e}", exc_info=True)
                    
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for LinkedIn jobs to load on page {page//25 + 1} for {search_term}")
                    
                    finally:
                        driver.quit()
                
                except Exception as e:
                    logger.error(f"Error scraping page {page//25 + 1} for {search_term}: {e}", exc_info=True)
                    if 'driver' in locals():
                        driver.quit()
        
        linkedin_jobs_count = len(self.job_listings) - jobs_before
        logger.info(f"Found {linkedin_jobs_count} job listings on LinkedIn")
        return self.job_listings
    
    def get_job_details(self, job, driver=None):
        """
        Get detailed job description from LinkedIn.
        
        Args:
            job (dict): Job data
            driver (WebDriver): Optional existing WebDriver instance
            
        Returns:
            str: Job description
        """
        if job['source'] != 'LinkedIn':
            logger.warning(f"Cannot get details for non-LinkedIn job: {job['title']}")
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
            description_selector = self.config.get('SELECTORS', 'linkedin_description', 'show-more-less-html__markup')
            
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