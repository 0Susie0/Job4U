"""
GUI package for job scraper application.
This package contains modules for the graphical user interface.
"""

from job_scraper.gui.main_window import MainWindow
from job_scraper.gui.search_tab import SearchTab
from job_scraper.gui.resume_tab import ResumeTab
from job_scraper.gui.matches_tab import MatchesTab
from job_scraper.gui.applications_tab import ApplicationsTab
from job_scraper.gui.settings_tab import SettingsTab
from job_scraper.gui.dialogs import (
    CoverLetterDialog, PasswordDialog, 
    ResumeViewDialog, JobDetailsDialog
)
from job_scraper.gui.workers import (
    ApplyToJobWorker, GenerateAICoverLetterWorker,
    ParseResumeWorker, MatchJobsWorker,
    ScrapeJobsWorker, LoadJobsWorker,
    CheckExpiredJobsWorker, DeleteExpiredJobsWorker
) 