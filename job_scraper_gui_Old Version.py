#!/usr/bin/env python3
"""
GUI for Job Scraper and Applicator application using PyQt5.
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QPushButton, QComboBox, QCheckBox, QFileDialog, 
                            QSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QProgressBar, QMessageBox, QGroupBox,
                            QGridLayout, QFormLayout, QListWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from job_scraper.main import JobScraperApp

class ScraperWorker(QThread):
    """Worker thread for running the job scraper."""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, app, search_terms, country, city, sites, num_pages):
        super().__init__()
        self.app = app
        self.search_terms = search_terms
        self.country = country
        self.city = city
        self.sites = sites
        self.num_pages = num_pages
        
    def run(self):
        """Run the job scraper in a separate thread."""
        try:
            self.progress_signal.emit(0, "Starting job search...")
            
            # Scrape jobs
            self.progress_signal.emit(10, "Scraping job listings...")
            jobs = self.app.scrape_jobs(
                self.search_terms, 
                self.country, 
                self.city, 
                self.sites, 
                self.num_pages
            )
            
            # Get job details for up to 10 jobs
            if jobs:
                self.progress_signal.emit(50, f"Getting details for {min(10, len(jobs))} jobs...")
                jobs_with_details = self.app.get_job_details(max_jobs=10)
                
                # Check for expired jobs
                self.progress_signal.emit(80, "Checking expired jobs...")
                self.app.check_expired_jobs()
                
                self.progress_signal.emit(100, "Job search completed!")
                self.finished_signal.emit(jobs)
            else:
                self.progress_signal.emit(100, "No jobs found.")
                self.finished_signal.emit([])
                
        except Exception as e:
            self.error_signal.emit(f"Error during job search: {str(e)}")


class JobScraperGUI(QMainWindow):
    """Main window for the Job Scraper and Applicator GUI."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize job scraper app
        self.app = JobScraperApp()
        
        # Set up UI
        self.setWindowTitle('Job Scraper and Applicator')
        self.setGeometry(100, 100, 1200, 800)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Add tabs
        self.setup_search_tab()
        self.setup_resume_tab()
        self.setup_application_tab()
        self.setup_management_tab()
        
        # Create status bar
        self.statusBar().showMessage('Ready')
    
    def setup_search_tab(self):
        """Set up the job search tab."""
        search_tab = QWidget()
        self.tab_widget.addTab(search_tab, "Job Search")
        
        # Main layout
        layout = QVBoxLayout(search_tab)
        
        # Search form
        search_group = QGroupBox("Search Criteria")
        search_form = QFormLayout()
        
        # Search terms
        self.search_terms_input = QLineEdit()
        self.search_terms_input.setPlaceholderText("e.g., python developer, data scientist")
        search_form.addRow("Search Terms:", self.search_terms_input)
        
        # Location inputs
        location_layout = QHBoxLayout()
        
        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("Country (e.g., Australia)")
        self.country_input.setText("Australia")  # Default
        
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("City (e.g., Sydney)")
        
        location_layout.addWidget(self.country_input)
        location_layout.addWidget(self.city_input)
        
        search_form.addRow("Location:", location_layout)
        
        # Job sites
        sites_layout = QHBoxLayout()
        self.seek_checkbox = QCheckBox("Seek")
        self.seek_checkbox.setChecked(True)
        self.indeed_checkbox = QCheckBox("Indeed")
        self.indeed_checkbox.setChecked(True)
        self.linkedin_checkbox = QCheckBox("LinkedIn")
        self.linkedin_checkbox.setChecked(True)
        
        sites_layout.addWidget(self.seek_checkbox)
        sites_layout.addWidget(self.indeed_checkbox)
        sites_layout.addWidget(self.linkedin_checkbox)
        
        search_form.addRow("Job Sites:", sites_layout)
        
        # Advanced options
        advanced_layout = QHBoxLayout()
        
        pages_label = QLabel("Pages per site:")
        self.pages_spinbox = QSpinBox()
        self.pages_spinbox.setMinimum(1)
        self.pages_spinbox.setMaximum(10)
        self.pages_spinbox.setValue(2)
        
        details_label = QLabel("Detailed jobs:")
        self.details_spinbox = QSpinBox()
        self.details_spinbox.setMinimum(1)
        self.details_spinbox.setMaximum(50)
        self.details_spinbox.setValue(10)
        
        advanced_layout.addWidget(pages_label)
        advanced_layout.addWidget(self.pages_spinbox)
        advanced_layout.addSpacing(20)
        advanced_layout.addWidget(details_label)
        advanced_layout.addWidget(self.details_spinbox)
        advanced_layout.addStretch()
        
        search_form.addRow("Options:", advanced_layout)
        
        search_group.setLayout(search_form)
        layout.addWidget(search_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.search_button = QPushButton("Search Jobs")
        self.search_button.clicked.connect(self.start_job_search)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        
        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(self.clear_search_results)
        
        buttons_layout.addWidget(self.search_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.clear_button)
        
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to search")
        layout.addWidget(self.status_label)
        
        # Results
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        
        # Table for displaying jobs
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(5)
        self.jobs_table.setHorizontalHeaderLabels(["Title", "Company", "Location", "Source", "Deadline"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        results_layout.addWidget(self.jobs_table)
        
        # Jobs stats
        stats_layout = QHBoxLayout()
        self.jobs_count_label = QLabel("Total Jobs: 0")
        stats_layout.addWidget(self.jobs_count_label)
        stats_layout.addStretch()
        
        results_layout.addLayout(stats_layout)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
    
    def start_job_search(self):
        """Start the job search process."""
        # Get search terms
        search_terms_text = self.search_terms_input.text().strip()
        if not search_terms_text:
            QMessageBox.warning(self, "Input Required", "Please enter search terms")
            return
        
        search_terms = [term.strip() for term in search_terms_text.split(",")]
        
        # Get location
        country = self.country_input.text().strip()
        city = self.city_input.text().strip()
        
        # Get selected job sites
        sites = []
        if self.seek_checkbox.isChecked():
            sites.append("seek")
        if self.indeed_checkbox.isChecked():
            sites.append("indeed")
        if self.linkedin_checkbox.isChecked():
            sites.append("linkedin")
        
        if not sites:
            QMessageBox.warning(self, "Selection Required", "Please select at least one job site")
            return
        
        # Get options
        num_pages = self.pages_spinbox.value()
        
        # Update UI for search in progress
        self.search_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting job search...")
        
        # Create worker thread
        self.worker = ScraperWorker(
            self.app,
            search_terms,
            country,
            city,
            sites,
            num_pages
        )
        
        # Connect signals
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.search_completed)
        self.worker.error_signal.connect(self.search_error)
        
        # Start the worker
        self.worker.start()
    
    def update_progress(self, value, message):
        """Update the progress bar and status message."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def search_completed(self, jobs):
        """Handle completion of job search."""
        # Update UI
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Display jobs in table
        self.display_jobs(jobs)
        
        # Update stats
        self.jobs_count_label.setText(f"Total Jobs: {len(jobs)}")
        
        # Show completion message
        QMessageBox.information(self, "Search Completed", f"Found {len(jobs)} job listings")
    
    def search_error(self, error_message):
        """Handle errors during job search."""
        # Update UI
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Search failed")
        
        # Show error message
        QMessageBox.critical(self, "Error", error_message)
    
    def display_jobs(self, jobs):
        """Display jobs in the table."""
        self.jobs_table.setRowCount(len(jobs))
        
        for row, job in enumerate(jobs):
            self.jobs_table.setItem(row, 0, QTableWidgetItem(job.get('title', 'Unknown')))
            self.jobs_table.setItem(row, 1, QTableWidgetItem(job.get('company', 'Unknown')))
            self.jobs_table.setItem(row, 2, QTableWidgetItem(job.get('location', 'Unknown')))
            self.jobs_table.setItem(row, 3, QTableWidgetItem(job.get('source', 'Unknown')))
            self.jobs_table.setItem(row, 4, QTableWidgetItem(job.get('deadline', 'Unknown')))
    
    def clear_search_results(self):
        """Clear the search results."""
        self.jobs_table.setRowCount(0)
        self.jobs_count_label.setText("Total Jobs: 0")
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready to search")
    
    def setup_resume_tab(self):
        """Set up the resume matching tab."""
        resume_tab = QWidget()
        self.tab_widget.addTab(resume_tab, "Resume Matching")
        
        # Main layout
        layout = QVBoxLayout(resume_tab)
        
        # Resume selection group
        resume_group = QGroupBox("Resume Selection")
        resume_layout = QHBoxLayout()
        
        self.resume_path_input = QLineEdit()
        self.resume_path_input.setPlaceholderText("Select your resume file (PDF, DOCX, or TXT)")
        self.resume_path_input.setReadOnly(True)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_resume)
        
        resume_layout.addWidget(self.resume_path_input, 3)
        resume_layout.addWidget(browse_button, 1)
        
        resume_group.setLayout(resume_layout)
        layout.addWidget(resume_group)
        
        # Resume parsing results
        parsing_group = QGroupBox("Resume Parsing Results")
        parsing_layout = QVBoxLayout()
        
        # Add a text area to display parsing results
        self.resume_results_text = QTextEdit()
        self.resume_results_text.setReadOnly(True)
        self.resume_results_text.setPlaceholderText("Resume parsing results will be displayed here")
        parsing_layout.addWidget(self.resume_results_text)
        
        parsing_group.setLayout(parsing_layout)
        layout.addWidget(parsing_group)
        
        # Matching options
        matching_group = QGroupBox("Matching Options")
        matching_layout = QFormLayout()
        
        self.match_count_spinbox = QSpinBox()
        self.match_count_spinbox.setMinimum(1)
        self.match_count_spinbox.setMaximum(50)
        self.match_count_spinbox.setValue(10)
        matching_layout.addRow("Top matches to show:", self.match_count_spinbox)
        
        matching_group.setLayout(matching_layout)
        layout.addWidget(matching_group)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        self.parse_resume_button = QPushButton("Parse Resume")
        self.parse_resume_button.clicked.connect(self.parse_resume)
        self.parse_resume_button.setEnabled(False)
        
        self.match_jobs_button = QPushButton("Match Jobs")
        self.match_jobs_button.clicked.connect(self.match_jobs_with_resume)
        self.match_jobs_button.setEnabled(False)
        
        actions_layout.addWidget(self.parse_resume_button)
        actions_layout.addWidget(self.match_jobs_button)
        
        layout.addLayout(actions_layout)
        
        # Progress indicators
        self.resume_progress_bar = QProgressBar()
        self.resume_progress_bar.setRange(0, 100)
        self.resume_progress_bar.setValue(0)
        layout.addWidget(self.resume_progress_bar)
        
        self.resume_status_label = QLabel("Select a resume file to begin")
        layout.addWidget(self.resume_status_label)
        
        # Matched jobs results
        matches_group = QGroupBox("Matched Jobs")
        matches_layout = QVBoxLayout()
        
        # Table for displaying matched jobs
        self.matched_jobs_table = QTableWidget()
        self.matched_jobs_table.setColumnCount(6)
        self.matched_jobs_table.setHorizontalHeaderLabels(["Title", "Company", "Location", "Match %", "Missing Skills", "Deadline"])
        self.matched_jobs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.matched_jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        matches_layout.addWidget(self.matched_jobs_table)
        
        matches_group.setLayout(matches_layout)
        layout.addWidget(matches_group)
    
    def browse_resume(self):
        """Open file dialog to browse for resume file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Resume File",
            "",
            "Resume Files (*.pdf *.docx *.txt);;All Files (*)"
        )
        
        if file_path:
            self.resume_path_input.setText(file_path)
            self.parse_resume_button.setEnabled(True)
            self.resume_status_label.setText("Resume selected. Click 'Parse Resume' to continue.")
    
    def parse_resume(self):
        """Parse the selected resume file."""
        resume_path = self.resume_path_input.text()
        if not resume_path:
            QMessageBox.warning(self, "Error", "Please select a resume file first")
            return
        
        self.resume_status_label.setText("Parsing resume...")
        self.resume_progress_bar.setValue(25)
        
        # Create a separate thread for parsing to avoid UI freezing
        class ResumeParserWorker(QThread):
            finished_signal = pyqtSignal(dict)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app, resume_path):
                super().__init__()
                self.app = app
                self.resume_path = resume_path
            
            def run(self):
                try:
                    # Parse resume
                    resume_data = self.app.parse_resume(self.resume_path)
                    if resume_data:
                        self.finished_signal.emit(resume_data)
                    else:
                        self.error_signal.emit("Failed to parse resume. Please check the file format.")
                except Exception as e:
                    self.error_signal.emit(f"Error parsing resume: {str(e)}")
        
        # Create and start the worker
        self.resume_worker = ResumeParserWorker(self.app, resume_path)
        self.resume_worker.finished_signal.connect(self.resume_parsed)
        self.resume_worker.error_signal.connect(self.resume_parse_error)
        self.resume_worker.start()
    
    def resume_parsed(self, resume_data):
        """Handle successful resume parsing."""
        self.resume_progress_bar.setValue(100)
        self.resume_status_label.setText("Resume parsed successfully")
        
        # Store resume data for later use
        self.resume_data = resume_data
        
        # Display resume parsing results
        result_text = "Resume Parsing Results:\n\n"
        
        # Skills
        result_text += "Skills:\n"
        if 'skills' in resume_data and resume_data['skills']:
            for skill in resume_data['skills']:
                result_text += f"- {skill}\n"
        else:
            result_text += "No skills extracted\n"
        
        result_text += "\nWork Experience:\n"
        if 'work_experience' in resume_data and resume_data['work_experience']:
            for exp in resume_data['work_experience']:
                result_text += f"- {exp}\n"
        else:
            result_text += "No work experience extracted\n"
        
        result_text += "\nEducation:\n"
        if 'education' in resume_data and resume_data['education']:
            for edu in resume_data['education']:
                result_text += f"- {edu}\n"
        else:
            result_text += "No education extracted\n"
        
        # Update the text area
        self.resume_results_text.setText(result_text)
        
        # Enable match button if we have jobs
        if hasattr(self, 'jobs_table') and self.jobs_table.rowCount() > 0:
            self.match_jobs_button.setEnabled(True)
    
    def resume_parse_error(self, error_message):
        """Handle errors during resume parsing."""
        self.resume_progress_bar.setValue(0)
        self.resume_status_label.setText("Resume parsing failed")
        QMessageBox.critical(self, "Error", error_message)
    
    def match_jobs_with_resume(self):
        """Match jobs with parsed resume."""
        if not hasattr(self, 'resume_data'):
            QMessageBox.warning(self, "Error", "Please parse a resume first")
            return
        
        # Check if we have any jobs
        if self.jobs_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No jobs to match. Please search for jobs first.")
            return
        
        self.resume_status_label.setText("Matching jobs with resume...")
        self.resume_progress_bar.setValue(50)
        
        # Create a worker for job matching
        class JobMatcherWorker(QThread):
            finished_signal = pyqtSignal(list)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app, resume_data, job_listings):
                super().__init__()
                self.app = app
                self.resume_data = resume_data
                self.job_listings = job_listings
            
            def run(self):
                try:
                    # Match jobs with resume
                    matched_jobs = self.app.match_jobs(self.resume_data, self.job_listings)
                    self.finished_signal.emit(matched_jobs)
                except Exception as e:
                    self.error_signal.emit(f"Error matching jobs: {str(e)}")
        
        # Get job listings from app
        job_listings = self.app.job_listings
        
        # Create and start the worker
        self.matcher_worker = JobMatcherWorker(self.app, self.resume_data, job_listings)
        self.matcher_worker.finished_signal.connect(self.jobs_matched)
        self.matcher_worker.error_signal.connect(self.job_match_error)
        self.matcher_worker.start()
    
    def jobs_matched(self, matched_jobs):
        """Handle successful job matching."""
        self.resume_progress_bar.setValue(100)
        self.resume_status_label.setText("Jobs matched successfully")
        
        # Store matched jobs
        self.matched_jobs = matched_jobs
        
        # Get the number of matches to display
        top_n = self.match_count_spinbox.value()
        top_matches = matched_jobs[:min(top_n, len(matched_jobs))]
        
        # Display matched jobs in table
        self.matched_jobs_table.setRowCount(len(top_matches))
        
        for row, job in enumerate(top_matches):
            self.matched_jobs_table.setItem(row, 0, QTableWidgetItem(job.get('title', 'Unknown')))
            self.matched_jobs_table.setItem(row, 1, QTableWidgetItem(job.get('company', 'Unknown')))
            self.matched_jobs_table.setItem(row, 2, QTableWidgetItem(job.get('location', 'Unknown')))
            
            # Match score with color coding
            match_score = job.get('match_score', 0)
            match_item = QTableWidgetItem(f"{match_score:.1f}%")
            
            # Color based on match score
            if match_score >= 80:
                match_item.setBackground(Qt.green)
            elif match_score >= 60:
                match_item.setBackground(Qt.yellow)
            elif match_score >= 40:
                match_item.setBackground(Qt.lightGray)
            
            self.matched_jobs_table.setItem(row, 3, match_item)
            
            # Missing skills
            missing_skills = job.get('missing_skills', [])
            self.matched_jobs_table.setItem(row, 4, QTableWidgetItem(", ".join(missing_skills)))
            
            # Deadline
            self.matched_jobs_table.setItem(row, 5, QTableWidgetItem(job.get('deadline', 'Unknown')))
        
        # Show match completion message
        QMessageBox.information(self, "Matching Completed", 
                               f"Found {len(matched_jobs)} matches. Displaying top {len(top_matches)}.")
    
    def job_match_error(self, error_message):
        """Handle errors during job matching."""
        self.resume_progress_bar.setValue(0)
        self.resume_status_label.setText("Job matching failed")
        QMessageBox.critical(self, "Error", error_message)
    
    def setup_application_tab(self):
        """Set up the job application tab."""
        application_tab = QWidget()
        self.tab_widget.addTab(application_tab, "Job Application")
        
        # Main layout
        layout = QVBoxLayout(application_tab)
        
        # Application settings
        settings_group = QGroupBox("Application Settings")
        settings_layout = QFormLayout()
        
        # Resume selection
        resume_layout = QHBoxLayout()
        self.app_resume_path_input = QLineEdit()
        self.app_resume_path_input.setPlaceholderText("Select your resume file (PDF, DOCX, or TXT)")
        self.app_resume_path_input.setReadOnly(True)
        
        app_browse_resume_button = QPushButton("Browse...")
        app_browse_resume_button.clicked.connect(self.browse_app_resume)
        
        resume_layout.addWidget(self.app_resume_path_input, 3)
        resume_layout.addWidget(app_browse_resume_button, 1)
        
        settings_layout.addRow("Resume:", resume_layout)
        
        # Cover letter template selection
        cover_letter_layout = QHBoxLayout()
        self.cover_letter_path_input = QLineEdit()
        self.cover_letter_path_input.setPlaceholderText("Select a cover letter template (.txt)")
        self.cover_letter_path_input.setReadOnly(True)
        
        browse_cover_letter_button = QPushButton("Browse...")
        browse_cover_letter_button.clicked.connect(self.browse_cover_letter)
        
        cover_letter_layout.addWidget(self.cover_letter_path_input, 3)
        cover_letter_layout.addWidget(browse_cover_letter_button, 1)
        
        settings_layout.addRow("Cover Letter Template:", cover_letter_layout)
        
        # Maximum applications setting
        self.max_applications_spinbox = QSpinBox()
        self.max_applications_spinbox.setMinimum(1)
        self.max_applications_spinbox.setMaximum(20)
        self.max_applications_spinbox.setValue(5)
        settings_layout.addRow("Max Applications Per Session:", self.max_applications_spinbox)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Application candidates
        candidates_group = QGroupBox("Job Application Candidates")
        candidates_layout = QVBoxLayout()
        
        # Table for displaying matched jobs to apply for
        self.application_jobs_table = QTableWidget()
        self.application_jobs_table.setColumnCount(6)
        self.application_jobs_table.setHorizontalHeaderLabels(
            ["Title", "Company", "Location", "Match %", "Missing Skills", "Applied"]
        )
        self.application_jobs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.application_jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.application_jobs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.application_jobs_table.itemSelectionChanged.connect(self.application_job_selected)
        
        candidates_layout.addWidget(self.application_jobs_table)
        
        candidates_group.setLayout(candidates_layout)
        layout.addWidget(candidates_group)
        
        # Job description preview
        description_group = QGroupBox("Job Description")
        description_layout = QVBoxLayout()
        
        self.application_job_description = QTextEdit()
        self.application_job_description.setReadOnly(True)
        self.application_job_description.setPlaceholderText("Select a job to view description")
        
        description_layout.addWidget(self.application_job_description)
        
        description_group.setLayout(description_layout)
        layout.addWidget(description_group)
        
        # Cover letter preview
        cover_letter_group = QGroupBox("Cover Letter Preview")
        cover_letter_preview_layout = QVBoxLayout()
        
        self.cover_letter_preview = QTextEdit()
        self.cover_letter_preview.setReadOnly(True)
        self.cover_letter_preview.setPlaceholderText(
            "Cover letter preview will appear here after selecting a job and cover letter template"
        )
        
        cover_letter_preview_layout.addWidget(self.cover_letter_preview)
        
        generate_preview_button = QPushButton("Generate Cover Letter Preview")
        generate_preview_button.clicked.connect(self.generate_cover_letter_preview)
        cover_letter_preview_layout.addWidget(generate_preview_button)
        
        cover_letter_group.setLayout(cover_letter_preview_layout)
        layout.addWidget(cover_letter_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        setup_button = QPushButton("Setup Application Manager")
        setup_button.clicked.connect(self.setup_application_manager)
        
        apply_button = QPushButton("Apply to Selected Job")
        apply_button.clicked.connect(self.apply_to_selected_job)
        apply_button.setEnabled(False)
        self.apply_button = apply_button
        
        apply_top_button = QPushButton("Apply to Top Matches")
        apply_top_button.clicked.connect(self.apply_to_top_matches)
        apply_top_button.setEnabled(False)
        self.apply_top_button = apply_top_button
        
        action_layout.addWidget(setup_button)
        action_layout.addWidget(apply_button)
        action_layout.addWidget(apply_top_button)
        
        layout.addLayout(action_layout)
        
        # Status indicators
        self.application_status_label = QLabel("Set up resume and cover letter to enable job applications")
        layout.addWidget(self.application_status_label)
        
        # Load data if available
        self.update_application_jobs_table()
    
    def browse_app_resume(self):
        """Open file dialog to browse for resume file for applications."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Resume File",
            "",
            "Resume Files (*.pdf *.docx *.txt);;All Files (*)"
        )
        
        if file_path:
            self.app_resume_path_input.setText(file_path)
            
            # If resume path is set in other tab, make it consistent
            if hasattr(self, 'resume_path_input'):
                self.resume_path_input.setText(file_path)
            
            # Update status
            self.check_application_setup()
    
    def browse_cover_letter(self):
        """Open file dialog to browse for cover letter template."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Letter Template",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.cover_letter_path_input.setText(file_path)
            
            # Update status
            self.check_application_setup()
    
    def check_application_setup(self):
        """Check if resume and cover letter are set up for applications."""
        resume_path = self.app_resume_path_input.text()
        cover_letter_path = self.cover_letter_path_input.text()
        
        if resume_path and cover_letter_path:
            self.application_status_label.setText("Ready to set up application manager")
            return True
        elif resume_path:
            self.application_status_label.setText("Cover letter template needed")
        elif cover_letter_path:
            self.application_status_label.setText("Resume file needed")
        else:
            self.application_status_label.setText("Set up resume and cover letter to enable job applications")
        
        return False
    
    def setup_application_manager(self):
        """Set up the application manager with resume and cover letter."""
        if not self.check_application_setup():
            QMessageBox.warning(
                self, 
                "Setup Required", 
                "Please select both a resume file and cover letter template first"
            )
            return
        
        resume_path = self.app_resume_path_input.text()
        cover_letter_path = self.cover_letter_path_input.text()
        
        self.application_status_label.setText("Setting up application manager...")
        
        # Create worker thread for setup
        class ApplicationSetupWorker(QThread):
            finished_signal = pyqtSignal(bool)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app, resume_path, cover_letter_path):
                super().__init__()
                self.app = app
                self.resume_path = resume_path
                self.cover_letter_path = cover_letter_path
            
            def run(self):
                try:
                    # Set up application manager
                    result = self.app.setup_application_manager(
                        self.resume_path,
                        self.cover_letter_path
                    )
                    self.finished_signal.emit(result)
                except Exception as e:
                    self.error_signal.emit(f"Error setting up application manager: {str(e)}")
        
        # Create and start worker
        self.app_setup_worker = ApplicationSetupWorker(
            self.app,
            resume_path,
            cover_letter_path
        )
        self.app_setup_worker.finished_signal.connect(self.application_manager_setup)
        self.app_setup_worker.error_signal.connect(self.application_setup_error)
        self.app_setup_worker.start()
    
    def application_manager_setup(self, success):
        """Handle application manager setup completion."""
        if success:
            self.application_status_label.setText("Application manager set up successfully")
            self.apply_button.setEnabled(True)
            self.apply_top_button.setEnabled(True)
            QMessageBox.information(
                self, 
                "Setup Complete", 
                "Application manager has been set up successfully. You can now apply to jobs."
            )
            
            # Update the jobs table to include application status
            self.update_application_jobs_table()
        else:
            self.application_status_label.setText("Failed to set up application manager")
            QMessageBox.critical(
                self, 
                "Setup Failed", 
                "Failed to set up application manager. Please check your resume and cover letter files."
            )
    
    def application_setup_error(self, error_message):
        """Handle error during application manager setup."""
        self.application_status_label.setText("Error setting up application manager")
        QMessageBox.critical(self, "Error", error_message)
    
    def update_application_jobs_table(self):
        """Update the application jobs table with matched jobs."""
        if hasattr(self, 'matched_jobs'):
            jobs = self.matched_jobs
            self.application_jobs_table.setRowCount(len(jobs))
            
            for row, job in enumerate(jobs):
                self.application_jobs_table.setItem(row, 0, QTableWidgetItem(job.get('title', 'Unknown')))
                self.application_jobs_table.setItem(row, 1, QTableWidgetItem(job.get('company', 'Unknown')))
                self.application_jobs_table.setItem(row, 2, QTableWidgetItem(job.get('location', 'Unknown')))
                
                # Match score with color coding
                match_score = job.get('match_score', 0)
                match_item = QTableWidgetItem(f"{match_score:.1f}%")
                
                # Color based on match score
                if match_score >= 80:
                    match_item.setBackground(Qt.green)
                elif match_score >= 60:
                    match_item.setBackground(Qt.yellow)
                elif match_score >= 40:
                    match_item.setBackground(Qt.lightGray)
                
                self.application_jobs_table.setItem(row, 3, match_item)
                
                # Missing skills
                missing_skills = job.get('missing_skills', [])
                self.application_jobs_table.setItem(row, 4, QTableWidgetItem(", ".join(missing_skills)))
                
                # Application status
                if hasattr(self.app, 'application_manager') and self.app.application_manager:
                    job_id = job.get('id')
                    applied = self.app.db.check_if_applied(job_id) if job_id else False
                    status = "Yes" if applied else "No"
                    status_item = QTableWidgetItem(status)
                    
                    if applied:
                        status_item.setForeground(Qt.green)
                    
                    self.application_jobs_table.setItem(row, 5, status_item)
    
    def application_job_selected(self):
        """Handle selection of a job in the application table."""
        selected_items = self.application_jobs_table.selectedItems()
        if not selected_items:
            self.application_job_description.clear()
            return
        
        # Get selected row
        row = selected_items[0].row()
        
        # Get job info
        title = self.application_jobs_table.item(row, 0).text()
        company = self.application_jobs_table.item(row, 1).text()
        
        # Find job in matched jobs
        if not hasattr(self, 'matched_jobs'):
            return
        
        selected_job = None
        for job in self.matched_jobs:
            if (job.get('title') == title and job.get('company') == company):
                selected_job = job
                break
        
        if not selected_job:
            return
        
        # Store selected job for application
        self.selected_job = selected_job
        
        # Display job description
        description = selected_job.get('description', 'No description available')
        self.application_job_description.setText(description)
        
        # Generate cover letter preview if possible
        if hasattr(self, 'cover_letter_path_input') and self.cover_letter_path_input.text():
            self.generate_cover_letter_preview()
    
    def generate_cover_letter_preview(self):
        """Generate a preview of the cover letter for the selected job."""
        if not hasattr(self, 'selected_job'):
            QMessageBox.warning(self, "Selection Required", "Please select a job first")
            return
        
        # Check if we have a cover letter template
        cover_letter_path = self.cover_letter_path_input.text()
        if not cover_letter_path:
            QMessageBox.warning(self, "Template Required", "Please select a cover letter template first")
            return
        
        # Check if application manager is set up
        if not hasattr(self.app, 'application_manager') or not self.app.application_manager:
            QMessageBox.warning(
                self, 
                "Setup Required", 
                "Please set up the application manager first"
            )
            return
        
        try:
            # Generate cover letter
            cover_letter = self.app.application_manager.generate_cover_letter(self.selected_job)
            
            # Display preview
            self.cover_letter_preview.setText(cover_letter)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Error generating cover letter preview: {str(e)}"
            )
    
    def apply_to_selected_job(self):
        """Apply to the currently selected job."""
        if not hasattr(self, 'selected_job'):
            QMessageBox.warning(self, "Selection Required", "Please select a job first")
            return
        
        # Check if application manager is set up
        if not hasattr(self.app, 'application_manager') or not self.app.application_manager:
            QMessageBox.warning(
                self, 
                "Setup Required", 
                "Please set up the application manager first"
            )
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Application",
            f"Are you sure you want to apply to the position of {self.selected_job.get('title')} at {self.selected_job.get('company')}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.application_status_label.setText(f"Applying to {self.selected_job.get('title')}...")
        
        # Create worker thread for application
        class ApplicationWorker(QThread):
            finished_signal = pyqtSignal(bool)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app_manager, job):
                super().__init__()
                self.app_manager = app_manager
                self.job = job
            
            def run(self):
                try:
                    # Apply to job
                    result = self.app_manager.apply_to_job(self.job)
                    self.finished_signal.emit(result)
                except Exception as e:
                    self.error_signal.emit(f"Error applying to job: {str(e)}")
        
        # Create and start worker
        self.application_worker = ApplicationWorker(
            self.app.application_manager,
            self.selected_job
        )
        self.application_worker.finished_signal.connect(self.application_completed)
        self.application_worker.error_signal.connect(self.application_error)
        self.application_worker.start()
    
    def apply_to_top_matches(self):
        """Apply to top matching jobs."""
        # Check if we have matched jobs
        if not hasattr(self, 'matched_jobs') or not self.matched_jobs:
            QMessageBox.warning(self, "No Jobs", "No matched jobs available to apply to")
            return
        
        # Check if application manager is set up
        if not hasattr(self.app, 'application_manager') or not self.app.application_manager:
            QMessageBox.warning(
                self, 
                "Setup Required", 
                "Please set up the application manager first"
            )
            return
        
        # Get number of jobs to apply to
        max_applications = self.max_applications_spinbox.value()
        
        # Get top matches
        top_matches = self.matched_jobs[:min(max_applications, len(self.matched_jobs))]
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Multiple Applications",
            f"Are you sure you want to apply to the top {len(top_matches)} matching jobs?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.application_status_label.setText(f"Applying to top {len(top_matches)} jobs...")
        
        # Create worker thread for application
        class BulkApplicationWorker(QThread):
            progress_signal = pyqtSignal(int, str)
            finished_signal = pyqtSignal(int)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app, matched_jobs, max_count):
                super().__init__()
                self.app = app
                self.matched_jobs = matched_jobs
                self.max_count = max_count
            
            def run(self):
                try:
                    # Apply to jobs
                    successful_applications = 0
                    
                    for i, job in enumerate(self.matched_jobs[:self.max_count]):
                        # Skip if already applied
                        job_id = job.get('id')
                        if job_id and self.app.db.check_if_applied(job_id):
                            self.progress_signal.emit(
                                int((i + 1) * 100 / min(self.max_count, len(self.matched_jobs))),
                                f"Skipped {job.get('title')} (already applied)"
                            )
                            continue
                        
                        # Update progress
                        self.progress_signal.emit(
                            int(i * 100 / min(self.max_count, len(self.matched_jobs))),
                            f"Applying to {job.get('title')} at {job.get('company')}"
                        )
                        
                        # Apply to job
                        if self.app.application_manager.apply_to_job(job):
                            successful_applications += 1
                    
                    self.progress_signal.emit(100, f"Applied to {successful_applications} jobs")
                    self.finished_signal.emit(successful_applications)
                    
                except Exception as e:
                    self.error_signal.emit(f"Error applying to jobs: {str(e)}")
        
        # Create and start worker
        self.bulk_app_worker = BulkApplicationWorker(
            self.app,
            self.matched_jobs,
            max_applications
        )
        self.bulk_app_worker.progress_signal.connect(self.application_progress)
        self.bulk_app_worker.finished_signal.connect(self.bulk_application_completed)
        self.bulk_app_worker.error_signal.connect(self.application_error)
        self.bulk_app_worker.start()
    
    def application_progress(self, value, message):
        """Update application progress."""
        self.application_status_label.setText(message)
    
    def application_completed(self, success):
        """Handle completion of job application."""
        if success:
            self.application_status_label.setText("Application submitted successfully")
            QMessageBox.information(
                self, 
                "Application Successful", 
                f"Successfully applied to {self.selected_job.get('title')} at {self.selected_job.get('company')}"
            )
            
            # Update application status in table
            self.update_application_jobs_table()
        else:
            self.application_status_label.setText("Application failed")
            QMessageBox.critical(
                self, 
                "Application Failed", 
                "Failed to apply to the job. Please try again or check the job posting."
            )
    
    def bulk_application_completed(self, count):
        """Handle completion of bulk job applications."""
        self.application_status_label.setText(f"Applied to {count} jobs successfully")
        QMessageBox.information(
            self, 
            "Applications Completed", 
            f"Successfully applied to {count} jobs."
        )
        
        # Update application status in table
        self.update_application_jobs_table()
    
    def application_error(self, error_message):
        """Handle error during job application."""
        self.application_status_label.setText("Error applying to job")
        QMessageBox.critical(self, "Error", error_message)
    
    def expired_jobs_deleted(self, count):
        """Handle completion of expired jobs deletion."""
        self.statusBar().showMessage(f"Deleted {count} expired job(s)", 3000)
        QMessageBox.information(self, "Jobs Deleted", f"Successfully deleted {count} expired job(s)")
        
        # Refresh jobs list
        self.refresh_jobs()
    
    def delete_expired_error(self, error_message):
        """Handle error during expired jobs deletion."""
        self.statusBar().showMessage("Error deleting expired jobs", 3000)
        QMessageBox.critical(self, "Error", error_message)

    def setup_management_tab(self):
        """Set up the job management tab."""
        management_tab = QWidget()
        self.tab_widget.addTab(management_tab, "Job Management")
        
        # Main layout
        layout = QVBoxLayout(management_tab)
        
        # Filters and controls
        filters_group = QGroupBox("Filters and Actions")
        filters_layout = QVBoxLayout()
        
        # Filter options
        filter_options_layout = QHBoxLayout()
        
        # Status filter
        status_layout = QHBoxLayout()
        status_label = QLabel("Status:")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Jobs", "Active Jobs", "Expired Jobs"])
        self.status_combo.currentIndexChanged.connect(self.filter_jobs)
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_combo)
        
        # Source filter
        source_layout = QHBoxLayout()
        source_label = QLabel("Source:")
        self.source_combo = QComboBox()
        self.source_combo.addItems(["All Sources", "Seek", "Indeed", "LinkedIn"])
        self.source_combo.currentIndexChanged.connect(self.filter_jobs)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        
        filter_options_layout.addLayout(status_layout)
        filter_options_layout.addSpacing(20)
        filter_options_layout.addLayout(source_layout)
        filter_options_layout.addStretch()
        
        filters_layout.addLayout(filter_options_layout)
        
        # Expiration management
        expiration_layout = QHBoxLayout()
        
        self.expiring_days_spinbox = QSpinBox()
        self.expiring_days_spinbox.setMinimum(1)
        self.expiring_days_spinbox.setMaximum(30)
        self.expiring_days_spinbox.setValue(7)
        
        show_expiring_button = QPushButton("Show Expiring Jobs")
        show_expiring_button.clicked.connect(self.show_expiring_jobs)
        
        check_expired_button = QPushButton("Check Expired Jobs")
        check_expired_button.clicked.connect(self.check_expired_jobs)
        
        self.delete_days_spinbox = QSpinBox()
        self.delete_days_spinbox.setMinimum(1)
        self.delete_days_spinbox.setMaximum(365)
        self.delete_days_spinbox.setValue(30)
        
        delete_expired_button = QPushButton("Delete Expired Jobs")
        delete_expired_button.clicked.connect(self.delete_expired_jobs)
        
        expiration_layout.addWidget(QLabel("Expiring within:"))
        expiration_layout.addWidget(self.expiring_days_spinbox)
        expiration_layout.addWidget(QLabel("days"))
        expiration_layout.addWidget(show_expiring_button)
        expiration_layout.addSpacing(20)
        expiration_layout.addWidget(check_expired_button)
        expiration_layout.addSpacing(20)
        expiration_layout.addWidget(QLabel("Older than:"))
        expiration_layout.addWidget(self.delete_days_spinbox)
        expiration_layout.addWidget(QLabel("days"))
        expiration_layout.addWidget(delete_expired_button)
        
        filters_layout.addLayout(expiration_layout)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh Jobs")
        refresh_button.clicked.connect(self.refresh_jobs)
        
        refresh_layout.addStretch()
        refresh_layout.addWidget(refresh_button)
        
        filters_layout.addLayout(refresh_layout)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Jobs table
        jobs_group = QGroupBox("Job Database")
        jobs_layout = QVBoxLayout()
        
        self.management_jobs_table = QTableWidget()
        self.management_jobs_table.setColumnCount(7)
        self.management_jobs_table.setHorizontalHeaderLabels(
            ["ID", "Title", "Company", "Location", "Source", "Date Scraped", "Deadline"]
        )
        self.management_jobs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.management_jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.management_jobs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.management_jobs_table.itemSelectionChanged.connect(self.job_selected)
        
        jobs_layout.addWidget(self.management_jobs_table)
        
        jobs_group.setLayout(jobs_layout)
        layout.addWidget(jobs_group)
        
        # Job details
        details_group = QGroupBox("Job Details")
        details_layout = QVBoxLayout()
        
        self.job_details_text = QTextEdit()
        self.job_details_text.setReadOnly(True)
        self.job_details_text.setPlaceholderText("Select a job to view details")
        
        details_layout.addWidget(self.job_details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QHBoxLayout()
        
        self.active_jobs_label = QLabel("Active Jobs: 0")
        self.expired_jobs_label = QLabel("Expired Jobs: 0")
        self.applied_jobs_label = QLabel("Applied Jobs: 0")
        
        stats_layout.addWidget(self.active_jobs_label)
        stats_layout.addSpacing(20)
        stats_layout.addWidget(self.expired_jobs_label)
        stats_layout.addSpacing(20)
        stats_layout.addWidget(self.applied_jobs_label)
        stats_layout.addStretch()
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Initialize table
        self.refresh_jobs()
    
    def refresh_jobs(self):
        """Refresh the jobs table with data from the database."""
        # Update UI
        self.statusBar().showMessage("Loading jobs from database...")
        
        # Create worker thread to avoid UI freezing
        class JobsLoaderWorker(QThread):
            finished_signal = pyqtSignal(list, dict)
            error_signal = pyqtSignal(str)
            
            def __init__(self, db):
                super().__init__()
                self.db = db
            
            def run(self):
                try:
                    # Get all jobs from database
                    all_jobs = self.db.get_all_jobs(with_description=True)
                    
                    # Calculate statistics
                    stats = {
                        'total': len(all_jobs),
                        'active': sum(1 for job in all_jobs if job.get('is_expired', 0) == 0),
                        'expired': sum(1 for job in all_jobs if job.get('is_expired', 0) == 1),
                        'applied': sum(1 for job in all_jobs if 'applied' in job and job['applied'])
                    }
                    
                    self.finished_signal.emit(all_jobs, stats)
                except Exception as e:
                    self.error_signal.emit(f"Error loading jobs: {str(e)}")
        
        # Create and start worker
        self.jobs_loader = JobsLoaderWorker(self.app.db)
        self.jobs_loader.finished_signal.connect(self.jobs_loaded)
        self.jobs_loader.error_signal.connect(self.jobs_load_error)
        self.jobs_loader.start()
    
    def jobs_loaded(self, all_jobs, stats):
        """Handle successful loading of jobs."""
        # Store jobs
        self.all_jobs = all_jobs
        
        # Update statistics
        self.active_jobs_label.setText(f"Active Jobs: {stats['active']}")
        self.expired_jobs_label.setText(f"Expired Jobs: {stats['expired']}")
        self.applied_jobs_label.setText(f"Applied Jobs: {stats.get('applied', 0)}")
        
        # Apply current filters
        self.filter_jobs()
        
        # Update status
        self.statusBar().showMessage(f"Loaded {len(all_jobs)} jobs from database", 3000)
    
    def jobs_load_error(self, error_message):
        """Handle error loading jobs."""
        self.statusBar().showMessage("Error loading jobs", 3000)
        QMessageBox.critical(self, "Error", error_message)
    
    def filter_jobs(self):
        """Filter jobs based on selected criteria."""
        if not hasattr(self, 'all_jobs'):
            return
        
        # Get filter values
        status_filter = self.status_combo.currentText()
        source_filter = self.source_combo.currentText()
        
        # Apply filters
        filtered_jobs = []
        for job in self.all_jobs:
            # Status filter
            if status_filter == "Active Jobs" and job.get('is_expired', 0) == 1:
                continue
            if status_filter == "Expired Jobs" and job.get('is_expired', 0) == 0:
                continue
            
            # Source filter
            if source_filter != "All Sources" and job.get('source', '') != source_filter:
                continue
            
            filtered_jobs.append(job)
        
        # Display filtered jobs
        self.display_management_jobs(filtered_jobs)
    
    def display_management_jobs(self, jobs):
        """Display jobs in the management table."""
        self.management_jobs_table.setRowCount(len(jobs))
        
        for row, job in enumerate(jobs):
            # Add job ID
            self.management_jobs_table.setItem(row, 0, QTableWidgetItem(str(job.get('id', ''))))
            
            # Add job title with color coding for expired jobs
            title_item = QTableWidgetItem(job.get('title', 'Unknown'))
            if job.get('is_expired', 0) == 1:
                title_item.setForeground(Qt.red)
            self.management_jobs_table.setItem(row, 1, title_item)
            
            # Add other job info
            self.management_jobs_table.setItem(row, 2, QTableWidgetItem(job.get('company', 'Unknown')))
            self.management_jobs_table.setItem(row, 3, QTableWidgetItem(job.get('location', 'Unknown')))
            self.management_jobs_table.setItem(row, 4, QTableWidgetItem(job.get('source', 'Unknown')))
            self.management_jobs_table.setItem(row, 5, QTableWidgetItem(job.get('date_scraped', 'Unknown')))
            self.management_jobs_table.setItem(row, 6, QTableWidgetItem(job.get('deadline', 'Unknown')))
    
    def job_selected(self):
        """Handle selection of a job in the management table."""
        selected_items = self.management_jobs_table.selectedItems()
        if not selected_items:
            self.job_details_text.clear()
            return
        
        # Get selected row
        row = selected_items[0].row()
        
        # Get job ID
        job_id_item = self.management_jobs_table.item(row, 0)
        if not job_id_item:
            return
        
        job_id = int(job_id_item.text())
        
        # Find job by ID
        selected_job = None
        for job in self.all_jobs:
            if job.get('id') == job_id:
                selected_job = job
                break
        
        if not selected_job:
            return
        
        # Display job details
        details_text = f"Job Details\n{'='*50}\n\n"
        details_text += f"Title: {selected_job.get('title', 'Unknown')}\n"
        details_text += f"Company: {selected_job.get('company', 'Unknown')}\n"
        details_text += f"Location: {selected_job.get('location', 'Unknown')}\n"
        details_text += f"Source: {selected_job.get('source', 'Unknown')}\n"
        details_text += f"Date Scraped: {selected_job.get('date_scraped', 'Unknown')}\n"
        details_text += f"Deadline: {selected_job.get('deadline', 'Unknown')}\n"
        details_text += f"Status: {'Expired' if selected_job.get('is_expired', 0) == 1 else 'Active'}\n"
        details_text += f"URL: {selected_job.get('link', 'Unknown')}\n\n"
        
        details_text += f"Job Description\n{'-'*50}\n\n"
        details_text += selected_job.get('description', 'No description available')
        
        self.job_details_text.setText(details_text)
    
    def check_expired_jobs(self):
        """Check for and mark expired jobs."""
        self.statusBar().showMessage("Checking for expired jobs...")
        
        class ExpiredJobsWorker(QThread):
            finished_signal = pyqtSignal(int)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app):
                super().__init__()
                self.app = app
            
            def run(self):
                try:
                    # Check expired jobs
                    count = self.app.check_expired_jobs()
                    self.finished_signal.emit(count)
                except Exception as e:
                    self.error_signal.emit(f"Error checking expired jobs: {str(e)}")
        
        # Create and start worker
        self.expired_worker = ExpiredJobsWorker(self.app)
        self.expired_worker.finished_signal.connect(self.expired_jobs_checked)
        self.expired_worker.error_signal.connect(self.expired_jobs_error)
        self.expired_worker.start()
    
    def expired_jobs_checked(self, count):
        """Handle completion of expired jobs check."""
        self.statusBar().showMessage(f"Marked {count} job(s) as expired", 3000)
        QMessageBox.information(self, "Expired Jobs", f"Marked {count} job(s) as expired")
        
        # Refresh jobs list
        self.refresh_jobs()
    
    def expired_jobs_error(self, error_message):
        """Handle error during expired jobs check."""
        self.statusBar().showMessage("Error checking expired jobs", 3000)
        QMessageBox.critical(self, "Error", error_message)
    
    def show_expiring_jobs(self):
        """Show jobs that will expire soon."""
        days = self.expiring_days_spinbox.value()
        self.statusBar().showMessage(f"Finding jobs expiring within {days} days...")
        
        class ExpiringJobsWorker(QThread):
            finished_signal = pyqtSignal(list)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app, days):
                super().__init__()
                self.app = app
                self.days = days
            
            def run(self):
                try:
                    # Get expiring jobs
                    expiring_jobs = self.app.show_expiring_jobs(self.days)
                    self.finished_signal.emit(expiring_jobs)
                except Exception as e:
                    self.error_signal.emit(f"Error finding expiring jobs: {str(e)}")
        
        # Create and start worker
        self.expiring_worker = ExpiringJobsWorker(self.app, days)
        self.expiring_worker.finished_signal.connect(self.expiring_jobs_found)
        self.expiring_worker.error_signal.connect(self.expiring_jobs_error)
        self.expiring_worker.start()
    
    def expiring_jobs_found(self, expiring_jobs):
        """Handle found expiring jobs."""
        self.statusBar().showMessage(f"Found {len(expiring_jobs)} job(s) expiring soon", 3000)
        
        if not expiring_jobs:
            QMessageBox.information(self, "Expiring Jobs", "No jobs found that expire within the specified time frame.")
            return
        
        # Filter the table to show only expiring jobs
        self.status_combo.setCurrentText("Active Jobs")
        
        # Select the first expiring job
        for row in range(self.management_jobs_table.rowCount()):
            deadline_item = self.management_jobs_table.item(row, 6)
            for expiring_job in expiring_jobs:
                if deadline_item and deadline_item.text() == expiring_job.get('deadline', ''):
                    self.management_jobs_table.selectRow(row)
                    break
    
    def expiring_jobs_error(self, error_message):
        """Handle error during expiring jobs search."""
        self.statusBar().showMessage("Error finding expiring jobs", 3000)
        QMessageBox.critical(self, "Error", error_message)
    
    def delete_expired_jobs(self):
        """Delete expired jobs older than specified days."""
        days = self.delete_days_spinbox.value()
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete expired jobs older than {days} days?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.statusBar().showMessage(f"Deleting expired jobs older than {days} days...")
        
        class DeleteExpiredWorker(QThread):
            finished_signal = pyqtSignal(int)
            error_signal = pyqtSignal(str)
            
            def __init__(self, app, days):
                super().__init__()
                self.app = app
                self.days = days
            
            def run(self):
                try:
                    # Delete expired jobs
                    count = self.app.delete_expired_jobs(self.days)
                    self.finished_signal.emit(count)
                except Exception as e:
                    self.error_signal.emit(f"Error deleting expired jobs: {str(e)}")
        
        # Create and start worker
        self.delete_worker = DeleteExpiredWorker(self.app, days)
        self.delete_worker.finished_signal.connect(self.expired_jobs_deleted)
        self.delete_worker.error_signal.connect(self.expired_jobs_error)
        self.delete_worker.start()
    
    def expired_jobs_deleted(self, count):
        """Handle completion of expired jobs deletion."""
        self.statusBar().showMessage(f"Deleted {count} expired job(s)", 3000)
        QMessageBox.information(self, "Expired Jobs Deleted", f"Successfully deleted {count} expired job(s)")
        
        # Refresh jobs list
        self.refresh_jobs()
    
    def expired_jobs_error(self, error_message):
        """Handle error during expired jobs deletion."""
        self.statusBar().showMessage("Error deleting expired jobs", 3000)
        QMessageBox.critical(self, "Error", error_message)


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    window = JobScraperGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 