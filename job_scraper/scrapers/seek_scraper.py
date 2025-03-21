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
from typing import List, Dict, Any, Optional

from job_scraper.scrapers.base_scraper import BaseScraper
from job_scraper.utils.utils import Utils

logger = logging.getLogger(__name__)

class SeekScraper(BaseScraper):
    """Scraper for Seek.com.au job listings."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """Initialize Seek scraper."""
        super().__init__(config, logger)
        self.domain = "www.seek.com.au"
        self.user_agent = config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    def get_search_urls(self, keywords: List[str], location: str, num_pages: int = 1) -> List[str]:
        """
        Generate search URLs for Seek.com.au.
        
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
                url = f"https://{self.domain}/{keyword.replace(' ', '-')}-jobs/in-{location.replace(' ', '-')}?page={page}"
                urls.append(url)
        
        self.logger.info(f"Generated {len(urls)} search URLs for Seek.com.au")
        return urls
        
    def extract_job_urls(self, search_url: str) -> List[str]:
        """
        Extract job URLs from a Seek.com.au search results page.
        
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
            
        try:
            self.logger.info(f"Extracting job URLs from {search_url}")
            
            # Add random delay to avoid getting blocked
            self.add_random_delay()
            
            # Requests approach might not work due to JavaScript, let's try with Selenium
            driver = self.get_driver()
            
            try:
                driver.get(search_url)
                self.logger.info("Loaded page with Selenium, waiting for content to load...")
                
                # Wait for the page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Try several possible selectors for job listings
                selectors_to_try = [
                    "article[data-card-type='JobCard']",
                    "article[data-automation='normalJob']",
                    "article._1wkzzau0.szuv5u.szuv5v._1wkzzau2._1wkzzav3"
                ]
                
                found_elements = False
                for selector in selectors_to_try:
                    self.logger.info(f"Trying selector: {selector}")
                    job_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if job_elements:
                        self.logger.info(f"Found {len(job_elements)} job elements using selector: {selector}")
                        found_elements = True
                        
                        for job in job_elements:
                            try:
                                # Try several approaches to find the link
                                link_element = None
                                
                                # Approach 1: Find direct link
                                try:
                                    link_element = job.find_element(By.TAG_NAME, "a")
                                except NoSuchElementException:
                                    pass
                                
                                # Approach 2: Find link in job title
                                if not link_element:
                                    try:
                                        link_element = job.find_element(By.CSS_SELECTOR, "[data-automation='jobTitle'] a")
                                    except NoSuchElementException:
                                        pass
                                
                                # Approach 3: Find any link with href
                                if not link_element:
                                    try:
                                        all_links = job.find_elements(By.TAG_NAME, "a")
                                        for link in all_links:
                                            if link.get_attribute("href"):
                                                link_element = link
                                                break
                                    except:
                                        pass
                                        
                                if link_element and link_element.get_attribute("href"):
                                    job_url = link_element.get_attribute("href")
                                    job_urls.append(job_url)
                                    self.logger.debug(f"Found job URL: {job_url}")
                            except Exception as e:
                                self.logger.error(f"Error getting job URL: {str(e)}")
                        
                        break  # Break after finding job elements with a selector
                
                if not found_elements:
                    self.logger.warning(f"No job elements found with any selector on {search_url}")
                    # Log the page source for debugging
                    self.logger.debug(f"Page source: {driver.page_source[:1000]}...")
            
            finally:
                driver.quit()
                
            self.logger.info(f"Found {len(job_urls)} job URLs on {search_url}")
        
        except Exception as e:
            self.logger.error(f"Error extracting job URLs from {search_url}: {str(e)}")
            
        return job_urls
            
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
            num_pages = self.config.get('max_pages', 3)
        
        # Check if scraping is allowed
        if not self.check_site_allowed(self.domain):
            self.logger.warning(f"Scraping not allowed for {self.domain} according to robots.txt")
            return self.job_listings
        
        self.logger.info(f"Scraping Seek.com.au for {search_terms} in {location}...")
        
        # Get selectors from configuration
        job_container_selector = self.config.get('seek_job_container', '_1yhfl9r')
        title_selector = self.config.get('seek_title', 'h3')
        company_selector = self.config.get('seek_company', '[data-automation="jobCompany"]')
        location_selector = self.config.get('seek_location', '[data-automation="jobLocation"]')
        
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
                            self.logger.warning(f"No job elements found on page {page} for {search_term}. Selector might need updating.")
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
                                
                                # Add job to results
                                self.job_listings.append(job_data)
                                
                            except Exception as e:
                                self.logger.error(f"Error parsing job: {e}", exc_info=True)
                    else:
                        self.logger.warning(f"Failed to fetch page {page} for {search_term}: {response.status_code}")
                
                except Exception as e:
                    self.logger.error(f"Error scraping page {page} for {search_term}: {e}", exc_info=True)
        
        seek_jobs_count = len(self.job_listings) - jobs_before
        self.logger.info(f"Found {seek_jobs_count} job listings on Seek")
        return self.job_listings
    
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific job from Seek.com.au.
        
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
                    title_element = driver.find_element(By.TAG_NAME, "h1")
                    title = title_element.text.strip()
                except NoSuchElementException:
                    self.logger.warning(f"Could not find job title for {job_url}")
                
                # Get company name
                try:
                    company_element = driver.find_element(By.CSS_SELECTOR, '[data-automation="jobCompany"]')
                    company = company_element.text.strip()
                except NoSuchElementException:
                    self.logger.warning(f"Could not find company name for {job_url}")
                
                # Get location
                try:
                    location_element = driver.find_element(By.CSS_SELECTOR, '[data-automation="jobLocation"]')
                    location = location_element.text.strip()
                except NoSuchElementException:
                    self.logger.warning(f"Could not find location for {job_url}")
                
                # Get description
                description_selectors = self.config.get('seek_description', 'FYwKg,yvsb870').split(',')
                for selector in description_selectors:
                    try:
                        description_element = driver.find_element(By.CLASS_NAME, selector.strip())
                        description = description_element.text.strip()
                        if description:
                            break
                    except NoSuchElementException:
                        continue
                
                # Create job details dictionary
                job_details = {
                    'title': title,
                    'company': company,
                    'location': location,
                    'description': description,
                    'link': job_url,
                    'source': 'Seek'
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
                'source': 'Seek',
                'error': str(e)
            } 