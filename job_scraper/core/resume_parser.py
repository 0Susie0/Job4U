"""
Resume parser module for extracting information from resumes.
"""

import logging
import subprocess
import sys
import docx2txt
from PyPDF2 import PdfReader
import spacy

from .constants import Constants

logger = logging.getLogger(__name__)

class ResumeParser:
    """
    Class for parsing resume files and extracting relevant information.
    """
    
    def __init__(self):
        """
        Initialize the resume parser with NLP models.
        """
        try:
            self.nlp = spacy.load("en_core_web_md")
            logger.debug("Loaded spaCy model")
        except OSError:
            logger.info("Downloading spaCy model...")
            try:
                subprocess.call([sys.executable, "-m", "spacy", "download", "en_core_web_md"])
                self.nlp = spacy.load("en_core_web_md")
                logger.info("spaCy model downloaded and loaded")
            except Exception as e:
                logger.error(f"Error downloading spaCy model: {e}")
                raise
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text
        """
        logger.debug(f"Extracting text from PDF: {pdf_path}")
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def extract_text_from_docx(self, docx_path):
        """
        Extract text from DOCX file.
        
        Args:
            docx_path (str): Path to the DOCX file
            
        Returns:
            str: Extracted text
        """
        logger.debug(f"Extracting text from DOCX: {docx_path}")
        try:
            text = docx2txt.process(docx_path)
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise
    
    def extract_text(self, file_path):
        """
        Extract text from resume file based on file extension.
        
        Args:
            file_path (str): Path to the resume file
            
        Returns:
            str: Extracted text
        """
        if file_path.endswith('.pdf'):
            return self.extract_text_from_pdf(file_path)
        elif file_path.endswith('.docx'):
            return self.extract_text_from_docx(file_path)
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            raise ValueError("Unsupported file format. Please provide a PDF, DOCX, or TXT file.")
    
    def extract_skills(self, text):
        """
        Extract skills from resume text.
        
        Args:
            text (str): Resume text
            
        Returns:
            list: List of skills
        """
        logger.debug("Extracting skills from resume text")
        # Use the list of skills from Constants
        it_skills = Constants.IT_SKILLS
        
        # Extract skills from text
        skills = []
        text_lower = text.lower()
        doc = self.nlp(text_lower)
        
        for skill in it_skills:
            if skill in text_lower:
                skills.append(skill)
        
        return skills
    
    def extract_work_experience(self, text):
        """
        Extract work experience from resume text.
        
        Args:
            text (str): Resume text
            
        Returns:
            list: List of work experience entries
        """
        logger.debug("Extracting work experience from resume text")
        # Use the section headers from Constants
        experience_headers = Constants.EXPERIENCE_HEADERS
        
        # Find the experience section
        experience_section = ""
        lines = text.split('\n')
        in_experience_section = False
        next_section_start = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line is an experience header
            if not in_experience_section and any(header in line_lower for header in experience_headers):
                in_experience_section = True
                continue
            
            # If we're already in the experience section, check if we've reached another section
            if in_experience_section:
                # Check if we've reached another section header (likely to be capitalized and end with colon)
                if line_lower and line_lower[0].isupper() and (line_lower.endswith(':') or line_lower.endswith('.')):
                    # Check if it's a new section and not a job title
                    if not any(exp_header in line_lower for exp_header in experience_headers):
                        next_section_start = i
                        break
                
                experience_section += line + '\n'
        
        # Extract company names and job titles
        experiences = []
        
        # Split the experience section into paragraphs
        paragraphs = [p.strip() for p in experience_section.split('\n\n') if p.strip()]
        
        for paragraph in paragraphs:
            if paragraph:
                experiences.append(paragraph)
        
        return experiences
    
    def extract_education(self, text):
        """
        Extract education from resume text.
        
        Args:
            text (str): Resume text
            
        Returns:
            list: List of education entries
        """
        logger.debug("Extracting education from resume text")
        # Use the section headers from Constants
        education_headers = Constants.EDUCATION_HEADERS
        
        # Find the education section
        education_section = ""
        lines = text.split('\n')
        in_education_section = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line is an education header
            if not in_education_section and any(header in line_lower for header in education_headers):
                in_education_section = True
                continue
            
            # If we're already in the education section, check if we've reached another section
            if in_education_section:
                # Check if we've reached another section header (likely to be capitalized and end with colon)
                if line_lower and line_lower[0].isupper() and (line_lower.endswith(':') or line_lower.endswith('.')):
                    # Check if it's a new section and not a degree or institution
                    if not any(edu_header in line_lower for edu_header in education_headers):
                        break
                
                education_section += line + '\n'
        
        # Extract education entries
        education = []
        
        # Split the education section into paragraphs
        paragraphs = [p.strip() for p in education_section.split('\n\n') if p.strip()]
        
        for paragraph in paragraphs:
            if paragraph:
                education.append(paragraph)
        
        return education
    
    def parse_resume(self, file_path):
        """
        Parse resume file and extract information.
        
        Args:
            file_path (str): Path to the resume file
            
        Returns:
            dict: Parsed resume information
        """
        logger.info(f"Parsing resume: {file_path}")
        try:
            # Extract text from file
            text = self.extract_text(file_path)
            
            # Extract information from text
            skills = self.extract_skills(text)
            work_experience = self.extract_work_experience(text)
            education = self.extract_education(text)
            
            # Create resume data dictionary
            resume_data = {
                'skills': skills,
                'work_experience': work_experience,
                'education': education,
                'full_text': text
            }
            
            logger.info(f"Resume parsed successfully with {len(skills)} skills, {len(work_experience)} work experiences, and {len(education)} education entries.")
            return resume_data
        
        except Exception as e:
            logger.error(f"Error parsing resume: {e}", exc_info=True)
            return None 