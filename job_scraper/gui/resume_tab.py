#!/usr/bin/env python3
"""
Resume tab for the job scraper GUI application.
"""

import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QLabel, QLineEdit, QPushButton, QTextEdit,
                            QGroupBox, QFileDialog, QMessageBox, QTableWidget,
                            QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSlot

from job_scraper.gui.workers import ParseResumeWorker
from job_scraper.gui.dialogs import ResumeViewDialog

class ResumeTab(QWidget):
    """Resume tab for resume parsing and handling functionality."""
    
    def __init__(self, app):
        """Initialize the resume tab."""
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.worker = None
        self.resume_data = None
        
        self._setup_ui()
        self._load_default_resume()
        
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout()
        
        # Resume file selection
        file_group = QGroupBox("Resume File")
        file_layout = QHBoxLayout()
        
        self.resume_path_input = QLineEdit()
        self.resume_path_input.setPlaceholderText("Select resume file (.pdf, .docx, .doc, .txt)")
        file_layout.addWidget(self.resume_path_input)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_resume)
        file_layout.addWidget(self.browse_button)
        
        self.parse_button = QPushButton("Parse Resume")
        self.parse_button.clicked.connect(self.parse_resume)
        file_layout.addWidget(self.parse_button)
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Status and progress
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        main_layout.addLayout(status_layout)
        
        # Resume data
        data_group = QGroupBox("Parsed Resume Data")
        data_layout = QGridLayout()
        
        # Basic info
        data_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_label = QLabel("Not parsed")
        data_layout.addWidget(self.name_label, 0, 1)
        
        data_layout.addWidget(QLabel("Email:"), 1, 0)
        self.email_label = QLabel("Not parsed")
        data_layout.addWidget(self.email_label, 1, 1)
        
        data_layout.addWidget(QLabel("Phone:"), 2, 0)
        self.phone_label = QLabel("Not parsed")
        data_layout.addWidget(self.phone_label, 2, 1)
        
        # Skills table
        data_layout.addWidget(QLabel("Skills:"), 3, 0, 1, 2)
        self.skills_table = QTableWidget()
        self.skills_table.setColumnCount(1)
        self.skills_table.setHorizontalHeaderLabels(["Skill"])
        self.skills_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.skills_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        data_layout.addWidget(self.skills_table, 4, 0, 1, 2)
        
        # View details button
        self.view_details_button = QPushButton("View Full Resume Details")
        self.view_details_button.clicked.connect(self.view_resume_details)
        self.view_details_button.setEnabled(False)
        data_layout.addWidget(self.view_details_button, 5, 0, 1, 2)
        
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        self.save_as_default_button = QPushButton("Save as Default Resume")
        self.save_as_default_button.clicked.connect(self.save_as_default)
        self.save_as_default_button.setEnabled(False)
        actions_layout.addWidget(self.save_as_default_button)
        
        self.match_jobs_button = QPushButton("Match with Jobs")
        self.match_jobs_button.clicked.connect(self.match_with_jobs)
        self.match_jobs_button.setEnabled(False)
        actions_layout.addWidget(self.match_jobs_button)
        
        main_layout.addLayout(actions_layout)
        
        self.setLayout(main_layout)
        
    def _load_default_resume(self):
        """Load the default resume path from settings."""
        try:
            resume_settings = self.app.config_manager.get_resume_settings()
            default_path = resume_settings.get('default_resume_path', '')
            
            if default_path and os.path.exists(default_path):
                self.resume_path_input.setText(default_path)
                self.status_label.setText("Default resume loaded from settings")
                
        except Exception as e:
            self.logger.error(f"Error loading default resume: {str(e)}", exc_info=True)
            
    def browse_resume(self):
        """Open file dialog to select a resume."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Resume",
            "",
            "Resume Files (*.pdf *.docx *.doc *.txt);;All Files (*)"
        )
        
        if file_path:
            self.resume_path_input.setText(file_path)
            
    def parse_resume(self):
        """Parse the selected resume file."""
        resume_path = self.resume_path_input.text().strip()
        
        if not resume_path:
            QMessageBox.warning(self, "No File Selected", "Please select a resume file to parse.")
            return
            
        if not os.path.exists(resume_path):
            QMessageBox.warning(self, "File Not Found", f"The file {resume_path} does not exist.")
            return
            
        # Clear previous data
        self.resume_data = None
        self.skills_table.setRowCount(0)
        self.name_label.setText("Parsing...")
        self.email_label.setText("Parsing...")
        self.phone_label.setText("Parsing...")
        
        # Disable buttons while parsing
        self.parse_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.view_details_button.setEnabled(False)
        self.save_as_default_button.setEnabled(False)
        self.match_jobs_button.setEnabled(False)
        
        # Update status
        self.status_label.setText("Parsing resume...")
        
        # Start worker thread
        try:
            self.worker = ParseResumeWorker(self.app, resume_path)
            
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.parse_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error starting resume parsing: {str(e)}", exc_info=True)
            self.show_error(f"Failed to start resume parsing: {str(e)}")
            
    @pyqtSlot(str)
    def update_progress(self, message):
        """Update the progress status.
        
        Args:
            message: Progress message
        """
        self.status_label.setText(message)
        
    @pyqtSlot(dict)
    def parse_completed(self, resume_data):
        """Handle resume parsing completion.
        
        Args:
            resume_data: Parsed resume data dictionary
        """
        self.resume_data = resume_data
        
        # Update UI with parsed data
        self.name_label.setText(resume_data.get('name', 'Not found'))
        self.email_label.setText(resume_data.get('email', 'Not found'))
        self.phone_label.setText(resume_data.get('phone', 'Not found'))
        
        # Update skills table
        skills = resume_data.get('skills', [])
        self.skills_table.setRowCount(len(skills))
        
        for i, skill in enumerate(skills):
            self.skills_table.setItem(i, 0, QTableWidgetItem(skill))
            
        # Enable buttons
        self.parse_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.view_details_button.setEnabled(True)
        self.save_as_default_button.setEnabled(True)
        self.match_jobs_button.setEnabled(True)
        
        # Update status
        self.status_label.setText("Resume parsed successfully")
        
        # Store the filename in the resume data
        self.resume_data['filename'] = os.path.basename(self.resume_path_input.text())
        
        self.worker = None
        
    @pyqtSlot(str)
    def show_error(self, error_message):
        """Display an error message.
        
        Args:
            error_message: Error message to display
        """
        self.logger.error(error_message)
        self.status_label.setText(f"Error: {error_message}")
        
        # Re-enable buttons
        self.parse_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        
        self.name_label.setText("Not parsed")
        self.email_label.setText("Not parsed")
        self.phone_label.setText("Not parsed")
        
        QMessageBox.critical(self, "Error", error_message)
        
    def view_resume_details(self):
        """Open a dialog to view detailed resume data."""
        if not self.resume_data:
            QMessageBox.warning(self, "No Data", "No resume data available. Please parse a resume first.")
            return
            
        dialog = ResumeViewDialog(self.resume_data, self)
        dialog.exec_()
        
    def save_as_default(self):
        """Save the current resume as the default."""
        if not self.resume_data:
            QMessageBox.warning(self, "No Data", "No resume data available. Please parse a resume first.")
            return
            
        try:
            resume_path = self.resume_path_input.text()
            
            # Save to config
            resume_settings = {
                'default_resume_path': resume_path
            }
            self.app.config_manager.set_resume_settings(resume_settings)
            
            QMessageBox.information(
                self,
                "Default Resume Set",
                f"The resume '{os.path.basename(resume_path)}' has been set as the default."
            )
            
        except Exception as e:
            self.logger.error(f"Error setting default resume: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to set default resume: {str(e)}"
            )
            
    def match_with_jobs(self):
        """Switch to the matches tab and start job matching."""
        if not self.resume_data:
            QMessageBox.warning(self, "No Data", "No resume data available. Please parse a resume first.")
            return
            
        # Find the main window and switch to matches tab
        main_window = self.window()
        if hasattr(main_window, 'tabs'):
            # Find the matches tab index
            for i in range(main_window.tabs.count()):
                if main_window.tabs.tabText(i) == "Job Matches":
                    main_window.tabs.setCurrentIndex(i)
                    
                    # Start matching (if matches tab has this method)
                    matches_tab = main_window.tabs.widget(i)
                    if hasattr(matches_tab, 'start_matching'):
                        matches_tab.start_matching(self.resume_data)
                    break 