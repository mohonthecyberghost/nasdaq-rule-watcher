# Nasdaq Rule Filings Monitor

This script monitors the Nasdaq rule filings page and sends new entries to a Discord channel.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Discord webhook URL:
```
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

To get a Discord webhook URL:
1. Go to your Discord server
2. Right-click on the channel where you want to receive notifications
3. Select "Edit Channel"
4. Go to "Integrations"
5. Click "Create Webhook"
6. Copy the webhook URL

## Usage

Run the script:
```bash
python nasdaq_scraper.py
```

The script will:
- Check for new rule filings every 5 minutes
- Send new entries to your Discord channel
- Keep track of seen entries to avoid duplicates
- Automatically retry on errors

## Features

- Monitors Nasdaq rule filings page
- Sends notifications to Discord
- Prevents duplicate notifications
- Error handling and automatic retries
- Persistent storage of seen entries
