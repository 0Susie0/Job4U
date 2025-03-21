#!/usr/bin/env python3
"""
Configuration manager for the job scraper application.
Handles loading, saving, and managing user settings.
"""

import os
import json
import logging
from pathlib import Path

from .constants import Constants

class ConfigManager:
    """Class to manage configuration settings for the application."""

    def __init__(self, config_file=None):
        """Initialize the configuration manager.
        
        Args:
            config_file (str, optional): Path to the configuration file.
                                       If not provided, uses the default path.
        """
        self.logger = logging.getLogger(__name__)
        
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
        """Get job scraper settings.
        
        Returns:
            dict: Job scraper settings
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