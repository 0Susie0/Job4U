"""Applications tab for the job scraper GUI."""

import os
import logging
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QProgressBar,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QFileDialog
)

from job_scraper.gui.workers import LoadJobsWorker, ApplyToJobWorker, CheckExpiredJobsWorker, DeleteExpiredJobsWorker
from job_scraper.gui.dialogs import JobDetailsDialog, CoverLetterDialog
from job_scraper.config.constants import Constants


class ApplicationsTab(QWidget):
    """Applications tab for managing job applications."""
    
    def __init__(self, app):
        """Initialize the applications tab."""
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.worker = None
        self.jobs = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout()
        
        # Filter controls
        filter_group = QGroupBox("Filter Jobs")
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "All Jobs",
            "New",
            "Applied",
            "Rejected",
            "Interview",
            "Offer",
            "Expired"
        ])
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addWidget(QLabel("Min Match Score:"))
        self.min_score_combo = QComboBox()
        self.min_score_combo.addItems([
            "All",
            "60%+",
            "70%+",
            "80%+",
            "90%+"
        ])
        filter_layout.addWidget(self.min_score_combo)
        
        self.load_button = QPushButton("Load Jobs")
        self.load_button.clicked.connect(self.load_jobs)
        filter_layout.addWidget(self.load_button)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # Status and progress
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(status_layout)
        
        # Jobs table
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(7)
        self.jobs_table.setHorizontalHeaderLabels([
            "Title", "Company", "Status", "Match Score", "Posted", "Applied", "Source"
        ])
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.jobs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Double-click to view job details
        self.jobs_table.itemDoubleClicked.connect(self.view_job_details)
        
        main_layout.addWidget(self.jobs_table, 1)
        
        # Job actions
        job_actions_group = QGroupBox("Job Actions")
        job_actions_layout = QHBoxLayout()
        
        self.view_button = QPushButton("View Job")
        self.view_button.clicked.connect(self.view_selected_job)
        self.view_button.setEnabled(False)
        job_actions_layout.addWidget(self.view_button)
        
        self.edit_letter_button = QPushButton("Edit Cover Letter")
        self.edit_letter_button.clicked.connect(self.edit_cover_letter)
        self.edit_letter_button.setEnabled(False)
        job_actions_layout.addWidget(self.edit_letter_button)
        
        self.apply_button = QPushButton("Apply to Job")
        self.apply_button.clicked.connect(self.apply_to_job)
        self.apply_button.setEnabled(False)
        job_actions_layout.addWidget(self.apply_button)
        
        self.set_status_combo = QComboBox()
        self.set_status_combo.addItems([
            "Set Status",
            "New",
            "Applied",
            "Rejected",
            "Interview",
            "Offer",
            "Expired"
        ])
        self.set_status_combo.setCurrentIndex(0)
        self.set_status_combo.currentIndexChanged.connect(self.update_job_status)
        job_actions_layout.addWidget(self.set_status_combo)
        
        job_actions_group.setLayout(job_actions_layout)
        main_layout.addWidget(job_actions_group)
        
        # Maintenance actions
        maintenance_layout = QHBoxLayout()
        
        self.check_expired_button = QPushButton("Check Expired Jobs")
        self.check_expired_button.clicked.connect(self.check_expired_jobs)
        maintenance_layout.addWidget(self.check_expired_button)
        
        self.delete_expired_button = QPushButton("Delete Expired Jobs")
        self.delete_expired_button.clicked.connect(self.delete_expired_jobs)
        maintenance_layout.addWidget(self.delete_expired_button)
        
        main_layout.addLayout(maintenance_layout)
        
        self.setLayout(main_layout)
        
    def load_jobs(self):
        """Load jobs from the database with the current filters."""
        # Get filter values
        status = None
        if self.status_combo.currentText() != "All Jobs":
            status = self.status_combo.currentText()
            
        min_score = 0
        score_text = self.min_score_combo.currentText()
        if score_text != "All":
            min_score = int(score_text.strip("%+"))
            
        # Clear previous results
        self.jobs_table.setRowCount(0)
        self.jobs = []
        
        # Update UI
        self.status_label.setText("Loading jobs...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.view_button.setEnabled(False)
        self.edit_letter_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        
        # Start worker thread
        try:
            self.worker = LoadJobsWorker(
                self.app,
                status,
                min_score
            )
            
            self.worker.progress.connect(self.update_progress)
            self.worker.job_loaded.connect(self.add_job)
            self.worker.completed.connect(self.loading_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error loading jobs: {str(e)}", exc_info=True)
            self.show_error(f"Failed to load jobs: {str(e)}")
            
    @pyqtSlot(str)
    def update_progress(self, message):
        """Update the progress status.
        
        Args:
            message: Progress message
        """
        self.status_label.setText(message)
        
    @pyqtSlot(dict)
    def add_job(self, job):
        """Add a job to the table.
        
        Args:
            job: Job data dictionary
        """
        # Store job data
        self.jobs.append(job)
        
        # Add to table
        row = self.jobs_table.rowCount()
        self.jobs_table.insertRow(row)
        
        # Set job title
        title_item = QTableWidgetItem(job.get('title', ''))
        title_item.setData(Qt.UserRole, job.get('id'))
        self.jobs_table.setItem(row, 0, title_item)
        
        # Set other columns
        self.jobs_table.setItem(row, 1, QTableWidgetItem(job.get('company', '')))
        self.jobs_table.setItem(row, 2, QTableWidgetItem(job.get('status', 'New')))
        
        # Match score
        match_score = job.get('match_score', 0)
        score_text = f"{match_score:.1f}%" if match_score else "N/A"
        self.jobs_table.setItem(row, 3, QTableWidgetItem(score_text))
        
        self.jobs_table.setItem(row, 4, QTableWidgetItem(job.get('date_posted', '')))
        self.jobs_table.setItem(row, 5, QTableWidgetItem(job.get('date_applied', '')))
        self.jobs_table.setItem(row, 6, QTableWidgetItem(job.get('source', '')))
        
    @pyqtSlot(list)
    def loading_completed(self, jobs):
        """Handle job loading completion.
        
        Args:
            jobs: List of loaded job dictionaries
        """
        # Update UI
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        
        # Update status
        count = len(jobs)
        if count > 0:
            self.status_label.setText(f"Loaded {count} jobs")
            self.view_button.setEnabled(True)
            self.edit_letter_button.setEnabled(True)
            self.apply_button.setEnabled(True)
        else:
            self.status_label.setText("No jobs found")
            
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
        self.load_button.setEnabled(True)
        
        QMessageBox.critical(self, "Error", error_message)
        
    def get_selected_job(self):
        """Get the currently selected job.
        
        Returns:
            Selected job dictionary or None if no job is selected
        """
        selected_items = self.jobs_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a job first.")
            return None
            
        # Get the job ID from the first column's UserRole data
        row = selected_items[0].row()
        job_id = self.jobs_table.item(row, 0).data(Qt.UserRole)
        
        # Find the job in the jobs list
        for job in self.jobs:
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
        
    def edit_cover_letter(self):
        """Edit the cover letter for the selected job."""
        job = self.get_selected_job()
        if not job:
            return
            
        # Get resume data
        resume_settings = self.app.config_manager.get_resume_settings()
        default_resume_path = resume_settings.get('default_resume_path', '')
        
        if not default_resume_path or not os.path.exists(default_resume_path):
            reply = QMessageBox.question(
                self,
                "No Default Resume",
                "No default resume is set. Would you like to select a resume file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                resume_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select Resume",
                    "",
                    "Resume Files (*.pdf *.docx *.doc *.txt);;All Files (*)"
                )
                
                if not resume_path:
                    return
                    
                # Parse the resume
                try:
                    resume_data = self.app.resume_parser.parse_resume(resume_path)
                    resume_data['filename'] = os.path.basename(resume_path)
                except Exception as e:
                    self.logger.error(f"Error parsing resume: {str(e)}", exc_info=True)
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to parse resume: {str(e)}"
                    )
                    return
            else:
                return
        else:
            try:
                resume_data = self.app.resume_parser.parse_resume(default_resume_path)
                resume_data['filename'] = os.path.basename(default_resume_path)
            except Exception as e:
                self.logger.error(f"Error parsing resume: {str(e)}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to parse default resume: {str(e)}"
                )
                return
                
        # Open cover letter dialog
        dialog = CoverLetterDialog(self.app, self, resume_data, job)
        
        if dialog.exec_() == dialog.Accepted:
            cover_letter = dialog.get_cover_letter()
            
            if cover_letter:
                # Update the job in the database with the cover letter
                self.app.db_manager.update_job(job.get('id'), {'cover_letter': cover_letter})
                
                QMessageBox.information(
                    self,
                    "Cover Letter Saved",
                    "Cover letter has been saved to the job."
                )
                
    def apply_to_job(self):
        """Apply to the selected job."""
        job = self.get_selected_job()
        if not job:
            return
            
        # Check if job has a cover letter
        if not job.get('cover_letter'):
            reply = QMessageBox.question(
                self,
                "No Cover Letter",
                "This job doesn't have a cover letter. Would you like to create one now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.edit_cover_letter()
                
                # Get the updated job
                job = self.get_selected_job()
                if not job or not job.get('cover_letter'):
                    return
            else:
                return
                
        # Generate cover letter file
        cover_letter_dir = os.path.join(os.path.expanduser("~"), ".job_scraper", "cover_letters")
        os.makedirs(cover_letter_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        company = job.get('company', 'company').replace(' ', '_')
        cover_letter_path = os.path.join(
            cover_letter_dir,
            f"cover_letter_{company}_{timestamp}.txt"
        )
        
        # Update UI
        self.status_label.setText("Applying to job...")
        self.progress_bar.setVisible(True)
        self.apply_button.setEnabled(False)
        
        # Start worker thread
        try:
            self.worker = ApplyToJobWorker(
                self.app,
                job,
                cover_letter_path
            )
            
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.application_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error applying to job: {str(e)}", exc_info=True)
            self.show_error(f"Failed to apply to job: {str(e)}")
            
    @pyqtSlot(bool)
    def application_completed(self, success):
        """Handle job application completion.
        
        Args:
            success: Whether the application was successful
        """
        # Update UI
        self.progress_bar.setVisible(False)
        self.apply_button.setEnabled(True)
        
        if success:
            self.status_label.setText("Job application process completed")
            
            # Update job status
            job = self.get_selected_job()
            if job:
                job['status'] = 'Applied'
                job['date_applied'] = datetime.now().strftime('%Y-%m-%d')
                
                # Update UI and database
                self.update_job_in_table(job)
                self.app.db_manager.update_job(job.get('id'), {
                    'status': 'Applied',
                    'date_applied': job['date_applied']
                })
        else:
            self.status_label.setText("Job application process failed")
            
        self.worker = None
        
    def update_job_status(self, index):
        """Update the status of the selected job.
        
        Args:
            index: Index of the selected status in the combo box
        """
        if index == 0:  # "Set Status" placeholder
            return
            
        job = self.get_selected_job()
        if not job:
            self.set_status_combo.setCurrentIndex(0)
            return
            
        status = self.set_status_combo.currentText()
        
        # Update job data
        job['status'] = status
        
        # If status is "Applied", set the application date
        if status == 'Applied' and not job.get('date_applied'):
            job['date_applied'] = datetime.now().strftime('%Y-%m-%d')
            
        # Update UI and database
        self.update_job_in_table(job)
        update_data = {'status': status}
        if status == 'Applied' and not job.get('date_applied'):
            update_data['date_applied'] = job['date_applied']
            
        self.app.db_manager.update_job(job.get('id'), update_data)
        
        # Reset status combo
        self.set_status_combo.setCurrentIndex(0)
        
    def update_job_in_table(self, job):
        """Update the job in the table.
        
        Args:
            job: Job data dictionary
        """
        # Find the row for this job
        for row in range(self.jobs_table.rowCount()):
            job_id = self.jobs_table.item(row, 0).data(Qt.UserRole)
            if job_id == job.get('id'):
                # Update status column
                self.jobs_table.item(row, 2).setText(job.get('status', 'New'))
                
                # Update applied date column
                self.jobs_table.item(row, 5).setText(job.get('date_applied', ''))
                break
                
    def check_expired_jobs(self):
        """Check for expired jobs."""
        # Update UI
        self.status_label.setText("Checking for expired jobs...")
        self.progress_bar.setVisible(True)
        self.check_expired_button.setEnabled(False)
        
        # Start worker thread
        try:
            self.worker = CheckExpiredJobsWorker(self.app)
            
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.check_expired_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error checking expired jobs: {str(e)}", exc_info=True)
            self.show_error(f"Failed to check expired jobs: {str(e)}")
            
    @pyqtSlot(int)
    def check_expired_completed(self, count):
        """Handle expired job check completion.
        
        Args:
            count: Number of expired jobs found
        """
        # Update UI
        self.progress_bar.setVisible(False)
        self.check_expired_button.setEnabled(True)
        
        self.status_label.setText(f"Found {count} expired jobs")
        
        if count > 0:
            reply = QMessageBox.question(
                self,
                "Expired Jobs",
                f"Found {count} expired jobs. Would you like to reload the job list?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.load_jobs()
                
        self.worker = None
        
    def delete_expired_jobs(self):
        """Delete expired jobs."""
        # Get delete days from settings
        app_settings = self.app.config_manager.get_application_settings()
        days = app_settings.get('expire_days', 30)
        
        reply = QMessageBox.question(
            self,
            "Delete Expired Jobs",
            f"Are you sure you want to delete jobs that expired more than {days} days ago?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Update UI
        self.status_label.setText(f"Deleting expired jobs older than {days} days...")
        self.progress_bar.setVisible(True)
        self.delete_expired_button.setEnabled(False)
        
        # Start worker thread
        try:
            self.worker = DeleteExpiredJobsWorker(self.app, days)
            
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.delete_expired_completed)
            self.worker.error.connect(self.show_error)
            
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error deleting expired jobs: {str(e)}", exc_info=True)
            self.show_error(f"Failed to delete expired jobs: {str(e)}")
            
    @pyqtSlot(int)
    def delete_expired_completed(self, count):
        """Handle expired job deletion completion.
        
        Args:
            count: Number of expired jobs deleted
        """
        # Update UI
        self.progress_bar.setVisible(False)
        self.delete_expired_button.setEnabled(True)
        
        self.status_label.setText(f"Deleted {count} expired jobs")
        
        if count > 0:
            reply = QMessageBox.question(
                self,
                "Expired Jobs Deleted",
                f"Deleted {count} expired jobs. Would you like to reload the job list?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.load_jobs()
                
        self.worker = None 