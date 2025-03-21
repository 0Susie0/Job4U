#!/usr/bin/env python3
"""
Settings tab for the job scraper GUI.
"""

import os
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QGroupBox, QTabWidget, QMessageBox, QComboBox, QFileDialog
)

from job_scraper.gui.dialogs import PasswordDialog
from job_scraper.config.constants import Constants


class SettingsTab(QWidget):
    """Settings tab for configuring the application."""
    
    def __init__(self, app):
        """Initialize the settings tab."""
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
        self._load_settings()
        
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout()
        
        # API settings
        api_group = QGroupBox("OpenAI API Settings")
        api_layout = QGridLayout()
        
        # API key
        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.api_key_status = QLabel("Not set")
        api_layout.addWidget(self.api_key_status, 0, 1)
        
        self.set_api_key_button = QPushButton("Set API Key")
        self.set_api_key_button.clicked.connect(self.set_api_key)
        api_layout.addWidget(self.set_api_key_button, 0, 2)
        
        # Model
        api_layout.addWidget(QLabel("AI Model:"), 1, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ])
        api_layout.addWidget(self.model_combo, 1, 1, 1, 2)
        
        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)
        
        # User info settings
        user_group = QGroupBox("User Information")
        user_layout = QGridLayout()
        
        # Name
        user_layout.addWidget(QLabel("Full Name:"), 0, 0)
        self.name_input = QLineEdit()
        user_layout.addWidget(self.name_input, 0, 1)
        
        # Email
        user_layout.addWidget(QLabel("Email:"), 1, 0)
        self.email_input = QLineEdit()
        user_layout.addWidget(self.email_input, 1, 1)
        
        # Phone
        user_layout.addWidget(QLabel("Phone:"), 2, 0)
        self.phone_input = QLineEdit()
        user_layout.addWidget(self.phone_input, 2, 1)
        
        # Location
        user_layout.addWidget(QLabel("Location:"), 3, 0)
        self.location_input = QLineEdit()
        user_layout.addWidget(self.location_input, 3, 1)
        
        user_group.setLayout(user_layout)
        main_layout.addWidget(user_group)
        
        # Resume settings
        resume_group = QGroupBox("Resume Settings")
        resume_layout = QGridLayout()
        
        # Default resume
        resume_layout.addWidget(QLabel("Default Resume:"), 0, 0)
        
        resume_path_layout = QHBoxLayout()
        self.resume_path_input = QLineEdit()
        resume_path_layout.addWidget(self.resume_path_input)
        
        self.browse_resume_button = QPushButton("Browse")
        self.browse_resume_button.clicked.connect(self.browse_resume)
        resume_path_layout.addWidget(self.browse_resume_button)
        
        resume_layout.addLayout(resume_path_layout, 0, 1)
        
        resume_group.setLayout(resume_layout)
        main_layout.addWidget(resume_group)
        
        # Job search settings
        search_group = QGroupBox("Job Search Settings")
        search_layout = QGridLayout()
        
        # Default job sites
        search_layout.addWidget(QLabel("Default Job Sites:"), 0, 0)
        sites_layout = QHBoxLayout()
        
        self.seek_checkbox = QCheckBox("Seek")
        sites_layout.addWidget(self.seek_checkbox)
        
        self.indeed_checkbox = QCheckBox("Indeed")
        sites_layout.addWidget(self.indeed_checkbox)
        
        self.linkedin_checkbox = QCheckBox("LinkedIn")
        sites_layout.addWidget(self.linkedin_checkbox)
        
        search_layout.addLayout(sites_layout, 0, 1)
        
        # Pages per site
        search_layout.addWidget(QLabel("Pages per site:"), 1, 0)
        self.pages_spinbox = QSpinBox()
        self.pages_spinbox.setRange(1, 20)
        self.pages_spinbox.setValue(3)
        search_layout.addWidget(self.pages_spinbox, 1, 1)
        
        # Job expiry
        search_layout.addWidget(QLabel("Expire jobs after (days):"), 2, 0)
        self.expire_days_spinbox = QSpinBox()
        self.expire_days_spinbox.setRange(1, 180)
        self.expire_days_spinbox.setValue(30)
        search_layout.addWidget(self.expire_days_spinbox, 2, 1)
        
        # Auto check expiry
        self.auto_check_expiry = QCheckBox("Check for expired jobs on startup")
        search_layout.addWidget(self.auto_check_expiry, 3, 0, 1, 2)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Selenium settings
        selenium_group = QGroupBox("Web Browser Settings")
        selenium_layout = QGridLayout()
        
        # Headless mode
        self.headless_checkbox = QCheckBox("Run in headless mode (no visible browser)")
        selenium_layout.addWidget(self.headless_checkbox, 0, 0, 1, 2)
        
        # Browser selection
        selenium_layout.addWidget(QLabel("Browser:"), 1, 0)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome"])  # Currently only Chrome is supported
        selenium_layout.addWidget(self.browser_combo, 1, 1)
        
        # Timeout
        selenium_layout.addWidget(QLabel("Timeout (seconds):"), 2, 0)
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(10, 120)
        self.timeout_spinbox.setValue(30)
        selenium_layout.addWidget(self.timeout_spinbox, 2, 1)
        
        # ChromeDriver path
        selenium_layout.addWidget(QLabel("Chrome Driver Path:"), 3, 0)
        driver_path_layout = QHBoxLayout()
        self.driver_path_input = QLineEdit()
        self.driver_path_input.setPlaceholderText("Leave empty to use ChromeDriverManager (recommended)")
        driver_path_layout.addWidget(self.driver_path_input)
        
        self.browse_driver_button = QPushButton("Browse")
        self.browse_driver_button.clicked.connect(self.browse_driver_path)
        driver_path_layout.addWidget(self.browse_driver_button)
        
        selenium_layout.addLayout(driver_path_layout, 3, 1)
        
        selenium_group.setLayout(selenium_layout)
        main_layout.addWidget(selenium_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def _load_settings(self):
        """Load settings from config manager."""
        try:
            # User settings
            user_info = self.app.config_manager.get_user_info()
            self.name_input.setText(user_info.get('name', ''))
            self.email_input.setText(user_info.get('email', ''))
            self.phone_input.setText(user_info.get('phone', ''))
            self.location_input.setText(user_info.get('location', ''))
            
            # Resume settings
            resume_config = self.app.config_manager.get_resume_settings()
            self.resume_path_input.setText(resume_config.get('default_resume_path', ''))
            
            # Job search settings
            search_config = self.app.config_manager.get_scraper_settings()
            self.pages_spinbox.setValue(search_config.get('pages_per_site', 3))
            
            # Check job sites
            job_sites = search_config.get('job_sites', [])
            self.seek_checkbox.setChecked('seek' in job_sites)
            self.indeed_checkbox.setChecked('indeed' in job_sites)
            self.linkedin_checkbox.setChecked('linkedin' in job_sites)
            
            # Job management settings
            job_mgmt = self.app.config_manager.get_application_settings()
            self.expire_days_spinbox.setValue(job_mgmt.get('expire_days', 30))
            self.auto_check_expiry.setChecked(job_mgmt.get('auto_check_expiry', True))
            
            # API settings
            api_settings = self.app.config_manager.get_ai_settings()
            self.api_key_status.setText(
                "Set" if api_settings.get('openai_api_key') else "Not set"
            )
            self.model_combo.setCurrentText(api_settings.get('model', 'gpt-3.5-turbo'))
            
            # Selenium settings
            selenium_settings = self.app.config_manager.get_selenium_settings()
            self.headless_checkbox.setChecked(selenium_settings.get('headless', True))
            self.timeout_spinbox.setValue(selenium_settings.get('timeout', 30))
            self.driver_path_input.setText(selenium_settings.get('chrome_driver_path', ''))
            
        except Exception as e:
            self.logger.error(f"Error loading settings: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load settings: {str(e)}"
            )
            
    def save_settings(self):
        """Save settings to config manager."""
        try:
            # User settings
            user_info = {
                'name': self.name_input.text(),
                'email': self.email_input.text(),
                'phone': self.phone_input.text(),
                'location': self.location_input.text()
            }
            self.app.config_manager.set_user_info(user_info)
            
            # Resume settings
            resume_config = {
                'default_resume_path': self.resume_path_input.text()
            }
            self.app.config_manager.set_resume_settings(resume_config)
            
            # Job search settings
            default_sites = []
            if self.seek_checkbox.isChecked():
                default_sites.append('seek')
            if self.indeed_checkbox.isChecked():
                default_sites.append('indeed')
            if self.linkedin_checkbox.isChecked():
                default_sites.append('linkedin')
                
            search_config = {
                'pages_per_site': self.pages_spinbox.value(),
                'job_sites': default_sites
            }
            self.app.config_manager.set_scraper_settings(search_config)
            
            # Job management settings
            job_mgmt = {
                'expire_days': self.expire_days_spinbox.value(),
                'auto_check_expiry': self.auto_check_expiry.isChecked()
            }
            self.app.config_manager.set_application_settings(job_mgmt)
            
            # AI settings
            ai_config = {
                'model': self.model_combo.currentText()
            }
            self.app.config_manager.set_ai_settings(ai_config)
            
            # Selenium settings
            selenium_config = {
                'headless': self.headless_checkbox.isChecked(),
                'timeout': self.timeout_spinbox.value(),
                'chrome_driver_path': self.driver_path_input.text().strip()
            }
            self.app.config_manager.set_selenium_settings(selenium_config)
            
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved successfully."
            )
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings: {str(e)}"
            )
            
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.app.config_manager.reset_to_defaults()
                self._load_settings()
                
                QMessageBox.information(
                    self,
                    "Settings Reset",
                    "Settings have been reset to defaults."
                )
                
            except Exception as e:
                self.logger.error(f"Error resetting settings: {str(e)}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to reset settings: {str(e)}"
                )
                
    def browse_resume(self):
        """Open file dialog to select default resume."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Resume",
            "",
            "Resume Files (*.pdf *.docx *.doc *.txt);;All Files (*)"
        )
        
        if file_path:
            self.resume_path_input.setText(file_path)
            
    def set_api_key(self):
        """Open dialog to set OpenAI API key."""
        dialog = PasswordDialog(
            self,
            "Set OpenAI API Key",
            "Enter your OpenAI API key:"
        )
        
        if dialog.exec_() == dialog.Accepted:
            api_key = dialog.get_password()
            
            if api_key:
                try:
                    self.app.config_manager.set_openai_api_key(api_key)
                    
                    self.api_key_status.setText("API key is set")
                    self.api_key_status.setStyleSheet("color: green")
                    
                    QMessageBox.information(
                        self,
                        "API Key Saved",
                        "OpenAI API key has been saved securely."
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error setting API key: {str(e)}", exc_info=True)
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to save API key: {str(e)}"
                    )
                    
    def browse_driver_path(self):
        """Open file dialog to select ChromeDriver path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ChromeDriver",
            "",
            "ChromeDriver Files (*.exe);;All Files (*)"
        )
        
        if file_path:
            self.driver_path_input.setText(file_path) 