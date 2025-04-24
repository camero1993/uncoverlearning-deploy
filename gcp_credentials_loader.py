# gcp_credentials_loader.py
import os
import json
import google.auth
from google.oauth2 import service_account # Or the specific credentials class you need

def load_gcp_credentials():
    """
    Loads Google Cloud credentials from environment variables.

    Looks for JSON content in GOOGLE_APPLICATION_CREDENTIALS_JSON,
    falls back to the GOOGLE_APPLICATION_CREDENTIALS file path method
    if the content variable is not set.

    Returns:
        google.auth.credentials.Credentials or None: The loaded credentials object,
                                                    or None if loading failed.
    """
    # Name of the environment variable holding the JSON content
    GCP_CREDENTIALS_ENV_VAR_NAME = "GOOGLE_APPLICATION_CREDENTIALS_JSON"

    credentials_json_content = os.getenv(GCP_CREDENTIALS_ENV_VAR_NAME)
    gcp_credentials = None # Initialize credentials variable

    if credentials_json_content:
        print(f"Attempting to load GCP credentials from environment variable '{GCP_CREDENTIALS_ENV_VAR_NAME}'...")
        try:
            # Parse the JSON string content into a Python dictionary
            credentials_info = json.loads(credentials_json_content)

            # Create credentials object from the dictionary
            # Use the appropriate class (service_account.Credentials is common for service accounts)
            gcp_credentials = service_account.Credentials.from_service_account_info(credentials_info)

            print("Successfully loaded GCP credentials from JSON content.")
            # Optional: You might want to return the project ID as well if needed later
            # return gcp_credentials, credentials_info.get("project_id")

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from '{GCP_CREDENTIALS_ENV_VAR_NAME}': {e}")
            print("Please ensure the environment variable contains valid JSON.")
            # Handle error appropriately - could re-raise or return None
            gcp_credentials = None
        except Exception as e:
            print(f"Error loading GCP credentials from JSON content environment variable: {e}")
            gcp_credentials = None # Ensure it's None if creation fails

    # Fallback: If the content variable wasn't set or failed, try the default methods
    # This includes checking GOOGLE_APPLICATION_CREDENTIALS pointing to a file path,
    # or application default credentials.
    if gcp_credentials is None:
        print(f"'{GCP_CREDENTIALS_ENV_VAR_NAME}' not set or failed. Attempting to load credentials via default methods (e.g., GOOGLE_APPLICATION_CREDENTIALS file path).")
        try:
            # google.auth.default() handles GOOGLE_APPLICATION_CREDENTIALS env var automatically
            # It also finds credentials in other standard locations (like ~/.config/gcloud)
            gcp_credentials, project = google.auth.default()
            print("Loaded GCP credentials using google.auth.default().")
            # If using google.auth.default(), it often returns the project ID too
            # return gcp_credentials, project
        except Exception as e:
            print(f"Error loading GCP credentials using default methods: {e}")
            gcp_credentials = None

    if gcp_credentials is None:
        print("Failed to load Google Cloud credentials using any method.")
        # Depending on your app, you might want to raise a critical error here
        # raise EnvironmentError("Google Cloud credentials could not be loaded.")


    return gcp_credentials
    # return gcp_credentials, project_id_or_none # If you decide to return project ID
