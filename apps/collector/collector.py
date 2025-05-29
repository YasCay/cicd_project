#!/usr/bin/env python3
"""
Reddit FinBERT Sentiment Collector

Fetches Reddit posts, de-duplicates, scores sentiment with FinBERT,
and saves to CSV. Designed to run as Kubernetes CronJob.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import praw
import psutil
from dotenv import load_dotenv

# Handle imports for both standalone and module execution
try:
    from .dedup import PostDeduplicator
    from .metrics import MetricsServer, get_metrics
    from .sentiment import FinBERTSentimentAnalyzer
except ImportError:
    # Fallback for standalone execution
    sys.path.append(str(Path(__file__).parent))
    from dedup import PostDeduplicator
    from metrics import MetricsServer, get_metrics
    from sentiment import FinBERTSentimentAnalyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RedditSentimentCollector:
    """Main collector class for Reddit sentiment analysis."""

    def __init__(self):
        """Initialize collector with configuration."""
        self.output_path = os.getenv("OUTPUT_PATH", "/data/reddit_sentiment.csv")
        self.run_id = os.getenv("RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

        # Reddit configuration
        self.subreddits = os.getenv(
            "SUBREDDITS", "CryptoCurrency,Bitcoin,ethereum"
        ).split(",")
        self.fetch_limit = int(os.getenv("FETCH_LIMIT", "100"))

        # Deduplication configuration
        dedup_db_path = os.getenv("DEDUP_DB_PATH", "/data/dupes.db")
        dedup_capacity = int(os.getenv("DEDUP_CAPACITY", "100000"))

        # Sentiment analysis configuration
        finbert_model = os.getenv("FINBERT_MODEL", "ProsusAI/finbert")
        sentiment_batch_size = int(os.getenv("SENTIMENT_BATCH_SIZE", "8"))
        enable_sentiment = os.getenv("ENABLE_SENTIMENT", "true").lower() == "true"

        # Metrics configuration
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.metrics_port = int(os.getenv("METRICS_PORT", "8000"))

        # Initialize metrics
        if self.enable_metrics:
            self.metrics = get_metrics()
            self.metrics_server = MetricsServer(
                port=self.metrics_port, metrics=self.metrics
            )
            logger.info(f"Metrics enabled on port {self.metrics_port}")
        else:
            self.metrics = None
            self.metrics_server = None
            logger.info("Metrics disabled")

        # Initialize components
        self.reddit = self._init_reddit_client()
        self.deduplicator = PostDeduplicator(
            db_path=dedup_db_path, capacity=dedup_capacity
        )

        # Initialize sentiment analyzer
        if enable_sentiment:
            self.sentiment_analyzer = self._init_sentiment_analyzer(
                finbert_model, sentiment_batch_size
            )
        else:
            self.sentiment_analyzer = None
            logger.info("Sentiment analysis disabled")

        logger.info(f"Collector initialized with output path: {self.output_path}")
        logger.info(f"Target subreddits: {self.subreddits}")
        logger.info(f"Deduplication database: {dedup_db_path}")
        logger.info(f"Sentiment analysis enabled: {enable_sentiment}")

    def _init_reddit_client(self) -> praw.Reddit:
        """Initialize Reddit client with credentials."""
        try:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "finbert-ci/0.1")

            if (
                not client_id
                or not client_secret
                or client_id.startswith("dummy")
                or client_secret.startswith("dummy")
            ):
                logger.warning(
                    "Reddit credentials not found or dummy - using dummy mode"
                )
                return None

            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )

            # Test the connection
            reddit.user.me()
            logger.info("Reddit client initialized successfully")
            return reddit

        except Exception as e:
            logger.warning(
                f"Failed to initialize Reddit client: {e} - using dummy mode"
            )
            return None

    def _init_sentiment_analyzer(
        self, model_name: str, batch_size: int
    ) -> FinBERTSentimentAnalyzer:
        """Initialize FinBERT sentiment analyzer with error handling."""
        try:
            start_time = time.time()
            analyzer = FinBERTSentimentAnalyzer(
                model_name=model_name, batch_size=batch_size
            )
            load_duration = time.time() - start_time

            # Record metrics
            if self.metrics:
                self.metrics.record_model_load_time(load_duration)

            logger.info(
                f"FinBERT sentiment analyzer initialized: {model_name} "
                f"({load_duration:.2f}s)"
            )
            return analyzer
        except Exception as e:
            if self.metrics:
                self.metrics.record_error("sentiment_analyzer", "initialization_failed")
            logger.warning(
                f"Failed to initialize FinBERT analyzer: {e} - "
                f"sentiment analysis disabled"
            )
            return None

    def create_dummy_data(self) -> pd.DataFrame:
        """Create dummy data for initial testing."""
        dummy_data = {
            "post_id": ["dummy_1", "dummy_2"],
            "title": ["Bitcoin price rising!", "Ethereum looks bearish"],
            "content": ["Great news for crypto", "Market looks uncertain"],
            "score": [150, 75],
            "created_utc": [1640995200, 1640995260],
            "subreddit": ["Bitcoin", "ethereum"],
            "sentiment_label": ["positive", "negative"],
            "sentiment_score": [0.85, 0.72],
            "run_id": [self.run_id, self.run_id],
        }
        return pd.DataFrame(dummy_data)

    def save_to_csv(self, df: pd.DataFrame) -> None:
        """Save DataFrame to CSV file."""
        try:
            # Ensure output directory exists
            Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

            df.to_csv(self.output_path, index=False)
            logger.info(f"Successfully saved {len(df)} records to {self.output_path}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
            raise

    def fetch_reddit_posts(self) -> List[Dict[str, Any]]:
        """Fetch posts from configured subreddits."""
        if not self.reddit:
            logger.info("No Reddit client available - using dummy data")
            return self._get_dummy_posts()

        posts = []

        for subreddit_name in self.subreddits:
            try:
                logger.info(f"Fetching posts from r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)
                subreddit_posts = []

                # Fetch hot posts from the last hour
                for post in subreddit.hot(limit=self.fetch_limit):
                    post_data = {
                        "post_id": post.id,
                        "title": post.title,
                        "content": post.selftext if post.selftext else "",
                        "score": post.score,
                        "created_utc": int(post.created_utc),
                        "subreddit": subreddit_name,
                        "url": post.url,
                        "num_comments": post.num_comments,
                    }
                    subreddit_posts.append(post_data)

                posts.extend(subreddit_posts)

                # Record metrics for this subreddit
                if self.metrics:
                    self.metrics.record_posts_fetched(
                        len(subreddit_posts), subreddit_name
                    )

                logger.info(
                    f"Fetched {len(subreddit_posts)} posts from r/{subreddit_name}"
                )

            except Exception as e:
                if self.metrics:
                    self.metrics.record_reddit_api_error("fetch_failed")
                logger.error(f"Failed to fetch from r/{subreddit_name}: {e}")
                continue

        logger.info(f"Total posts fetched: {len(posts)}")
        return posts

    def _get_dummy_posts(self) -> List[Dict[str, Any]]:
        """Generate dummy posts for testing."""
        return [
            {
                "post_id": "dummy_1",
                "title": "Bitcoin price rising!",
                "content": "Great news for crypto investors",
                "score": 150,
                "created_utc": 1640995200,
                "subreddit": "Bitcoin",
                "url": "https://reddit.com/dummy1",
                "num_comments": 25,
            },
            {
                "post_id": "dummy_2",
                "title": "Ethereum looks bearish",
                "content": "Market sentiment is uncertain",
                "score": 75,
                "created_utc": 1640995260,
                "subreddit": "ethereum",
                "url": "https://reddit.com/dummy2",
                "num_comments": 12,
            },
        ]

    def posts_to_dataframe(self, posts: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert posts list to DataFrame with sentiment analysis."""
        if not posts:
            logger.warning("No posts to convert to DataFrame")
            return pd.DataFrame()

        df = pd.DataFrame(posts)

        # Perform sentiment analysis
        if self.sentiment_analyzer:
            logger.info(f"Analyzing sentiment for {len(df)} posts...")

            start_time = time.time()

            # Combine title and content for sentiment analysis
            texts_for_analysis = []
            for _, row in df.iterrows():
                title = row.get("title", "")
                content = row.get("content", "")
                # Combine title and content, prioritizing title if content is empty
                combined_text = f"{title}. {content}".strip() if content else title
                texts_for_analysis.append(combined_text)

            # Batch sentiment analysis
            sentiment_results = self.sentiment_analyzer.analyze_batch(
                texts_for_analysis
            )

            # Record sentiment analysis metrics
            analysis_duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_sentiment_analysis(analysis_duration, len(df))

            # Add sentiment columns
            df["sentiment_label"] = [result["label"] for result in sentiment_results]
            df["sentiment_confidence"] = [
                result["confidence"] for result in sentiment_results
            ]
            df["sentiment_positive"] = [
                result["positive"] for result in sentiment_results
            ]
            df["sentiment_negative"] = [
                result["negative"] for result in sentiment_results
            ]
            df["sentiment_neutral"] = [
                result["neutral"] for result in sentiment_results
            ]

            # Legacy compatibility - use confidence as score
            df["sentiment_score"] = df["sentiment_confidence"]

            logger.info(
                f"Sentiment analysis completed for {len(df)} posts "
                f"({analysis_duration:.2f}s)"
            )

            # Log sentiment distribution and record metrics
            sentiment_counts = df["sentiment_label"].value_counts()
            logger.info(f"Sentiment distribution: {sentiment_counts.to_dict()}")

            if self.metrics:
                self.metrics.record_sentiment_distribution(sentiment_counts.to_dict())

        else:
            # Fallback to neutral sentiment
            logger.info("Sentiment analyzer not available, using neutral sentiment")
            df["sentiment_label"] = "neutral"
            df["sentiment_confidence"] = 0.5
            df["sentiment_positive"] = 0.33
            df["sentiment_negative"] = 0.33
            df["sentiment_neutral"] = 0.34
            df["sentiment_score"] = 0.5  # Legacy compatibility

        df["run_id"] = self.run_id

        logger.info(f"Created DataFrame with {len(df)} posts")
        return df

    def run(self) -> None:
        """Main execution method."""
        logger.info(f"Starting Reddit sentiment collection - Run ID: {self.run_id}")
        start_time = time.time()

        try:
            # Record memory usage
            if self.metrics:
                memory_usage = psutil.Process().memory_info().rss
                self.metrics.record_memory_usage(memory_usage)
                self.metrics.reset_health_status()

            # Fetch posts from Reddit
            posts = self.fetch_reddit_posts()

            if not posts:
                logger.warning("No posts fetched - exiting")
                if self.metrics:
                    self.metrics.record_error("pipeline", "no_posts_fetched")
                return

            # Deduplicate posts
            logger.info(f"Deduplicating {len(posts)} posts...")
            unique_posts = self.deduplicator.deduplicate_posts(posts)

            # Record deduplication metrics
            duplicates_count = len(posts) - len(unique_posts)
            if self.metrics:
                self.metrics.record_posts_deduplicated(duplicates_count)

            if not unique_posts:
                logger.warning("No unique posts after deduplication - exiting")
                if self.metrics:
                    self.metrics.record_error("pipeline", "no_unique_posts")
                return

            # Convert to DataFrame
            df = self.posts_to_dataframe(unique_posts)

            if df.empty:
                logger.warning("Empty DataFrame - exiting")
                if self.metrics:
                    self.metrics.record_error("pipeline", "empty_dataframe")
                return

            # Record processed posts
            if self.metrics:
                self.metrics.record_posts_processed(len(df))

            # Save to CSV
            self.save_to_csv(df)

            # Log deduplication stats
            stats = self.deduplicator.get_stats()
            logger.info(f"Deduplication stats: {stats}")

            # Record successful run
            total_duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_successful_run(total_duration)

            logger.info(f"Collection completed successfully in {total_duration:.2f}s")

        except Exception as e:
            if self.metrics:
                self.metrics.record_error("pipeline", "execution_failed")
            logger.error(f"Collection failed: {e}")
            sys.exit(1)

    def shutdown(self):
        """Graceful shutdown method."""
        logger.info("Shutting down collector...")
        if self.metrics_server:
            logger.info("Stopping metrics server...")
            self.metrics_server.stop()
        logger.info("Collector shutdown complete")


class CollectorManager:
    """Manager for handling Docker lifecycle and signals."""

    def __init__(self):
        self.collector = None
        self.running = True
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        if self.collector:
            self.collector.shutdown()
        sys.exit(0)

    def run_as_service(self):
        """Run collector as a long-running service with metrics server."""
        logger.info("Starting collector in service mode with metrics endpoint...")

        try:
            self.collector = RedditSentimentCollector()

            # Start metrics server if enabled
            if self.collector.metrics_server:
                self.collector.metrics_server.start()
                logger.info(
                    f"Metrics server started on port {self.collector.metrics_port}"
                )

            # Keep the service running
            logger.info("Collector service is running. Press Ctrl+C to stop.")
            while self.running:
                time.sleep(10)  # Check every 10 seconds

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
        finally:
            if self.collector:
                self.collector.shutdown()

    def run_once(self):
        """Run collector once (CronJob mode)."""
        logger.info("Running collector in CronJob mode...")
        try:
            self.collector = RedditSentimentCollector()

            # Start metrics server if enabled
            if self.collector.metrics_server:
                self.collector.metrics_server.start()
                logger.info(
                    f"Metrics server started on port {self.collector.metrics_port}"
                )

            # Run the collection
            self.collector.run()

        except Exception as e:
            logger.error(f"CronJob execution failed: {e}")
            raise
        finally:
            if self.collector:
                self.collector.shutdown()


def main():
    """Entry point for the collector."""
    # Check if running in service mode (for Docker)
    run_mode = os.getenv("RUN_MODE", "once").lower()

    manager = CollectorManager()

    if run_mode == "service":
        manager.run_as_service()
    else:
        manager.run_once()


if __name__ == "__main__":
    main()
