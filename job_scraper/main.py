#!/usr/bin/env python3
"""
Main entry point for the Job Scraper and Applicator application.
"""

import os
import sys
import logging
import argparse
from PyQt5.QtWidgets import QApplication

from job_scraper.app import JobScraperApp
from job_scraper.gui.main_window import MainWindow


def setup_logging():
    """Set up logging for the application.
    
    Returns:
        Logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.expanduser("~"), ".job_scraper", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger("job_scraper")
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    log_file = os.path.join(log_dir, "job_scraper.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Job Scraper and Applicator")
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no GUI)"
    )
    
    parser.add_argument(
        "--check-expired",
        action="store_true",
        help="Check for expired jobs"
    )
    
    parser.add_argument(
        "--delete-expired",
        action="store_true",
        help="Delete expired jobs"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days for expired job deletion (default: 30)"
    )
    
    return parser.parse_args()


def run_gui():
    """Run the GUI application."""
    app = QApplication(sys.argv)
    
    # Initialize application
    job_scraper_app = JobScraperApp()
    
    # Create main window
    main_window = MainWindow(job_scraper_app)
    main_window.show()
    
    # Exit application when window is closed
    sys.exit(app.exec_())


def run_headless(args):
    """Run the application in headless mode.
    
    Args:
        args: Command line arguments
    """
    logger = logging.getLogger("job_scraper")
    job_scraper_app = JobScraperApp()
    
    if args.check_expired:
        logger.info("Checking for expired jobs...")
        count = job_scraper_app.check_expired_jobs()
        logger.info(f"Found {count} expired jobs")
        
    if args.delete_expired:
        logger.info(f"Deleting expired jobs older than {args.days} days...")
        count = job_scraper_app.delete_expired_jobs(args.days)
        logger.info(f"Deleted {count} expired jobs")


def main():
    """Main entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Job Scraper and Applicator")
    
    # Parse command line arguments
    args = parse_args()
    
    try:
        if args.headless:
            run_headless(args)
        else:
            run_gui()
    except Exception as e:
        logger.error(f"Error running application: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 