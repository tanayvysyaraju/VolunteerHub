# main_bot.py
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from postgres_database import db
import json
from Scraper import scrape_and_group_messages
from user_mapping import get_user_name
from llm_analyzer import analyze_user_messages

# Load environment variables from .env file
load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])

def update_user_profile_in_db(user_id, user_name, raw_text, analysis):
    """Inserts or updates a user's profile in the PostgreSQL database."""
    return db.create_or_update_user_profile(user_id, user_name, raw_text, analysis)

@app.command("/generate-insights")
def handle_insights_command(ack, body, client, logger):
    ack(text="Starting analysis... This might take a minute!")
    channel_id = body["channel_id"]
    
    # Test database connection first
    if not db.test_connection():
        client.chat_postMessage(channel=channel_id, text="❌ Database connection failed. Please check your DATABASE_URL environment variable.")
        return
    
    # 1. Scrape and group messages
    user_messages_dict = scrape_and_group_messages(client, channel_id)
    
    # 2. Process each user
    processed_count = 0
    for user_id, messages_list in user_messages_dict.items():
        # Skip users with very few messages
        if len(messages_list) < 3:
            continue
            
        # Get the user's real name
        user_name = get_user_name(client, user_id)
        
        # Combine all their messages into one text
        raw_convo_text = " ".join(messages_list)
        
        # 3. Send to LLM for analysis
        print(f"Analyzing messages for {user_name}...")
        try:
            analysis_result = analyze_user_messages(raw_convo_text)
        except Exception as e:
            print(f"LLM analysis failed for {user_name}: {e}")
            continue
        
        # 4. Save to PostgreSQL Database
        success = update_user_profile_in_db(user_id, user_name, raw_convo_text, analysis_result)
        if success:
            print(f"✅ Successfully updated profile for {user_name}")
            processed_count += 1
        else:
            print(f"❌ Failed to update profile for {user_name}")
    
    # 5. Notify the channel
    client.chat_postMessage(channel=channel_id, text=f"Analysis complete! Successfully processed {processed_count} user profiles in the PostgreSQL database.")

@app.command("/link-user")
def handle_link_user_command(ack, body, client, logger):
    """Link a Slack user to an existing app user by email."""
    ack(text="Linking user...")
    channel_id = body["channel_id"]
    
    # Parse the command text to get email
    command_text = body.get("text", "").strip()
    if not command_text:
        client.chat_postMessage(channel=channel_id, text="❌ Please provide an email address. Usage: `/link-user user@example.com`")
        return
    
    # Get the user who ran the command
    user_id = body["user_id"]
    user_name = get_user_name(client, user_id)
    
    # Link the Slack user to the existing app user
    success = db.link_slack_user_to_existing_user(user_id, user_name, command_text)
    
    if success:
        client.chat_postMessage(channel=channel_id, text=f"✅ Successfully linked Slack user {user_name} to {command_text}")
    else:
        client.chat_postMessage(channel=channel_id, text=f"❌ Failed to link user. Make sure {command_text} exists in the app database.")

@app.command("/my-profile")
def handle_my_profile_command(ack, body, client, logger):
    """Show the current user's profile data."""
    ack(text="Fetching your profile...")
    channel_id = body["channel_id"]
    user_id = body["user_id"]
    
    profile = db.get_user_profile(user_id)
    if not profile:
        client.chat_postMessage(channel=channel_id, text="❌ No profile found. Run `/generate-insights` first to create your profile.")
        return
    
    # Format the profile data for display
    strengths = json.loads(profile.get('strengths', '[]'))
    interests = json.loads(profile.get('interests', '[]'))
    expertise = json.loads(profile.get('expertise', '[]'))
    comm_style = json.loads(profile.get('communication_style', '[]'))
    
    profile_text = f"""*Profile for {profile.get('slack_user_name', 'Unknown')}*

*Strengths:* {', '.join(strengths) if strengths else 'None identified'}
*Interests:* {', '.join(interests) if interests else 'None identified'}
*Expertise:* {', '.join(expertise) if expertise else 'None identified'}
*Communication Style:* {', '.join(comm_style) if comm_style else 'None identified'}

*App User ID:* {profile.get('id', 'Not linked')}
*Email:* {profile.get('email', 'Not provided')}
*Last Updated:* {profile.get('last_updated', 'Unknown')}
"""
    
    client.chat_postMessage(channel=channel_id, text=profile_text)

if __name__ == "__main__":
    # Test database connection before starting
    if not db.test_connection():
        print("❌ Failed to connect to PostgreSQL database. Please check your DATABASE_URL environment variable.")
        exit(1)
    
    print("✅ Connected to PostgreSQL database successfully")
    # Start the bot
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()