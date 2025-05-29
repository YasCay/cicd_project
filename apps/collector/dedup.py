"""De-duplication logic for Reddit posts using Bloom filter and SQLite."""

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from pybloom_live import BloomFilter

logger = logging.getLogger(__name__)


class PostDeduplicator:
    """Handles de-duplication of Reddit posts using Bloom filter and SQLite cache."""

    def __init__(self, db_path: str = "/data/dupes.db", capacity: int = 100000):
        """
        Initialize the deduplicator.

        Args:
            db_path: Path to SQLite database for persistent storage
            capacity: Expected number of posts for Bloom filter sizing
        """
        self.db_path = db_path
        self.capacity = capacity
        self.error_rate = 0.1  # 10% false positive rate for Bloom filter

        # Initialize Bloom filter
        self.bloom_filter = BloomFilter(capacity=capacity, error_rate=self.error_rate)

        # Initialize SQLite database
        self._init_database()

        # Load existing hashes into Bloom filter
        self._load_existing_hashes()

        logger.info(
            f"Deduplicator initialized with capacity={capacity}, "
            f"error_rate={self.error_rate}, db_path={db_path}"
        )

    def _init_database(self) -> None:
        """Initialize SQLite database with posts table."""
        try:
            # Ensure directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create posts table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    post_id TEXT PRIMARY KEY,
                    content_hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    subreddit TEXT NOT NULL,
                    created_utc INTEGER NOT NULL,
                    first_seen_utc INTEGER NOT NULL
                )
            """
            )

            # Create index on content_hash for faster lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_content_hash
                ON posts(content_hash)
            """
            )

            conn.commit()
            conn.close()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_existing_hashes(self) -> None:
        """Load existing content hashes into Bloom filter."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT content_hash FROM posts")
            rows = cursor.fetchall()

            for row in rows:
                self.bloom_filter.add(row[0])

            conn.close()

            logger.info(f"Loaded {len(rows)} existing hashes into Bloom filter")

        except Exception as e:
            logger.warning(f"Failed to load existing hashes: {e}")

    def _generate_content_hash(self, post: Dict[str, Any]) -> str:
        """
        Generate SHA-256 hash of post content for deduplication.

        Args:
            post: Dictionary containing post data

        Returns:
            SHA-256 hash as hexadecimal string
        """
        # Combine title and content for hashing
        content = f"{post.get('title', '')}\n{post.get('content', '')}"
        content_bytes = content.encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    def is_duplicate(self, post: Dict[str, Any]) -> bool:
        """
        Check if a post is a duplicate.

        Args:
            post: Dictionary containing post data

        Returns:
            True if post is a duplicate, False otherwise
        """
        content_hash = self._generate_content_hash(post)

        # First check Bloom filter for fast negative lookup
        if content_hash not in self.bloom_filter:
            return False

        # If Bloom filter says it might exist, check SQLite for definitive answer
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM posts WHERE content_hash = ?", (content_hash,)
            )
            count = cursor.fetchone()[0]

            conn.close()

            return count > 0

        except Exception as e:
            logger.error(f"Error checking for duplicate in database: {e}")
            # On error, assume it's not a duplicate to avoid losing posts
            return False

    def add_post(self, post: Dict[str, Any]) -> None:
        """
        Add a post to the deduplication cache.

        Args:
            post: Dictionary containing post data
        """
        content_hash = self._generate_content_hash(post)

        # Add to Bloom filter
        self.bloom_filter.add(content_hash)

        # Add to SQLite database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO posts
                (post_id, content_hash, title, subreddit, created_utc, first_seen_utc)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    post.get("post_id", ""),
                    content_hash,
                    post.get("title", ""),
                    post.get("subreddit", ""),
                    post.get("created_utc", 0),
                    post.get("created_utc", 0),  # Use post creation time as first seen
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error adding post to database: {e}")

    def deduplicate_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate posts from a list.

        Args:
            posts: List of post dictionaries

        Returns:
            List of unique posts with duplicates removed
        """
        unique_posts = []
        duplicates_found = 0

        for post in posts:
            if not self.is_duplicate(post):
                self.add_post(post)
                unique_posts.append(post)
            else:
                duplicates_found += 1

        logger.info(
            f"Deduplication complete: {len(unique_posts)} unique posts, "
            f"{duplicates_found} duplicates removed"
        )

        return unique_posts

    def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.

        Returns:
            Dictionary with statistics about stored posts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total posts
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]

            # Posts by subreddit
            cursor.execute(
                """
                SELECT subreddit, COUNT(*)
                FROM posts
                GROUP BY subreddit
                ORDER BY COUNT(*) DESC
            """
            )
            by_subreddit = dict(cursor.fetchall())

            # Oldest and newest posts
            cursor.execute("SELECT MIN(first_seen_utc), MAX(first_seen_utc) FROM posts")
            oldest, newest = cursor.fetchone()

            conn.close()

            return {
                "total_posts": total_posts,
                "by_subreddit": by_subreddit,
                "oldest_post": oldest,
                "newest_post": newest,
                "bloom_filter_capacity": self.capacity,
                "bloom_filter_error_rate": self.error_rate,
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
