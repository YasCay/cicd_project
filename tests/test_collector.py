"""Tests for Reddit sentiment collector."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from apps.collector.collector import RedditSentimentCollector


class TestRedditSentimentCollector:
    """Test cases for RedditSentimentCollector."""

    def test_collector_initialization(self):
        """Test collector initialization with default values."""
        # Ensure RUN_ID is not set
        if "RUN_ID" in os.environ:
            del os.environ["RUN_ID"]

        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            assert collector.output_path == os.path.join(
                temp_dir, "reddit_sentiment.csv"
            )
            assert collector.run_id is not None
            assert len(collector.run_id) > 0

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_collector_initialization_with_env(self):
        """Test collector initialization with environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "test_output.csv")
            os.environ["RUN_ID"] = "test_run_123"
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            assert collector.output_path == os.path.join(temp_dir, "test_output.csv")
            assert collector.run_id == "test_run_123"

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["RUN_ID"]
            del os.environ["DEDUP_DB_PATH"]

    def test_dummy_data_creation(self):
        """Test creation of dummy data DataFrame."""
        # Ensure RUN_ID is not set
        if "RUN_ID" in os.environ:
            del os.environ["RUN_ID"]

        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            df = collector.create_dummy_data()

            # Check DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2

            # Check required columns
            expected_columns = [
                "post_id",
                "title",
                "content",
                "score",
                "created_utc",
                "subreddit",
                "sentiment_label",
                "sentiment_score",
                "run_id",
            ]
            for col in expected_columns:
                assert col in df.columns

            # Check data types and values
            assert df["sentiment_score"].dtype in ["float64", "float32"]
            assert all(df["sentiment_score"] > 0)
            assert all(df["sentiment_score"] <= 1)
            assert df["run_id"].iloc[0] == collector.run_id

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]
        assert all(df["sentiment_score"] > 0)
        assert all(df["sentiment_score"] <= 1)
        assert df["run_id"].iloc[0] == collector.run_id

    def test_save_to_csv(self):
        """Test saving DataFrame to CSV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_output.csv"
            dedup_path = Path(temp_dir) / "dupes.db"

            # Set up collector with temporary output path
            os.environ["OUTPUT_PATH"] = str(output_path)
            os.environ["DEDUP_DB_PATH"] = str(dedup_path)
            collector = RedditSentimentCollector()

            # Create and save dummy data
            df = collector.create_dummy_data()
            collector.save_to_csv(df)

            # Verify file was created and has correct content
            assert output_path.exists()

            # Load and verify content
            loaded_df = pd.read_csv(output_path)
            assert len(loaded_df) == len(df)
            assert list(loaded_df.columns) == list(df.columns)

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_run_method_success(self):
        """Test successful execution of run method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_output.csv"
            dedup_path = Path(temp_dir) / "dupes.db"

            os.environ["OUTPUT_PATH"] = str(output_path)
            os.environ["DEDUP_DB_PATH"] = str(dedup_path)
            collector = RedditSentimentCollector()

            # Should not raise any exceptions
            collector.run()

            # Verify output file was created
            assert output_path.exists()

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_run_method_with_invalid_path(self):
        """Test run method with invalid output path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dedup_path = Path(temp_dir) / "dupes.db"

            os.environ["OUTPUT_PATH"] = (
                "/root/invalid/path/that/does/not/exist/output.csv"
            )
            os.environ["DEDUP_DB_PATH"] = str(dedup_path)
            collector = RedditSentimentCollector()

            # Should raise SystemExit due to permission error during save
            with pytest.raises(SystemExit):
                collector.run()

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]
