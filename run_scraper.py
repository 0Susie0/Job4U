#!/usr/bin/env python3
"""
Entry point script for the job scraper application.
"""

import sys
from job_scraper.main import main

if __name__ == "__main__":
    # Add headless flag if not explicitly provided
    if "--headless" not in sys.argv:
        sys.argv.append("--headless")
    sys.exit(main())    