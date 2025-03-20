#!/usr/bin/env python3
"""
AI-powered cover letter generator module.
This module uses AI to tailor cover letters based on resume data and job descriptions.
"""

import os
import logging
import json
import requests
from typing import Dict, List, Any, Optional

class AILetterGenerator:
    """AI-powered cover letter generator that tailors content to match resume with job descriptions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI letter generator.
        
        Args:
            api_key: API key for the AI service. If None, will try to load from environment variable.
        """
        self.logger = logging.getLogger('job_scraper.ai_letter')
        
        # Try to get API key from environment if not provided
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            self.logger.warning("No API key provided. AI letter generation will be limited.")
            self.api_available = False
        else:
            self.api_available = True
        
        # Base URL for API calls
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def generate_cover_letter(self, resume_data: Dict[str, Any], 
                              job_description: str, 
                              template: str) -> str:
        """Generate a tailored cover letter based on resume and job description.
        
        Args:
            resume_data: Parsed resume data (skills, experience, education)
            job_description: Full job description
            template: Base cover letter template with placeholders
            
        Returns:
            Completed cover letter text
        """
        if not self.api_available:
            return self._fallback_generation(resume_data, job_description, template)
        
        try:
            # Extract key elements from resume
            skills = resume_data.get('skills', [])
            experience = resume_data.get('work_experience', [])
            education = resume_data.get('education', [])
            
            # Create prompt for the AI
            prompt = self._create_prompt(skills, experience, education, job_description)
            
            # Call AI API
            response = self._call_ai_api(prompt)
            
            # Extract generated content
            if response and 'choices' in response:
                ai_content = response['choices'][0]['message']['content']
                
                # Insert AI-generated content into the template
                return self._apply_to_template(template, ai_content, resume_data, job_description)
            else:
                self.logger.error("Failed to get valid response from AI service")
                return self._fallback_generation(resume_data, job_description, template)
                
        except Exception as e:
            self.logger.error(f"Error generating AI cover letter: {str(e)}")
            return self._fallback_generation(resume_data, job_description, template)
    
    def _create_prompt(self, skills: List[str], experience: List[str], 
                       education: List[str], job_description: str) -> str:
        """Create a prompt for the AI model.
        
        Args:
            skills: List of skills from resume
            experience: List of work experience entries
            education: List of education entries
            job_description: Full job description
            
        Returns:
            Formatted prompt for AI
        """
        prompt = f"""
        You are an expert cover letter writer. I need a highly tailored and compelling cover letter 
        paragraph that connects my background to a specific job.

        MY SKILLS:
        {', '.join(skills)}

        MY EXPERIENCE:
        {'. '.join(experience)}

        MY EDUCATION:
        {'. '.join(education)}

        JOB DESCRIPTION:
        {job_description}

        Write a personalized, professional paragraph (200-250 words) for the middle section of my 
        cover letter that:
        1. Highlights 3-4 of my most relevant skills and experiences for this specific job
        2. Makes clear connections between my background and the job requirements
        3. Demonstrates my understanding of the role and company needs
        4. Uses professional language with confident but not arrogant tone
        5. Focuses on how I can provide value to the company

        Do not include salutations, closings, or mention specific company/job title as those will be 
        handled separately.
        """
        return prompt
    
    def _call_ai_api(self, prompt: str) -> Dict[str, Any]:
        """Call the AI API to generate cover letter content.
        
        Args:
            prompt: The prepared prompt for the AI
            
        Returns:
            JSON response from the API
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a professional cover letter writer."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {}
        except Exception as e:
            self.logger.error(f"Error calling AI API: {str(e)}")
            return {}
    
    def _apply_to_template(self, template: str, ai_content: str, 
                          resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
        """Apply AI-generated content and standard replacements to the template.
        
        Args:
            template: Cover letter template with placeholders
            ai_content: AI-generated paragraph
            resume_data: Resume data for standard placeholders
            job_data: Job data for standard placeholders
            
        Returns:
            Completed cover letter
        """
        # Replace standard placeholders
        letter = template.replace('[YOUR_NAME]', resume_data.get('name', 'YOUR NAME'))
        letter = letter.replace('[YOUR_EMAIL]', resume_data.get('email', 'YOUR EMAIL'))
        letter = letter.replace('[YOUR_PHONE]', resume_data.get('phone', 'YOUR PHONE'))
        
        letter = letter.replace('[COMPANY_NAME]', job_data.get('company', 'the Company'))
        letter = letter.replace('[JOB_TITLE]', job_data.get('title', 'the position'))
        letter = letter.replace('[JOB_ID]', job_data.get('id', ''))
        
        # Replace the content placeholder with AI-generated content
        letter = letter.replace('[BODY_CONTENT]', ai_content)
        
        current_date = resume_data.get('current_date', '')
        letter = letter.replace('[CURRENT_DATE]', current_date)
        
        return letter
    
    def _fallback_generation(self, resume_data: Dict[str, Any], 
                            job_description: str, template: str) -> str:
        """Generate a basic cover letter when AI is not available.
        
        Args:
            resume_data: Resume data for standard placeholders
            job_description: Job description
            template: Cover letter template
            
        Returns:
            Basic cover letter with standard replacements
        """
        self.logger.info("Using fallback cover letter generation method")
        
        # Extract job info
        job_title = resume_data.get('job_title', 'the position')
        company_name = resume_data.get('company_name', 'your company')
        
        # Create basic custom paragraph
        skills_list = ', '.join(resume_data.get('skills', [])[:5])
        
        custom_paragraph = f"""
        I am excited to apply for the {job_title} position at {company_name}. 
        Based on my review of the job description, I believe my skills in {skills_list} 
        make me a strong candidate for this role. My previous experience has prepared me 
        to contribute effectively to your team from day one. I am particularly interested 
        in this position because it aligns well with my career goals and skillset.
        """
        
        # Apply to template
        letter = template.replace('[BODY_CONTENT]', custom_paragraph)
        
        # Replace other standard placeholders
        letter = letter.replace('[YOUR_NAME]', resume_data.get('name', 'YOUR NAME'))
        letter = letter.replace('[YOUR_EMAIL]', resume_data.get('email', 'YOUR EMAIL'))
        letter = letter.replace('[YOUR_PHONE]', resume_data.get('phone', 'YOUR PHONE'))
        
        letter = letter.replace('[COMPANY_NAME]', resume_data.get('company_name', 'the Company'))
        letter = letter.replace('[JOB_TITLE]', resume_data.get('job_title', 'the position'))
        
        current_date = resume_data.get('current_date', '')
        letter = letter.replace('[CURRENT_DATE]', current_date)
        
        return letter 