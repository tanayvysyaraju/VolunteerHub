#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from slack_bolt import App

# Load environment variables
load_dotenv()

# Get tokens
bot_token = os.getenv("SLACK_BOT_TOKEN")
app_token = os.getenv("SLACK_APP_TOKEN")

print(f"Bot Token: {'SET' if bot_token else 'NOT SET'}")
print(f"App Token: {'SET' if app_token else 'NOT SET'}")

if not bot_token or not app_token:
    print("❌ Missing tokens!")
    exit(1)

# Test basic connection
try:
    app = App(token=bot_token)
    print("✅ Bot app created successfully")
    
    # Test API call
    response = app.client.auth_test()
    if response["ok"]:
        print(f"✅ Connected to Slack! Bot user: {response['user']}")
        print(f"✅ Team: {response['team']}")
    else:
        print(f"❌ Auth test failed: {response}")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
