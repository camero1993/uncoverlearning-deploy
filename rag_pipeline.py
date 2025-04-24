import os
import json
import requests
from google.cloud import storage
from datetime import timedelta
from typing import List
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from tqdm import tqdm
from supabase import create_client
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if credentials were loaded successfully before proceeding with GCP operations
if gcp_credentials is None:
    print("FATAL ERROR: Google Cloud credentials not loaded. Cannot proceed with GCP operations.")

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

def upload_to_gcp(buffer: bytes, filename: str, destination: str):
    """Uploads a file buffer to a specified GCP bucket and destination."""
    if not GCP_BUCKET:
        raise ValueError("GCP_BUCKET environment variable is not set.")
        
    storage_client = storage.Client()
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


def format_prompt_with_context(search_results: list, user_query: str) -> str:
    """Formats the retrieved chunks and user query into a prompt for the LLM."""
    context_sections = []

    for i, result in enumerate(search_results):
        # Adjust this field name if your Supabase rows use something else for chunk text
        # The key 'extractedText' is assumed based on the processing function
        content = result.get("extractedText", "")
        # Include file title and position for better context attribution
        file_info = f"File: {result.get('originalName', 'Unknown File')}, Chunk Position: {result.get('position', 'Unknown')}"
        context_sections.append(f"---{file_info}---\n{content.strip()}")

    context_text = "\\n\\n".join(context_sections) # Use double newline for better separation

    prompt = f"""You are a helpful assistant answering questions based on the following document excerpts.
Each excerpt is marked with '---File: [file_name], Chunk Position: [position]---' before the content.

{context_text}

---

Based on the above document excerpts, please answer the following question.
If the information needed to answer the question is not present in the excerpts,
please state that you cannot answer based on the provided context.

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
    supabase_table: str,
    supabase_url: str,
    supabase_key: str,
    chunk_size: int,
    destination: str,
    model: str, # Embedding model name
    gemini_api_key: str
):
    """
    Master function to process a document: upload, extract text, chunk,
    embed, and store metadata and chunks in Supabase.
    """
    if not supabase_url or not supabase_key or not GCP_BUCKET or not gemini_api_key:
         raise ValueError("Missing required environment variables for processing.")

    # Step 1: Upload to GCP
    print("📤 Uploading file to GCP...")
    # Use a unique filename to avoid conflicts, e.g., original_name + timestamp or a UUID
    unique_filename = f"{os.path.splitext(original_name)[0]}_{os.urandom(4).hex()}{os.path.splitext(original_name)[1] if os.path.splitext(original_name)[1] else '.pdf'}"
    gcp_url = upload_to_gcp(buffer, unique_filename, destination)
    print(f"✅ Uploaded to GCP: {gcp_url}")

    # Step 2: Insert file metadata to Supabase
    print("📝 Inserting file record to Supabase...")
    file_metadata = {
        # Using a UUID for the file ID is generally better practice
        "id": os.urandom(16).hex(), # Generate a simple hex ID for the file record
        "title": original_name,
        "link": gcp_url, # Store the GCP URL
        "license": "unknown", # optional: set a default if needed
        "in_database": True # optional: if you want to flag it's been uploaded
        # 'subject' is not included — add if needed
    }

    # Supabase insert returns a list of inserted objects
    file_record = supabase_insert(supabase_table, file_metadata, supabase_url, supabase_key)
    if not file_record:
         raise Exception("Failed to insert file metadata into Supabase.")
    file_id = file_record[0]["id"]
    print(f"✅ Inserted file record to Supabase with ID: {file_id}")


    # Step 3: Extract text from the uploaded file URL
    print("📄 Extracting text from PDF...")
    # Pass the GCP URL for text extraction
    content = pdf_to_text(pdf_url=gcp_url)
    print("✅ Text extraction complete.")

    # Step 4: Split into chunks
    print("✂️ Splitting text into chunks...")
    chunks = split_text(content, chunk_size)
    print(f"✅ Created {len(chunks)} chunks.")

    # Step 5 & 6: Generate embeddings and insert chunks into Supabase
    print("🧠 Generating embeddings and uploading chunks to Supabase...")
    for i, chunk in enumerate(chunks):
        print(f"🔍 Processing chunk {i + 1}/{len(chunks)}...")

        try:
            # Generate embedding for the chunk
            embedding = generate_gemini_embedding(chunk, model, gemini_api_key)

            # Insert chunk data into Supabase 'chunks' table
            chunk_data = {
                # Using a UUID for the chunk ID is recommended
                "id": f"{file_id}_chunk_{i}", # Simple ID based on file ID and position
                "fileId": file_id, # Link to the file record
                "position": i,
                "extractedText": chunk,
                "embedding": embedding,
                "originalName": original_name, # Store original name for easier filtering
                "downloadUrl": gcp_url # Store the file URL with the chunk
            }

            supabase_insert("chunks", chunk_data, supabase_url, supabase_key)
            print(f"✅ Processed and uploaded chunk {i + 1}")

        except Exception as chunk_e:
            print(f"❌ Error processing chunk {i + 1}: {chunk_e}")
            # Decide how to handle chunk processing errors - skip, retry, etc.
            # For now, just print and continue with the next chunk.
            pass


    print("✅ All chunks processed and uploaded.")
    return {
        "file_url": gcp_url,
        "file_id": file_id,
        "total_chunks": len(chunks),
        # Return a sample of the first embedding (first 5 elements) if embeddings were generated
        "sample_embedding": generate_gemini_embedding(chunks[0], model, gemini_api_key)[:5] if chunks else []
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
