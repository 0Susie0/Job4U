"""
Seek.com.au job scraper implementation.
"""

import logging
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_scraper import BaseScraper
from ..utils import Utils

logger = logging.getLogger(__name__)

class SeekScraper(BaseScraper):
    """Scraper for Seek.com.au job listings."""
    
    def __init__(self, config_manager, db_manager):
        """Initialize Seek scraper."""
        super().__init__(config_manager, db_manager)
        self.domain = "www.seek.com.au"
    
    def scrape(self, search_terms, location, num_pages=None):
        """
        Scrape job listings from Seek.com.au.
        
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
        
        logger.info(f"Scraping Seek.com.au for {search_terms} in {location}...")
        
        # Get selectors from configuration
        job_container_selector = self.config.get('SELECTORS', 'seek_job_container', '_1yhfl9r')
        title_selector = self.config.get('SELECTORS', 'seek_title', 'h3')
        company_selector = self.config.get('SELECTORS', 'seek_company', '[data-automation="jobCompany"]')
        location_selector = self.config.get('SELECTORS', 'seek_location', '[data-automation="jobLocation"]')
        
        jobs_before = len(self.job_listings)
        
        for search_term in search_terms:
            for page in range(1, num_pages + 1):
                url = f"https://{self.domain}/{search_term.replace(' ', '-')}-jobs/in-{location.replace(' ', '-')}?page={page}"
                
                # Add random delay to avoid getting blocked
                self.add_random_delay()
                
                try:
                    response = requests.get(url, headers={'User-Agent': self.user_agent})
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        job_elements = soup.find_all('article', class_=job_container_selector)
                        
                        if not job_elements:
                            logger.warning(f"No job elements found on page {page} for {search_term}. Selector might need updating.")
                            continue
                        
                        for job in job_elements:
                            try:
                                title_element = job.find(title_selector)
                                title = title_element.text.strip() if title_element else "No title"
                                
                                company_element = job.find('span', {'data-automation': company_selector.strip('[]').split('=')[1].strip('"')})
                                company = company_element.text.strip() if company_element else "No company"
                                
                                location_element = job.find('span', {'data-automation': location_selector.strip('[]').split('=')[1].strip('"')})
                                location = location_element.text.strip() if location_element else "No location"
                                
                                link_element = job.find('a', href=True)
                                link = "https://www.seek.com.au" + link_element['href'] if link_element else ""
                                
                                # Create job data dictionary
                                job_data = {
                                    'title': title,
                                    'company': company,
                                    'location': location,
                                    'link': link,
                                    'source': 'Seek'
                                }
                                
                                # Insert into database
                                job_id = self.db.insert_job(job_data)
                                if job_id:
                                    job_data['id'] = job_id
                                    self.job_listings.append(job_data)
                                
                            except Exception as e:
                                logger.error(f"Error parsing job: {e}", exc_info=True)
                    else:
                        logger.warning(f"Failed to fetch page {page} for {search_term}: {response.status_code}")
                
                except Exception as e:
                    logger.error(f"Error scraping page {page} for {search_term}: {e}", exc_info=True)
        
        seek_jobs_count = len(self.job_listings) - jobs_before
        logger.info(f"Found {seek_jobs_count} job listings on Seek")
        return self.job_listings
    
    def get_job_details(self, job, driver=None):
        """
        Get detailed job description from Seek.com.au.
        
        Args:
            job (dict): Job data
            driver (WebDriver): Optional existing WebDriver instance
            
        Returns:
            str: Job description
        """
        if job['source'] != 'Seek':
            logger.warning(f"Cannot get details for non-Seek job: {job['title']}")
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
            
            # Get description selectors as list (might be comma-separated)
            description_selectors = self.config.get('SELECTORS', 'seek_description', 'FYwKg,yvsb870').split(',')
            
            # Try each selector
            description = "Could not extract job description"
            for selector in description_selectors:
                try:
                    # Wait for element to be present
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, selector.strip()))
                    )
                    description_element = driver.find_element(By.CLASS_NAME, selector.strip())
                    description = description_element.text.strip()
                    if description:
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            return description
            
        except Exception as e:
            logger.error(f"Error getting job details: {e}", exc_info=True)
            return None
        
        finally:
            if close_driver and driver:
                driver.quit() 