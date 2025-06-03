# gcp_credentials_loader.py
import os
import json
import google.auth
from google.oauth2 import service_account
import tempfile

def load_gcp_credentials():
    """
    Loads Google Cloud credentials using either:
    1. GOOGLE_APPLICATION_CREDENTIALS env var (path to JSON file)
    2. GOOGLE_APPLICATION_CREDENTIALS_JSON env var (JSON content)

    Returns:
        google.auth.credentials.Credentials or None: The loaded credentials object,
                                                    or None if loading failed.
    """
    try:
        # First try: Check if JSON content is provided directly
        json_content = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if json_content:
            try:
                # Parse the JSON content
                json_data = json.loads(json_content)
                credentials = service_account.Credentials.from_service_account_info(json_data)
                print("Successfully loaded GCP credentials from JSON content.")
                return credentials
            except Exception as e:
                print(f"Error loading credentials from JSON content: {e}")

        # Second try: Use google.auth.default() which handles GOOGLE_APPLICATION_CREDENTIALS
        try:
            credentials, project = google.auth.default()
            print("Successfully loaded GCP credentials from default location.")
            return credentials
        except Exception as e:
            print(f"Error loading credentials from default location: {e}")

        # If both methods fail, return None
        print("Failed to load GCP credentials from both JSON content and default location.")
        return None
    except Exception as e:
        print(f"Unexpected error loading GCP credentials: {e}")
        return None
