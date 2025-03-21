"""
Manager for job scraper implementations.
"""

import logging
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from job_scraper.scrapers.seek_scraper import SeekScraper
from job_scraper.scrapers.indeed_scraper import IndeedScraper
from job_scraper.scrapers.linkedin_scraper import LinkedInScraper

class ScraperManager:
    """Manages multiple job scraper implementations."""
    
    def __init__(self, settings: Dict[str, Any], logger: logging.Logger):
        """
        Initialize the scraper manager.
        
        Args:
            settings: Dictionary containing scraper settings
            logger: Logger instance
        """
        self.settings = settings
        self.logger = logger
        self.scrapers = []
        self._init_scrapers()
        
    def _init_scrapers(self):
        """Initialize supported scrapers based on configuration."""
        job_sites = self.settings.get('job_sites', ['seek', 'indeed', 'linkedin'])
        
        if 'seek' in job_sites:
            try:
                self.scrapers.append(SeekScraper(self.settings, self.logger))
                self.logger.info("Initialized Seek scraper")
            except Exception as e:
                self.logger.error(f"Failed to initialize Seek scraper: {str(e)}")
        
        if 'indeed' in job_sites:
            try:
                self.scrapers.append(IndeedScraper(self.settings, self.logger))
                self.logger.info("Initialized Indeed scraper")
            except Exception as e:
                self.logger.error(f"Failed to initialize Indeed scraper: {str(e)}")
        
        if 'linkedin' in job_sites:
            try:
                self.scrapers.append(LinkedInScraper(self.settings, self.logger))
                self.logger.info("Initialized LinkedIn scraper")
            except Exception as e:
                self.logger.error(f"Failed to initialize LinkedIn scraper: {str(e)}")
        
        self.logger.info(f"Initialized {len(self.scrapers)} job scrapers")
        
    def search_jobs(self, keywords: List[str], location: str) -> List[Dict[str, Any]]:
        """
        Search for jobs using all configured scrapers.
        
        Args:
            keywords: List of job keywords to search for
            location: Location to search in
            
        Returns:
            List of job dictionaries
        """
        results = []
        self.logger.info(f"Searching for jobs with keywords: {keywords}, location: {location}")
        
        if not self.scrapers:
            self.logger.warning("No job scrapers configured. Please check your settings.")
            return results
            
        # Convert keywords to string if it's a list
        if isinstance(keywords, list):
            keywords_str = " ".join(keywords)
        else:
            keywords_str = keywords
        
        # Use a ThreadPoolExecutor to run scrapers in parallel
        with ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
            # Create a future for each scraper
            future_to_scraper = {
                executor.submit(scraper.search_jobs, keywords_str, location): scraper 
                for scraper in self.scrapers
            }
            
            # Process results as they complete
            for future in as_completed(future_to_scraper):
                scraper = future_to_scraper[future]
                try:
                    # Get jobs found by this scraper
                    scraper_results = future.result()
                    if scraper_results:
                        self.logger.info(f"Found {len(scraper_results)} jobs from {scraper.__class__.__name__}")
                        results.extend(scraper_results)
                    else:
                        self.logger.info(f"No jobs found from {scraper.__class__.__name__}")
                except Exception as e:
                    self.logger.error(f"Error in {scraper.__class__.__name__}: {str(e)}")
        
        self.logger.info(f"Total jobs found: {len(results)}")
        return results 