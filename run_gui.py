#!/usr/bin/env python3
"""
Entry point script for the Job4U GUI application.
"""

import sys
from job_scraper.app import Job4UApp

if __name__ == "__main__":
    app = Job4UApp()
    sys.exit(app.run())   