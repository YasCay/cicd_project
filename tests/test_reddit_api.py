"""Tests for Reddit API integration."""

import os
import tempfile
from unittest.mock import Mock, patch

from apps.collector.collector import RedditSentimentCollector


class TestRedditIntegration:
    """Test cases for Reddit API integration."""

    def test_init_without_credentials(self):
        """Test initialization without Reddit credentials."""
        # Ensure no credentials are set
        for key in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]:
            if key in os.environ:
                del os.environ[key]

        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            assert collector.reddit is None
            assert collector.subreddits == ["CryptoCurrency", "Bitcoin", "ethereum"]
            assert collector.fetch_limit == 100

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_init_with_env_config(self):
        """Test initialization with environment configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["SUBREDDITS"] = "Bitcoin,dogecoin"
            os.environ["FETCH_LIMIT"] = "50"
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            assert collector.subreddits == ["Bitcoin", "dogecoin"]
            assert collector.fetch_limit == 50

            # Clean up
            del os.environ["SUBREDDITS"]
            del os.environ["FETCH_LIMIT"]
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    @patch("praw.Reddit")
    def test_reddit_client_initialization_success(self, mock_reddit):
        """Test successful Reddit client initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["REDDIT_CLIENT_ID"] = "test_id"
            os.environ["REDDIT_CLIENT_SECRET"] = "test_secret"
            os.environ["REDDIT_USER_AGENT"] = "test_agent"
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            # Mock successful Reddit instance
            mock_instance = Mock()
            mock_instance.user.me.return_value = None
            mock_reddit.return_value = mock_instance

            collector = RedditSentimentCollector()
            assert collector.reddit is not None

            # Clean up
            del os.environ["REDDIT_CLIENT_ID"]
            del os.environ["REDDIT_CLIENT_SECRET"]
            del os.environ["REDDIT_USER_AGENT"]
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    @patch("praw.Reddit")
    def test_reddit_client_initialization_failure(self, mock_reddit):
        """Test Reddit client initialization failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["REDDIT_CLIENT_ID"] = "test_id"
            os.environ["REDDIT_CLIENT_SECRET"] = "test_secret"
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            # Mock Reddit client that raises exception
            mock_reddit.side_effect = Exception("Authentication failed")

            collector = RedditSentimentCollector()
            assert collector.reddit is None

            # Clean up
            del os.environ["REDDIT_CLIENT_ID"]
            del os.environ["REDDIT_CLIENT_SECRET"]
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_dummy_posts_generation(self):
        """Test dummy posts generation when no Reddit client."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            posts = collector.fetch_reddit_posts()

            assert len(posts) == 2
            assert posts[0]["post_id"] == "dummy_1"
            assert posts[1]["post_id"] == "dummy_2"
            assert all("title" in post for post in posts)
            assert all("content" in post for post in posts)
            assert all("subreddit" in post for post in posts)

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    @patch("praw.Reddit")
    def test_fetch_reddit_posts_success(self, mock_reddit):
        """Test successful Reddit posts fetching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup mock Reddit client
            mock_post1 = Mock()
            mock_post1.id = "test_post_1"
            mock_post1.title = "Test Bitcoin Post"
            mock_post1.selftext = "This is test content"
            mock_post1.score = 100
            mock_post1.created_utc = 1640995200
            mock_post1.url = "https://reddit.com/test1"
            mock_post1.num_comments = 10

            mock_post2 = Mock()
            mock_post2.id = "test_post_2"
            mock_post2.title = "Test Ethereum Post"
            mock_post2.selftext = ""
            mock_post2.score = 75
            mock_post2.created_utc = 1640995260
            mock_post2.url = "https://reddit.com/test2"
            mock_post2.num_comments = 5

            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_post1, mock_post2]

            mock_instance = Mock()
            mock_instance.user.me.return_value = None
            mock_instance.subreddit.return_value = mock_subreddit
            mock_reddit.return_value = mock_instance

            # Setup environment
            os.environ["REDDIT_CLIENT_ID"] = "test_id"
            os.environ["REDDIT_CLIENT_SECRET"] = "test_secret"
            os.environ["SUBREDDITS"] = "Bitcoin"
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            posts = collector.fetch_reddit_posts()

            assert len(posts) == 2
            assert posts[0]["post_id"] == "test_post_1"
            assert posts[0]["title"] == "Test Bitcoin Post"
            assert posts[0]["content"] == "This is test content"
            assert posts[1]["content"] == ""  # Empty selftext

            # Clean up
            del os.environ["REDDIT_CLIENT_ID"]
            del os.environ["REDDIT_CLIENT_SECRET"]
            del os.environ["SUBREDDITS"]
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_posts_to_dataframe(self):
        """Test converting posts list to DataFrame."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")
            os.environ["ENABLE_SENTIMENT"] = "false"  # Disable sentiment for this test

            collector = RedditSentimentCollector()

            posts = [
                {
                    "post_id": "test1",
                    "title": "Test Title",
                    "content": "Test content",
                    "score": 100,
                    "created_utc": 1640995200,
                    "subreddit": "Bitcoin",
                    "url": "https://reddit.com/test1",
                    "num_comments": 10,
                }
            ]

            df = collector.posts_to_dataframe(posts)

            assert len(df) == 1
            assert df.iloc[0]["post_id"] == "test1"
            assert df.iloc[0]["sentiment_label"] == "neutral"
            assert df.iloc[0]["sentiment_score"] == 0.5
            assert df.iloc[0]["run_id"] == collector.run_id

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]
            del os.environ["ENABLE_SENTIMENT"]

    def test_posts_to_dataframe_empty(self):
        """Test converting empty posts list to DataFrame."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "reddit_sentiment.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")

            collector = RedditSentimentCollector()
            df = collector.posts_to_dataframe([])

            assert df.empty

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]

    def test_run_with_dummy_data(self):
        """Test full run with dummy data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = f"{temp_dir}/test_output.csv"
            dedup_path = f"{temp_dir}/dupes.db"

            os.environ["OUTPUT_PATH"] = output_path
            os.environ["DEDUP_DB_PATH"] = dedup_path
            collector = RedditSentimentCollector()

            # Should complete successfully with dummy data
            collector.run()

            # Verify output file exists
            assert os.path.exists(output_path)

            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]
