#!/usr/bin/env python3
"""
Telegram Bot Webhook Management Script

This script helps you:
1. Check current webhook status
2. Set webhook URL
3. Delete webhook (for polling mode)
4. Get bot info
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def get_webhook_info():
    """Get current webhook information"""
    response = requests.get(f"{BASE_URL}/getWebhookInfo")
    if response.status_code == 200:
        data = response.json()
        if data["ok"]:
            info = data["result"]
            print("\n=== Current Webhook Info ===")
            print(f"URL: {info.get('url', 'Not set')}")
            print(f"Has Custom Certificate: {info.get('has_custom_certificate', False)}")
            print(f"Pending Update Count: {info.get('pending_update_count', 0)}")
            
            if info.get('last_error_date'):
                print(f"\n⚠️  Last Error Date: {info.get('last_error_date')}")
                print(f"Last Error Message: {info.get('last_error_message', 'N/A')}")
            
            if not info.get('url'):
                print("\n❌ Webhook is NOT configured!")
                print("   Messages will NOT be received by your server.")
            else:
                print("\n✅ Webhook is configured")
            
            return info
        else:
            print(f"Error: {data.get('description', 'Unknown error')}")
            return None
    else:
        print(f"HTTP Error: {response.status_code}")
        return None


def set_webhook(url):
    """Set webhook URL"""
    print(f"\nSetting webhook to: {url}")
    response = requests.post(
        f"{BASE_URL}/setWebhook",
        json={"url": url}
    )
    if response.status_code == 200:
        data = response.json()
        if data["ok"]:
            print("✅ Webhook set successfully!")
            return True
        else:
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return False
    else:
        print(f"HTTP Error: {response.status_code}")
        return False


def delete_webhook():
    """Delete webhook (use for polling mode)"""
    print("\nDeleting webhook...")
    response = requests.post(f"{BASE_URL}/deleteWebhook")
    if response.status_code == 200:
        data = response.json()
        if data["ok"]:
            print("✅ Webhook deleted successfully!")
            print("   You can now use polling mode if needed.")
            return True
        else:
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return False
    else:
        print(f"HTTP Error: {response.status_code}")
        return False


def get_bot_info():
    """Get bot information"""
    response = requests.get(f"{BASE_URL}/getMe")
    if response.status_code == 200:
        data = response.json()
        if data["ok"]:
            info = data["result"]
            print("\n=== Bot Info ===")
            print(f"Bot Name: {info.get('first_name')}")
            print(f"Username: @{info.get('username')}")
            print(f"Bot ID: {info.get('id')}")
            print(f"Can Join Groups: {info.get('can_join_groups', False)}")
            print(f"Can Read All Group Messages: {info.get('can_read_all_group_messages', False)}")
            return info
        else:
            print(f"Error: {data.get('description', 'Unknown error')}")
            return None
    else:
        print(f"HTTP Error: {response.status_code}")
        return None


def main():
    print("=" * 60)
    print("Telegram Bot Webhook Management")
    print("=" * 60)
    
    # Get bot info
    get_bot_info()
    
    # Get webhook info
    webhook_info = get_webhook_info()
    
    print("\n" + "=" * 60)
    print("What would you like to do?")
    print("=" * 60)
    print("1. Set webhook URL")
    print("2. Delete webhook")
    print("3. Refresh webhook info")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\n" + "=" * 60)
        print("Set Webhook URL")
        print("=" * 60)
        print("\n⚠️  Important:")
        print("   - URL must be HTTPS (not HTTP)")
        print("   - Server must be publicly accessible")
        print("   - For local testing, use ngrok or similar")
        print("\nExample: https://your-domain.com/webhook")
        print("         https://abc123.ngrok.io/webhook")
        
        url = input("\nEnter webhook URL (or press Enter to cancel): ").strip()
        if url:
            set_webhook(url)
            print("\n✅ Testing webhook...")
            get_webhook_info()
        else:
            print("Cancelled.")
    
    elif choice == "2":
        confirm = input("\n⚠️  Delete webhook? (yes/no): ").strip().lower()
        if confirm == "yes":
            delete_webhook()
        else:
            print("Cancelled.")
    
    elif choice == "3":
        get_webhook_info()
    
    elif choice == "4":
        print("\nGoodbye!")
    
    else:
        print("\nInvalid choice.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
