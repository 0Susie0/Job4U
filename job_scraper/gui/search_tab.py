#!/usr/bin/env python3
"""
Search tab for the job scraper GUI.
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QSpinBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QGroupBox,
    QSplitter, QFrame
)

from job_scraper.gui.workers import ScrapeJobsWorker


class SearchTab(QWidget):
    """Search tab for job scraping functionality."""
    
    def __init__(self, app):
        """Initialize the search tab.
        
        Args:
            app: Application instance
        """
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.worker = None
        self.jobs = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout()
        
        # Search controls
        search_group = QGroupBox("Search Criteria")
        search_layout = QGridLayout()
        
        # Keywords
        search_layout.addWidget(QLabel("Keywords:"), 0, 0)
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("e.g. Python Developer")
        search_layout.addWidget(self.keywords_input, 0, 1, 1, 3)
        
        # Location
        search_layout.addWidget(QLabel("Location:"), 1, 0)
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g. New York")
        search_layout.addWidget(self.location_input, 1, 1, 1, 3)
        
        # Job sites
        search_layout.addWidget(QLabel("Job Sites:"), 2, 0)
        sites_layout = QHBoxLayout()
        
        self.seek_checkbox = QCheckBox("Seek")
        self.seek_checkbox.setChecked(True)
        sites_layout.addWidget(self.seek_checkbox)
        
        self.indeed_checkbox = QCheckBox("Indeed")
        self.indeed_checkbox.setChecked(True)
        sites_layout.addWidget(self.indeed_checkbox)
        
        self.linkedin_checkbox = QCheckBox("LinkedIn")
        self.linkedin_checkbox.setChecked(True)
        sites_layout.addWidget(self.linkedin_checkbox)
        
        search_layout.addLayout(sites_layout, 2, 1, 1, 3)
        
        # Pages per site
        search_layout.addWidget(QLabel("Pages per site:"), 3, 0)
        self.pages_spinbox = QSpinBox()
        self.pages_spinbox.setRange(1, 20)
        self.pages_spinbox.setValue(3)
        search_layout.addWidget(self.pages_spinbox, 3, 1)
        
        # Detailed job count
        search_layout.addWidget(QLabel("Detailed jobs:"), 3, 2)
        self.detailed_spinbox = QSpinBox()
        self.detailed_spinbox.setRange(10, 100)
        self.detailed_spinbox.setValue(20)
        search_layout.addWidget(self.detailed_spinbox, 3, 3)
        
        # Search button
        button_layout = QHBoxLayout()
        self.search_button = QPushButton("Search Jobs")
        self.search_button.clicked.connect(self.search_jobs)
        button_layout.addWidget(self.search_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_search)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        search_layout.addLayout(button_layout, 4, 0, 1, 4)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label = QLabel("Ready")
        
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Title", "Company", "Location", "Date Posted", 
            "Salary", "Job Type", "Source"
        ])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        main_layout.addWidget(self.results_table, 1)
        
        self.setLayout(main_layout)
        
    def search_jobs(self):
        """Start the job search process."""
        # Validate inputs
        keywords = self.keywords_input.text().strip()
        location = self.location_input.text().strip()
        
        if not keywords:
            QMessageBox.warning(self, "Input Error", "Please enter keywords for job search.")
            return
            
        # Get selected job sites
        sites = []
        if self.seek_checkbox.isChecked():
            sites.append("seek")
        if self.indeed_checkbox.isChecked():
            sites.append("indeed")
        if self.linkedin_checkbox.isChecked():
            sites.append("linkedin")
            
        if not sites:
            QMessageBox.warning(self, "Input Error", "Please select at least one job site.")
            return
            
        # Clear previous results
        self.results_table.setRowCount(0)
        self.jobs = []
        
        # Update UI state
        self.search_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting job search...")
        
        # Start worker thread
        try:
            self.worker = ScrapeJobsWorker(
                self.app,
                keywords,
                location,
                sites,
                self.pages_spinbox.value(),
                self.detailed_spinbox.value()
            )
            
            self.worker.progress.connect(self.update_progress)
            self.worker.job_found.connect(self.add_job_result)
            self.worker.completed.connect(self.search_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error starting job search: {str(e)}", exc_info=True)
            self.show_error(f"Failed to start job search: {str(e)}")
            self.search_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
    def stop_search(self):
        """Stop the current job search."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.progress_label.setText("Search stopped by user")
            self.search_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
    @pyqtSlot(str, int, int)
    def update_progress(self, message, current, total):
        """Update the progress bar and label.
        
        Args:
            message: Progress message
            current: Current progress value
            total: Total progress value
        """
        self.progress_label.setText(message)
        self.progress_bar.setValue(int(current / total * 100))
        
    @pyqtSlot(dict)
    def add_job_result(self, job):
        """Add a job to the results table.
        
        Args:
            job: Job data dictionary
        """
        # Store job data
        self.jobs.append(job)
        
        # Add to table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Set job title
        title_item = QTableWidgetItem(job.get('title', ''))
        title_item.setData(Qt.UserRole, job.get('id'))
        self.results_table.setItem(row, 0, title_item)
        
        # Set other columns
        self.results_table.setItem(row, 1, QTableWidgetItem(job.get('company', '')))
        self.results_table.setItem(row, 2, QTableWidgetItem(job.get('location', '')))
        self.results_table.setItem(row, 3, QTableWidgetItem(job.get('date_posted', '')))
        self.results_table.setItem(row, 4, QTableWidgetItem(job.get('salary', '')))
        self.results_table.setItem(row, 5, QTableWidgetItem(job.get('job_type', '')))
        self.results_table.setItem(row, 6, QTableWidgetItem(job.get('source', '')))
        
    @pyqtSlot(list)
    def search_completed(self, jobs):
        """Handle job search completion.
        
        Args:
            jobs: List of jobs found
        """
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        count = len(jobs)
        if count > 0:
            self.progress_label.setText(f"Found {count} jobs")
        else:
            self.progress_label.setText("No jobs found")
            
        self.worker = None
        
    @pyqtSlot(str)
    def show_error(self, error_message):
        """Display an error message.
        
        Args:
            error_message: Error message to display
        """
        self.logger.error(error_message)
        self.progress_label.setText(f"Error: {error_message}")
        
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        QMessageBox.critical(self, "Error", error_message)  
