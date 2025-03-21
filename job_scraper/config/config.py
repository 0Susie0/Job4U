"""
Configuration management for the Job4U application.
"""

import os
import configparser
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manage application configuration settings."""
    
    def __init__(self, config_file="config.ini"):
        """Initialize configuration manager with specified config file."""
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # Create default config if doesn't exist
        if not os.path.exists(config_file):
            logger.info(f"Creating default configuration file: {config_file}")
            self.create_default_config()
        
        self.config.read(config_file)
    
    def create_default_config(self):
        """Create default configuration file."""
        # Scraping settings
        self.config['SCRAPING'] = {
            'min_delay': '2',
            'max_delay': '5',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'max_pages': '3',
            'respect_robots_txt': 'true'
        }
        
        # Selenium settings
        self.config['SELENIUM'] = {
            'headless': 'true',
            'disable_gpu': 'true',
            'no_sandbox': 'true',
            'disable_dev_shm_usage': 'true',
            'timeout': '10'
        }
        
        # Selectors for different job sites
        self.config['SELECTORS'] = {
            'seek_job_container': '_1yhfl9r',
            'seek_title': 'h3',
            'seek_company': '[data-automation="jobCompany"]',
            'seek_location': '[data-automation="jobLocation"]',
            'seek_description': 'FYwKg,yvsb870',
            
            'indeed_job_container': 'job_seen_beacon',
            'indeed_title': 'jcs-JobTitle',
            'indeed_company': 'companyName',
            'indeed_location': 'companyLocation',
            'indeed_description': 'jobDescriptionText',
            
            'linkedin_job_container': 'base-search-card',
            'linkedin_title': 'base-search-card__title',
            'linkedin_company': 'base-search-card__subtitle',
            'linkedin_location': 'job-search-card__location',
            'linkedin_description': 'show-more-less-html__markup'
        }
        
        # Database settings
        self.config['DATABASE'] = {
            'db_name': 'job_scraper.db',
            'table_prefix': 'js_'
        }
        
        # Write the configuration file
        with open(self.config_file, 'w') as file:
            self.config.write(file)
    
    def get(self, section, option, fallback=None):
        """Get a configuration value as string."""
        try:
            return self.config.get(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.warning(f"Configuration error: {e}")
            return fallback
    
    def get_int(self, section, option, fallback=None):
        """Get a configuration value as integer."""
        try:
            return self.config.getint(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
            logger.warning(f"Configuration error: {e}")
            return fallback
    
    def get_float(self, section, option, fallback=None):
        """Get a configuration value as float."""
        try:
            return self.config.getfloat(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
            logger.warning(f"Configuration error: {e}")
            return fallback
    
    def get_boolean(self, section, option, fallback=None):
        """Get a configuration value as boolean."""
        try:
            return self.config.getboolean(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
            logger.warning(f"Configuration error: {e}")
            return fallback
    
    def get_list(self, section, option, fallback=None, delimiter=','):
        """Get a configuration value as list."""
        try:
            value = self.config.get(section, option, fallback=fallback)
            if value:
                return [item.strip() for item in value.split(delimiter)]
            return []
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.warning(f"Configuration error: {e}")
            return [] if fallback is None else fallback
    
    def set(self, section, option, value):
        """Set a configuration value."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))
    
    def save(self):
        """Save the configuration to file."""
        with open(self.config_file, 'w') as file:
            self.config.write(file) 