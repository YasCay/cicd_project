#!/usr/bin/env python3
"""
Tests for FinBERT sentiment analysis module.

Tests cover model initialization, single text analysis, batch processing,
error handling, and integration with the collector.
"""

import os
import tempfile
import unittest.mock
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.collector.sentiment import FinBERTSentimentAnalyzer


class TestFinBERTSentimentAnalyzer(TestCase):
    """Test cases for FinBERT sentiment analyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_texts = [
            "Bitcoin price is soaring to new heights!",
            "The market is crashing, massive losses everywhere",
            "No significant changes in the crypto market today",
            "",  # Empty text
            "This is a very long text that exceeds the typical token limit for BERT models. " * 100,  # Long text
        ]
        
        self.expected_sentiment_keys = [
            "label", "confidence", "positive", "negative", "neutral"
        ]

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_init_success(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test successful initialization of FinBERT analyzer."""
        # Mock successful model loading
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        mock_pipeline.return_value = Mock()
        
        analyzer = FinBERTSentimentAnalyzer(
            model_name="ProsusAI/finbert",
            batch_size=4
        )
        
        self.assertEqual(analyzer.model_name, "ProsusAI/finbert")
        self.assertEqual(analyzer.batch_size, 4)
        self.assertIsNotNone(analyzer.device)
        mock_tokenizer.from_pretrained.assert_called_once_with("ProsusAI/finbert")
        mock_model.from_pretrained.assert_called_once_with("ProsusAI/finbert")

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_init_failure(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test initialization failure handling."""
        # Mock model loading failure
        mock_tokenizer.from_pretrained.side_effect = Exception("Model not found")
        
        with self.assertRaises(Exception):
            FinBERTSentimentAnalyzer()

    def test_preprocess_text(self):
        """Test text preprocessing functionality."""
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        
        # Test normal text
        result = analyzer._preprocess_text("  Bitcoin is great!  ")
        self.assertEqual(result, "Bitcoin is great!")
        
        # Test empty text
        result = analyzer._preprocess_text("")
        self.assertEqual(result, "")
        
        # Test None
        result = analyzer._preprocess_text(None)
        self.assertEqual(result, "")
        
        # Test very long text (should be truncated to 400 chars max)
        long_text = "Bitcoin " * 1000
        result = analyzer._preprocess_text(long_text)
        self.assertTrue(len(result) <= 400)  # Should be truncated to 400 chars

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_analyze_sentiment_success(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test successful sentiment analysis of single text."""
        # Mock model components
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        
        # Mock pipeline response
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.return_value = [[
            {"label": "positive", "score": 0.8},
            {"label": "negative", "score": 0.1},
            {"label": "neutral", "score": 0.1}
        ]]
        mock_pipeline.return_value = mock_pipeline_instance
        
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.analyze_sentiment("Bitcoin price is rising!")
        
        # Verify result structure
        for key in self.expected_sentiment_keys:
            self.assertIn(key, result)
        
        self.assertEqual(result["label"], "positive")
        self.assertEqual(result["confidence"], 0.8)
        self.assertEqual(result["positive"], 0.8)
        self.assertEqual(result["negative"], 0.1)
        self.assertEqual(result["neutral"], 0.1)

    def test_analyze_sentiment_no_model(self):
        """Test sentiment analysis when model is not loaded."""
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        analyzer.pipeline = None
        
        result = analyzer.analyze_sentiment("Test text")
        
        # Should return neutral sentiment
        self.assertEqual(result["label"], "neutral")
        self.assertEqual(result["confidence"], 0.5)
        self.assertAlmostEqual(result["positive"], 0.33, places=2)
        self.assertAlmostEqual(result["negative"], 0.33, places=2)
        self.assertAlmostEqual(result["neutral"], 0.34, places=2)

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_analyze_sentiment_error(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test sentiment analysis error handling."""
        # Mock model components
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        
        # Mock pipeline that raises an error
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.side_effect = Exception("Analysis failed")
        mock_pipeline.return_value = mock_pipeline_instance
        
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.analyze_sentiment("Test text")
        
        # Should return neutral sentiment on error
        self.assertEqual(result["label"], "neutral")
        self.assertEqual(result["confidence"], 0.5)

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_analyze_batch_success(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test successful batch sentiment analysis."""
        # Mock model components
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        
        # Mock batch pipeline response
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.return_value = [
            [
                {"label": "positive", "score": 0.8},
                {"label": "negative", "score": 0.1},
                {"label": "neutral", "score": 0.1}
            ],
            [
                {"label": "negative", "score": 0.7},
                {"label": "positive", "score": 0.2},
                {"label": "neutral", "score": 0.1}
            ]
        ]
        mock_pipeline.return_value = mock_pipeline_instance
        
        analyzer = FinBERTSentimentAnalyzer()
        texts = ["Great news!", "Bad news!"]
        results = analyzer.analyze_batch(texts)
        
        self.assertEqual(len(results), 2)
        
        # Check first result
        self.assertEqual(results[0]["label"], "positive")
        self.assertEqual(results[0]["confidence"], 0.8)
        
        # Check second result
        self.assertEqual(results[1]["label"], "negative")
        self.assertEqual(results[1]["confidence"], 0.7)

    def test_analyze_batch_no_model(self):
        """Test batch analysis when model is not loaded."""
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        analyzer.pipeline = None
        
        texts = ["Text 1", "Text 2"]
        results = analyzer.analyze_batch(texts)
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result["label"], "neutral")
            self.assertEqual(result["confidence"], 0.5)

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_analyze_batch_with_empty_texts(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test batch analysis with empty and None texts."""
        # Mock model components
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        
        # Mock pipeline response for valid text
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.return_value = [
            [
                {"label": "positive", "score": 0.8},
                {"label": "negative", "score": 0.1},
                {"label": "neutral", "score": 0.1}
            ]
        ]
        mock_pipeline.return_value = mock_pipeline_instance
        
        analyzer = FinBERTSentimentAnalyzer()
        texts = ["", "Valid text", None, "  "]  # Mix of empty and valid texts
        results = analyzer.analyze_batch(texts)
        
        self.assertEqual(len(results), 4)
        
        # Empty texts should get neutral sentiment
        self.assertEqual(results[0]["label"], "neutral")
        self.assertEqual(results[2]["label"], "neutral")
        self.assertEqual(results[3]["label"], "neutral")
        
        # Valid text should get analyzed result
        self.assertEqual(results[1]["label"], "positive")

    @patch('apps.collector.sentiment.pipeline')
    @patch('apps.collector.sentiment.AutoTokenizer')
    @patch('apps.collector.sentiment.AutoModelForSequenceClassification')
    def test_get_model_info(self, mock_model, mock_tokenizer, mock_pipeline):
        """Test getting model information."""
        # Mock model components
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        mock_pipeline.return_value = Mock()
        
        analyzer = FinBERTSentimentAnalyzer(
            model_name="test/model",
            batch_size=16
        )
        
        info = analyzer.get_model_info()
        
        self.assertEqual(info["model_name"], "test/model")
        self.assertEqual(info["batch_size"], "16")
        self.assertEqual(info["model_loaded"], "True")
        self.assertIn("device", info)

    def test_get_model_info_no_model(self):
        """Test getting model info when model failed to load."""
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        analyzer.model_name = "test/model"
        analyzer.batch_size = 8
        analyzer.device = "cpu"
        analyzer.pipeline = None
        
        info = analyzer.get_model_info()
        
        self.assertEqual(info["model_loaded"], "False")

    @patch('apps.collector.sentiment.torch')
    def test_device_detection_cuda(self, mock_torch):
        """Test CUDA device detection."""
        mock_torch.cuda.is_available.return_value = True
        
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        device = analyzer._get_device()
        
        self.assertEqual(device, "cuda")

    @patch('apps.collector.sentiment.torch')
    def test_device_detection_mps(self, mock_torch):
        """Test MPS (Apple Silicon) device detection."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        device = analyzer._get_device()
        
        self.assertEqual(device, "mps")

    @patch('apps.collector.sentiment.torch')
    def test_device_detection_cpu(self, mock_torch):
        """Test CPU device detection as fallback."""
        mock_torch.cuda.is_available.return_value = False
        # Mock missing MPS support
        mock_torch.backends = Mock(spec=[])
        
        analyzer = FinBERTSentimentAnalyzer.__new__(FinBERTSentimentAnalyzer)
        device = analyzer._get_device()
        
        self.assertEqual(device, "cpu")


class TestSentimentIntegration(TestCase):
    """Test sentiment analysis integration with collector."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_posts = [
            {
                "post_id": "test_1",
                "title": "Bitcoin reaches new all-time high!",
                "content": "Incredible bull run continues",
                "score": 500,
                "created_utc": 1640995200,
                "subreddit": "Bitcoin",
            },
            {
                "post_id": "test_2", 
                "title": "Market crash imminent",
                "content": "All indicators point to massive correction",
                "score": 100,
                "created_utc": 1640995260,
                "subreddit": "CryptoCurrency",
            },
        ]

    @patch('apps.collector.collector.FinBERTSentimentAnalyzer')
    def test_collector_sentiment_integration(self, mock_analyzer_class):
        """Test sentiment analysis integration in collector."""
        from apps.collector.collector import RedditSentimentCollector
        
        # Mock analyzer instance
        mock_analyzer = Mock()
        mock_analyzer.analyze_batch.return_value = [
            {
                "label": "positive",
                "confidence": 0.85,
                "positive": 0.85,
                "negative": 0.10,
                "neutral": 0.05
            },
            {
                "label": "negative", 
                "confidence": 0.75,
                "positive": 0.15,
                "negative": 0.75,
                "neutral": 0.10
            }
        ]
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create collector with mocked Reddit client
        with patch('apps.collector.collector.os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                'OUTPUT_PATH': '/tmp/test_output.csv',
                'ENABLE_SENTIMENT': 'true',
                'FINBERT_MODEL': 'ProsusAI/finbert',
                'SENTIMENT_BATCH_SIZE': '8',
                'DEDUP_DB_PATH': '/tmp/test_dupes.db',
                'SUBREDDITS': 'Bitcoin,CryptoCurrency',
            }.get(key, default)
            
            collector = RedditSentimentCollector()
            collector.reddit = None  # Disable Reddit API
            
            # Test dataframe creation with sentiment
            df = collector.posts_to_dataframe(self.test_posts)
            
            # Verify sentiment columns exist
            expected_columns = [
                'sentiment_label', 'sentiment_confidence', 
                'sentiment_positive', 'sentiment_negative', 'sentiment_neutral',
                'sentiment_score'  # Legacy compatibility
            ]
            for col in expected_columns:
                self.assertIn(col, df.columns)
            
            # Verify sentiment values
            self.assertEqual(df.iloc[0]['sentiment_label'], 'positive')
            self.assertEqual(df.iloc[0]['sentiment_confidence'], 0.85)
            self.assertEqual(df.iloc[1]['sentiment_label'], 'negative')
            self.assertEqual(df.iloc[1]['sentiment_confidence'], 0.75)
            
            # Verify analyzer was called
            mock_analyzer.analyze_batch.assert_called_once()

    def test_collector_sentiment_disabled(self):
        """Test collector behavior when sentiment analysis is disabled."""
        from apps.collector.collector import RedditSentimentCollector
        
        with patch('apps.collector.collector.os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                'OUTPUT_PATH': '/tmp/test_output.csv',
                'ENABLE_SENTIMENT': 'false',
                'DEDUP_DB_PATH': '/tmp/test_dupes.db',
                'SUBREDDITS': 'Bitcoin',
            }.get(key, default)
            
            collector = RedditSentimentCollector()
            collector.reddit = None  # Disable Reddit API
            
            # Verify sentiment analyzer is None
            self.assertIsNone(collector.sentiment_analyzer)
            
            # Test dataframe creation without sentiment
            df = collector.posts_to_dataframe(self.test_posts)
            
            # Should have fallback neutral sentiment
            self.assertTrue(all(df['sentiment_label'] == 'neutral'))
            self.assertTrue(all(df['sentiment_confidence'] == 0.5))

    @patch('apps.collector.collector.FinBERTSentimentAnalyzer')
    def test_collector_sentiment_analyzer_failure(self, mock_analyzer_class):
        """Test collector behavior when sentiment analyzer fails to initialize."""
        # Mock analyzer initialization failure
        mock_analyzer_class.side_effect = Exception("Model loading failed")
        
        from apps.collector.collector import RedditSentimentCollector
        
        with patch('apps.collector.collector.os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                'OUTPUT_PATH': '/tmp/test_output.csv',
                'ENABLE_SENTIMENT': 'true',
                'FINBERT_MODEL': 'ProsusAI/finbert',
                'DEDUP_DB_PATH': '/tmp/test_dupes.db',
                'SUBREDDITS': 'Bitcoin',
            }.get(key, default)
            
            collector = RedditSentimentCollector()
            collector.reddit = None  # Disable Reddit API
            
            # Verify sentiment analyzer is None after failure
            self.assertIsNone(collector.sentiment_analyzer)
            
            # Test dataframe creation falls back to neutral sentiment
            df = collector.posts_to_dataframe(self.test_posts)
            
            self.assertTrue(all(df['sentiment_label'] == 'neutral'))
            self.assertTrue(all(df['sentiment_confidence'] == 0.5))


if __name__ == "__main__":
    pytest.main([__file__])
