"""
Utility functions for the job scraper application.
"""

import hashlib
import os
import re
import urllib.robotparser
import logging
from cryptography.fernet import Fernet
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, List, Union, Optional
from datetime import datetime
from pathlib import Path

from .constants import Constants

logger = logging.getLogger(__name__)

class Utils:
    """Utility functions used throughout the application."""
    
    @staticmethod
    def generate_encryption_key():
        """Generate a key for encryption/decryption"""
        return Fernet.generate_key()
    
    @staticmethod
    def get_or_create_key(key_file="secret.key"):
        """Get existing key or create a new one"""
        if os.path.exists(key_file):
            with open(key_file, "rb") as file:
                key = file.read()
        else:
            key = Utils.generate_encryption_key()
            with open(key_file, "wb") as file:
                file.write(key)
        return key
    
    @staticmethod
    def encrypt_data(data, key):
        """Encrypt data using Fernet symmetric encryption"""
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data, key):
        """Decrypt data using Fernet symmetric encryption"""
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode()).decode()
    
    @staticmethod
    def hash_identifier(text):
        """Create a secure hash of an identifier"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanitize a string to be used as a filename"""
        return re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')
    
    @staticmethod
    def safe_get_element_text(driver, by, selector, default=""):
        """Safely get element text with fallback to default value"""
        try:
            element = driver.find_element(by, selector)
            return element.text.strip() if element else default
        except NoSuchElementException:
            return default
    
    @staticmethod
    def check_robots_txt(domain):
        """Check if scraping is allowed for a domain"""
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"https://{domain}/robots.txt")
        try:
            rp.read()
            return rp.can_fetch("*", f"https://{domain}/")
        except Exception as e:
            logger.warning(f"Could not check robots.txt for {domain}: {e}")
            return True  # Assume allowed if we can't check
    
    @staticmethod
    def setup_logging(log_file="job_scraper.log", level=logging.INFO):
        """Set up logging configuration"""
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        ) 

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email:
        return False
    pattern = Constants.PATTERNS["email"]
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return False
    pattern = Constants.PATTERNS["phone"]
    return bool(re.match(pattern, phone))

def validate_name(name: str) -> bool:
    """Validate name format."""
    if not name:
        return False
    pattern = Constants.PATTERNS["name"]
    return bool(re.match(pattern, name))

def validate_file_path(file_path: str, required_extensions: Optional[List[str]] = None) -> bool:
    """Validate file path and extension."""
    if not file_path:
        return False
        
    try:
        path = Path(file_path)
        if not path.exists():
            return False
            
        if required_extensions:
            return path.suffix.lower() in required_extensions
            
        return True
    except Exception:
        return False

def validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url:
        return False
    pattern = r'^https?://(?:[\w-]+\.)+[\w-]+(?:/[\w-./?%&=]*)?$'
    return bool(re.match(pattern, url))

def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_user_info(user_info: Dict) -> List[str]:
    """Validate user information."""
    errors = []
    
    if not validate_name(user_info.get('name', '')):
        errors.append("Invalid name format")
        
    if not validate_email(user_info.get('email', '')):
        errors.append("Invalid email format")
        
    if not validate_phone(user_info.get('phone', '')):
        errors.append("Invalid phone number format")
        
    if not user_info.get('location'):
        errors.append("Location is required")
        
    if not user_info.get('skills'):
        errors.append("At least one skill is required")
        
    return errors

def validate_job_data(job_data: Dict) -> List[str]:
    """Validate job data."""
    errors = []
    
    if not job_data.get('title'):
        errors.append("Job title is required")
        
    if not job_data.get('company'):
        errors.append("Company name is required")
        
    if not validate_url(job_data.get('url', '')):
        errors.append("Invalid job URL")
        
    if not job_data.get('description'):
        errors.append("Job description is required")
        
    if job_data.get('deadline') and not validate_date(job_data['deadline']):
        errors.append("Invalid deadline date format")
        
    return errors

def validate_resume_data(resume_data: Dict) -> List[str]:
    """Validate resume data."""
    errors = []
    
    if not resume_data.get('skills'):
        errors.append("At least one skill is required")
        
    if not resume_data.get('experience'):
        errors.append("At least one work experience is required")
        
    if not resume_data.get('education'):
        errors.append("At least one education entry is required")
        
    return errors

def sanitize_file_path(file_path: str) -> str:
    """Sanitize file path to prevent directory traversal."""
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(file_path)
        
        # Check if path is within allowed directories
        allowed_dirs = [
            Constants.APP_DIR,
            Constants.COVER_LETTER_DIR,
            Constants.APPLICATION_LOG_DIR
        ]
        
        for allowed_dir in allowed_dirs:
            if abs_path.startswith(allowed_dir):
                return abs_path
                
        raise ValidationError("File path is outside allowed directories")
        
    except Exception as e:
        raise ValidationError(f"Invalid file path: {str(e)}")

def validate_config(config: Dict) -> List[str]:
    """Validate application configuration."""
    errors = []
    
    # Validate user info
    if 'user_info' in config:
        errors.extend(validate_user_info(config['user_info']))
        
    # Validate job scraper settings
    if 'job_scraper' in config:
        scraper_config = config['job_scraper']
        if not scraper_config.get('keywords'):
            errors.append("At least one search keyword is required")
        if not scraper_config.get('location'):
            errors.append("Search location is required")
            
    # Validate resume settings
    if 'resume' in config:
        resume_config = config['resume']
        if resume_config.get('default_resume'):
            if not validate_file_path(resume_config['default_resume'], Constants.FILE_EXTENSIONS['RESUME']):
                errors.append("Invalid default resume file path")
                
    # Validate application settings
    if 'application' in config:
        app_config = config['application']
        if app_config.get('default_cover_letter_template'):
            if not validate_file_path(app_config['default_cover_letter_template'], Constants.FILE_EXTENSIONS['COVER_LETTER']):
                errors.append("Invalid cover letter template file path")
                
    return errors

def validate_api_key(api_key: str) -> bool:
    """Validate OpenAI API key format."""
    if not api_key:
        return False
    pattern = r'^sk-[a-zA-Z0-9]{32,}$'
    return bool(re.match(pattern, api_key))

def validate_match_percentage(percentage: Union[int, float]) -> bool:
    """Validate job match percentage."""
    try:
        percentage = float(percentage)
        return 0 <= percentage <= 100
    except (ValueError, TypeError):
        return False 