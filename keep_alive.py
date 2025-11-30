#!/usr/bin/env python3
"""
Keep-alive script for PythonAnywhere scheduled tasks.
Sends a message to admin chat to keep the bot responsive.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = 6412752484  # Your admin chat ID

async def send_keep_alive():
    """Send a message to admin chat to keep bot alive"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": "🤖 Naina is still alive and ready to chat! 💕"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Keep-alive message sent successfully!")
                return True
            else:
                logger.error(f"Failed to send keep-alive: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending keep-alive: {e}")
        return False

def main():
    """Run the keep-alive check"""
    logger.info("Running keep-alive check for Naina Bot...")
    result = asyncio.run(send_keep_alive())
    
    if result:
        logger.info("Keep-alive successful! Bot is responsive.")
    else:
        logger.warning("Keep-alive check failed. Bot may be offline.")

if __name__ == "__main__":
    main()
