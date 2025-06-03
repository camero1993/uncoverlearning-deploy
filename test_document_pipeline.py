import os
import sys # Added for path manipulation
import time
from dotenv import load_dotenv
import logging

# --- Add backend to sys.path for correct relative imports within backend code ---
# Get the absolute path to the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the 'backend' directory (assuming this script is in the project root)
BACKEND_DIR = os.path.join(SCRIPT_DIR, 'backend')
# Add the backend directory to sys.path if it's not already there
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR) # Insert at the beginning to ensure it's found first
# --- End path modification ---

# Now imports from backend.src should work, and internal imports within backend code
# (like 'from src...') should resolve correctly relative to the BACKEND_DIR.
from backend.src.infrastructure.document_processing.rag_pipeline_langchain import process_document
from backend.src.core.app_settings import settings # For GEMINI_API_KEY, CHUNK_SIZE etc.

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_pipeline_test():
    load_dotenv() # Load environment variables from .env file in the project root

    logger.info("Starting document processing pipeline test...")

    # Configuration - Adjust as necessary
    # Using absolute path for clarity and robustness in a script
    pdf_file_path = "/Users/magnusgraham/Downloads/uncoverlearning-deploy-main/test_documents/Psychiatric-Mental_Health_Nursing-WEB.pdf"
    original_filename = os.path.basename(pdf_file_path)
    
    # These should match your Supabase setup and environment variables
    # The process_document function expects these directly now, not from settings obj for supabase
    supabase_url_from_env = os.getenv("SUPABASE_URL")
    supabase_key_from_env = os.getenv("SUPABASE_KEY")
    
    # From app_settings, which loads from .env
    files_metadata_table = "files" # Your table name for file metadata
    # chunk_size_from_settings = settings.CHUNK_SIZE # process_document gets this
    gcp_destination_folder_from_settings = settings.GCP_DESTINATION_FOLDER
    gemini_api_key_from_settings = settings.GEMINI_API_KEY
    chunk_size_from_settings = settings.CHUNK_SIZE


    # Validate required environment variables for the test script itself
    required_for_test = {
        "Supabase URL": supabase_url_from_env,
        "Supabase Key": supabase_key_from_env,
        "Gemini API Key (from settings)": gemini_api_key_from_settings,
        "GCP Destination Folder (from settings)": gcp_destination_folder_from_settings
    }
    missing_test_vars = [key for key, value in required_for_test.items() if not value]
    if missing_test_vars:
        logger.error(f"Missing required environment variables for the test: {', '.join(missing_test_vars)}")
        logger.error("Please ensure your .env file in the project root is correctly configured.")
        return

    logger.info(f"Test PDF: {pdf_file_path}")
    logger.info(f"Original Filename: {original_filename}")
    logger.info(f"Supabase URL: {supabase_url_from_env[:30]}...") # Print partial for brevity
    logger.info(f"Files Metadata Table: {files_metadata_table}")
    logger.info(f"Chunk Size: {chunk_size_from_settings}")
    logger.info(f"GCP Destination Folder: {gcp_destination_folder_from_settings}")

    try:
        with open(pdf_file_path, "rb") as f:
            pdf_buffer = f.read()
        logger.info(f"Successfully read {len(pdf_buffer)} bytes from {pdf_file_path}")
    except FileNotFoundError:
        logger.error(f"Test PDF not found at: {pdf_file_path}")
        return
    except Exception as e:
        logger.error(f"Error reading test PDF: {e}")
        return

    start_time = time.time()
    try:
        logger.info("Calling process_document...")
        result = process_document(
            buffer=pdf_buffer,
            original_name=original_filename,
            files_table_name=files_metadata_table,
            supabase_url=supabase_url_from_env, # Pass directly
            supabase_key=supabase_key_from_env, # Pass directly
            chunk_size=chunk_size_from_settings, # Pass directly
            gcp_destination_folder=gcp_destination_folder_from_settings, # Pass directly
            gemini_api_key_param=gemini_api_key_from_settings # Pass directly
        )
        end_time = time.time()
        logger.info("--- process_document FINISHED ---")
        logger.info(f"Processing Result: {result}")
        logger.info(f"Total time taken for process_document: {end_time - start_time:.2f} seconds")

    except ValueError as ve:
        end_time = time.time()
        logger.error(f"ValueError during processing: {ve}")
        logger.error(f"Time elapsed before error: {end_time - start_time:.2f} seconds")
    except Exception as e:
        end_time = time.time()
        logger.error(f"An unexpected error occurred during processing: {e}", exc_info=True) # Log traceback
        logger.error(f"Time elapsed before error: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    run_pipeline_test() 