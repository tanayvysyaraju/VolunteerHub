import logging
from slack_sdk import WebClient
from collections import defaultdict

logging.basicConfig(level=logging.INFO)

def scrape_and_group_messages(client, channel_id, limit=500):
    """Fetches messages and groups them by user."""
    try:
        result = client.conversations_history(channel=channel_id, limit=limit)
        all_messages = result["messages"]
        
        # Handle pagination
        while result.get("has_more"):
            result = client.conversations_history(
                channel=channel_id,
                limit=limit,
                cursor=result["response_metadata"]["next_cursor"]
            )
            all_messages.extend(result["messages"])
        
        # Group messages by user
        user_messages = defaultdict(list)
        for msg in all_messages:
            user_id = msg.get('user')
            # Filter out messages without a user or text
            if user_id and 'text' in msg and msg.get('subtype') not in ['bot_message', 'channel_join']:
                user_messages[user_id].append(msg['text'])
                
        logging.info(f"Scraped and grouped messages for channel {channel_id}. Users found: {len(user_messages)}")
        return user_messages
        
    except Exception as e:
        logging.error(f"Error fetching messages: {e}")
        return {}