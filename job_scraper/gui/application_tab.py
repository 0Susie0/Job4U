#!/usr/bin/env python3
"""
Application tab for the job scraper GUI application.
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QGroupBox, QFormLayout,
                            QComboBox, QSpinBox, QProgressBar, QMessageBox,
                            QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QCheckBox, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal

from job_scraper.gui.workers import ApplyToJobWorker

class ApplicationTab:
    """Class to handle the job application tab functionality."""
    
    def __init__(self, parent, app):
        """Initialize application tab.
        
        Args:
            parent: Parent widget (main window)
            app: JobScraperApp instance
        """
        self.parent = parent
        self.app = app
        self.tab = QWidget()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface for the application tab."""
        # Main layout
        layout = QVBoxLayout(self.tab)
        
        # Create a splitter to divide the top and bottom sections
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # Top section - Job selection and cover letter configuration
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Job selection group
        job_selection_group = QGroupBox("Select Job to Apply")
        job_selection_layout = QVBoxLayout(job_selection_group)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Jobs", "Matched Jobs", "Not Applied"])
        self.status_combo.currentIndexChanged.connect(self.filter_jobs)
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addWidget(QLabel("Min Match:"))
        self.match_threshold = QSpinBox()
        self.match_threshold.setRange(0, 100)
        self.match_threshold.setValue(60)
        self.match_threshold.setSuffix("%")
        self.match_threshold.valueChanged.connect(self.filter_jobs)
        filter_layout.addWidget(self.match_threshold)
        
        filter_layout.addStretch()
        
        # Refresh button
        refresh_button = QPushButton("Refresh Jobs")
        refresh_button.clicked.connect(self.refresh_jobs)
        filter_layout.addWidget(refresh_button)
        
        job_selection_layout.addLayout(filter_layout)
        
        # Jobs table
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(6)
        self.jobs_table.setHorizontalHeaderLabels(["ID", "Title", "Company", "Location", "Match %", "Deadline"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Stretch the Title column
        self.jobs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Stretch the Company column
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.jobs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.jobs_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.jobs_table.itemSelectionChanged.connect(self.job_selected)
        job_selection_layout.addWidget(self.jobs_table)
        
        top_layout.addWidget(job_selection_group)
        
        # Cover letter configuration group
        cl_config_group = QGroupBox("Cover Letter Configuration")
        cl_config_layout = QFormLayout(cl_config_group)
        
        # Cover letter template
        cl_template_layout = QHBoxLayout()
        self.cl_template_input = QLineEdit()
        self.cl_template_input.setText(self.app.config_manager.get_config('default_cover_letter_template', ''))
        
        browse_cl_button = QPushButton("Browse...")
        browse_cl_button.clicked.connect(self.browse_cl_template)
        
        cl_template_layout.addWidget(self.cl_template_input)
        cl_template_layout.addWidget(browse_cl_button)
        
        cl_config_layout.addRow("Cover Letter Template:", cl_template_layout)
        
        # AI options
        self.use_ai_checkbox = QCheckBox("Use AI to generate cover letter")
        self.use_ai_checkbox.setChecked(self.app.config_manager.get_config('use_ai_cover_letter', True))
        cl_config_layout.addRow("", self.use_ai_checkbox)
        
        # Preview button
        self.preview_button = QPushButton("Preview Cover Letter")
        self.preview_button.clicked.connect(self.preview_cover_letter)
        self.preview_button.setEnabled(False)  # Disabled until a job is selected
        cl_config_layout.addRow("", self.preview_button)
        
        top_layout.addWidget(cl_config_group)
        
        splitter.addWidget(top_widget)
        
        # Bottom section - Cover letter preview and apply button
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Cover letter preview
        cl_preview_group = QGroupBox("Cover Letter Preview")
        cl_preview_layout = QVBoxLayout(cl_preview_group)
        
        self.cl_preview = QTextEdit()
        self.cl_preview.setReadOnly(True)
        cl_preview_layout.addWidget(self.cl_preview)
        
        bottom_layout.addWidget(cl_preview_group)
        
        # Apply controls
        apply_group = QGroupBox("Apply to Job")
        apply_layout = QVBoxLayout(apply_group)
        
        # Progress indicators
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        apply_layout.addLayout(progress_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.save_cl_button = QPushButton("Save Cover Letter")
        self.save_cl_button.clicked.connect(self.save_cover_letter)
        self.save_cl_button.setEnabled(False)  # Disabled until cover letter is generated
        action_layout.addWidget(self.save_cl_button)
        
        action_layout.addStretch()
        
        self.apply_button = QPushButton("Apply to Job")
        self.apply_button.clicked.connect(self.apply_to_job)
        self.apply_button.setEnabled(False)  # Disabled until cover letter is generated
        action_layout.addWidget(self.apply_button)
        
        apply_layout.addLayout(action_layout)
        
        bottom_layout.addWidget(apply_group)
        
        splitter.addWidget(bottom_widget)
        
        # Set initial split position (30% top, 70% bottom)
        splitter.setSizes([300, 700])
        
        # Refresh jobs table
        self.refresh_jobs()
    
    def refresh_jobs(self):
        """Refresh the jobs table with data from the database."""
        try:
            # Fetch jobs from the database
            self.parent.logger.info("Refreshing jobs table")
            self.status_label.setText("Loading jobs...")
            self.progress_bar.setValue(10)
            
            # Get all jobs from DB
            self.jobs = self.app.db_manager.get_all_jobs()
            
            self.filter_jobs()
            self.status_label.setText("Jobs loaded")
            self.progress_bar.setValue(100)
            
        except Exception as e:
            self.parent.logger.error(f"Error refreshing jobs: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Error loading jobs: {str(e)}")
    
    def filter_jobs(self):
        """Filter jobs based on selected criteria."""
        if not hasattr(self, 'jobs'):
            return
        
        filtered_jobs = []
        status_filter = self.status_combo.currentText()
        match_threshold = self.match_threshold.value()
        
        for job in self.jobs:
            match_score = job.get('match_score', 0)
            
            # Skip jobs below match threshold
            if match_score < match_threshold:
                continue
            
            # Apply status filter
            if status_filter == "Matched Jobs" and match_score == 0:
                continue
            elif status_filter == "Not Applied" and job.get('applied', False):
                continue
            
            filtered_jobs.append(job)
        
        self.display_jobs(filtered_jobs)
    
    def display_jobs(self, jobs):
        """Display filtered jobs in the jobs table.
        
        Args:
            jobs: List of job dictionaries to display
        """
        self.jobs_table.setRowCount(0)  # Clear table
        
        for job in jobs:
            row = self.jobs_table.rowCount()
            self.jobs_table.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(str(job.get('id', '')))
            self.jobs_table.setItem(row, 0, id_item)
            
            # Title
            title_item = QTableWidgetItem(job.get('title', ''))
            self.jobs_table.setItem(row, 1, title_item)
            
            # Company
            company_item = QTableWidgetItem(job.get('company', ''))
            self.jobs_table.setItem(row, 2, company_item)
            
            # Location
            location_item = QTableWidgetItem(job.get('location', ''))
            self.jobs_table.setItem(row, 3, location_item)
            
            # Match %
            match_score = job.get('match_score', 0)
            match_item = QTableWidgetItem(f"{match_score}%")
            self.jobs_table.setItem(row, 4, match_item)
            
            # Color code based on match score
            if match_score >= 80:
                match_item.setBackground(Qt.green)
            elif match_score >= 60:
                match_item.setBackground(Qt.yellow)
            elif match_score > 0:
                match_item.setBackground(Qt.lightGray)
            
            # Deadline
            deadline_item = QTableWidgetItem(job.get('deadline', 'Not specified'))
            self.jobs_table.setItem(row, 5, deadline_item)
            
            # Store the job data in first column item
            id_item.setData(Qt.UserRole, job)
        
        self.parent.logger.info(f"Displayed {len(jobs)} jobs in application tab")
    
    def job_selected(self):
        """Handle job selection event."""
        selected_items = self.jobs_table.selectedItems()
        if not selected_items:
            self.preview_button.setEnabled(False)
            return
        
        # Get the job data from the first cell of the selected row
        row = selected_items[0].row()
        job_item = self.jobs_table.item(row, 0)
        self.selected_job = job_item.data(Qt.UserRole)
        
        self.parent.logger.info(f"Selected job: {self.selected_job.get('title')} at {self.selected_job.get('company')}")
        
        # Enable preview button
        self.preview_button.setEnabled(True)
        
        # Clear cover letter preview
        self.cl_preview.clear()
        self.save_cl_button.setEnabled(False)
        self.apply_button.setEnabled(False)
    
    def browse_cl_template(self):
        """Browse for cover letter template file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Cover Letter Template",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.cl_template_input.setText(file_path)
            # Save as default template
            self.app.config_manager.set_config('default_cover_letter_template', file_path)
            self.app.config_manager.save_config()
    
    def preview_cover_letter(self):
        """Generate and preview the cover letter for the selected job."""
        if not hasattr(self, 'selected_job'):
            QMessageBox.warning(self.parent, "Warning", "Please select a job first.")
            return
        
        # Get template path
        template_path = self.cl_template_input.text()
        if not template_path:
            QMessageBox.warning(self.parent, "Warning", "Please select a cover letter template.")
            return
        
        # Get parsed resume data
        resume_data = self.parent.resume_tab.get_parsed_resume() if hasattr(self.parent, 'resume_tab') else None
        if not resume_data:
            QMessageBox.warning(self.parent, "Warning", "Please parse your resume first in the Resume Matching tab.")
            return
        
        try:
            # Update UI
            self.status_label.setText("Generating cover letter...")
            self.progress_bar.setValue(10)
            
            # Generate cover letter based on AI setting
            use_ai = self.use_ai_checkbox.isChecked()
            
            if use_ai:
                # Check if API key is set
                api_key = self.app.config_manager.get_openai_api_key()
                if not api_key:
                    response = QMessageBox.question(
                        self.parent,
                        "API Key Missing",
                        "No OpenAI API key found. Would you like to use the basic template instead?\n\n"
                        "You can add your API key in the Settings tab.",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if response == QMessageBox.No:
                        self.status_label.setText("Operation cancelled")
                        self.progress_bar.setValue(0)
                        return
                    
                    # Fall back to basic template
                    use_ai = False
            
            # Generate cover letter
            job_description = self.selected_job.get('description', '')
            
            if use_ai:
                self.parent.logger.info("Generating AI cover letter")
                self.cover_letter = self.app.application_manager.generate_cover_letter(
                    resume_data, 
                    job_description, 
                    template_path
                )
            else:
                self.parent.logger.info("Generating basic cover letter from template")
                self.cover_letter = self.app.application_manager._fallback_generate_cover_letter(
                    resume_data,
                    self.selected_job,
                    template_path
                )
            
            # Display preview
            self.cl_preview.setText(self.cover_letter)
            
            # Enable save and apply buttons
            self.save_cl_button.setEnabled(True)
            self.apply_button.setEnabled(True)
            
            # Update UI
            self.status_label.setText("Cover letter generated")
            self.progress_bar.setValue(100)
            
        except Exception as e:
            self.parent.logger.error(f"Error generating cover letter: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            self.progress_bar.setValue(0)
            QMessageBox.critical(self.parent, "Error", f"Error generating cover letter: {str(e)}")
    
    def save_cover_letter(self):
        """Save the generated cover letter to a file."""
        if not hasattr(self, 'cover_letter'):
            QMessageBox.warning(self.parent, "Warning", "No cover letter has been generated.")
            return
        
        # Create default filename
        job_title = self.selected_job.get('title', 'job').replace(' ', '_')
        company = self.selected_job.get('company', 'company').replace(' ', '_')
        default_filename = f"Cover_Letter_{job_title}_{company}.txt"
        
        # Get save path
        save_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save Cover Letter",
            os.path.join(os.path.expanduser("~"), default_filename),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not save_path:
            return
        
        try:
            # Save cover letter
            self.app.application_manager.save_cover_letter(
                self.cover_letter,
                self.selected_job,
                save_path
            )
            
            self.status_label.setText(f"Cover letter saved to {save_path}")
            QMessageBox.information(self.parent, "Success", f"Cover letter saved to {save_path}")
            
        except Exception as e:
            self.parent.logger.error(f"Error saving cover letter: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Error saving cover letter: {str(e)}")
    
    def apply_to_job(self):
        """Apply to the selected job."""
        if not hasattr(self, 'cover_letter'):
            QMessageBox.warning(self.parent, "Warning", "No cover letter has been generated.")
            return
        
        if not hasattr(self, 'selected_job'):
            QMessageBox.warning(self.parent, "Warning", "Please select a job first.")
            return
        
        # Confirm application
        job_title = self.selected_job.get('title', '')
        company = self.selected_job.get('company', '')
        
        response = QMessageBox.question(
            self.parent,
            "Confirm Application",
            f"Are you sure you want to apply to '{job_title}' at {company}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if response == QMessageBox.No:
            return
        
        # Start application process
        try:
            # Update UI
            self.status_label.setText("Applying to job...")
            self.progress_bar.setValue(10)
            self.apply_button.setEnabled(False)
            
            # Create worker thread
            self.apply_worker = ApplyToJobWorker(
                self.app.application_manager,
                self.selected_job,
                self.cover_letter
            )
            
            # Connect signals
            self.apply_worker.progress.connect(self.update_apply_progress)
            self.apply_worker.finished.connect(self.application_finished)
            self.apply_worker.error.connect(self.application_error)
            
            # Start worker
            self.apply_worker.start()
            
        except Exception as e:
            self.parent.logger.error(f"Error starting application process: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            self.progress_bar.setValue(0)
            self.apply_button.setEnabled(True)
            QMessageBox.critical(self.parent, "Error", f"Error applying to job: {str(e)}")
    
    def update_apply_progress(self, progress, status):
        """Update the UI with application progress.
        
        Args:
            progress (int): Progress percentage (0-100)
            status (str): Status message
        """
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def application_finished(self):
        """Handle successful job application."""
        self.status_label.setText("Application submitted successfully")
        self.progress_bar.setValue(100)
        self.apply_button.setEnabled(True)
        
        # Update job status in DB
        self.app.db_manager.mark_job_as_applied(self.selected_job.get('id'))
        
        # Refresh jobs table
        self.refresh_jobs()
        
        QMessageBox.information(
            self.parent, 
            "Success", 
            "Job application submitted successfully!"
        )
    
    def application_error(self, error_msg):
        """Handle error during job application.
        
        Args:
            error_msg (str): Error message
        """
        self.parent.logger.error(f"Application error: {error_msg}")
        self.status_label.setText(f"Error: {error_msg}")
        self.progress_bar.setValue(0)
        self.apply_button.setEnabled(True)
        
        QMessageBox.critical(
            self.parent, 
            "Application Error", 
            f"Error applying to job: {error_msg}"
        )
    
    def get_tab(self):
        """Get the tab widget.
        
        Returns:
            The configured tab widget
        """
        return self.tab 