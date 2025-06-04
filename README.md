# Nasdaq Rule Filings Monitor

A Python script that monitors Nasdaq rule filings and sends notifications to Discord when new entries are found.

## Features

- Monitors the Nasdaq rule filings page for new entries
- Sends notifications to Discord with detailed information
- Includes timestamps for each notification
- Configurable check intervals (default: 500ms)
- Persistent tracking of seen entries
- Comprehensive logging system
- Intelligent caching system
- Rate limiting protection
- Connection pooling for better performance

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project directory with the following variables:
   ```
   # Discord webhook URL for notifications
   DISCORD_WEBHOOK_URL=your_discord_webhook_url_here

   # Nasdaq rule filings URL
   NASDAQ_URL=https://listingcenter.nasdaq.com/rulebook/nasdaq/rulefilings

   # Timer settings
   CHECK_INTERVAL=0.5           # Check interval in seconds (default: 0.5s = 500ms)
   CACHE_DURATION=0.5          # Cache duration in seconds (default: 0.5s)
   ERROR_RETRY_INTERVAL=30     # Error retry interval in seconds (default: 30s)
   REQUEST_TIMEOUT=10          # Request timeout in seconds (default: 10s)
   MAX_RETRIES=3              # Maximum number of retries (default: 3)

   # Rate limiting settings
   RATE_LIMIT_WINDOW=60       # Rate limit window in seconds (default: 60s)
   MAX_REQUESTS_PER_WINDOW=120 # Maximum requests per window (default: 120)
   ```

   Replace `your_discord_webhook_url_here` with your actual Discord webhook URL.

## Usage

Run the script:
```bash
python nasdaq_scraper.py
```

The script will:
- Check for new rule filings every 500ms (configurable via CHECK_INTERVAL)
- Cache content to reduce server load
- Enforce rate limiting to prevent server overload
- Send notifications to Discord for any new entries
- Include timestamps in UTC format for each notification
- Log all activities to both console and log files
- Retry after errors with a configurable delay
- Use connection pooling for better performance

## Performance Optimizations

- **Caching System**: Stores page content for 500ms to reduce server load
- **Rate Limiting**: Prevents exceeding server limits (120 requests per minute)
- **Connection Pooling**: Reuses connections for better performance
- **LRU Cache**: Caches parsed table rows for faster processing
- **Content Hashing**: Detects changes without unnecessary processing
- **Garbage Collection**: Regular cleanup to prevent memory issues

## Discord Message Format

Each notification includes:
- Rule Filing ID
- Description
- Status
- SEC Notice status
- Comment Period (if available)
- Notice Date (if available)
- Timestamp in UTC (e.g., 2025-05-27T11:33:42.804064+00:00)

## Logging

Logs are stored in the `logs` directory:
- Main log file: `logs/nasdaq_scraper.log`
- Log rotation: 5MB per file, keeping 3 backup files
- Log format includes timestamp, level, and message
- Debug level logging for detailed monitoring

## Error Handling

- The script handles network errors and retries automatically
- Failed Discord notifications are logged
- Corrupted or missing seen entries file is handled gracefully
- Rate limiting is handled by falling back to cached content
- Session is automatically recreated after multiple consecutive errors
