#!/usr/bin/env python3
"""
Main window for the job scraper GUI application.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar, QMessageBox,
    QAction, QToolBar, QMenu, QMenuBar, QDialog,
    QFileDialog, QApplication
)

from job_scraper.gui.search_tab import SearchTab
from job_scraper.gui.resume_tab import ResumeTab
from job_scraper.gui.matches_tab import MatchesTab
from job_scraper.gui.applications_tab import ApplicationsTab
from job_scraper.gui.settings_tab import SettingsTab
from job_scraper.gui.dialogs import AboutDialog
from job_scraper.config.constants import Constants


class MainWindow(QMainWindow):
    """Main window for the job scraper GUI application."""
    
    def __init__(self, app):
        """Initialize the main window.
        
        Args:
            app: Application instance
        """
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        
    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Job4U")
        self.setMinimumSize(900, 700)
        
        # Center the window
        screen_size = QApplication.desktop().screenGeometry()
        self.resize(min(screen_size.width() - 100, 1200),
                   min(screen_size.height() - 100, 800))
        self.move(screen_size.width() // 2 - self.width() // 2,
                 screen_size.height() // 2 - self.height() // 2)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Add tabs
        self.search_tab = SearchTab(self.app)
        self.tabs.addTab(self.search_tab, "Job Search")
        
        self.resume_tab = ResumeTab(self.app)
        self.tabs.addTab(self.resume_tab, "Resume")
        
        self.matches_tab = MatchesTab(self.app)
        self.tabs.addTab(self.matches_tab, "Job Matches")
        
        self.applications_tab = ApplicationsTab(self.app)
        self.tabs.addTab(self.applications_tab, "Applications")
        
        self.settings_tab = SettingsTab(self.app)
        self.tabs.addTab(self.settings_tab, "Settings")
        
    def _setup_menubar(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Jobs menu
        jobs_menu = menubar.addMenu("&Jobs")
        
        search_action = QAction("&Search Jobs", self)
        search_action.setStatusTip("Search for jobs")
        search_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        jobs_menu.addAction(search_action)
        
        check_expired_action = QAction("Check &Expired Jobs", self)
        check_expired_action.setStatusTip("Check for expired job listings")
        check_expired_action.triggered.connect(self.check_expired_jobs)
        jobs_menu.addAction(check_expired_action)
        
        delete_expired_action = QAction("&Delete Expired Jobs", self)
        delete_expired_action.setStatusTip("Delete expired job listings")
        delete_expired_action.triggered.connect(self.delete_expired_jobs)
        jobs_menu.addAction(delete_expired_action)
        
        # Resume menu
        resume_menu = menubar.addMenu("&Resume")
        
        parse_resume_action = QAction("&Parse Resume", self)
        parse_resume_action.setStatusTip("Parse a resume file")
        parse_resume_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        resume_menu.addAction(parse_resume_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("Show the application's About box")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
    def _setup_statusbar(self):
        """Set up the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
    def check_expired_jobs(self):
        """Check for expired job listings."""
        try:
            count = self.app.check_expired_jobs()
            QMessageBox.information(
                self,
                "Expired Jobs",
                f"Found {count} expired job listings."
            )
        except Exception as e:
            self.logger.error(f"Error checking expired jobs: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to check expired jobs: {str(e)}"
            )
            
    def delete_expired_jobs(self):
        """Delete expired job listings."""
        try:
            days = 30  # Default to 30 days
            count = self.app.delete_expired_jobs(days)
            QMessageBox.information(
                self,
                "Deleted Jobs",
                f"Deleted {count} expired job listings older than {days} days."
            )
        except Exception as e:
            self.logger.error(f"Error deleting expired jobs: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete expired jobs: {str(e)}"
            )
            
    def show_about_dialog(self):
        """Show the about dialog."""
        dialog = AboutDialog(self)
        dialog.exec_()
        
    def closeEvent(self, event):
        """Handle window close event.
        
        Args:
            event: Close event
        """
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
            
class AboutDialog(QDialog):
    """About dialog."""
    
    def __init__(self, parent=None):
        """Initialize the about dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("About Job4U")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Application name
        app_name = QLabel("Job4U")
        app_name.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        app_name.setFont(font)
        layout.addWidget(app_name)
        
        # Version
        version = QLabel(f"Version: {Constants.VERSION}")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # Description
        description = QLabel(
            "An automated tool for job searching, resume matching, "
            "and application tracking with AI-powered cover letter generation."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # Copyright
        copyright_label = QLabel("© 2025 Job4U Team")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        self.setLayout(layout)


def main():
    """Main entry point for the GUI application."""
    import sys
    from PyQt5.QtWidgets import QApplication
    from job_scraper.app import Job4UApp
    
    # Create the application
    qt_app = QApplication(sys.argv)
    qt_app.setStyle('Fusion')  # Use Fusion style for consistent look across platforms
    
    # Create the job scraper app instance
    scraper_app = Job4UApp()
    
    # Create main window
    main_window = MainWindow(scraper_app)
    main_window.show()
    
    # Run the application
    return qt_app.exec_()


if __name__ == "__main__":
    sys.exit(main()) 