from gcp_credentials_loader import load_gcp_credentials
from google.cloud import storage
from dotenv import load_dotenv
import os

def test_gcp_auth():
    print("\n=== GCP Credentials Test ===")
    
    # Load .env file
    load_dotenv()
    
    # 1. Check environment variable
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"\n1. Checking GOOGLE_APPLICATION_CREDENTIALS:")
    print(f"   Path set to: {creds_path}")
    
    if not creds_path:
        print("   ❌ GOOGLE_APPLICATION_CREDENTIALS is not set")
        return
    
    if not os.path.exists(creds_path):
        print(f"   ❌ Credentials file not found at: {creds_path}")
        return
    
    print(f"   ✅ Credentials file exists")
    
    # 2. Try loading credentials
    print("\n2. Attempting to load credentials:")
    try:
        credentials = load_gcp_credentials()
        if credentials:
            print(f"   ✅ Credentials loaded successfully")
            print(f"   Type: {type(credentials).__name__}")
            if hasattr(credentials, 'project_id'):
                print(f"   Project ID: {credentials.project_id}")
        else:
            print("   ❌ Failed to load credentials")
    except Exception as e:
        print(f"   ❌ Error loading credentials: {str(e)}")
    
    # 3. Try creating a storage client
    print("\n3. Testing GCP Storage client creation:")
    try:
        storage_client = storage.Client()
        print("   ✅ Storage client created successfully")
        
        # Try listing buckets as a basic API test
        buckets = list(storage_client.list_buckets())
        print(f"   ✅ Successfully listed {len(buckets)} buckets")
        print("   Available buckets:")
        for bucket in buckets:
            print(f"   - {bucket.name}")
    except Exception as e:
        print(f"   ❌ Error testing storage client: {str(e)}")

if __name__ == "__main__":
    test_gcp_auth() 