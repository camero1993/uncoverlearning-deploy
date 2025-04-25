import os
import json
import requests
from google.cloud import storage
from datetime import timedelta
from typing import List, Dict, Any
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from tqdm import tqdm
from supabase import create_client
import google.generativeai as genai
from dotenv import load_dotenv
from gcp_credentials_loader import load_gcp_credentials
import uuid

# Load environment variables
load_dotenv()

gcp_credentials = load_gcp_credentials()
# Check if credentials were loaded successfully before proceeding with GCP operations
if gcp_credentials is None:
    print("FATAL ERROR: Google Cloud credentials not loaded. Cannot proceed with GCP operations.")
    import sys
    sys.exit(1)

# Set environment variables or manually insert them
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly in your Render environment or .env file
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GCP_BUCKET = os.getenv("BUCKET")  # or manually set
# BUCKET_FOLDER_PATH is likely not needed for Render deployment if using cloud storage URLs
BUCKET_FOLDER_PATH = os.getenv("BUCKET_FOLDER_PATH")  # if using local file upload
gemini_api_key = os.getenv("GEMINI_API_KEY")

# --- Helper Functions ---

def supabase_insert(table: str, object_data: dict, supabase_url: str, api_key: str):
    """Inserts data into a specified Supabase table."""
    url = f"{supabase_url}/rest/v1/{table}"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    response = requests.post(url, headers=headers, json=object_data)
    if not response.ok:
        print("Error inserting:")
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        # Consider raising an exception here in a production environment
        response.raise_for_status()
    return response.json()

def supabase_batch_insert(table: str, data_list: List[Dict[str, Any]], supabase_url: str, api_key: str):
    """Inserts a list of data objects (batch) into a specified Supabase table."""
    if not data_list:
        print("Warning: Attempted to insert an empty batch.")
        return [] # Return empty list if there's no data to insert

    url = f"{supabase_url}/rest/v1/{table}"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation" # Get the inserted rows back in the response
    }

    print(f"Attempting batch insert of {len(data_list)} records into table '{table}'...") # Log attempt

    try:
        # Send a JSON array of objects
        # requests.post(json=...) automatically handles converting the list of dicts to a JSON array
        response = requests.post(url, headers=headers, json=data_list)

        # Check for HTTP errors (status codes 4xx or 5xx)
        if not response.ok:
             print(f"Error during batch insert into '{table}':")
             print("Status Code:", response.status_code)
             print("Response Text:", response.text)
             response.raise_for_status() # Raises an HTTPError

        print(f"Successfully inserted batch into '{table}'.") # Log success
        return response.json() # Returns a list of the inserted records if Prefer is set

    except requests.exceptions.RequestException as e:
        # Catch request-specific errors (network issues, timeouts, etc.)
        print(f"Network or request error during batch insert into '{table}': {e}")
        # You might want to print the response text if available for more details on HTTP errors
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Supabase response body: {e.response.text}")
        raise # Re-raise the exception after logging


def upload_to_gcp(buffer: bytes, filename: str, destination: str):
    """Uploads a file buffer to a specified GCP bucket and destination."""
    if not GCP_BUCKET:
        raise ValueError("GCP_BUCKET environment variable is not set.")
        
    storage_client = storage.Client(credentials=gcp_credentials)
    bucket = storage_client.bucket(GCP_BUCKET)
    full_path = f"{destination}/{filename}"

    # Upload file
    blob = bucket.blob(full_path)
    blob.upload_from_string(buffer, content_type='application/pdf') # Specify content type

    # Generate signed URL for temporary access (optional, adjust expiration as needed)
    # For public access, you might configure the bucket or blob differently
    url = blob.generate_signed_url(expiration=timedelta(minutes=15))
    return url

def update_supabase_row(table: str, supabase_url: str, api_key: str, filter_str: str, data: dict):
    """Updates a row in a specified Supabase table based on a filter string."""
    url = f"{supabase_url}/rest/v1/{table}?{filter_str}"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    response = requests.patch(url, headers=headers, json=data)
    if not response.ok:
        print("Error updating:", response.status_code)
        print("Response Text:", response.text)
        # Consider raising an exception here
        response.raise_for_status()
    return response.json()

def pdf_to_text(pdf_url=None, pdf_path=None, text_threshold: int = 20):
    """
    Extracts text from a PDF, using PyMuPDF for direct text extraction
    and falling back to Tesseract OCR if text density is below threshold.
    Can load from a URL or local path.
    """
    if not pdf_url and not pdf_path:
        raise ValueError("Specify either pdf_url or pdf_path")

    # Load PDF from URL or local path
    if pdf_url:
        print(f"Attempting to download PDF from URL: {pdf_url}")
        try:
            response = requests.get(pdf_url)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.content
            doc = fitz.open("pdf", data)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading PDF from URL: {e}")
            raise
        except fitz.FileDataError as e:
             print(f"Error opening PDF data: {e}")
             raise
    else:
        # Handle local path - adjust if BUCKET_FOLDER_PATH is not always used
        full_path = pdf_path # Assuming pdf_path is the full path if no URL
        if 'BUCKET_FOLDER_PATH' in globals() and BUCKET_FOLDER_PATH and not os.path.isabs(pdf_path):
             full_path = os.path.join(BUCKET_FOLDER_PATH, pdf_path)

        print(f"Attempting to open PDF from local path: {full_path}")
        try:
            doc = fitz.open(full_path)
        except fitz.FileNotFoundError:
            print(f"Error: PDF file not found at {full_path}")
            raise
        except Exception as e:
            print(f"Error opening local PDF file: {e}")
            raise


    print(f"📄 Total pages: {len(doc)}")

    full_text = ""
    # Use tqdm for a progress bar during extraction
    for i in tqdm(range(len(doc)), desc="Extracting Text"):
        page = doc.load_page(i)
        text = page.get_text()

        # Fallback to OCR if extracted text is sparse
        if len(text.strip()) < text_threshold:
            try:
                pix = page.get_pixmap(dpi=300) # Increase DPI for better OCR accuracy
                # Convert to a format Pillow can use
                img_buffer = io.BytesIO(pix.tobytes("png"))
                image = Image.open(img_buffer)
                text = pytesseract.image_to_string(image)
                print(f"🔁 Page {i+1}: used OCR (fallback)")
            except Exception as ocr_e:
                print(f"⚠️ OCR failed for page {i+1}: {ocr_e}")
                text = "" # Fallback to empty string if OCR fails
        else:
            print(f"✅ Page {i+1}: extracted text normally")

        full_text += text + "\\n" # Add newline between pages


    print(f"\\n🧾 Total characters extracted: {len(full_text)}")
    return full_text

def split_text(content: str, chunk_size: int) -> List[str]:
    """Splits a long string into smaller chunks of a specified size."""
    # Replace multiple newlines or excessive whitespace with a single space for cleaner chunks
    content = ' '.join(content.split())
    total_chars = len(content)
    chunks = [content[i:i+chunk_size] for i in range(0, total_chars, chunk_size)]

    print(f"🧾 Total characters in text: {total_chars}")
    print(f"✂️ Splitting into chunks of {chunk_size} characters...")
    print(f"📦 Total chunks created: {len(chunks)}\\n")

    # Print a preview of the first few chunks
    for i, chunk in enumerate(chunks[:5]): # Preview only first 5 chunks
        print(f"🔹 Chunk {i+1} (length: {len(chunk)}):")
        print(f"{chunk[:100]}{'...' if len(chunk) > 100 else ''}\\n")

    return chunks

def generate_gemini_embedding(content: str, gemini_api_key: str):
    """Generates a Gemini embedding for the given text content."""
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    genai.configure(api_key=gemini_api_key)
    # Use the appropriate embedding model
    model_name = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    try:
        response = genai.embed_content(
            model=model_name,
            content=content,
            task_type="retrieval_document" # Task type for RAG
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Log the specific error from the API if possible
        if hasattr(e, 'response') and e.response.text:
             print(f"API Error details: {e.response.text}")
        raise

def hybrid_search(
    supabase_url: str,
    supabase_key: str,
    query: str,
    query_embedding: list,
    match_count: int = 10,
    full_text_weight: float = 1.0,
    semantic_weight: float = 1.0,
    rrf_k: int = 50,
    file_title: str = "" # Added parameter to filter by file title
):
    """
    Performs a hybrid search (full-text and semantic) in Supabase
    using a stored procedure. Can filter by file title.
    """
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL or Key environment variables are not set.")

    try:
        supabase = create_client(supabase_url, supabase_key)
        # Call the 'hybrid_search' RPC function in Supabase
        # Ensure your Supabase database has the 'hybrid_search' function defined
        # that accepts these parameters.
        response = supabase.rpc("hybrid_search", {
            "query_text": query,
            "query_embedding": query_embedding,
            "match_count": match_count,
            "full_text_weight": full_text_weight,
            "semantic_weight": semantic_weight,
            "rrf_k": rrf_k,
            "file_title": file_title # Pass the file title to the RPC
        }).execute()

        # Supabase client execute() returns a Response object, access data via .data
        if response.data is None:
             print("Supabase RPC returned no data.")
             return []

        print(f"Supabase RPC returned {len(response.data)} results.")
        return response.data
    except Exception as e:
        print(f"Error during Supabase hybrid search: {e}")
        # Log Supabase specific errors if available
        if hasattr(e, 'message'):
             print(f"Supabase Error Message: {e.message}")
        raise


def format_prompt_with_context(search_results: list, user_query: str, history: List[Dict[str, Any]]) -> str:
    """
    Formats the retrieved chunks, conversation history, and user query
    into a prompt for the LLM with an enhanced tutor persona.
    """
    context_sections = []

    for i, result in enumerate(search_results):
        content = result.get("extractedText", "")
        file_info = f"File: {result.get('originalName', 'Unknown File')}, Chunk Position: {result.get('position', 'Unknown')}"
        context_sections.append(f"---{file_info}---\n{content.strip()}")

    context_text = "\n\n".join(context_sections) # Use double newline for better separation

    # --- Format conversation history ---
    # Format history into a string that the LLM can understand as previous turns.
    # Use 'role' and 'parts' from the history objects sent by the frontend.
    history_text = ""
    if history:
        history_text = "Conversation History:\n"
        # Iterate through history in the order it happened
        for turn in history:
            role = turn.get('role', 'unknown') # 'user' or 'model'
            parts = turn.get('parts', '') # The message content

            # Basic formatting for history turns
            if role == 'user':
                history_text += f"User: {parts}\n"
            elif role == 'model':
                 # If the model response was Markdown, include the raw text or simplified version
                 # Including raw text is often fine for LLMs to understand the flow
                 history_text += f"Model: {parts}\n"
            else:
                 history_text += f"Unknown: {parts}\n"
        history_text += "---\n\n" # Separator after history


    # --- Construct the final prompt with enhanced instructions ---
    prompt = f"""You are a kind, peer-to-peer chat bot tutor for college students, focused on helping them understand the provided document.
Your primary goal is to guide the student's learning based *only* on the information found in the document excerpts and the conversation history.
Do not provide information from outside the document.

When answering:
- Explain concepts clearly and break down complex ideas.
- Provide examples from the document or create simple illustrative examples when helpful.
- Craft answers that guide the student's understanding, rather than just giving direct answers.
- If the information needed to answer the question is not present in the excerpts or history, state that you cannot answer based on the provided context.
- If the user's question is unclear or could refer to multiple concepts in the document/history, ask a clarifying question to understand exactly what they are asking about.
- Maintain a friendly, approachable, peer-to-peer tone throughout.
- Break up your answers into clear paragraphs (including a full blank line in between each one) and use bullets for lists to maximize readability.

{history_text}

Document Excerpts:
{context_text}

---

Based on the above document excerpts and conversation history, please answer the following question.

Question: {user_query}
"""
    return prompt

def generate_gemini_response(user_prompt: str, system_prompt: str, gemini_api_key: str):
    """Generates a response from the Gemini model using the formatted prompt."""
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    genai.configure(api_key=gemini_api_key)

    # Use the appropriate generation model
    model_name = os.getenv("GENERATION_MODEL", "models/gemini-1.5-pro-latest")

    try:
        model = genai.GenerativeModel(model_name)

        # The system prompt is included directly in the user_prompt for models
        # that don't have a dedicated system instruction parameter in the client library.
        # If the client library supports system instructions, you can pass it there.
        # For simplicity here, it's concatenated.
        full_prompt = f"{system_prompt}\\n\\n{user_prompt}"

        # Using generate_content is generally recommended over chat.send_message
        # for single turn prompts like this in a RAG context.
        response = model.generate_content(full_prompt)

        # Access the text content of the response
        return response.text
    except Exception as e:
        print(f"Error generating Gemini response: {e}")
        # Log API errors if possible
        if hasattr(e, 'response') and e.response.text:
             print(f"API Error details: {e.response.text}")
        raise


def process_document(
    buffer: bytes,
    original_name: str,
    supabase_table: str, # Table name for file metadata ('files')
    supabase_url: str,
    supabase_key: str,
    chunk_size: int,
    destination: str, # GCP destination folder name
    model: str, # Embedding model name (e.g., "models/text-embedding-004")
    gemini_api_key: str # Passed explicitly, but also loaded globally. Ensure consistency.
    # Removed gcp_credentials argument
):
    """
    Master function to process a document: upload, extract text, chunk,
    embed, and store metadata and chunks in Supabase (using batching).
    Relies on global variables for GCP/Supabase credentials and config.
    """
    # Check required global variables
    # Check variables read directly or used by functions relying on globals
    if not SUPABASE_URL or not SUPABASE_KEY or not GCP_BUCKET or not gemini_api_key:
         missing = []
         if not SUPABASE_URL: missing.append("SUPABASE_URL")
         if not SUPABASE_KEY: missing.append("SUPABASE_KEY")
         if not GCP_BUCKET: missing.append("GCP_BUCKET")
         if not gemini_api_key: missing.append("gemini_api_key")
         # Note: gcp_credentials is checked within upload_to_gcp in this global setup
         raise ValueError(f"Missing required global variables for processing: {', '.join(missing)}")


    # Step 1: Upload to GCP
    print("📤 Uploading file to GCP...")
    # Use a unique filename (uuid is better)
    file_extension = os.path.splitext(original_name)[1] if os.path.splitext(original_name)[1] else '.pdf'
    unique_filename = f"{os.path.splitext(original_name)[0]}_{uuid.uuid4().hex}{file_extension}" # Use uuid

    # --- MODIFIED: Call upload_to_gcp without passing credentials ---
    # It will use the global gcp_credentials variable
    gcp_url = upload_to_gcp(buffer, unique_filename, destination)
    # ----------------------------------------------------------------

    print(f"✅ Uploaded to GCP: {gcp_url}")

    # Step 2: Insert file metadata to Supabase
    print("📝 Inserting file record to Supabase...")
    file_id = uuid.uuid4().hex # Use uuid for the file ID
    file_metadata = {
        "id": file_id, # Use uuid for the file ID
        "title": original_name,
        "link": gcp_url,
        "license": "unknown",
        "in_database": True
    }

    # Use the single insert function for file metadata
    # Supabase insert returns a list of inserted objects
    file_record_response = supabase_insert(supabase_table, file_metadata, supabase_url, supabase_key)
    if not file_record_response or not isinstance(file_record_response, list) or not file_record_response:
         raise Exception("Failed to insert file metadata into Supabase or received unexpected response.")

    # Extract the ID from the inserted record's response (safer to use DB assigned ID)
    inserted_file_record = file_record_response[0]
    file_id_from_db = inserted_file_record.get("id")
    if file_id_from_db:
         file_id = file_id_from_db # Use the ID returned by the DB if available
    else:
         print(f"Warning: Inserted file record did not return an 'id'. Using generated ID: {file_id}")
         # Fallback to the generated ID if DB doesn't return one (ensure your table schema returns ID on insert)


    print(f"✅ Inserted file record to Supabase with ID: {file_id}")


    # Step 3: Extract text from the uploaded file URL
    print("📄 Extracting text from PDF...")
    # Pass the GCP URL for text extraction
    content = pdf_to_text(pdf_url=gcp_url) # Assuming pdf_to_text handles URLs
    print("✅ Text extraction complete.")

    # Step 4: Split into chunks
    print("✂️ Splitting text into chunks...")
    chunks = split_text(content, chunk_size) # Assuming split_text returns a list of strings
    print(f"✅ Created {len(chunks)} chunks.")

    # Step 5 & 6: Generate embeddings and insert chunks into Supabase
    print("🧠 Generating embeddings and uploading chunks to Supabase...")

    # --- ADDED BATCHING LOGIC ---
    chunk_batch_data = [] # List to hold data for a batch
    batch_size = 100 # <<< Configure your desired batch size here >>>

    for i, chunk in enumerate(chunks):
        # Keep chunk processing printout for progress tracking
        print(f"🔍 Processing chunk {i + 1}/{len(chunks)}...")

        try:
            # Generate embedding for the chunk
            # The generate_gemini_embedding signature expects (content: str, gemini_api_key: str)
            # gemini_api_key is passed explicitly as an argument to process_document
            embedding = generate_gemini_embedding(chunk, gemini_api_key)

            # Prepare data for the chunk
            chunk_data = {
                # Use a robust ID system. Supabase can generate UUIDs automatically if configured.
                # Using file_id_from_db in the ID might be safer if the DB generated the file ID.
                "id": f"{file_id}_chunk_{i}", # Example ID format
                "fileId": file_id, # Link to the file record (using the ID obtained after DB insert)
                "position": i,
                "extractedText": chunk,
                "embedding": embedding, # Ensure embedding format matches your DB (vector type)
                "originalName": original_name,
                "downloadUrl": gcp_url # Optional: Store the file URL with the chunk
            }

            # Add chunk data to the current batch list
            chunk_batch_data.append(chunk_data)

            # Check if the batch is ready for upload
            # Batch is ready if it's full OR if it's the last chunk AND there are chunks in the batch
            if chunk_batch_data and ((i + 1) % batch_size == 0 or (i + 1) == len(chunks)):
                print(f"⬆️ Uploading batch of {len(chunk_batch_data)} chunks to Supabase...")
                # --- Perform a single batch insert using the new function ---
                try:
                    # supabase_url and supabase_key are used here, assumed to be global
                    supabase_batch_insert("chunks", chunk_batch_data, supabase_url, supabase_key)
                    print(f"✅ Batch upload successful.")
                except Exception as batch_upload_e:
                    # Handle errors for the *entire batch*
                    print(f"❌ Error uploading batch: {batch_upload_e}")
                    # Decide how to handle this critical error: re-raise? Log batch data?
                    # Re-raising will stop the entire process. Logging might lose data.
                    # For now, print and continue, but be aware data might be missing.
                    # A robust solution might save failed batches for retry.
                    pass # Continue loop despite batch upload failure

                chunk_batch_data = [] # Clear the list for the next batch

        except Exception as chunk_processing_e:
            # Error specific to processing a single chunk (embedding failure, etc.)
            print(f"❌ Error processing chunk {i + 1}: {chunk_processing_e}")
            # Decide how to handle chunk processing errors: skip, retry, etc.
            # If you 'pass' here, the failed chunk's data won't be added to the batch.
            pass # Continue loop despite single chunk processing failure
    # --- END BATCHING LOGIC ---


    print("✅ All chunks processed and Supabase batch uploads initiated.")
    return {
        "file_url": gcp_url,
        "file_id": file_id, # Using the file ID obtained after DB insert
        "total_chunks": len(chunks),
        # Return a sample of the first embedding (first 5 elements) if embeddings were generated
        # Corrected the call to generate_gemini_embedding for the sample
        # The 'model' variable is not used here, gemini_api_key is the second arg
        "sample_embedding": generate_gemini_embedding(chunks[0], gemini_api_key)[:5] if chunks else []
    }

# Example usage (commented out for web wrapper)
# if __name__ == "__main__":
#     # Example of processing a local file
#     # Make sure you have a 'sample.pdf' file and environment variables set
#     try:
#         print("--- Starting Document Processing Example ---")
#         pdf_file_path_example = 'sample.pdf' # Replace with actual path or handle file upload
#         original_name_example = "Sample Document"
#         supabase_table_example = "files" # Your Supabase table for file metadata
#         chunk_size_example = 1000
#         destination_example = "uploaded_docs" # Folder in GCP bucket
#         embedding_model_example = "models/text-embedding-004"
#
#         with open(pdf_file_path_example, "rb") as f:
#             pdf_buffer = f.read()
#
#         processing_output = process_document(
#             buffer=pdf_buffer,
#             original_name=original_name_example,
#             supabase_table=supabase_table_example,
#             supabase_url=SUPABASE_URL,
#             supabase_key=SUPABASE_KEY,
#             chunk_size=chunk_size_example,
#             destination=destination_example,
#             model=embedding_model_example,
#             gemini_api_key=gemini_api_key
#         )
#         print("\nDocument processing successful:", processing_output)
#
#         print("\n--- Starting Query Example ---")
#         # Example of querying the processed document
#         user_query_example = "What is the main topic of the document?"
#         file_title_example = original_name_example # Use the title used during processing
#         match_count_example = 10
#         full_text_weight_example = 1.0
#         semantic_weight_example = 1.0
#         rrf_k_example = 50
#
#         query_embedding_example = generate_gemini_embedding(user_query_example, gemini_api_key)
#
#         search_results_example = hybrid_search(
#             supabase_url=SUPABASE_URL,
#             supabase_key=SUPABASE_KEY,
#             query=user_query_example,
#             query_embedding=query_embedding_example,
#             match_count=match_count_example,
#             full_text_weight=full_text_weight_example,
#             semantic_weight=semantic_weight_example,
#             rrf_k=rrf_k_example,
#             file_title=file_title_example
#         )
#
#         formatted_prompt_example = format_prompt_with_context(search_results_example, user_query_example)
#
#         answer_example = generate_gemini_response(
#             user_prompt=formatted_prompt_example,
#             system_prompt="You are a helpful assistant that answers questions based on the provided document excerpts. If the information is not in the excerpts, state that you cannot answer based on the provided context.",
#             gemini_api_key=gemini_api_key
#         )
#         print("\n🧠 Answer:", answer_example)
#
#     except Exception as e:
#         print("\nAn error occurred:", e)
