"""
Job Scraper and Applicator package.
"""

__version__ = "1.0.0"
__author__ = "Job Scraper Team"

from .config.constants import Constants
from .utils.utils import Utils
from .data.database import DatabaseManager
from .config.config_manager import ConfigManager
from .scrapers.base_scraper import BaseScraper
from .scrapers.seek_scraper import SeekScraper
from .scrapers.indeed_scraper import IndeedScraper
from .scrapers.linkedin_scraper import LinkedInScraper
from .core.job_matcher import JobMatcher
from .core.resume_parser import ResumeParser
from .services.application_manager import ApplicationManager
from .app import JobScraperApp 