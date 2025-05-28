#!/usr/bin/env python3
"""
Simple validation test for Step 4 completion.
"""

import tempfile
import os
from apps.collector.sentiment import FinBERTSentimentAnalyzer
from apps.collector.collector import RedditSentimentCollector

def test_step4_finbert_integration():
    """Test that Step 4 FinBERT integration is working."""
    
    print("Testing Step 4: FinBERT Sentiment Integration")
    print("=" * 50)
    
    # Test 1: FinBERT Analyzer initialization
    try:
        analyzer = FinBERTSentimentAnalyzer(model_name="ProsusAI/finbert", batch_size=2)
        print("✅ FinBERT analyzer initialization: PASSED")
    except Exception as e:
        print(f"❌ FinBERT analyzer initialization: FAILED - {e}")
        return False
    
    # Test 2: Text preprocessing
    try:
        short_text = "Bitcoin price is rising!"
        long_text = "Bitcoin analysis " * 100  # Long text
        
        result1 = analyzer._preprocess_text(short_text)
        result2 = analyzer._preprocess_text(long_text)
        
        assert result1 == "Bitcoin price is rising!"
        assert len(result2) <= 400  # Should be truncated
        print("✅ Text preprocessing: PASSED")
    except Exception as e:
        print(f"❌ Text preprocessing: FAILED - {e}")
        return False
    
    # Test 3: Single sentiment analysis
    try:
        result = analyzer.analyze_sentiment("Bitcoin price is soaring!")
        assert "label" in result
        assert "confidence" in result
        assert result["label"] in ["positive", "negative", "neutral"]
        print("✅ Single sentiment analysis: PASSED")
    except Exception as e:
        print(f"❌ Single sentiment analysis: FAILED - {e}")
        return False
    
    # Test 4: Batch sentiment analysis
    try:
        texts = ["Great bullish news!", "Market crash imminent", "No changes today"]
        results = analyzer.analyze_batch(texts)
        assert len(results) == 3
        assert all("label" in r for r in results)
        print("✅ Batch sentiment analysis: PASSED")
    except Exception as e:
        print(f"❌ Batch sentiment analysis: FAILED - {e}")
        return False
    
    # Test 5: Collector integration
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OUTPUT_PATH"] = os.path.join(temp_dir, "test.csv")
            os.environ["DEDUP_DB_PATH"] = os.path.join(temp_dir, "dupes.db")
            os.environ["ENABLE_SENTIMENT"] = "true"
            
            collector = RedditSentimentCollector()
            
            # Test with dummy posts
            test_posts = [
                {
                    "post_id": "test_1",
                    "title": "Bitcoin hits new highs!",
                    "content": "Amazing bull run continues",
                    "score": 100,
                    "created_utc": 1640995200,
                    "subreddit": "Bitcoin",
                }
            ]
            
            df = collector.posts_to_dataframe(test_posts)
            
            # Verify sentiment columns exist
            required_cols = ["sentiment_label", "sentiment_confidence", 
                           "sentiment_positive", "sentiment_negative", "sentiment_neutral"]
            assert all(col in df.columns for col in required_cols)
            
            # Clean up
            del os.environ["OUTPUT_PATH"]
            del os.environ["DEDUP_DB_PATH"]
            del os.environ["ENABLE_SENTIMENT"]
            
        print("✅ Collector integration: PASSED")
    except Exception as e:
        print(f"❌ Collector integration: FAILED - {e}")
        return False
    
    print("\n🎉 Step 4 FinBERT Integration: ALL TESTS PASSED!")
    return True

if __name__ == "__main__":
    test_step4_finbert_integration()
