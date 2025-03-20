"""
Database management for the job scraper application.
"""

import sqlite3
import time
import logging
import datetime
from .constants import Constants
from .utils import Utils

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manage database operations for job scraper."""
    
    def __init__(self, db_name=Constants.DB_NAME):
        """Initialize database connection."""
        self.db_name = db_name
        self.conn = None
        self.create_tables()
    
    def connect(self):
        """Connect to the database."""
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_name)
                self.conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
                return self.conn
            except sqlite3.Error as e:
                logger.error(f"Database connection error: {e}")
                raise
        return self.conn
    
    def create_tables(self):
        """Create tables if they don't exist."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Create jobs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                job_hash TEXT UNIQUE,
                title TEXT,
                company TEXT,
                location TEXT,
                source TEXT,
                link TEXT,
                description TEXT,
                match_score REAL,
                date_scraped TEXT,
                deadline TEXT,
                is_expired INTEGER DEFAULT 0
            )
            ''')
            
            # Upgrade existing tables to add new columns if they don't exist
            # This is a safe operation that allows for backward compatibility
            try:
                cursor.execute("SELECT deadline FROM jobs LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE jobs ADD COLUMN deadline TEXT")
                logger.info("Added deadline column to jobs table")
                
            try:
                cursor.execute("SELECT is_expired FROM jobs LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE jobs ADD COLUMN is_expired INTEGER DEFAULT 0")
                logger.info("Added is_expired column to jobs table")
            
            # Create applications table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY,
                job_id INTEGER,
                applied_date TEXT,
                status TEXT,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            ''')
            
            # Create skills table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_skills (
                id INTEGER PRIMARY KEY,
                job_id INTEGER,
                skill TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            ''')
            
            conn.commit()
            logger.debug("Database tables created/verified")
            
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def insert_job(self, job_data):
        """
        Insert or update a job in the database.
        
        Args:
            job_data (dict): Job data dictionary
            
        Returns:
            int: Job ID or None if error
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Create a hash identifier for the job
            if 'job_hash' not in job_data:
                job_hash = Utils.hash_identifier(f"{job_data.get('title', '')}_{job_data.get('company', '')}_{job_data.get('link', '')}")
            else:
                job_hash = job_data['job_hash']
            
            # Check if job exists by hash
            cursor.execute('SELECT id FROM jobs WHERE job_hash = ?', (job_hash,))
            existing_job = cursor.fetchone()
            
            if existing_job:
                # Update existing job
                job_id = existing_job['id']
                update_fields = []
                update_values = []
                
                for key, value in job_data.items():
                    if key not in ['id', 'job_hash'] and value is not None:
                        update_fields.append(f"{key} = ?")
                        update_values.append(value)
                
                if update_fields:
                    query = f"UPDATE jobs SET {', '.join(update_fields)} WHERE id = ?"
                    update_values.append(job_id)
                    cursor.execute(query, update_values)
                    conn.commit()
                
                return job_id
            else:
                # Insert new job
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Handle deadline if present
                deadline = job_data.get('deadline', None)
                
                cursor.execute('''
                INSERT INTO jobs (
                    job_hash, title, company, location, source, 
                    link, description, match_score, date_scraped, deadline,
                    is_expired
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_hash,
                    job_data.get('title', ''),
                    job_data.get('company', ''),
                    job_data.get('location', ''),
                    job_data.get('source', ''),
                    job_data.get('link', ''),
                    job_data.get('description', ''),
                    job_data.get('match_score', 0.0),
                    now,
                    deadline,
                    0  # Not expired by default
                ))
                conn.commit()
                
                # Get the inserted job ID
                cursor.execute('SELECT id FROM jobs WHERE job_hash = ?', (job_hash,))
                job_row = cursor.fetchone()
                
                if job_row:
                    job_id = job_row['id']
                    
                    # Add skills if provided
                    if 'missing_skills' in job_data and job_data['missing_skills']:
                        self.insert_job_skills(job_id, job_data['missing_skills'])
                    
                    return job_id
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error inserting job: {e}")
            if conn:
                conn.rollback()
            return None
    
    def insert_job_skills(self, job_id, skills):
        """Insert skills for a specific job."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            for skill in skills:
                cursor.execute('''
                INSERT INTO job_skills (job_id, skill)
                VALUES (?, ?)
                ''', (job_id, skill))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error inserting job skills: {e}")
            if conn:
                conn.rollback()
            return False
    
    def insert_application(self, job_id, status="applied", notes=""):
        """
        Insert an application record.
        
        Args:
            job_id (int): Job ID
            status (str): Application status
            notes (str): Notes about the application
            
        Returns:
            bool: Success or failure
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO applications (job_id, applied_date, status, notes)
            VALUES (?, ?, ?, ?)
            ''', (
                job_id,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                status,
                notes
            ))
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error inserting application: {e}")
            if conn:
                conn.rollback()
            return False
    
    def check_if_applied(self, job_id):
        """
        Check if already applied to a job.
        
        Args:
            job_id (int): Job ID
            
        Returns:
            bool: True if applied, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id FROM applications WHERE job_id = ?
            ''', (job_id,))
            
            result = cursor.fetchone()
            return result is not None
            
        except sqlite3.Error as e:
            logger.error(f"Error checking application: {e}")
            return False
    
    def get_all_jobs(self, with_description=False):
        """
        Get all jobs from database.
        
        Args:
            with_description (bool): Include job description or not
            
        Returns:
            list: List of job dictionaries
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            if with_description:
                cursor.execute('SELECT * FROM jobs ORDER BY date_scraped DESC')
            else:
                cursor.execute('SELECT id, title, company, location, source, link, match_score, date_scraped FROM jobs ORDER BY date_scraped DESC')
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving jobs: {e}")
            return []
    
    def get_job_by_id(self, job_id):
        """
        Get job by ID.
        
        Args:
            job_id (int): Job ID
            
        Returns:
            dict: Job data or None if not found
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            job = cursor.fetchone()
            
            if job:
                # Get skills for this job
                cursor.execute('SELECT skill FROM job_skills WHERE job_id = ?', (job_id,))
                skills = [row['skill'] for row in cursor.fetchall()]
                
                job_dict = dict(job)
                job_dict['skills'] = skills
                return job_dict
                
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving job: {e}")
            return None
    
    def search_jobs(self, query):
        """
        Search jobs by title, company, or location.
        
        Args:
            query (str): Search query
            
        Returns:
            list: List of job dictionaries matching the query
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            search_term = f"%{query}%"
            cursor.execute('''
            SELECT id, title, company, location, source, link, match_score, date_scraped 
            FROM jobs 
            WHERE title LIKE ? OR company LIKE ? OR location LIKE ?
            ORDER BY date_scraped DESC
            ''', (search_term, search_term, search_term))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error searching jobs: {e}")
            return []
    
    def delete_job(self, job_id):
        """
        Delete a job from database.
        
        Args:
            job_id (int): Job ID
            
        Returns:
            bool: Success or failure
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Delete associated records first
            cursor.execute('DELETE FROM job_skills WHERE job_id = ?', (job_id,))
            cursor.execute('DELETE FROM applications WHERE job_id = ?', (job_id,))
            
            # Delete the job
            cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
            conn.commit()
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting job: {e}")
            if conn:
                conn.rollback()
            return False
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
    
    def update_job_deadline(self, job_id, deadline):
        """
        Update the deadline for a job.
        
        Args:
            job_id (int): Job ID
            deadline (str): Deadline in YYYY-MM-DD format
            
        Returns:
            bool: Success or failure
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE jobs SET deadline = ? WHERE id = ?
            ''', (deadline, job_id))
            
            conn.commit()
            logger.info(f"Updated deadline for job {job_id} to {deadline}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating job deadline: {e}")
            if conn:
                conn.rollback()
            return False
    
    def mark_job_as_expired(self, job_id):
        """
        Mark a job as expired.
        
        Args:
            job_id (int): Job ID
            
        Returns:
            bool: Success or failure
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE jobs SET is_expired = 1 WHERE id = ?
            ''', (job_id,))
            
            conn.commit()
            logger.info(f"Marked job {job_id} as expired")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error marking job as expired: {e}")
            if conn:
                conn.rollback()
            return False
    
    def check_and_mark_expired_jobs(self):
        """
        Check for jobs with passed deadlines and mark them as expired.
        
        Returns:
            int: Number of jobs marked as expired
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            today = datetime.date.today().strftime("%Y-%m-%d")
            
            # Find jobs with deadlines that have passed and not yet marked as expired
            cursor.execute('''
            SELECT id FROM jobs 
            WHERE deadline IS NOT NULL 
            AND deadline < ? 
            AND is_expired = 0
            ''', (today,))
            
            expired_jobs = cursor.fetchall()
            
            # Mark each job as expired
            for job in expired_jobs:
                job_id = job['id']
                self.mark_job_as_expired(job_id)
            
            num_expired = len(expired_jobs)
            if num_expired > 0:
                logger.info(f"Marked {num_expired} job(s) as expired")
            
            return num_expired
            
        except sqlite3.Error as e:
            logger.error(f"Error checking for expired jobs: {e}")
            return 0
    
    def delete_expired_jobs(self, older_than_days=30):
        """
        Delete expired jobs that have been expired for more than the specified number of days.
        
        Args:
            older_than_days (int): Number of days since expiration to keep jobs before deletion
            
        Returns:
            int: Number of jobs deleted
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Calculate the cutoff date
            cutoff_date = (datetime.date.today() - datetime.timedelta(days=older_than_days)).strftime("%Y-%m-%d")
            
            # Get expired jobs with deadlines older than the cutoff date
            cursor.execute('''
            SELECT id FROM jobs 
            WHERE is_expired = 1 
            AND deadline < ?
            ''', (cutoff_date,))
            
            jobs_to_delete = cursor.fetchall()
            
            # Delete job skills first (foreign key constraint)
            for job in jobs_to_delete:
                job_id = job['id']
                cursor.execute('DELETE FROM job_skills WHERE job_id = ?', (job_id,))
            
            # Delete jobs
            cursor.execute('''
            DELETE FROM jobs 
            WHERE is_expired = 1 
            AND deadline < ?
            ''', (cutoff_date,))
            
            conn.commit()
            
            num_deleted = len(jobs_to_delete)
            if num_deleted > 0:
                logger.info(f"Deleted {num_deleted} expired job(s)")
            
            return num_deleted
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting expired jobs: {e}")
            if conn:
                conn.rollback()
            return 0 