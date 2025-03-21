#!/usr/bin/env python3
"""
AI-powered cover letter generator module.
This module uses AI to tailor cover letters based on resume data and job descriptions.
"""

import os
import logging
import json
import hashlib
import time
from functools import lru_cache
from typing import Dict, List, Any, Optional

import openai
from openai import OpenAI

from job_scraper.config.constants import Constants
from job_scraper.utils.utils import validate_api_key

class AILetterGenerator:
    """AI-powered cover letter generator that tailors content to match resume with job descriptions."""
    
    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the AI letter generator.
        
        Args:
            api_key: OpenAI API key
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.api_key = api_key
        self.client = self._initialize_client()
        self.cache_dir = os.path.join(Constants.APP_DIR, 'cache')
        self.cache_expiry = 60 * 60 * 24 * 7  # 7 days in seconds
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.logger.debug(f"Cache directory ensured: {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"Error creating cache directory: {str(e)}")
        
    def _initialize_client(self) -> Optional[OpenAI]:
        """Initialize the OpenAI client."""
        if not self.api_key:
            self.logger.warning("No API key provided, AI letter generation will be disabled")
            return None
            
        if not validate_api_key(self.api_key):
            self.logger.warning("Invalid API key format, AI letter generation will be disabled")
            return None
            
        try:
            return OpenAI(api_key=self.api_key)
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {str(e)}")
            return None
            
    def _compute_cache_key(self, data: Dict[str, Any]) -> str:
        """
        Compute a cache key for the given data.
        
        Args:
            data: Data to use for cache key generation
            
        Returns:
            String hash to use as cache key
        """
        # Create a stable string representation of the data
        job_key = f"{data.get('job_title', '')}-{data.get('company_name', '')}"
        
        # Only include the most relevant parts for caching
        cache_data = {
            'job_title': data.get('job_title', ''),
            'company_name': data.get('company_name', ''),
            'description': data.get('description', '')[:500],  # Truncate for stability
            'skills': data.get('skills', '')
        }
        
        # Create a hash of the data
        data_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
        
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        Get cached cover letter if available and not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached cover letter or None
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            if time.time() - cache_data.get('timestamp', 0) > self.cache_expiry:
                self.logger.debug(f"Cache expired for key {cache_key}")
                return None
                
            self.logger.debug(f"Cache hit for key {cache_key}")
            return cache_data.get('content')
            
        except Exception as e:
            self.logger.error(f"Error reading cache: {str(e)}")
            return None
            
    def _save_to_cache(self, cache_key: str, content: str):
        """
        Save cover letter to cache.
        
        Args:
            cache_key: Cache key
            content: Cover letter content
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            cache_data = {
                'content': content,
                'timestamp': time.time()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
                
            self.logger.debug(f"Cached content for key {cache_key}")
            
        except Exception as e:
            self.logger.error(f"Error writing to cache: {str(e)}")
            
    def generate_cover_letter(self, data: Dict[str, Any]) -> str:
        """
        Generate a personalized cover letter using AI.
        
        Args:
            data: Data to use for cover letter generation
            
        Returns:
            Generated cover letter
        """
        if not self.client:
            self.logger.warning("AI client not initialized, generating fallback cover letter")
            return self._generate_fallback_cover_letter(data)
            
        # Check cache first
        cache_key = self._compute_cache_key(data)
        cached_content = self._get_from_cache(cache_key)
        
        if cached_content:
            return cached_content
            
        # Configure parameters based on AI settings
        try:
            prompt = self._prepare_prompt(data)
            
            # Make API request with exponential backoff
            for attempt in range(3):
                try:
                    response = self.client.chat.completions.create(
                        model=data.get('model', 'gpt-3.5-turbo'),
                        messages=[
                            {"role": "system", "content": "You are an expert cover letter writer who creates personalized, professional cover letters."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=data.get('temperature', 0.7),
                        max_tokens=data.get('max_tokens', 1000)
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # Cache the response
                    self._save_to_cache(cache_key, content)
                    
                    return content
                    
                except (openai.APIError, openai.RateLimitError) as e:
                    self.logger.warning(f"OpenAI API error (attempt {attempt+1}/3): {str(e)}")
                    if attempt < 2:
                        time.sleep((2 ** attempt) * 1.5)  # Exponential backoff
                    else:
                        return self._generate_fallback_cover_letter(data)
                        
                except Exception as e:
                    self.logger.error(f"Error generating cover letter: {str(e)}")
                    return self._generate_fallback_cover_letter(data)
                    
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return self._generate_fallback_cover_letter(data)
            
    def _prepare_prompt(self, data: Dict[str, Any]) -> str:
        """
        Prepare prompt for OpenAI API.
        
        Args:
            data: Data to include in prompt
            
        Returns:
            Formatted prompt
        """
        prompt_template = Constants.COVER_LETTER_PROMPT
        
        # Format prompt with job and resume data
        try:
            formatted_prompt = prompt_template.format(
                job_title=data.get('job_title', 'the position'),
                company_name=data.get('company_name', 'the company'),
                location=data.get('location', 'the location'),
                description=data.get('description', 'No description provided'),
                resume_data=self._format_resume_data(data.get('resume_data', {}))
            )
            
            return formatted_prompt
            
        except Exception as e:
            self.logger.error(f"Error formatting prompt: {str(e)}")
            
            # Return a simplified prompt as fallback
            return f"""
            Write a cover letter for a {data.get('job_title', 'job')} position at {data.get('company_name', 'a company')}.
            The applicant's skills include: {data.get('skills', 'various relevant skills')}.
            Make it professional, concise and specific to the role.
            """
            
    def _format_resume_data(self, resume_data: Dict[str, Any]) -> str:
        """
        Format resume data for inclusion in the prompt.
        
        Args:
            resume_data: Resume data
            
        Returns:
            Formatted resume data as string
        """
        if not resume_data:
            return "No resume data provided."
            
        formatted_data = "Resume Information:\n\n"
        
        # Add skills
        skills = resume_data.get('skills', [])
        if skills:
            formatted_data += "Skills: " + ", ".join(skills) + "\n\n"
            
        # Add experience
        experience = resume_data.get('experience', [])
        if experience:
            formatted_data += "Work Experience:\n"
            for exp in experience:
                company = exp.get('company', 'Unknown')
                title = exp.get('title', 'Unknown')
                period = exp.get('period', 'Unknown')
                description = exp.get('description', '')
                
                formatted_data += f"- {title} at {company} ({period})\n"
                if description:
                    formatted_data += f"  {description}\n"
            formatted_data += "\n"
            
        # Add education
        education = resume_data.get('education', [])
        if education:
            formatted_data += "Education:\n"
            for edu in education:
                institution = edu.get('institution', 'Unknown')
                degree = edu.get('degree', 'Unknown')
                year = edu.get('year', 'Unknown')
                
                formatted_data += f"- {degree} from {institution} ({year})\n"
            formatted_data += "\n"
            
        return formatted_data
        
    def _generate_fallback_cover_letter(self, data: Dict[str, Any]) -> str:
        """
        Generate a basic cover letter without AI.
        
        Args:
            data: Job and resume data
            
        Returns:
            Basic cover letter
        """
        self.logger.info("Generating fallback cover letter")
        
        job_title = data.get('job_title', 'the position')
        company_name = data.get('company_name', 'your company')
        skills = data.get('skills', 'relevant skills and experience')
        
        return f"""
Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company_name}. With my background in {skills}, I believe I would be a valuable addition to your team.

My experience has prepared me well for this role, and I am excited about the opportunity to bring my skills to {company_name}. I am particularly drawn to this position because it aligns well with my career goals and expertise.

I am confident that my skills and experience make me a strong candidate for this position. I would welcome the opportunity to discuss how I can contribute to your team.

Thank you for your consideration.

Sincerely,
[Your Name]
        """.strip() 