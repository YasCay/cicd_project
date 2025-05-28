"""Tests for deduplication logic."""

import os
import tempfile
from unittest.mock import patch

from apps.collector.dedup import PostDeduplicator


class TestPostDeduplicator:
    """Test cases for PostDeduplicator."""

    def test_init_with_temp_db(self):
        """Test initialization with temporary database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path, capacity=1000)

            assert dedup.db_path == db_path
            assert dedup.capacity == 1000
            assert dedup.error_rate == 0.1
            assert os.path.exists(db_path)

    def test_content_hash_generation(self):
        """Test content hash generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            post1 = {"title": "Bitcoin rises", "content": "BTC up 5%"}
            post2 = {"title": "Bitcoin rises", "content": "BTC up 5%"}
            post3 = {"title": "Bitcoin falls", "content": "BTC down 3%"}

            hash1 = dedup._generate_content_hash(post1)
            hash2 = dedup._generate_content_hash(post2)
            hash3 = dedup._generate_content_hash(post3)

            # Same content should produce same hash
            assert hash1 == hash2
            # Different content should produce different hash
            assert hash1 != hash3
            # Hash should be SHA-256 (64 hex characters)
            assert len(hash1) == 64
            assert all(c in "0123456789abcdef" for c in hash1)

    def test_duplicate_detection(self):
        """Test duplicate detection logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            post = {
                "post_id": "test123",
                "title": "Test Bitcoin Post",
                "content": "This is test content",
                "subreddit": "Bitcoin",
                "created_utc": 1640995200,
            }

            # Initially should not be duplicate
            assert not dedup.is_duplicate(post)

            # Add post
            dedup.add_post(post)

            # Now should be detected as duplicate
            assert dedup.is_duplicate(post)

    def test_deduplicate_posts_list(self):
        """Test deduplicating a list of posts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            posts = [
                {
                    "post_id": "post1",
                    "title": "Bitcoin rises",
                    "content": "BTC up 5%",
                    "subreddit": "Bitcoin",
                    "created_utc": 1640995200,
                },
                {
                    "post_id": "post2",
                    "title": "Ethereum news",
                    "content": "ETH news",
                    "subreddit": "ethereum",
                    "created_utc": 1640995260,
                },
                {
                    "post_id": "post3",
                    "title": "Bitcoin rises",  # Duplicate content
                    "content": "BTC up 5%",
                    "subreddit": "Bitcoin",
                    "created_utc": 1640995320,
                },
            ]

            unique_posts = dedup.deduplicate_posts(posts)

            # Should have 2 unique posts (post3 is duplicate of post1)
            assert len(unique_posts) == 2
            assert unique_posts[0]["post_id"] == "post1"
            assert unique_posts[1]["post_id"] == "post2"

    def test_get_stats(self):
        """Test getting deduplication statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            posts = [
                {
                    "post_id": "post1",
                    "title": "Bitcoin news",
                    "content": "BTC content",
                    "subreddit": "Bitcoin",
                    "created_utc": 1640995200,
                },
                {
                    "post_id": "post2",
                    "title": "Ethereum news",
                    "content": "ETH content",
                    "subreddit": "ethereum",
                    "created_utc": 1640995260,
                },
            ]

            dedup.deduplicate_posts(posts)
            stats = dedup.get_stats()

            assert stats["total_posts"] == 2
            assert "Bitcoin" in stats["by_subreddit"]
            assert "ethereum" in stats["by_subreddit"]
            assert stats["by_subreddit"]["Bitcoin"] == 1
            assert stats["by_subreddit"]["ethereum"] == 1
            assert stats["bloom_filter_capacity"] == dedup.capacity

    def test_persistence_across_instances(self):
        """Test that deduplication data persists across instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"

            # First instance
            dedup1 = PostDeduplicator(db_path=db_path)
            post = {
                "post_id": "test123",
                "title": "Test Post",
                "content": "Test content",
                "subreddit": "Bitcoin",
                "created_utc": 1640995200,
            }
            dedup1.add_post(post)

            # Second instance (simulating restart)
            dedup2 = PostDeduplicator(db_path=db_path)

            # Should detect the post as duplicate
            assert dedup2.is_duplicate(post)

    def test_empty_content_handling(self):
        """Test handling of posts with empty content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            post1 = {"title": "Just title", "content": ""}
            post2 = {"title": "", "content": "Just content"}
            post3 = {"title": "", "content": ""}

            # Should not crash with empty content
            hash1 = dedup._generate_content_hash(post1)
            hash2 = dedup._generate_content_hash(post2)
            hash3 = dedup._generate_content_hash(post3)

            assert isinstance(hash1, str)
            assert isinstance(hash2, str)
            assert isinstance(hash3, str)
            assert hash1 != hash2
            assert hash2 != hash3

    def test_missing_fields_handling(self):
        """Test handling of posts with missing fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            post = {"post_id": "test123"}  # Missing title, content, etc.

            # Should not crash with missing fields
            assert not dedup.is_duplicate(post)
            dedup.add_post(post)
            assert dedup.is_duplicate(post)

    @patch("sqlite3.connect")
    def test_database_error_handling(self, mock_connect):
        """Test handling of database errors."""
        mock_connect.side_effect = Exception("Database error")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"

            # Should handle database initialization error gracefully
            try:
                PostDeduplicator(db_path=db_path)
                assert False, "Should have raised exception"
            except Exception as e:
                assert "Database error" in str(e)

    def test_large_content_handling(self):
        """Test handling of posts with large content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test_dupes.db"
            dedup = PostDeduplicator(db_path=db_path)

            # Create post with large content
            large_content = "A" * 10000  # 10KB of text
            post = {
                "post_id": "large_post",
                "title": "Large Post",
                "content": large_content,
                "subreddit": "test",
                "created_utc": 1640995200,
            }

            # Should handle large content without issues
            assert not dedup.is_duplicate(post)
            dedup.add_post(post)
            assert dedup.is_duplicate(post)
