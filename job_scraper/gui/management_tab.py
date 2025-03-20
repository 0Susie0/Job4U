#!/usr/bin/env python3
"""
Management tab for the job scraper GUI application.
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QGroupBox, QFormLayout,
                            QComboBox, QSpinBox, QProgressBar, QMessageBox,
                            QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QSplitter)
from PyQt5.QtCore import Qt

from job_scraper.gui.workers import LoadJobsWorker, CheckExpiredJobsWorker, DeleteExpiredJobsWorker

class ManagementTab:
    """Class to handle the job management tab functionality."""
    
    def __init__(self, parent, app):
        """Initialize management tab.
        
        Args:
            parent: Parent widget (main window)
            app: JobScraperApp instance
        """
        self.parent = parent
        self.app = app
        self.tab = QWidget()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface for the management tab."""
        # Main layout
        layout = QVBoxLayout(self.tab)
        
        # Create a splitter for top controls and bottom table
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # Top section - Controls and filters
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Filters and actions group
        filters_group = QGroupBox("Filters and Actions")
        filters_layout = QVBoxLayout(filters_group)
        
        # Filter controls
        filter_controls = QHBoxLayout()
        
        # Status filter
        filter_controls.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Jobs", "Active Jobs", "Expired Jobs", "Applied Jobs"])
        self.status_combo.currentIndexChanged.connect(self.filter_jobs)
        filter_controls.addWidget(self.status_combo)
        
        # Source filter
        filter_controls.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["All Sources", "Seek", "Indeed", "LinkedIn"])
        self.source_combo.currentIndexChanged.connect(self.filter_jobs)
        filter_controls.addWidget(self.source_combo)
        
        filter_controls.addStretch()
        
        # Refresh button
        refresh_button = QPushButton("Refresh Jobs")
        refresh_button.clicked.connect(self.refresh_jobs)
        filter_controls.addWidget(refresh_button)
        
        filters_layout.addLayout(filter_controls)
        
        # Actions section
        actions_layout = QHBoxLayout()
        
        # Expiration management
        expiration_layout = QHBoxLayout()
        expiration_layout.addWidget(QLabel("Expiration (days):"))
        
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(30)
        expiration_layout.addWidget(self.days_spin)
        
        # Show expiring button
        show_expiring_button = QPushButton("Show Expiring Jobs")
        show_expiring_button.clicked.connect(self.show_expiring_jobs)
        expiration_layout.addWidget(show_expiring_button)
        
        # Check expired button
        check_expired_button = QPushButton("Check Expired Jobs")
        check_expired_button.clicked.connect(self.check_expired_jobs)
        expiration_layout.addWidget(check_expired_button)
        
        # Delete expired button
        delete_expired_button = QPushButton("Delete Expired Jobs")
        delete_expired_button.clicked.connect(self.delete_expired_jobs)
        expiration_layout.addWidget(delete_expired_button)
        
        actions_layout.addLayout(expiration_layout)
        filters_layout.addLayout(actions_layout)
        
        # Progress indicators
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        filters_layout.addLayout(progress_layout)
        
        top_layout.addWidget(filters_group)
        
        # Statistics group
        stats_group = QGroupBox("Job Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        # Active jobs count
        self.active_jobs_label = QLabel("Active Jobs: 0")
        self.active_jobs_label.setStyleSheet("font-weight: bold; color: green;")
        stats_layout.addWidget(self.active_jobs_label)
        
        # Expired jobs count
        self.expired_jobs_label = QLabel("Expired Jobs: 0")
        self.expired_jobs_label.setStyleSheet("font-weight: bold; color: red;")
        stats_layout.addWidget(self.expired_jobs_label)
        
        # Applied jobs count
        self.applied_jobs_label = QLabel("Applied Jobs: 0")
        self.applied_jobs_label.setStyleSheet("font-weight: bold; color: blue;")
        stats_layout.addWidget(self.applied_jobs_label)
        
        top_layout.addWidget(stats_group)
        
        splitter.addWidget(top_widget)
        
        # Bottom section - Jobs table and details
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Create horizontal splitter for table and details
        horizontal_splitter = QSplitter(Qt.Horizontal)
        
        # Jobs table
        jobs_group = QGroupBox("Jobs")
        jobs_layout = QVBoxLayout(jobs_group)
        
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(7)
        self.jobs_table.setHorizontalHeaderLabels(["ID", "Title", "Company", "Location", "Source", "Date Scraped", "Deadline"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Stretch the Title column
        self.jobs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Stretch the Company column
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.jobs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.jobs_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.jobs_table.itemSelectionChanged.connect(self.job_selected)
        jobs_layout.addWidget(self.jobs_table)
        
        horizontal_splitter.addWidget(jobs_group)
        
        # Job details
        details_group = QGroupBox("Job Details")
        details_layout = QVBoxLayout(details_group)
        
        self.job_details = QTextEdit()
        self.job_details.setReadOnly(True)
        details_layout.addWidget(self.job_details)
        
        horizontal_splitter.addWidget(details_group)
        
        # Set initial sizes for horizontal splitter (60% table, 40% details)
        horizontal_splitter.setSizes([600, 400])
        
        bottom_layout.addWidget(horizontal_splitter)
        
        splitter.addWidget(bottom_widget)
        
        # Set initial sizes for vertical splitter (30% controls, 70% table)
        splitter.setSizes([300, 700])
        
        # Load jobs
        self.refresh_jobs()
    
    def refresh_jobs(self):
        """Refresh the jobs table with data from the database."""
        try:
            # Update UI
            self.progress_bar.setValue(10)
            self.status_label.setText("Loading jobs...")
            
            # Create worker thread
            self.load_worker = LoadJobsWorker(self.app.db_manager)
            
            # Connect signals
            self.load_worker.loaded.connect(self.jobs_loaded)
            self.load_worker.error.connect(self.jobs_load_error)
            
            # Start worker
            self.load_worker.start()
            
        except Exception as e:
            self.parent.logger.error(f"Error refreshing jobs: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Error loading jobs: {str(e)}")
    
    def jobs_loaded(self, jobs):
        """Handle successful job loading.
        
        Args:
            jobs (list): List of job dictionaries
        """
        self.jobs = jobs
        self.filter_jobs()
        
        # Update statistics
        active_count = sum(1 for job in jobs if not job.get('expired', False))
        expired_count = sum(1 for job in jobs if job.get('expired', False))
        applied_count = sum(1 for job in jobs if job.get('applied', False))
        
        self.active_jobs_label.setText(f"Active Jobs: {active_count}")
        self.expired_jobs_label.setText(f"Expired Jobs: {expired_count}")
        self.applied_jobs_label.setText(f"Applied Jobs: {applied_count}")
        
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Loaded {len(jobs)} jobs")
        
        self.parent.logger.info(f"Loaded {len(jobs)} jobs in management tab")
    
    def jobs_load_error(self, error_msg):
        """Handle error during job loading.
        
        Args:
            error_msg (str): Error message
        """
        self.parent.logger.error(f"Error loading jobs: {error_msg}")
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {error_msg}")
        QMessageBox.critical(self.parent, "Load Error", f"Error loading jobs: {error_msg}")
    
    def filter_jobs(self):
        """Filter jobs based on selected criteria."""
        if not hasattr(self, 'jobs'):
            return
        
        filtered_jobs = []
        status_filter = self.status_combo.currentText()
        source_filter = self.source_combo.currentText()
        
        for job in self.jobs:
            # Apply status filter
            if status_filter == "Active Jobs" and job.get('expired', False):
                continue
            elif status_filter == "Expired Jobs" and not job.get('expired', False):
                continue
            elif status_filter == "Applied Jobs" and not job.get('applied', False):
                continue
            
            # Apply source filter
            if source_filter != "All Sources":
                if job.get('source', '').lower() != source_filter.lower():
                    continue
            
            filtered_jobs.append(job)
        
        self.display_management_jobs(filtered_jobs)
    
    def display_management_jobs(self, jobs):
        """Display filtered jobs in the management table.
        
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
            
            # Source
            source_item = QTableWidgetItem(job.get('source', ''))
            self.jobs_table.setItem(row, 4, source_item)
            
            # Date Scraped
            date_scraped = job.get('date_scraped', '')
            date_item = QTableWidgetItem(date_scraped)
            self.jobs_table.setItem(row, 5, date_item)
            
            # Deadline
            deadline_item = QTableWidgetItem(job.get('deadline', 'Not specified'))
            self.jobs_table.setItem(row, 6, deadline_item)
            
            # Color code expired jobs
            if job.get('expired', False):
                for col in range(self.jobs_table.columnCount()):
                    item = self.jobs_table.item(row, col)
                    item.setBackground(Qt.lightGray)
            
            # Store the job data in first column item
            id_item.setData(Qt.UserRole, job)
        
        self.status_label.setText(f"Displayed {len(jobs)} jobs")
        self.parent.logger.info(f"Displayed {len(jobs)} jobs in management tab")
    
    def job_selected(self):
        """Handle job selection event."""
        selected_items = self.jobs_table.selectedItems()
        if not selected_items:
            self.job_details.clear()
            return
        
        # Get the job data from the first cell of the selected row
        row = selected_items[0].row()
        job_item = self.jobs_table.item(row, 0)
        selected_job = job_item.data(Qt.UserRole)
        
        # Display job details
        details = ""
        details += f"<h2>{selected_job.get('title', '')}</h2>"
        details += f"<p><b>Company:</b> {selected_job.get('company', '')}</p>"
        details += f"<p><b>Location:</b> {selected_job.get('location', '')}</p>"
        details += f"<p><b>Source:</b> {selected_job.get('source', '')}</p>"
        details += f"<p><b>Date Scraped:</b> {selected_job.get('date_scraped', '')}</p>"
        details += f"<p><b>Deadline:</b> {selected_job.get('deadline', 'Not specified')}</p>"
        
        if selected_job.get('expired', False):
            details += f"<p><b>Status:</b> <span style='color:red'>Expired</span></p>"
        elif selected_job.get('applied', False):
            details += f"<p><b>Status:</b> <span style='color:blue'>Applied</span></p>"
            details += f"<p><b>Application Date:</b> {selected_job.get('application_date', '')}</p>"
        else:
            details += f"<p><b>Status:</b> <span style='color:green'>Active</span></p>"
        
        if selected_job.get('match_score', 0) > 0:
            details += f"<p><b>Match Score:</b> {selected_job.get('match_score')}%</p>"
        
        if 'url' in selected_job and selected_job['url']:
            details += f"<p><b>URL:</b> <a href='{selected_job['url']}'>{selected_job['url']}</a></p>"
        
        if 'description' in selected_job and selected_job['description']:
            details += "<h3>Description</h3>"
            details += f"<div style='white-space: pre-wrap;'>{selected_job['description']}</div>"
        
        self.job_details.setHtml(details)
        
        self.parent.logger.info(f"Selected job: {selected_job.get('title')} at {selected_job.get('company')}")
    
    def check_expired_jobs(self):
        """Check for expired jobs based on deadline."""
        try:
            # Update UI
            self.progress_bar.setValue(10)
            self.status_label.setText("Checking for expired jobs...")
            
            # Create worker thread
            self.check_expired_worker = CheckExpiredJobsWorker(self.app.db_manager)
            
            # Connect signals
            self.check_expired_worker.progress.connect(self.update_check_progress)
            self.check_expired_worker.finished.connect(self.check_expired_finished)
            self.check_expired_worker.error.connect(self.check_expired_error)
            
            # Start worker
            self.check_expired_worker.start()
            
        except Exception as e:
            self.parent.logger.error(f"Error checking expired jobs: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Error checking expired jobs: {str(e)}")
    
    def update_check_progress(self, progress, status):
        """Update the UI with check expired jobs progress.
        
        Args:
            progress (int): Progress percentage (0-100)
            status (str): Status message
        """
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def check_expired_finished(self, expired_count):
        """Handle successful expired jobs check.
        
        Args:
            expired_count (int): Number of expired jobs found
        """
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Found {expired_count} expired jobs")
        
        # Refresh jobs to show updated status
        self.refresh_jobs()
        
        QMessageBox.information(
            self.parent, 
            "Expired Jobs Check", 
            f"Found {expired_count} expired jobs."
        )
    
    def check_expired_error(self, error_msg):
        """Handle error during expired jobs check.
        
        Args:
            error_msg (str): Error message
        """
        self.parent.logger.error(f"Error checking expired jobs: {error_msg}")
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {error_msg}")
        QMessageBox.critical(self.parent, "Check Error", f"Error checking expired jobs: {error_msg}")
    
    def show_expiring_jobs(self):
        """Show jobs that will expire within specified days."""
        days = self.days_spin.value()
        
        try:
            # Get jobs that will expire in the specified days
            expiring_jobs = self.app.db_manager.get_expiring_jobs(days)
            
            if not expiring_jobs:
                QMessageBox.information(
                    self.parent, 
                    "Expiring Jobs", 
                    f"No jobs found that will expire within {days} days."
                )
                return
            
            # Display expiring jobs
            self.display_management_jobs(expiring_jobs)
            
            self.status_label.setText(f"Found {len(expiring_jobs)} jobs expiring within {days} days")
            self.parent.logger.info(f"Displayed {len(expiring_jobs)} expiring jobs")
            
        except Exception as e:
            self.parent.logger.error(f"Error showing expiring jobs: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Error showing expiring jobs: {str(e)}")
    
    def delete_expired_jobs(self):
        """Delete expired jobs older than specified days."""
        days = self.days_spin.value()
        
        # Confirm deletion
        confirm = QMessageBox.question(
            self.parent,
            "Confirm Deletion",
            f"Are you sure you want to delete expired jobs older than {days} days?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        try:
            # Update UI
            self.progress_bar.setValue(10)
            self.status_label.setText(f"Deleting expired jobs older than {days} days...")
            
            # Create worker thread
            self.delete_expired_worker = DeleteExpiredJobsWorker(
                self.app.db_manager,
                days
            )
            
            # Connect signals
            self.delete_expired_worker.progress.connect(self.update_delete_progress)
            self.delete_expired_worker.finished.connect(self.delete_expired_finished)
            self.delete_expired_worker.error.connect(self.delete_expired_error)
            
            # Start worker
            self.delete_expired_worker.start()
            
        except Exception as e:
            self.parent.logger.error(f"Error deleting expired jobs: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Error deleting expired jobs: {str(e)}")
    
    def update_delete_progress(self, progress, status):
        """Update the UI with delete expired jobs progress.
        
        Args:
            progress (int): Progress percentage (0-100)
            status (str): Status message
        """
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def delete_expired_finished(self, deleted_count):
        """Handle successful expired jobs deletion.
        
        Args:
            deleted_count (int): Number of deleted jobs
        """
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Deleted {deleted_count} expired jobs")
        
        # Refresh jobs to show updated list
        self.refresh_jobs()
        
        QMessageBox.information(
            self.parent, 
            "Delete Expired Jobs", 
            f"Successfully deleted {deleted_count} expired jobs."
        )
    
    def delete_expired_error(self, error_msg):
        """Handle error during expired jobs deletion.
        
        Args:
            error_msg (str): Error message
        """
        self.parent.logger.error(f"Error deleting expired jobs: {error_msg}")
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {error_msg}")
        QMessageBox.critical(self.parent, "Delete Error", f"Error deleting expired jobs: {error_msg}")
    
    def get_tab(self):
        """Get the tab widget.
        
        Returns:
            The configured tab widget
        """
        return self.tab 