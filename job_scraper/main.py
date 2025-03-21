#!/usr/bin/env python3
"""
Main entry point for the Job4U application.
"""

import sys
import argparse
import logging

from .app import Job4UApp


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Job4U")
    
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


def run_headless(app, args):
    """Run the application in headless mode.
    
    Args:
        app: Job4UApp instance
        args: Command line arguments
    """
    logger = logging.getLogger("job_scraper")
    
    if args.check_expired:
        logger.info("Checking for expired jobs...")
        count = app.check_expired_jobs()
        logger.info(f"Found {count} expired jobs")
        
    if args.delete_expired:
        logger.info(f"Deleting expired jobs older than {args.days} days...")
        count = app.delete_expired_jobs(args.days)
        logger.info(f"Deleted {count} expired jobs")


def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Initialize application
    app = Job4UApp()
    
    try:
        if args.headless:
            run_headless(app, args)
        else:
            # Run GUI application
            app.run()
            
    except Exception as e:
        app.logger.error(f"Error running application: {str(e)}", exc_info=True)
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 