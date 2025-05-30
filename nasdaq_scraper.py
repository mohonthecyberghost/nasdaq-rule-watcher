import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import gc
import signal
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
def setup_logging():
    """Configure logging with both file and console handlers."""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging format
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Create formatter
    formatter = logging.Formatter(log_format, date_format)
    
    # Setup file handler with rotation
    file_handler = RotatingFileHandler(
        'logs/nasdaq_scraper.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    file_handler.setFormatter(formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

# Load environment variables
load_dotenv()

# Configuration from environment variables
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
NASDAQ_URL = os.getenv('NASDAQ_URL', 'https://listingcenter.nasdaq.com/rulebook/nasdaq/rulefilings')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1'))  # Default to 1 second
ERROR_RETRY_INTERVAL = int(os.getenv('ERROR_RETRY_INTERVAL', '60'))  # Default to 60 seconds
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # Default to 30 seconds
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))  # Default to 3 retries

# File to store seen entries
SEEN_ENTRIES_FILE = 'seen_entries.json'

# Configure requests session with retry strategy
def create_session():
    """Create a requests session with retry strategy."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Global session
session = create_session()

def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    logger.info("Received termination signal. Cleaning up...")
    session.close()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def load_seen_entries():
    """Load previously seen entries from file."""
    try:
        if os.path.exists(SEEN_ENTRIES_FILE):
            with open(SEEN_ENTRIES_FILE, 'r') as f:
                return json.load(f)
    except json.JSONDecodeError:
        logger.warning("seen_entries.json is corrupted or empty. Starting with empty list.")
    except Exception as e:
        logger.error(f"Error loading seen entries: {e}. Starting with empty list.")
    return []

def save_seen_entries(entries):
    """Save seen entries to file."""
    try:
        with open(SEEN_ENTRIES_FILE, 'w') as f:
            json.dump(entries, f)
        logger.debug(f"Successfully saved {len(entries)} entries to {SEEN_ENTRIES_FILE}")
    except Exception as e:
        logger.error(f"Error saving seen entries: {e}")

def send_to_discord(rule_filing, description, status, sec_notice, comment_period, notice_date):
    """Send message to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL not set in .env file")
        return False

    # Get current timestamp in ISO format with timezone
    current_time = datetime.now(timezone.utc).isoformat()

    message = f"**Rule Filing:** {rule_filing}\n"
    message += f"**Description:** {description}\n"
    message += f"**Status:** {status}\n"
    if sec_notice:
        message += f"**SEC Notice:** {sec_notice}\n"
    if comment_period:
        message += f"**Comment Period:** {comment_period}\n"
    if notice_date:
        message += f"**Notice Date:** {notice_date}\n"
    message += f"**Timestamp:** {current_time}\n"
    
    payload = {
        "content": message
    }
    
    try:
        response = session.post(DISCORD_WEBHOOK_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f"Successfully sent message to Discord: {rule_filing}")
        return True
    except Exception as e:
        logger.error(f"Error sending to Discord: {e}")
        return False

def scrape_nasdaq():
    """Scrape the Nasdaq rule filings page."""
    try:
        logger.info(f"Fetching data from {NASDAQ_URL}")
        response = session.get(NASDAQ_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table inside the tab content div
        tab_content = soup.find('div', {'id': 'NASDAQ-tab-2025', 'class': 'tab-content'})
        if not tab_content:
            logger.error("Could not find the NASDAQ tab content")
            return []
            
        table = tab_content.find('table', {'width': '100%'})
        if not table:
            logger.error("Could not find the rule filings table")
            return []
            
        rows = table.find_all('tr')[1:]  # Skip header row
        entries = []
        
        for row in rows:
            # Get all cells in the row
            cells = row.find_all('td')
            if len(cells) < 6:  # Skip if not enough cells
                continue
                
            # Extract rule filing ID from the first cell
            rule_filing_cell = cells[0]
            rule_filing_id = rule_filing_cell.find('a').text.strip() if rule_filing_cell.find('a') else ''
            
            # Get other fields
            description = cells[1].text.strip()
            status = cells[2].text.strip()
            sec_notice = cells[3].text.strip()
            comment_period = cells[4].text.strip()
            notice_date = cells[5].text.strip()
            
            if rule_filing_id and description:
                entry_data = {
                    'Rule Filing': rule_filing_id,
                    'Description': description,
                    'Status': status,
                    'Noticed by the SEC for Comment': sec_notice,
                    'Expiration of the SEC Comment Period': comment_period,
                    'Federal Register Notice Date': notice_date
                }
                entries.append(entry_data)
        
        logger.info(f"Successfully scraped {len(entries)} entries from Nasdaq")
        return entries
    except Exception as e:
        logger.error(f"Error scraping Nasdaq: {e}")
        return []

def main():
    """Main function to monitor Nasdaq rule filings."""
    logger.info("Starting Nasdaq rule filings monitor...")
    logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Error retry interval: {ERROR_RETRY_INTERVAL} seconds")
    logger.info(f"Request timeout: {REQUEST_TIMEOUT} seconds")
    logger.info(f"Max retries: {MAX_RETRIES}")
    
    seen_entries = load_seen_entries()
    logger.info(f"Loaded {len(seen_entries)} previously seen entries")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            # Get current entries
            current_entries = scrape_nasdaq()
            
            # Check for new entries
            new_entries_count = 0
            for entry in current_entries:
                entry_id = entry['Rule Filing']
                
                if entry_id not in seen_entries:
                    logger.info(f"New entry found: {entry_id}")
                    
                    # Send to Discord
                    if send_to_discord(
                        entry['Rule Filing'],
                        entry['Description'],
                        entry['Status'],
                        entry['Noticed by the SEC for Comment'],
                        entry['Expiration of the SEC Comment Period'],
                        entry['Federal Register Notice Date']
                    ):
                        seen_entries.append(entry_id)
                        save_seen_entries(seen_entries)
                        new_entries_count += 1
            
            if new_entries_count > 0:
                logger.info(f"Processed {new_entries_count} new entries")
            else:
                logger.info("No new entries found in this check")
            
            # Reset consecutive errors counter on success
            consecutive_errors = 0
            
            # Force garbage collection
            gc.collect()
            
            # Wait before next check
            logger.debug(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error in main loop: {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many consecutive errors ({consecutive_errors}). Restarting session...")
                global session
                session.close()
                session = create_session()
                consecutive_errors = 0
            
            logger.info(f"Waiting {ERROR_RETRY_INTERVAL} seconds before retrying...")
            time.sleep(ERROR_RETRY_INTERVAL)

if __name__ == "__main__":
    main() 