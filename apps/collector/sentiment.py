"""FinBERT sentiment analysis module for financial text classification.

This module provides sentiment analysis capabilities using FinBERT,
a BERT model fine-tuned on financial text for accurate financial sentiment classification.
"""

import logging
from typing import Dict, List, Union

import torch
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          pipeline)

logger = logging.getLogger(__name__)


class FinBERTSentimentAnalyzer:
    """FinBERT-based sentiment analyzer for financial text."""

    def __init__(self, model_name: str = "ProsusAI/finbert", batch_size: int = 8):
        """
        Initialize the FinBERT sentiment analyzer.

        Args:
            model_name: HuggingFace model name for FinBERT
            batch_size: Batch size for processing multiple texts
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = self._get_device()

        # Initialize model and tokenizer
        self.model = None
        self.tokenizer = None
        self.pipeline = None

        # Load model with error handling
        self._load_model()

        logger.info(
            f"FinBERT analyzer initialized with model: {model_name}, "
            f"device: {self.device}, batch_size: {batch_size}"
        )

    def _get_device(self) -> str:
        """Determine the best available device for inference."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"

    def _load_model(self) -> None:
        """Load FinBERT model and tokenizer with error handling."""
        try:
            logger.info(f"Loading FinBERT model: {self.model_name}")

            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )

            # Create sentiment analysis pipeline
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True,
                batch_size=self.batch_size,
            )

            logger.info("FinBERT model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            self.model = None
            self.tokenizer = None
            self.pipeline = None
            raise

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for FinBERT analysis.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text ready for sentiment analysis
        """
        if not text or not isinstance(text, str):
            return ""

        # Basic text cleaning
        text = text.strip()

        # More aggressive truncation for FinBERT's 512 token limit
        # Use a simple but effective character-based approach
        # Since we can't rely on tokenizer kwargs, use conservative limits
        max_chars = 400  # Very conservative to avoid token limit issues

        if len(text) > max_chars:
            text = text[:max_chars]
            logger.debug(
                f"Text truncated to {max_chars} characters to avoid token limits"
            )

        return text

    def analyze_sentiment(self, text: str) -> Dict[str, Union[str, float]]:
        """
        Analyze sentiment of a single text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment label and confidence scores
        """
        if not self.pipeline:
            logger.warning("FinBERT model not loaded, returning neutral sentiment")
            return {
                "label": "neutral",
                "confidence": 0.5,
                "positive": 0.33,
                "negative": 0.33,
                "neutral": 0.34,
            }

        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)

            if not processed_text:
                return {
                    "label": "neutral",
                    "confidence": 0.5,
                    "positive": 0.33,
                    "negative": 0.33,
                    "neutral": 0.34,
                }

            # Get predictions with error handling for token limits
            try:
                results = self.pipeline(processed_text)[0]  # First (and only) result
            except Exception as pipeline_e:
                if (
                    "token" in str(pipeline_e).lower()
                    or "length" in str(pipeline_e).lower()
                ):
                    logger.warning(
                        f"Token length issue, further truncating text: {pipeline_e}"
                    )
                    # Further truncate and retry
                    if len(processed_text) > 500:
                        processed_text = processed_text[:500]
                        results = self.pipeline(processed_text)[0]
                    else:
                        raise pipeline_e
                else:
                    raise pipeline_e

            # Convert to standardized format
            sentiment_scores = {}
            for result in results:
                label = result["label"].lower()
                score = result["score"]
                sentiment_scores[label] = score

            # Determine dominant sentiment
            dominant_label = max(
                sentiment_scores.keys(), key=lambda k: sentiment_scores[k]
            )
            confidence = sentiment_scores[dominant_label]

            return {
                "label": dominant_label,
                "confidence": confidence,
                "positive": sentiment_scores.get("positive", 0.0),
                "negative": sentiment_scores.get("negative", 0.0),
                "neutral": sentiment_scores.get("neutral", 0.0),
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "label": "neutral",
                "confidence": 0.5,
                "positive": 0.33,
                "negative": 0.33,
                "neutral": 0.34,
            }

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Union[str, float]]]:
        """
        Analyze sentiment for a batch of texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of sentiment analysis results
        """
        if not self.pipeline:
            logger.warning("FinBERT model not loaded, returning neutral sentiments")
            return [
                {
                    "label": "neutral",
                    "confidence": 0.5,
                    "positive": 0.33,
                    "negative": 0.33,
                    "neutral": 0.34,
                }
                for _ in texts
            ]

        try:
            # Preprocess all texts
            processed_texts = [self._preprocess_text(text) for text in texts]

            # Filter out empty texts and keep track of indices
            valid_texts = []
            valid_indices = []
            for i, text in enumerate(processed_texts):
                if text:
                    valid_texts.append(text)
                    valid_indices.append(i)

            results = [None] * len(texts)

            if valid_texts:
                # Batch processing with individual error handling
                batch_results = []
                try:
                    batch_results = self.pipeline(valid_texts)
                except Exception as e:
                    logger.warning(
                        f"Batch processing failed, falling back to individual processing: {e}"
                    )
                    # Fallback to individual processing
                    for text in valid_texts:
                        try:
                            individual_result = self.pipeline(text)
                            batch_results.append(individual_result[0])
                        except Exception as individual_e:
                            logger.warning(
                                f"Individual text processing failed: {individual_e}"
                            )
                            # Add neutral result for failed individual text
                            batch_results.append(
                                [
                                    {"label": "neutral", "score": 0.34},
                                    {"label": "positive", "score": 0.33},
                                    {"label": "negative", "score": 0.33},
                                ]
                            )

                # Process results
                for idx, batch_result in zip(valid_indices, batch_results):
                    sentiment_scores = {}
                    for result in batch_result:
                        label = result["label"].lower()
                        score = result["score"]
                        sentiment_scores[label] = score

                    # Determine dominant sentiment
                    dominant_label = max(
                        sentiment_scores.keys(), key=lambda k: sentiment_scores[k]
                    )
                    confidence = sentiment_scores[dominant_label]

                    results[idx] = {
                        "label": dominant_label,
                        "confidence": confidence,
                        "positive": sentiment_scores.get("positive", 0.0),
                        "negative": sentiment_scores.get("negative", 0.0),
                        "neutral": sentiment_scores.get("neutral", 0.0),
                    }

            # Fill in None results with neutral sentiment
            for i in range(len(results)):
                if results[i] is None:
                    results[i] = {
                        "label": "neutral",
                        "confidence": 0.5,
                        "positive": 0.33,
                        "negative": 0.33,
                        "neutral": 0.34,
                    }

            return results

        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {e}")
            return [
                {
                    "label": "neutral",
                    "confidence": 0.5,
                    "positive": 0.33,
                    "negative": 0.33,
                    "neutral": 0.34,
                }
                for _ in texts
            ]

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": str(self.batch_size),
            "model_loaded": str(self.pipeline is not None),
        }
