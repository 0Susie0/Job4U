#!/usr/bin/env python3
"""
Dialog windows for the job scraper GUI.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QProgressBar, QGroupBox, QComboBox, QCheckBox,
    QSpinBox, QDialogButtonBox
)

from job_scraper.config.constants import Constants
from job_scraper.gui.workers import GenerateAICoverLetterWorker


class CoverLetterDialog(QDialog):
    """Dialog for generating and editing cover letters."""
    
    def __init__(self, app, parent=None, resume_data=None, job_data=None):
        """Initialize the dialog.
        
        Args:
            app: Application instance
            parent: Parent widget
            resume_data: Resume data dictionary
            job_data: Job data dictionary
        """
        super().__init__(parent)
        self.app = app
        self.resume_data = resume_data
        self.job_data = job_data
        self.logger = logging.getLogger(__name__)
        self.worker = None
        
        self._setup_ui()
        
        # Generate cover letter if resume and job data are provided
        if self.resume_data and self.job_data:
            # Check if the cover letter is already generated
            if 'cover_letter' in self.job_data and self.job_data['cover_letter']:
                self.cover_letter_edit.setPlainText(self.job_data['cover_letter'])
            else:
                self._setup_template_cover_letter()
        
    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Cover Letter Generator")
        self.setMinimumSize(700, 600)
        
        main_layout = QVBoxLayout()
        
        # Job and resume info
        info_layout = QGridLayout()
        
        # Company name
        info_layout.addWidget(QLabel("Company:"), 0, 0)
        self.company_label = QLabel(self.job_data.get('company', 'Unknown'))
        self.company_label.setFont(QFont('Arial', 10, QFont.Bold))
        info_layout.addWidget(self.company_label, 0, 1)
        
        # Job title
        info_layout.addWidget(QLabel("Job Title:"), 0, 2)
        self.title_label = QLabel(self.job_data.get('title', 'Unknown'))
        self.title_label.setFont(QFont('Arial', 10, QFont.Bold))
        info_layout.addWidget(self.title_label, 0, 3)
        
        # Resume name
        info_layout.addWidget(QLabel("Resume:"), 1, 0)
        resume_name = self.resume_data.get('filename', 'Unknown') if self.resume_data else 'Not selected'
        self.resume_label = QLabel(resume_name)
        info_layout.addWidget(self.resume_label, 1, 1, 1, 3)
        
        main_layout.addLayout(info_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        
        self.progress_label = QLabel("Ready")
        self.progress_label.setVisible(False)
        
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # Editor for cover letter
        main_layout.addWidget(QLabel("Cover Letter:"))
        self.cover_letter_edit = QTextEdit()
        self.cover_letter_edit.setPlaceholderText("Your cover letter will appear here")
        main_layout.addWidget(self.cover_letter_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.generate_ai_button = QPushButton("Generate with AI")
        self.generate_ai_button.clicked.connect(self.generate_ai_cover_letter)
        button_layout.addWidget(self.generate_ai_button)
        
        self.template_button = QPushButton("Use Template")
        self.template_button.clicked.connect(self._setup_template_cover_letter)
        button_layout.addWidget(self.template_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_cover_letter)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def _setup_template_cover_letter(self):
        """Set up a template cover letter based on user's resume and job data."""
        try:
            if not self.resume_data or not self.job_data:
                self.progress_label.setText("Resume or job data missing")
                self.progress_label.setVisible(True)
                return
                
            # Get template from constants
            template = Constants.DEFAULT_COVER_LETTER_TEMPLATE
            
            # Fill in template with resume and job data
            name = self.resume_data.get('name', '[Your Name]')
            email = self.resume_data.get('email', '[Your Email]')
            phone = self.resume_data.get('phone', '[Your Phone]')
            company = self.job_data.get('company', '[Company Name]')
            job_title = self.job_data.get('title', '[Job Title]')
            
            template = template.replace('[Your Name]', name)
            template = template.replace('[Your Email]', email)
            template = template.replace('[Your Phone]', phone)
            template = template.replace('[Company Name]', company)
            template = template.replace('[Job Title]', job_title)
            
            self.cover_letter_edit.setPlainText(template)
            
        except Exception as e:
            self.logger.error(f"Error setting up template: {str(e)}", exc_info=True)
            self.progress_label.setText(f"Error setting up template: {str(e)}")
            self.progress_label.setVisible(True)
            
    def generate_ai_cover_letter(self):
        """Generate a cover letter using AI."""
        try:
            # Check if resume and job data are available
            if not self.resume_data:
                QMessageBox.warning(self, "Missing Data", "Resume data is missing.")
                return
                
            if not self.job_data:
                QMessageBox.warning(self, "Missing Data", "Job data is missing.")
                return
                
            # Check if OpenAI API key is set
            api_key = self.app.config_manager.get_openai_api_key()
            if not api_key:
                QMessageBox.warning(
                    self,
                    "API Key Missing",
                    "OpenAI API key is not set. Please set it in the Settings tab."
                )
                return
                
            # Update UI
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_label.setText("Generating cover letter...")
            
            self.generate_ai_button.setEnabled(False)
            self.template_button.setEnabled(False)
            self.save_button.setEnabled(False)
            
            # Start worker thread
            self.worker = GenerateAICoverLetterWorker(
                self.app,
                self.resume_data,
                self.job_data
            )
            
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.ai_generation_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error generating cover letter: {str(e)}", exc_info=True)
            self.show_error(f"Failed to generate cover letter: {str(e)}")
            
    @pyqtSlot(str)
    def update_progress(self, message):
        """Update the progress label.
        
        Args:
            message: Progress message
        """
        self.progress_label.setText(message)
        
    @pyqtSlot(str)
    def ai_generation_completed(self, cover_letter):
        """Handle AI cover letter generation completion.
        
        Args:
            cover_letter: Generated cover letter text
        """
        # Update UI
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Cover letter generated")
        
        self.generate_ai_button.setEnabled(True)
        self.template_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        # Set cover letter text
        self.cover_letter_edit.setPlainText(cover_letter)
        
        # Update job data
        self.job_data['cover_letter'] = cover_letter
        
        self.worker = None
        
    @pyqtSlot(str)
    def show_error(self, error_message):
        """Display an error message.
        
        Args:
            error_message: Error message to display
        """
        self.logger.error(error_message)
        self.progress_label.setText(f"Error: {error_message}")
        
        self.progress_bar.setVisible(False)
        self.generate_ai_button.setEnabled(True)
        self.template_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        QMessageBox.critical(self, "Error", error_message)
        
    def save_cover_letter(self):
        """Save the cover letter and accept the dialog."""
        cover_letter = self.cover_letter_edit.toPlainText()
        
        if not cover_letter:
            QMessageBox.warning(self, "Empty Cover Letter", "Cover letter cannot be empty.")
            return
            
        # Update job data with the cover letter
        self.job_data['cover_letter'] = cover_letter
        
        # Accept the dialog
        self.accept()
        
    def get_cover_letter(self):
        """Get the cover letter text.
        
        Returns:
            Cover letter text
        """
        return self.cover_letter_edit.toPlainText()


class PasswordDialog(QDialog):
    """Dialog for entering and managing passwords, like API keys."""
    
    def __init__(self, parent=None, title="Enter Password", prompt="Password:"):
        """Initialize the dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            prompt: Prompt text
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.prompt = prompt
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QGridLayout()
        
        # Prompt label
        layout.addWidget(QLabel(self.prompt), 0, 0)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input, 0, 1)
        
        # Show password checkbox
        self.show_password = QCheckBox("Show")
        self.show_password.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password, 0, 2)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box, 1, 0, 1, 3)
        
        self.setLayout(layout)
        
    def toggle_password_visibility(self, checked):
        """Toggle password visibility.
        
        Args:
            checked: Whether the checkbox is checked
        """
        self.password_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )
        
    def get_password(self):
        """Get the entered password.
        
        Returns:
            Password string
        """
        return self.password_input.text()
        

class ResumeViewDialog(QDialog):
    """Dialog for viewing resume data."""
    
    def __init__(self, resume_data, parent=None):
        """Initialize the dialog.
        
        Args:
            resume_data: Resume data dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.resume_data = resume_data
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Resume Data")
        self.setMinimumSize(600, 500)
        
        main_layout = QVBoxLayout()
        
        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QGridLayout()
        
        # Name
        basic_layout.addWidget(QLabel("Name:"), 0, 0)
        name_label = QLabel(self.resume_data.get('name', 'N/A'))
        name_label.setFont(QFont('Arial', 10, QFont.Bold))
        basic_layout.addWidget(name_label, 0, 1)
        
        # Email
        basic_layout.addWidget(QLabel("Email:"), 1, 0)
        basic_layout.addWidget(QLabel(self.resume_data.get('email', 'N/A')), 1, 1)
        
        # Phone
        basic_layout.addWidget(QLabel("Phone:"), 2, 0)
        basic_layout.addWidget(QLabel(self.resume_data.get('phone', 'N/A')), 2, 1)
        
        # Location
        basic_layout.addWidget(QLabel("Location:"), 3, 0)
        basic_layout.addWidget(QLabel(self.resume_data.get('location', 'N/A')), 3, 1)
        
        # LinkedIn
        basic_layout.addWidget(QLabel("LinkedIn:"), 4, 0)
        basic_layout.addWidget(QLabel(self.resume_data.get('linkedin', 'N/A')), 4, 1)
        
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # Skills
        skills_group = QGroupBox("Skills")
        skills_layout = QVBoxLayout()
        
        skills_text = QTextEdit()
        skills_text.setReadOnly(True)
        skills_text.setPlainText('\n'.join(self.resume_data.get('skills', [])))
        skills_layout.addWidget(skills_text)
        
        skills_group.setLayout(skills_layout)
        main_layout.addWidget(skills_group)
        
        # Experience
        experience_group = QGroupBox("Experience")
        experience_layout = QVBoxLayout()
        
        experience_text = QTextEdit()
        experience_text.setReadOnly(True)
        
        experience_str = ""
        for exp in self.resume_data.get('experience', []):
            if isinstance(exp, dict):
                experience_str += f"Title: {exp.get('title', 'N/A')}\n"
                experience_str += f"Company: {exp.get('company', 'N/A')}\n"
                experience_str += f"Period: {exp.get('period', 'N/A')}\n"
                experience_str += f"Description: {exp.get('description', 'N/A')}\n\n"
            else:
                experience_str += f"{exp}\n\n"
                
        experience_text.setPlainText(experience_str)
        experience_layout.addWidget(experience_text)
        
        experience_group.setLayout(experience_layout)
        main_layout.addWidget(experience_group)
        
        # Education
        education_group = QGroupBox("Education")
        education_layout = QVBoxLayout()
        
        education_text = QTextEdit()
        education_text.setReadOnly(True)
        
        education_str = ""
        for edu in self.resume_data.get('education', []):
            if isinstance(edu, dict):
                education_str += f"Degree: {edu.get('degree', 'N/A')}\n"
                education_str += f"Institution: {edu.get('institution', 'N/A')}\n"
                education_str += f"Year: {edu.get('year', 'N/A')}\n\n"
            else:
                education_str += f"{edu}\n\n"
                
        education_text.setPlainText(education_str)
        education_layout.addWidget(education_text)
        
        education_group.setLayout(education_layout)
        main_layout.addWidget(education_group)
        
        # Button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        self.setLayout(main_layout)


class JobDetailsDialog(QDialog):
    """Dialog for viewing job details."""
    
    def __init__(self, job_data, parent=None):
        """Initialize the dialog.
        
        Args:
            job_data: Job data dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.job_data = job_data
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Job Details")
        self.setMinimumSize(700, 600)
        
        main_layout = QVBoxLayout()
        
        # Top info
        info_group = QGroupBox("Job Information")
        info_layout = QGridLayout()
        
        # Title
        info_layout.addWidget(QLabel("Title:"), 0, 0)
        title_label = QLabel(self.job_data.get('title', 'N/A'))
        title_label.setFont(QFont('Arial', 10, QFont.Bold))
        info_layout.addWidget(title_label, 0, 1, 1, 3)
        
        # Company
        info_layout.addWidget(QLabel("Company:"), 1, 0)
        company_label = QLabel(self.job_data.get('company', 'N/A'))
        company_label.setFont(QFont('Arial', 10, QFont.Bold))
        info_layout.addWidget(company_label, 1, 1, 1, 3)
        
        # Location
        info_layout.addWidget(QLabel("Location:"), 2, 0)
        info_layout.addWidget(QLabel(self.job_data.get('location', 'N/A')), 2, 1)
        
        # Date posted
        info_layout.addWidget(QLabel("Posted:"), 2, 2)
        info_layout.addWidget(QLabel(self.job_data.get('date_posted', 'N/A')), 2, 3)
        
        # Salary
        info_layout.addWidget(QLabel("Salary:"), 3, 0)
        info_layout.addWidget(QLabel(self.job_data.get('salary', 'N/A')), 3, 1)
        
        # Job type
        info_layout.addWidget(QLabel("Type:"), 3, 2)
        info_layout.addWidget(QLabel(self.job_data.get('job_type', 'N/A')), 3, 3)
        
        # Source
        info_layout.addWidget(QLabel("Source:"), 4, 0)
        info_layout.addWidget(QLabel(self.job_data.get('source', 'N/A')), 4, 1)
        
        # Match score
        info_layout.addWidget(QLabel("Match Score:"), 4, 2)
        match_score = self.job_data.get('match_score', 0)
        match_score_str = f"{match_score:.1f}%" if match_score else "N/A"
        info_layout.addWidget(QLabel(match_score_str), 4, 3)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Description
        main_layout.addWidget(QLabel("Job Description:"))
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setPlainText(self.job_data.get('description', 'No description available.'))
        main_layout.addWidget(self.description_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if 'url' in self.job_data and self.job_data['url']:
            self.open_url_button = QPushButton("Open Job URL")
            self.open_url_button.clicked.connect(self.open_job_url)
            button_layout.addWidget(self.open_url_button)
            
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def open_job_url(self):
        """Open the job URL in a web browser."""
        import webbrowser
        url = self.job_data.get('url')
        if url:
            webbrowser.open(url) 