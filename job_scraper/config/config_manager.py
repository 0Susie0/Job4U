#!/usr/bin/env python3
"""
Configuration manager for the Job4U application.
Handles loading, saving, and managing user settings.
"""

import os
import json
import logging
from pathlib import Path

from .constants import Constants

class ConfigManager:
    """Class to manage configuration settings for the application."""

    def __init__(self, logger=None, config_file=None):
        """Initialize the configuration manager.
        
        Args:
            logger (logging.Logger, optional): Logger instance
            config_file (str, optional): Path to the configuration file.
                                       If not provided, uses the default path.
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Use the specified config file or the default from Constants
        self.config_file = config_file or Constants.CONFIG_FILE
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Load existing config or create default
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create default if it doesn't exist.
        
        Returns:
            dict: The loaded configuration or default configuration
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.logger.info(f"Loaded configuration from {self.config_file}")
                    return config
            except Exception as e:
                self.logger.error(f"Error loading configuration: {str(e)}")
                self.logger.info("Using default configuration")
                return self._get_default_config()
        else:
            self.logger.info(f"Configuration file {self.config_file} not found, using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Get the default configuration.
        
        Returns:
            dict: The default configuration
        """
        return Constants.DEFAULT_CONFIG
    
    def save_config(self):
        """Save the current configuration to the config file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get_config(self, key, default=None):
        """Get a configuration value.
        
        Args:
            key (str): The configuration key to retrieve
            default: The default value to return if the key is not found
        
        Returns:
            The configuration value or the default value
        """
        # Split the key into parts for nested configs
        if '.' in key:
            parts = key.split('.')
            current = self.config
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return default
            return current
        
        return self.config.get(key, default)
    
    def set_config(self, key, value):
        """Set a configuration value.
        
        Args:
            key (str): The configuration key to set
            value: The value to set
        """
        # Handle nested keys
        if '.' in key:
            parts = key.split('.')
            current = self.config
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self.config[key] = value
    
    def reset_config(self):
        """Reset the configuration to defaults."""
        self.config = self._get_default_config()
        self.save_config()
        self.logger.info("Configuration reset to defaults")
    
    def get_openai_api_key(self):
        """Get the OpenAI API key.
        
        Returns:
            str: The OpenAI API key or None if not set
        """
        return self.get_config('openai_api_key')
    
    def get_user_info(self):
        """Get the user's personal information.
        
        Returns:
            dict: A dictionary containing the user's personal information
        """
        return {
            'name': self.get_config('name', ''),
            'email': self.get_config('email', ''),
            'phone': self.get_config('phone', ''),
            'skills': self.get_config('skills', [])
        }
    
    def get_resume_settings(self):
        """Get resume-related settings.
        
        Returns:
            dict: Resume settings
        """
        return {
            'default_resume_path': self.get_config('default_resume_path', ''),
            'default_cover_letter_template': self.get_config('default_cover_letter_template', '')
        }
    
    def get_scraper_settings(self):
        """Get job search settings.
        
        Returns:
            dict: Job search settings
        """
        return {
            'search_terms': self.get_config('search_terms', []),
            'location': self.get_config('location', ''),
            'job_sites': self.get_config('job_sites', ['seek', 'indeed', 'linkedin']),
            'pages_per_site': self.get_config('pages_per_site', 2),
            'detailed_job_count': self.get_config('detailed_job_count', 10)
        }
    
    def get_application_settings(self):
        """Get job application settings.
        
        Returns:
            dict: Job application settings
        """
        return {
            'use_ai_cover_letter': self.get_config('use_ai_cover_letter', True),
            'auto_apply': self.get_config('auto_apply', False)
        }
    
    def get_ai_settings(self):
        """Get AI-related settings.
        
        Returns:
            dict: AI settings
        """
        return {
            'openai_api_key': self.get_config('openai_api_key', ''),
            'use_ai_cover_letter': self.get_config('use_ai_cover_letter', True)
        }
    
    def get_selenium_settings(self):
        """Get Selenium-related settings.
        
        Returns:
            dict: Selenium settings
        """
        return {
            'headless': self.get_config('headless', True),
            'timeout': self.get_config('timeout', 30),
            'browser': self.get_config('browser', 'chrome'),
            'chrome_driver_path': self.get_config('chrome_driver_path', '')
        }
    
    def set_user_info(self, user_info):
        """Set user information.
        
        Args:
            user_info (dict): User information dictionary
        """
        for key, value in user_info.items():
            self.set_config(key, value)
        self.save_config()
    
    def set_resume_settings(self, resume_settings):
        """Set resume-related settings.
        
        Args:
            resume_settings (dict): Resume settings dictionary
        """
        for key, value in resume_settings.items():
            self.set_config(key, value)
        self.save_config()
        
    def set_scraper_settings(self, scraper_settings):
        """Set job search settings.
        
        Args:
            scraper_settings (dict): Job search settings dictionary
        """
        for key, value in scraper_settings.items():
            self.set_config(key, value)
        self.save_config()
        
    def set_application_settings(self, application_settings):
        """Set job application settings.
        
        Args:
            application_settings (dict): Application settings dictionary
        """
        for key, value in application_settings.items():
            self.set_config(key, value)
        self.save_config()
        
    def set_ai_settings(self, ai_settings):
        """Set AI-related settings.
        
        Args:
            ai_settings (dict): AI settings dictionary
        """
        for key, value in ai_settings.items():
            self.set_config(key, value)
        self.save_config()
        
    def set_selenium_settings(self, selenium_settings):
        """Set Selenium-related settings.
        
        Args:
            selenium_settings (dict): Selenium settings dictionary
        """
        for key, value in selenium_settings.items():
            self.set_config(key, value)
        self.save_config() 