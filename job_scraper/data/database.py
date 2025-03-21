import os
import sqlite3
import logging
import threading
import queue
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from job_scraper.config.constants import Constants

class ConnectionPool:
    """Connection pool for SQLite connections."""
    
    def __init__(self, db_path: str, max_connections: int = 5):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database file
            max_connections: Maximum number of connections to maintain
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = queue.Queue(maxsize=max_connections)
        self.connections_created = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool.
        
        Returns:
            SQLite connection
        """
        try:
            # Try to get an existing connection
            return self.connections.get(block=False)
        except queue.Empty:
            # Create a new connection if under the limit
            with self.lock:
                if self.connections_created < self.max_connections:
                    conn = self._create_connection()
                    self.connections_created += 1
                    return conn
                    
            # Wait for a connection to be returned to the pool
            self.logger.debug("Connection pool exhausted, waiting for a connection")
            return self.connections.get()
            
    def return_connection(self, conn: sqlite3.Connection):
        """
        Return a connection to the pool.
        
        Args:
            conn: SQLite connection to return
        """
        try:
            self.connections.put(conn, block=False)
        except queue.Full:
            # Close the connection if the pool is full
            conn.close()
            with self.lock:
                self.connections_created -= 1
                
    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new SQLite connection.
        
        Returns:
            New SQLite connection
        """
        conn = sqlite3.connect(self.db_path)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Configure connection for better performance
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 10000")
        # Row factory for dictionary results
        conn.row_factory = sqlite3.Row
        return conn
        
    def close_all(self):
        """Close all connections in the pool."""
        with self.lock:
            while not self.connections.empty():
                try:
                    conn = self.connections.get(block=False)
                    conn.close()
                except queue.Empty:
                    break
                except Exception as e:
                    self.logger.error(f"Error closing connection: {str(e)}")
            self.connections_created = 0

class DatabaseManager:
    """Manager for database operations with optimized queries and connection pooling."""
    
    def __init__(self, db_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = db_path or Constants.DB_FILE
        self.ensure_db_dir()
        self.connection_pool = ConnectionPool(self.db_path)
        self.initialize_db()
        
    def __del__(self):
        """Cleanup connection pool on deletion."""
        try:
            self.connection_pool.close_all()
        except Exception as e:
            # Cannot log here as logger might be already destroyed
            pass
            
    def ensure_db_dir(self):
        """Ensure database directory exists."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating database directory: {str(e)}")
            raise
            
    def initialize_db(self):
        """Initialize database tables and indexes."""
        self.logger.info("Initializing database")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Create jobs table
            cursor.execute(Constants.DB_SCHEMA)
            
            # Create indexes for common queries
            self._create_index(cursor, 'jobs', 'expired', 'idx_jobs_status')
            self._create_index(cursor, 'jobs', 'date_scraped', 'idx_jobs_date_scraped')
            self._create_index(cursor, 'jobs', 'deadline', 'idx_jobs_deadline')
            self._create_index(cursor, 'jobs', 'match_score', 'idx_jobs_match')
            self._create_index(cursor, 'jobs', 'applied', 'idx_jobs_applied')
            self._create_index(cursor, 'jobs', 'source', 'idx_jobs_source')
            
            # Create compound indexes for common query patterns
            self._create_index(cursor, 'jobs', 'expired, match_score', 'idx_jobs_status_match')
            self._create_index(cursor, 'jobs', 'expired, date_scraped', 'idx_jobs_status_date')
            
            conn.commit()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            conn.rollback()
            raise
        finally:
            self.connection_pool.return_connection(conn)
            
    def _create_index(self, cursor, table: str, columns: str, index_name: str):
        """
        Create an index if it doesn't exist.
        
        Args:
            cursor: SQLite cursor
            table: Table name
            columns: Columns to index
            index_name: Name of the index
        """
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({columns})")
        except Exception as e:
            self.logger.error(f"Error creating index {index_name}: {str(e)}")
            
    def add_job(self, job_data: Dict[str, Any]) -> int:
        """
        Add a job to the database.
        
        Args:
            job_data: Job data
            
        Returns:
            Job ID
        """
        self.logger.debug(f"Adding job: {job_data.get('title')} at {job_data.get('company')}")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Extract fields from job_data
            title = job_data.get('title', '')
            company = job_data.get('company', '')
            location = job_data.get('location', '')
            description = job_data.get('description', '')
            url = job_data.get('url', '')
            source = job_data.get('source', '')
            deadline = job_data.get('deadline', None)
            match_percentage = job_data.get('match_percentage', None)
            
            # Check if job already exists
            cursor.execute(
                "SELECT id FROM jobs WHERE url = ?",
                (url,)
            )
            existing_job = cursor.fetchone()
            
            if existing_job:
                job_id = existing_job['id']
                self.logger.debug(f"Job already exists with ID {job_id}")
                
                # Update existing job with new data
                cursor.execute(
                    """
                    UPDATE jobs SET 
                        title = ?, company = ?, location = ?, description = ?,
                        source = ?, deadline = ?, match_percentage = ?
                    WHERE id = ?
                    """,
                    (title, company, location, description, source, deadline, match_percentage, job_id)
                )
            else:
                # Insert new job
                cursor.execute(
                    """
                    INSERT INTO jobs 
                    (title, company, location, description, url, source, date_scraped, deadline, match_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (title, company, location, description, url, source, 
                     datetime.now().isoformat(), deadline, match_percentage)
                )
                job_id = cursor.lastrowid
                
            conn.commit()
            return job_id
        except Exception as e:
            self.logger.error(f"Error adding job: {str(e)}")
            conn.rollback()
            return -1
        finally:
            self.connection_pool.return_connection(conn)
            
    def add_jobs_batch(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Add multiple jobs in a single transaction.
        
        Args:
            jobs: List of job data dictionaries
            
        Returns:
            Number of jobs added
        """
        if not jobs:
            return 0
            
        self.logger.debug(f"Adding {len(jobs)} jobs in batch")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            count = 0
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            for job_data in jobs:
                title = job_data.get('title', '')
                company = job_data.get('company', '')
                location = job_data.get('location', '')
                description = job_data.get('description', '')
                url = job_data.get('url', '')
                source = job_data.get('source', '')
                deadline = job_data.get('deadline', None)
                match_percentage = job_data.get('match_percentage', None)
                
                # Check if job already exists
                cursor.execute(
                    "SELECT id FROM jobs WHERE url = ?",
                    (url,)
                )
                existing_job = cursor.fetchone()
                
                if existing_job:
                    job_id = existing_job['id']
                    
                    # Update existing job with new data
                    cursor.execute(
                        """
                        UPDATE jobs SET 
                            title = ?, company = ?, location = ?, description = ?,
                            source = ?, deadline = ?, match_percentage = ?
                        WHERE id = ?
                        """,
                        (title, company, location, description, source, deadline, match_percentage, job_id)
                    )
                else:
                    # Insert new job
                    cursor.execute(
                        """
                        INSERT INTO jobs 
                        (title, company, location, description, url, source, date_scraped, deadline, match_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (title, company, location, description, url, source, 
                         datetime.now().isoformat(), deadline, match_percentage)
                    )
                    count += 1
                    
            conn.commit()
            self.logger.debug(f"Added {count} new jobs in batch")
            return count
        except Exception as e:
            self.logger.error(f"Error adding jobs batch: {str(e)}")
            conn.rollback()
            return 0
        finally:
            self.connection_pool.return_connection(conn)
            
    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job data or None if not found
        """
        self.logger.debug(f"Getting job with ID {job_id}")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            job = cursor.fetchone()
            
            if job:
                return dict(job)
            return None
        except Exception as e:
            self.logger.error(f"Error getting job {job_id}: {str(e)}")
            return None
        finally:
            self.connection_pool.return_connection(conn)
            
    def get_jobs(self, 
                status: Optional[str] = None, 
                min_match: Optional[float] = None,
                source: Optional[str] = None,
                applied: Optional[bool] = None,
                limit: int = 100, 
                offset: int = 0,
                order_by: str = "date_scraped DESC") -> Tuple[List[Dict[str, Any]], int]:
        """
        Get jobs with pagination and filtering.
        
        Args:
            status: Filter by job status
            min_match: Minimum match percentage
            source: Filter by source
            applied: Filter by applied status
            limit: Maximum number of jobs to return
            offset: Offset for pagination
            order_by: Column and direction to sort by
            
        Returns:
            Tuple of (list of jobs, total count)
        """
        self.logger.debug(f"Getting jobs with filters: status={status}, min_match={min_match}, limit={limit}, offset={offset}")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Build query with filters
            query = "SELECT * FROM jobs WHERE 1=1"
            count_query = "SELECT COUNT(*) FROM jobs WHERE 1=1"
            params = []
            
            if status:
                query += " AND expired = ?"
                count_query += " AND expired = ?"
                params.append(status)
                
            if min_match is not None:
                query += " AND match_score >= ?"
                count_query += " AND match_score >= ?"
                params.append(min_match)
                
            if source:
                query += " AND source = ?"
                count_query += " AND source = ?"
                params.append(source)
                
            if applied is not None:
                query += " AND applied = ?"
                count_query += " AND applied = ?"
                params.append(1 if applied else 0)
                
            # Add order and pagination
            query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            
            # Execute count query first
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Execute main query with pagination
            cursor.execute(query, params + [limit, offset])
            jobs = [dict(row) for row in cursor.fetchall()]
            
            return jobs, total_count
        except Exception as e:
            self.logger.error(f"Error getting jobs: {str(e)}")
            return [], 0
        finally:
            self.connection_pool.return_connection(conn)
            
    def update_job_status(self, job_id: int, status: str) -> bool:
        """
        Update a job's status.
        
        Args:
            job_id: Job ID
            status: New status
            
        Returns:
            True if successful
        """
        self.logger.debug(f"Updating job {job_id} status to {status}")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET expired = ? WHERE id = ?",
                (status, job_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating job status: {str(e)}")
            conn.rollback()
            return False
        finally:
            self.connection_pool.return_connection(conn)
            
    def mark_job_applied(self, job_id: int) -> bool:
        """
        Mark a job as applied.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if successful
        """
        self.logger.debug(f"Marking job {job_id} as applied")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs 
                SET applied = 1, expired = ?, application_date = ?
                WHERE id = ?
                """,
                (Constants.JOB_STATUS["EXPIRED"], datetime.now().isoformat(), job_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error marking job as applied: {str(e)}")
            conn.rollback()
            return False
        finally:
            self.connection_pool.return_connection(conn)
            
    def get_job_match_stats(self) -> Dict[str, Any]:
        """
        Get job match statistics.
        
        Returns:
            Dictionary with match statistics
        """
        self.logger.debug("Getting job match statistics")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get total counts by match category
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN match_score >= ? THEN 1 ELSE 0 END) as excellent,
                    SUM(CASE WHEN match_score >= ? AND match_score < ? THEN 1 ELSE 0 END) as good,
                    SUM(CASE WHEN match_score >= ? AND match_score < ? THEN 1 ELSE 0 END) as fair,
                    SUM(CASE WHEN match_score < ? THEN 1 ELSE 0 END) as poor
                FROM jobs
                WHERE match_score IS NOT NULL
                """,
                (
                    Constants.MATCH_THRESHOLDS["EXCELLENT"],
                    Constants.MATCH_THRESHOLDS["GOOD"], Constants.MATCH_THRESHOLDS["EXCELLENT"],
                    Constants.MATCH_THRESHOLDS["FAIR"], Constants.MATCH_THRESHOLDS["GOOD"],
                    Constants.MATCH_THRESHOLDS["FAIR"]
                )
            )
            
            result = dict(cursor.fetchone())
            
            # Get counts by status
            cursor.execute(
                """
                SELECT expired, COUNT(*) as count
                FROM jobs
                GROUP BY expired
                """
            )
            
            status_counts = {row['expired']: row['count'] for row in cursor.fetchall()}
            result['status_counts'] = status_counts
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting job match stats: {str(e)}")
            return {}
        finally:
            self.connection_pool.return_connection(conn)
            
    def check_expired_jobs(self) -> int:
        """
        Check for expired jobs and update their status.
        
        Returns:
            Number of expired jobs found
        """
        self.logger.debug("Checking for expired jobs")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Update expired jobs
            cursor.execute(
                """
                UPDATE jobs
                SET expired = ?
                WHERE deadline < ? AND expired = ?
                """,
                (Constants.JOB_STATUS["EXPIRED"], now, Constants.JOB_STATUS["ACTIVE"])
            )
            
            count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"Found {count} expired jobs")
            return count
        except Exception as e:
            self.logger.error(f"Error checking expired jobs: {str(e)}")
            conn.rollback()
            return 0
        finally:
            self.connection_pool.return_connection(conn)
            
    def get_expiring_jobs(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get jobs that are expiring soon.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of expiring jobs
        """
        self.logger.debug(f"Getting jobs expiring in {days} days")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()
            future = (now + timedelta(days=days)).isoformat()
            
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE deadline BETWEEN ? AND ?
                AND expired = ?
                ORDER BY deadline ASC
                """,
                (now.isoformat(), future, Constants.JOB_STATUS["ACTIVE"])
            )
            
            jobs = [dict(row) for row in cursor.fetchall()]
            self.logger.debug(f"Found {len(jobs)} jobs expiring soon")
            return jobs
        except Exception as e:
            self.logger.error(f"Error getting expiring jobs: {str(e)}")
            return []
        finally:
            self.connection_pool.return_connection(conn)
            
    def delete_expired_jobs(self, days: int = 30) -> int:
        """
        Delete expired jobs older than the specified number of days.
        
        Args:
            days: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        self.logger.debug(f"Deleting expired jobs older than {days} days")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute(
                """
                DELETE FROM jobs
                WHERE expired = ? AND date_scraped < ?
                """,
                (Constants.JOB_STATUS["EXPIRED"], cutoff_date)
            )
            
            count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"Deleted {count} expired jobs")
            return count
        except Exception as e:
            self.logger.error(f"Error deleting expired jobs: {str(e)}")
            conn.rollback()
            return 0
        finally:
            self.connection_pool.return_connection(conn)
            
    def vacuum_database(self) -> bool:
        """
        Run VACUUM to optimize database storage.
        
        Returns:
            True if successful
        """
        self.logger.debug("Running VACUUM on database")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            return True
        except Exception as e:
            self.logger.error(f"Error running VACUUM: {str(e)}")
            return False
        finally:
            self.connection_pool.return_connection(conn)
            
    def update_job_matches(self, job_matches: List[Tuple[int, float]]) -> int:
        """
        Update match percentages for multiple jobs.
        
        Args:
            job_matches: List of (job_id, match_percentage) tuples
            
        Returns:
            Number of jobs updated
        """
        if not job_matches:
            return 0
            
        self.logger.debug(f"Updating match percentages for {len(job_matches)} jobs")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            count = 0
            
            conn.execute("BEGIN TRANSACTION")
            
            for job_id, match_percentage in job_matches:
                cursor.execute(
                    "UPDATE jobs SET match_score = ? WHERE id = ?",
                    (match_percentage, job_id)
                )
                count += cursor.rowcount
                
            conn.commit()
            self.logger.debug(f"Updated {count} job matches")
            return count
        except Exception as e:
            self.logger.error(f"Error updating job matches: {str(e)}")
            conn.rollback()
            return 0
        finally:
            self.connection_pool.return_connection(conn)
            
    def search_jobs(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for jobs by keyword.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching jobs
        """
        self.logger.debug(f"Searching jobs with query: {query}")
        conn = self.connection_pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Use SQLite FTS if available, otherwise use LIKE
            search_term = f"%{query}%"
            
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE title LIKE ? OR company LIKE ? OR description LIKE ?
                ORDER BY match_score DESC, date_scraped DESC
                LIMIT ?
                """,
                (search_term, search_term, search_term, limit)
            )
            
            jobs = [dict(row) for row in cursor.fetchall()]
            self.logger.debug(f"Found {len(jobs)} jobs matching query")
            return jobs
        except Exception as e:
            self.logger.error(f"Error searching jobs: {str(e)}")
            return []
        finally:
            self.connection_pool.return_connection(conn) 