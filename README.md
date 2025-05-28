# Reddit FinBERT Sentiment Pipeline

A production-ready, GitOps-driven micro-project that fetches Reddit posts every 3 hours, de-duplicates them, scores sentiment with FinBERT, and stores results in CSV format.

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and configure Reddit API credentials
3. Set up Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -r apps/collector/requirements.txt
   ```
4. Run tests:
   ```bash
   pytest -v
   ```
5. Run collector locally:
   ```bash
   python apps/collector/collector.py
   ```

## Architecture

```
Developer PC → GitHub → GitHub Actions → Docker → Kubernetes → Argo CD
                    ↓
               Server Push (/home/cayir/cicd_project)
                    ↓
               Virtual Environment + One-off Run
```

## Development Status

🟢 **Step 1 Complete**: Local skeleton with dummy data and tests (6 tests, 92% coverage)
🟢 **Step 2 Complete**: Reddit API integration with PRAW (15 tests, 90% coverage)
🟢 **Step 3 Complete**: De-duplication logic with Bloom filter and SQLite (25 tests, 89% coverage)
🟢 **Step 4 Complete**: FinBERT sentiment analysis integration (42 tests, 93% coverage)
🟢 **Step 5 Complete**: Prometheus metrics and monitoring (68 tests, 90% coverage)
🟢 **Step 6 Complete**: Docker containerization with CPU optimization
🟢 **Step 7 Complete**: GitHub Actions CI/CD pipeline with security scanning
🔄 **Next**: Helm charts and Kubernetes deployment (Step 8)

## Features

- **Reddit API Integration**: Fetches posts from configurable subreddits using PRAW
- **Smart De-duplication**: Bloom filter + SQLite for efficient duplicate detection
- **FinBERT Sentiment Analysis**: Financial domain-specific BERT model for accurate sentiment scoring
- **Batch Processing**: Efficient sentiment analysis with configurable batch sizes
- **Error Handling**: Graceful fallbacks and comprehensive logging
- **Token Limit Management**: Automatic text truncation for BERT's 512-token limit
- **Device Detection**: Automatic CUDA/MPS/CPU device selection for optimal performance

## Configuration

Key environment variables:
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`: Reddit API credentials
- `SUBREDDITS`: Comma-separated list of subreddits (default: CryptoCurrency,Bitcoin,ethereum)
- `ENABLE_SENTIMENT`: Enable/disable FinBERT analysis (default: true)
- `FINBERT_MODEL`: Model name (default: ProsusAI/finbert)
- `SENTIMENT_BATCH_SIZE`: Batch size for sentiment processing (default: 8)
- `DEDUP_CAPACITY`: Bloom filter capacity (default: 100000)

## License

MIT License - see LICENSE file for details.
