#!/usr/bin/env python3
"""
UI helper functions for job scraper GUI.
These functions help reduce code duplication in UI creation.
"""

from PyQt5.QtWidgets import (QLabel, QLineEdit, QPushButton, QFileDialog, 
                            QSpinBox, QCheckBox, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt


def create_file_selector(label_text, placeholder_text, file_types, parent=None):
    """Create a file selector with browse button.
    
    Args:
        label_text: Text for the dialog label
        placeholder_text: Placeholder text for the input field
        file_types: File types filter string (e.g., "PDF Files (*.pdf)")
        parent: Parent widget for the file dialog
        
    Returns:
        Tuple of (layout, input_field, browse_button)
    """
    layout = QHBoxLayout()
    
    input_field = QLineEdit()
    input_field.setPlaceholderText(placeholder_text)
    input_field.setReadOnly(True)
    
    browse_button = QPushButton("Browse...")
    
    # Connect button to file dialog
    def browse_file():
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            label_text,
            "",
            file_types
        )
        if file_path:
            input_field.setText(file_path)
    
    browse_button.clicked.connect(browse_file)
    
    layout.addWidget(input_field, 3)
    layout.addWidget(browse_button, 1)
    
    return layout, input_field, browse_button


def setup_table(column_names, stretch_column=0, selection_behavior=QTableWidget.SelectRows, 
                selection_mode=QTableWidget.SingleSelection):
    """Create and set up a table widget with specified columns.
    
    Args:
        column_names: List of column header names
        stretch_column: Index of column to stretch (default: 0)
        selection_behavior: Selection behavior for the table
        selection_mode: Selection mode for the table
        
    Returns:
        Configured QTableWidget instance
    """
    table = QTableWidget()
    table.setColumnCount(len(column_names))
    table.setHorizontalHeaderLabels(column_names)
    
    if stretch_column >= 0:
        table.horizontalHeader().setSectionResizeMode(stretch_column, QHeaderView.Stretch)
    
    table.setSelectionBehavior(selection_behavior)
    table.setSelectionMode(selection_mode)
    
    return table


def create_job_item(value, is_expired=False, color_by_match=None):
    """Create a table item for job data with appropriate styling.
    
    Args:
        value: Text value for the item
        is_expired: Whether this job is expired (colors text red)
        color_by_match: If provided, a match percentage to color-code the background
        
    Returns:
        Configured QTableWidgetItem
    """
    item = QTableWidgetItem(str(value))
    
    if is_expired:
        item.setForeground(Qt.red)
    
    if color_by_match is not None:
        match_score = float(color_by_match)
        if match_score >= 80:
            item.setBackground(Qt.green)
        elif match_score >= 60:
            item.setBackground(Qt.yellow)
        elif match_score >= 40:
            item.setBackground(Qt.lightGray)
    
    return item


def show_message(parent, title, message, icon=QMessageBox.Information):
    """Show a message box with specified parameters.
    
    Args:
        parent: Parent widget
        title: Window title
        message: Message text
        icon: Message box icon (default: Information)
        
    Returns:
        Result from QMessageBox
    """
    return QMessageBox.information(parent, title, message, icon)


def show_confirmation(parent, title, message):
    """Show a confirmation dialog with Yes/No options.
    
    Args:
        parent: Parent widget
        title: Window title
        message: Message text
        
    Returns:
        True if user clicked Yes, False otherwise
    """
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    
    return reply == QMessageBox.Yes


def create_spinner(minimum, maximum, default, label=None):
    """Create a spinner with specified parameters.
    
    Args:
        minimum: Minimum value
        maximum: Maximum value
        default: Default value
        label: Optional label text
        
    Returns:
        QSpinBox or tuple of (layout, QSpinBox) if label is provided
    """
    spinner = QSpinBox()
    spinner.setMinimum(minimum)
    spinner.setMaximum(maximum)
    spinner.setValue(default)
    
    if label:
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label))
        layout.addWidget(spinner)
        return layout, spinner
    
    return spinner


def format_job_details(job):
    """Format job details into a readable text representation.
    
    Args:
        job: Job dictionary
        
    Returns:
        Formatted text for display
    """
    details_text = f"Job Details\n{'='*50}\n\n"
    details_text += f"Title: {job.get('title', 'Unknown')}\n"
    details_text += f"Company: {job.get('company', 'Unknown')}\n"
    details_text += f"Location: {job.get('location', 'Unknown')}\n"
    details_text += f"Source: {job.get('source', 'Unknown')}\n"
    details_text += f"Date Scraped: {job.get('date_scraped', 'Unknown')}\n"
    details_text += f"Deadline: {job.get('deadline', 'Unknown')}\n"
    details_text += f"Status: {'Expired' if job.get('is_expired', 0) == 1 else 'Active'}\n"
    details_text += f"URL: {job.get('link', 'Unknown')}\n\n"
    
    details_text += f"Job Description\n{'-'*50}\n\n"
    details_text += job.get('description', 'No description available')
    
    return details_text


def format_resume_results(resume_data):
    """Format resume parsing results into a readable text representation.
    
    Args:
        resume_data: Dictionary with parsed resume data
        
    Returns:
        Formatted text for display
    """
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
    
    return result_text 