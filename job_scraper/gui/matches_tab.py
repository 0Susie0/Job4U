"""Matches tab for the job scraper GUI."""

import os
import logging
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QProgressBar,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QComboBox
)

from job_scraper.gui.workers import MatchJobsWorker
from job_scraper.gui.dialogs import JobDetailsDialog, CoverLetterDialog
from job_scraper.config.constants import Constants


class MatchesTab(QWidget):
    """Matches tab for job matching with resumes."""
    
    def __init__(self, app):
        """Initialize the matches tab."""
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.worker = None
        self.resume_data = None
        self.matched_jobs = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout()
        
        # Resume info
        resume_group = QGroupBox("Resume")
        resume_layout = QGridLayout()
        
        resume_layout.addWidget(QLabel("Name:"), 0, 0)
        self.resume_name_label = QLabel("No resume selected")
        resume_layout.addWidget(self.resume_name_label, 0, 1)
        
        resume_layout.addWidget(QLabel("Status:"), 1, 0)
        self.status_label = QLabel("Ready")
        resume_layout.addWidget(self.status_label, 1, 1)
        
        resume_group.setLayout(resume_layout)
        main_layout.addWidget(resume_group)
        
        # Match controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Top matches:"))
        self.top_n_spinbox = QSpinBox()
        self.top_n_spinbox.setRange(5, 50)
        self.top_n_spinbox.setValue(10)
        controls_layout.addWidget(self.top_n_spinbox)
        
        self.match_button = QPushButton("Match Jobs")
        self.match_button.clicked.connect(self.match_jobs)
        self.match_button.setEnabled(False)
        controls_layout.addWidget(self.match_button)
        
        main_layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Match Score", "Title", "Company", "Location", "Posted", "Source"
        ])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # Double-click to view job details
        self.results_table.itemDoubleClicked.connect(self.view_job_details)
        
        main_layout.addWidget(self.results_table, 1)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.view_button = QPushButton("View Job Details")
        self.view_button.clicked.connect(self.view_selected_job)
        self.view_button.setEnabled(False)
        action_layout.addWidget(self.view_button)
        
        self.generate_letter_button = QPushButton("Generate Cover Letter")
        self.generate_letter_button.clicked.connect(self.generate_cover_letter)
        self.generate_letter_button.setEnabled(False)
        action_layout.addWidget(self.generate_letter_button)
        
        main_layout.addLayout(action_layout)
        
        self.setLayout(main_layout)
        
    def start_matching(self, resume_data):
        """Start the job matching process with the given resume data.
        
        Args:
            resume_data: Resume data dictionary
        """
        if not resume_data:
            QMessageBox.warning(self, "No Resume Data", "No resume data available for matching.")
            return
            
        self.resume_data = resume_data
        self.resume_name_label.setText(resume_data.get('name', 'Unknown'))
        
        # Enable match button
        self.match_button.setEnabled(True)
        
        # Start matching immediately
        self.match_jobs()
        
    def match_jobs(self):
        """Match jobs with the loaded resume."""
        if not self.resume_data:
            QMessageBox.warning(self, "No Resume Data", "Please load a resume first.")
            return
            
        # Clear previous results
        self.results_table.setRowCount(0)
        self.matched_jobs = []
        
        # Update UI
        self.status_label.setText("Matching jobs...")
        self.progress_bar.setVisible(True)
        self.match_button.setEnabled(False)
        self.view_button.setEnabled(False)
        self.generate_letter_button.setEnabled(False)
        
        # Start worker thread
        try:
            self.worker = MatchJobsWorker(
                self.app,
                self.resume_data,
                self.top_n_spinbox.value()
            )
            
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.matching_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error starting job matching: {str(e)}", exc_info=True)
            self.show_error(f"Failed to start job matching: {str(e)}")
            
    @pyqtSlot(str)
    def update_progress(self, message):
        """Update the progress status.
        
        Args:
            message: Progress message
        """
        self.status_label.setText(message)
        
    @pyqtSlot(list)
    def matching_completed(self, matched_jobs):
        """Handle job matching completion.
        
        Args:
            matched_jobs: List of matched job dictionaries
        """
        self.matched_jobs = matched_jobs
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.match_button.setEnabled(True)
        
        # Populate table
        self.results_table.setRowCount(len(matched_jobs))
        
        for i, job in enumerate(matched_jobs):
            # Match score
            match_score = job.get('match_score', 0)
            score_item = QTableWidgetItem(f"{match_score:.1f}%")
            score_item.setData(Qt.UserRole, job.get('id'))
            self.results_table.setItem(i, 0, score_item)
            
            # Other columns
            self.results_table.setItem(i, 1, QTableWidgetItem(job.get('title', '')))
            self.results_table.setItem(i, 2, QTableWidgetItem(job.get('company', '')))
            self.results_table.setItem(i, 3, QTableWidgetItem(job.get('location', '')))
            self.results_table.setItem(i, 4, QTableWidgetItem(job.get('date_posted', '')))
            self.results_table.setItem(i, 5, QTableWidgetItem(job.get('source', '')))
            
        # Sort by match score
        self.results_table.sortItems(0, Qt.DescendingOrder)
        
        # Update status
        count = len(matched_jobs)
        if count > 0:
            self.status_label.setText(f"Found {count} matching jobs")
            self.view_button.setEnabled(True)
            self.generate_letter_button.setEnabled(True)
        else:
            self.status_label.setText("No matching jobs found")
            self.view_button.setEnabled(False)
            self.generate_letter_button.setEnabled(False)
            
        self.worker = None
        
    @pyqtSlot(str)
    def show_error(self, error_message):
        """Display an error message.
        
        Args:
            error_message: Error message to display
        """
        self.logger.error(error_message)
        self.status_label.setText(f"Error: {error_message}")
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.match_button.setEnabled(True)
        
        QMessageBox.critical(self, "Error", error_message)
        
    def get_selected_job(self):
        """Get the currently selected job.
        
        Returns:
            Selected job dictionary or None if no job is selected
        """
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a job first.")
            return None
            
        # Get the job ID from the first column's UserRole data
        row = selected_items[0].row()
        job_id = self.results_table.item(row, 0).data(Qt.UserRole)
        
        # Find the job in the matched jobs list
        for job in self.matched_jobs:
            if job.get('id') == job_id:
                return job
                
        return None
        
    def view_selected_job(self):
        """View details of the selected job."""
        job = self.get_selected_job()
        if job:
            self.view_job_details(job)
            
    def view_job_details(self, job_or_item):
        """View job details in a dialog.
        
        Args:
            job_or_item: Job dictionary or QTableWidgetItem
        """
        if isinstance(job_or_item, QTableWidgetItem):
            job = self.get_selected_job()
            if not job:
                return
        else:
            job = job_or_item
            
        dialog = JobDetailsDialog(job, self)
        dialog.exec_()
        
    def generate_cover_letter(self):
        """Generate a cover letter for the selected job."""
        job = self.get_selected_job()
        if not job:
            return
            
        if not self.resume_data:
            QMessageBox.warning(self, "No Resume Data", "Resume data is missing.")
            return
            
        dialog = CoverLetterDialog(self.app, self, self.resume_data, job)
        
        if dialog.exec_() == dialog.Accepted:
            cover_letter = dialog.get_cover_letter()
            
            if cover_letter:
                QMessageBox.information(
                    self,
                    "Cover Letter Generated",
                    "Cover letter has been generated and saved to the job."
                )
                
                # Update the job in the database with the cover letter
                self.app.db_manager.update_job(job.get('id'), {'cover_letter': cover_letter}) 