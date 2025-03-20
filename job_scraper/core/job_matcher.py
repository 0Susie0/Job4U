import logging
import re
import math
import threading
import multiprocessing
from typing import List, Dict, Any, Set, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..config.constants import Constants

class JobMatcher:
    """Match jobs with resume data using optimized text comparison."""
    
    def __init__(self, resume_settings: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the job matcher.
        
        Args:
            resume_settings: Resume settings
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.resume_settings = resume_settings
        self.num_threads = min(8, (multiprocessing.cpu_count() or 4) - 1)
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=10000,
            sublinear_tf=True
        )
        self.skill_pattern = re.compile(r'\b(' + '|'.join(re.escape(s.lower()) for s in self.get_common_skills()) + r')\b')
        
    def get_common_skills(self) -> List[str]:
        """
        Get a list of common tech skills to look for.
        
        Returns:
            List of skill keywords
        """
        # This could be expanded or loaded from a file
        return [
            "python", "java", "javascript", "html", "css", "sql", "nosql", "react", 
            "angular", "vue", "node.js", "express", "django", "flask", "spring", 
            "hibernate", "docker", "kubernetes", "aws", "azure", "gcp", "devops", 
            "ci/cd", "git", "agile", "scrum", "jenkins", "terraform", "ansible", 
            "machine learning", "artificial intelligence", "data science", "data analysis",
            "nlp", "computer vision", "blockchain", "ios", "android", "swift", "kotlin",
            "react native", "flutter", "c#", "c++", "ruby", "rails", "php", "laravel",
            "jira", "confluence", "tableau", "power bi", "excel", "powerpoint", "word",
            "cybersecurity", "network security", "penetration testing", "cryptography",
            "linux", "unix", "windows", "macos", "bash", "shell scripting", "powershell",
            "rest api", "graphql", "mongodb", "mysql", "postgresql", "oracle", "redis",
            "elasticsearch", "kafka", "rabbitmq", "microservices", "serverless", "sass",
            "less", "webpack", "babel", "typescript", "bootstrap", "jquery", "figma",
            "sketch", "photoshop", "illustrator", "ui/ux", "responsive design", "seo"
        ]
        
    def extract_skills(self, text: str) -> Set[str]:
        """
        Extract skills from text using regex pattern matching.
        
        Args:
            text: Text to extract skills from
            
        Returns:
            Set of skills found in the text
        """
        if not text:
            return set()
            
        # Convert to lowercase for case-insensitive matching
        text = text.lower()
        
        # Find all matches of skills
        matches = self.skill_pattern.findall(text)
        return set(matches)
        
    def match_jobs(self, resume_data: Dict[str, Any], jobs: List[Dict[str, Any]], 
                  top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Match jobs with resume data.
        
        Args:
            resume_data: Resume data
            jobs: List of job dictionaries
            top_n: Number of top matches to return
            
        Returns:
            List of job dictionaries with match scores
        """
        if not jobs:
            self.logger.warning("No jobs to match")
            return []
            
        if not resume_data:
            self.logger.warning("No resume data provided")
            return jobs[:top_n] if top_n > 0 else jobs
            
        self.logger.info(f"Matching {len(jobs)} jobs with resume")
        
        # Extract resume skills
        resume_skills = set(s.lower() for s in resume_data.get('skills', []))
        
        # Create resume text for TF-IDF
        resume_text = self._prepare_resume_text(resume_data)
        
        # Batch jobs for parallel processing
        batch_size = max(1, len(jobs) // self.num_threads)
        batches = [jobs[i:i + batch_size] for i in range(0, len(jobs), batch_size)]
        
        # Process batches in parallel
        matched_jobs = []
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            future_to_batch = {
                executor.submit(self._process_batch, resume_text, resume_skills, batch): i 
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    matched_jobs.extend(batch_results)
                except Exception as e:
                    self.logger.error(f"Error processing batch {batch_idx}: {str(e)}")
                    
        # Sort by match percentage descending
        matched_jobs.sort(key=lambda x: x.get('match_percentage', 0), reverse=True)
        
        # Return top N
        result = matched_jobs[:top_n] if top_n > 0 else matched_jobs
        self.logger.info(f"Returned {len(result)} matched jobs")
        return result
        
    def _prepare_resume_text(self, resume_data: Dict[str, Any]) -> str:
        """
        Prepare resume text for TF-IDF vectorization.
        
        Args:
            resume_data: Resume data
            
        Returns:
            Processed resume text
        """
        parts = []
        
        # Add skills (with repetition for emphasis)
        skills = resume_data.get('skills', [])
        parts.extend(skills * 3)  # Repeat skills for higher importance
        
        # Add job titles and descriptions from experience
        for exp in resume_data.get('experience', []):
            if 'title' in exp:
                parts.append(exp['title'])
            if 'description' in exp:
                parts.append(exp['description'])
                
        # Add education information
        for edu in resume_data.get('education', []):
            if 'degree' in edu:
                parts.append(edu['degree'])
            if 'field' in edu:
                parts.append(edu['field'])
                
        return ' '.join(parts)
        
    def _process_batch(self, resume_text: str, resume_skills: Set[str], 
                    jobs_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of jobs for matching.
        
        Args:
            resume_text: Prepared resume text
            resume_skills: Set of resume skills
            jobs_batch: Batch of jobs to process
            
        Returns:
            List of processed jobs with match scores
        """
        result = []
        
        # Prepare job descriptions for vectorization
        job_descriptions = [job.get('description', '') for job in jobs_batch]
        job_descriptions.append(resume_text)  # Add resume text as last document
        
        # TF-IDF vectorization
        tfidf_matrix = self.vectorizer.fit_transform(job_descriptions)
        
        # Calculate similarity between resume and each job
        resume_vector = tfidf_matrix[-1]  # Last vector is the resume
        job_vectors = tfidf_matrix[:-1]    # All except the last are jobs
        
        # Calculate cosine similarities
        similarities = cosine_similarity(job_vectors, resume_vector)
        
        # Process each job
        for i, job in enumerate(jobs_batch):
            sim_score = similarities[i][0]
            job_copy = job.copy()
            
            # Extract skills from job description
            job_skills = self.extract_skills(job.get('description', ''))
            
            # Calculate skill match percentage
            missing_skills = job_skills - resume_skills
            matching_skills = job_skills & resume_skills
            
            skill_match_pct = 0
            if job_skills:
                skill_match_pct = len(matching_skills) / len(job_skills) * 100
                
            # Calculate match percentage - weighted combination of skill match and text similarity
            text_sim_pct = sim_score * 100
            match_percentage = (skill_match_pct * 0.7) + (text_sim_pct * 0.3)
            
            # Add match info to job
            job_copy['match_percentage'] = round(match_percentage, 2)
            job_copy['matching_skills'] = list(matching_skills)
            job_copy['missing_skills'] = list(missing_skills)
            job_copy['text_similarity'] = round(text_sim_pct, 2)
            job_copy['skill_match'] = round(skill_match_pct, 2)
            
            result.append(job_copy)
            
        return result
        
    def check_job_match_threshold(self, job_data: Dict[str, Any], threshold: float = 70.0) -> bool:
        """
        Check if a job meets the match threshold.
        
        Args:
            job_data: Job data
            threshold: Match percentage threshold
            
        Returns:
            True if job meets or exceeds threshold
        """
        match_percentage = job_data.get('match_percentage', 0)
        return match_percentage >= threshold 