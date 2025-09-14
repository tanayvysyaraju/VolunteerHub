# postgres_database.py
# This module handles PostgreSQL database operations for the SlackBot
# Required environment variable: DATABASE_URL
import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)

class PostgresDatabase:
    def __init__(self):
        """Initialize PostgreSQL connection using the same DATABASE_URL as the backend."""
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def find_user_by_slack_id(self, slack_user_id):
        """Find an existing user by their Slack user ID."""
        with self.get_session() as db:
            try:
                row = db.execute(text("""
                    SELECT id, email, full_name, slack_user_id, slack_user_name,
                           raw_conversations, strengths, interests, expertise, communication_style
                    FROM app_users WHERE slack_user_id = :slack_user_id
                """), {"slack_user_id": slack_user_id}).mappings().first()
                return dict(row) if row else None
            except SQLAlchemyError as e:
                logging.error(f"Error finding user by Slack ID: {e}")
                return None
    
    def find_user_by_email(self, email):
        """Find an existing user by their email address."""
        with self.get_session() as db:
            try:
                row = db.execute(text("""
                    SELECT id, email, full_name, slack_user_id, slack_user_name,
                           raw_conversations, strengths, interests, expertise, communication_style
                    FROM app_users WHERE email = :email
                """), {"email": email}).mappings().first()
                return dict(row) if row else None
            except SQLAlchemyError as e:
                logging.error(f"Error finding user by email: {e}")
                return None
    
    def create_or_update_user_profile(self, slack_user_id, slack_user_name, raw_conversations, analysis):
        """Create a new user profile or update an existing one with Slack bot data."""
        with self.get_session() as db:
            try:
                # Convert the analysis dict to JSON strings for each column
                strengths_json = json.dumps(analysis.get('strengths', []))
                interests_json = json.dumps(analysis.get('interests', []))
                expertise_json = json.dumps(analysis.get('expertise', []))
                comm_style_json = json.dumps(analysis.get('communication_style', []))
                
                # Check if user already exists by Slack ID
                existing_user = self.find_user_by_slack_id(slack_user_id)
                
                if existing_user:
                    # Update existing user
                    db.execute(text("""
                        UPDATE app_users SET
                            slack_user_name = :slack_user_name,
                            raw_conversations = :raw_conversations,
                            strengths = :strengths,
                            interests = :interests,
                            expertise = :expertise,
                            communication_style = :communication_style,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE slack_user_id = :slack_user_id
                    """), {
                        "slack_user_id": slack_user_id,
                        "slack_user_name": slack_user_name,
                        "raw_conversations": raw_conversations,
                        "strengths": strengths_json,
                        "interests": interests_json,
                        "expertise": expertise_json,
                        "communication_style": comm_style_json
                    })
                    logging.info(f"Updated existing user profile for Slack user {slack_user_id}")
                else:
                    # Create new user with minimal required fields
                    # We'll use the Slack user ID as a temporary email if no email is provided
                    temp_email = f"slack_{slack_user_id}@temp.local"
                    
                    db.execute(text("""
                        INSERT INTO app_users (
                            email, full_name, password_hash, slack_user_id, slack_user_name,
                            raw_conversations, strengths, interests, expertise, communication_style
                        ) VALUES (
                            :email, :full_name, :password_hash, :slack_user_id, :slack_user_name,
                            :raw_conversations, :strengths, :interests, :expertise, :communication_style
                        )
                    """), {
                        "email": temp_email,
                        "full_name": slack_user_name,
                        "password_hash": "slack_user_no_password",  # Placeholder
                        "slack_user_id": slack_user_id,
                        "slack_user_name": slack_user_name,
                        "raw_conversations": raw_conversations,
                        "strengths": strengths_json,
                        "interests": interests_json,
                        "expertise": expertise_json,
                        "communication_style": comm_style_json
                    })
                    logging.info(f"Created new user profile for Slack user {slack_user_id}")
                
                db.commit()
                return True
                
            except SQLAlchemyError as e:
                logging.error(f"Error creating/updating user profile: {e}")
                db.rollback()
                return False
    
    def link_slack_user_to_existing_user(self, slack_user_id, slack_user_name, email):
        """Link a Slack user to an existing app user by email."""
        with self.get_session() as db:
            try:
                # Find existing user by email
                existing_user = self.find_user_by_email(email)
                if not existing_user:
                    logging.warning(f"No existing user found with email: {email}")
                    return False
                
                # Update the existing user with Slack information
                db.execute(text("""
                    UPDATE app_users SET
                        slack_user_id = :slack_user_id,
                        slack_user_name = :slack_user_name,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE email = :email
                """), {
                    "slack_user_id": slack_user_id,
                    "slack_user_name": slack_user_name,
                    "email": email
                })
                
                db.commit()
                logging.info(f"Linked Slack user {slack_user_id} to existing user {email}")
                return True
                
            except SQLAlchemyError as e:
                logging.error(f"Error linking Slack user to existing user: {e}")
                db.rollback()
                return False
    
    def get_user_profile(self, slack_user_id):
        """Get a user's profile data."""
        return self.find_user_by_slack_id(slack_user_id)
    
    def test_connection(self):
        """Test the database connection."""
        try:
            with self.get_session() as db:
                db.execute(text("SELECT 1"))
                logging.info("PostgreSQL connection test successful")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL connection test failed: {e}")
            return False

# Global instance
db = PostgresDatabase()
