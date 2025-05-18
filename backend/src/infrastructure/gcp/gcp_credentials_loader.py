# gcp_credentials_loader.py
import os
import json
import google.auth
from google.oauth2 import service_account

def load_gcp_credentials():
    """
    Loads Google Cloud credentials using GOOGLE_APPLICATION_CREDENTIALS
    which should point to a JSON file containing the credentials.

    Returns:
        google.auth.credentials.Credentials or None: The loaded credentials object,
                                                    or None if loading failed.
    """
    try:
        # google.auth.default() handles GOOGLE_APPLICATION_CREDENTIALS env var automatically
        # It also finds credentials in other standard locations (like ~/.config/gcloud)
        gcp_credentials, project = google.auth.default()
        print("Successfully loaded GCP credentials.")
        return gcp_credentials
    except Exception as e:
        print(f"Error loading GCP credentials: {e}")
        print("Please ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid credentials file.")
        return None
