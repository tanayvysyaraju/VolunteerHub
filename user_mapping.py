# user_mapping.py
def get_user_name(client, user_id):
  """Fetches the real name for a Slack user ID."""
  try:
    user_info = client.users_info(user=user_id)
    return user_info["user"]["real_name"]
  except Exception as e:
    print(f"Error fetching name for user {user_id}: {e}")
    return "Unknown User"