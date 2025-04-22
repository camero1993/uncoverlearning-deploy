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

# Set environment variables or manually insert them
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GCP_BUCKET = os.getenv("BUCKET")  # or manually set
BUCKET_FOLDER_PATH = os.getenv("BUCKET_FOLDER_PATH")  # if using local file upload
gemini_api_key = os.getenv("GEMINI_API_KEY")

def supabase_insert(table: str, object_data: dict, supabase_url: str, api_key: str):
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
    return response.json()

def upload_to_gcp(buffer, filename, destination):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCP_BUCKET)
    full_path = f"{destination}/{filename}"

    # Upload file
    blob = bucket.blob(full_path)
    blob.upload_from_string(buffer)

    # Optional: generate signed URL for temporary access
    url = blob.generate_signed_url(expiration=timedelta(minutes=15))
    return url

def update_supabase_row(table: str, supabase_url: str, api_key: str, filter_str: str, data: dict):
    url = f"{supabase_url}/rest/v1/{table}?{filter_str}"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    response = requests.patch(url, headers=headers, json=data)
    if not response.ok:
        print("Error updating:", response.status_code)
    return response.json()

def pdf_to_text(pdf_url=None, pdf_path=None, text_threshold: int = 20):
    if not pdf_url and not pdf_path:
        raise ValueError("Specify either pdf_url or pdf_path")

    # Load PDF from URL or local path
    if pdf_url:
        data = requests.get(pdf_url).content
        doc = fitz.open("pdf", data)
    else:
        full_path = BUCKET_FOLDER_PATH + pdf_path if 'BUCKET_FOLDER_PATH' in globals() else pdf_path
        doc = fitz.open(full_path)

    print(f"📄 Total pages: {len(doc)}")

    full_text = ""
    for i in tqdm(range(len(doc)), desc="Extracting"):
        page = doc.load_page(i)
        text = page.get_text()

        if len(text.strip()) < text_threshold:
            pix = page.get_pixmap(dpi=300)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(image)
            print(f"🔁 Page {i+1}: used OCR (fallback)")
        else:
            print(f"✅ Page {i+1}: extracted text normally")

        full_text += text + "\\n"

    print(f"\\n🧾 Total characters extracted: {len(full_text)}")
    return full_text

def split_text(content: str, chunk_size: int) -> List[str]:
    content = content.replace('\\n', ' ')
    total_chars = len(content)
    chunks = [content[i:i+chunk_size] for i in range(0, total_chars, chunk_size)]

    print(f"🧾 Total characters in text: {total_chars}")
    print(f"✂️ Splitting into chunks of {chunk_size} characters...")
    print(f"📦 Total chunks created: {len(chunks)}\\n")

    for i, chunk in enumerate(chunks):
        print(f"🔹 Chunk {i+1} (length: {len(chunk)}):")
        print(f"{chunk[:100]}{'...' if len(chunk) > 100 else ''}\\n")

    return chunks

def generate_gemini_embedding(content: str, gemini_api_key: str):
    genai.configure(api_key=gemini_api_key)
    model = genai.embed_content(model="models/text-embedding-004", content=content, task_type="retrieval_document")
    return model['embedding']

def hybrid_search(
    supabase_url: str,
    supabase_key: str,
    query: str,
    query_embedding: list,
    match_count: int = 10,
    full_text_weight: float = 1.0,
    semantic_weight: float = 1.0,
    rrf_k: int = 50,
    file_title: str = ""
):
    supabase = create_client(supabase_url, supabase_key)
    response = supabase.rpc("hybrid_search", {
        "query_text": query,
        "query_embedding": query_embedding,
        "match_count": match_count,
        "full_text_weight": full_text_weight,
        \"semantic_weight\": semantic_weight,
        \"rrf_k\": rrf_k,
        \"file_title\": file_title
    }).execute()

    print(type(response.data))
    print(len(response.data))
    return response.data

def format_prompt_with_context(search_results: list, user_query: str) -> str:
    context_sections = []

    for i, result in enumerate(search_results):
        content = result.get("extractedText", "")
        context_sections.append(f"Document {i+1}:\\n{content.strip()}\\n")

    context_text = "\\n---\\n".join(context_sections)

    prompt = f"""You are a helpful assistant answering questions based on the following context:

{context_text}

Based on the above documents, answer this question:
{user_query}
"""
    return prompt

def generate_gemini_response(user_prompt: str, system_prompt: str, gemini_api_key: str):
    genai.configure(api_key=gemini_api_key)

    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

    # Merge system instructions into user prompt
    full_prompt = f"{system_prompt}\\n\\n{user_prompt}"

    chat = model.start_chat()
    response = chat.send_message(full_prompt)
    return response.text

def process_document(
    buffer: bytes,
    original_name: str,
    supabase_table: str,
    supabase_url: str,
    supabase_key: str,
    chunk_size: int,
    destination: str,
    model: str,
    gemini_api_key: str
):
    # Step 1: Upload to GCP
    print("📤 Uploading file to GCP...")
    gcp_url = upload_to_gcp(buffer, original_name, destination)

    # Step 2: Insert file metadata to Supabase
    print("📝 Inserting file record to Supabase...")
    file_metadata = {
        "title": original_name,
        "link": gcp_url,
        "license": "unknown",
        "in_database": True
    }

    file_record = supabase_insert(supabase_table, file_metadata, supabase_url, supabase_key)

    # Step 3: Extract text from buffer
    print("📄 Extracting text from PDF buffer...")
    content = pdf_to_text(pdf_url=gcp_url)

    # Step 4: Split into chunks
    print("✂️ Splitting text into chunks...")
    chunks = split_text(content, chunk_size)

    embeddings = []
    for i, chunk in enumerate(chunks):
        print(f"🔍 Processing chunk {i + 1}/{len(chunks)}...")

        # Step 5: Generate embedding
        embedding = generate_gemini_embedding(chunk, model, gemini_api_key)
        embeddings.append(embedding)

        # Step 6: Insert chunk with embedding into Supabase
        chunk_data = {
            "id": f"{file_record[0]['id']}_chunk_{i}",
            "fileId": file_record[0]["id"],
            "position": i,
            "extractedText": chunk,
            "embedding": embedding,
            "originalName": original_name,
            "downloadUrl": gcp_url
        }

        supabase_insert("chunks", chunk_data, supabase_url, supabase_key)

    print("✅ All chunks processed and uploaded.")
    return {
        "file_url": gcp_url,
        "file_id": file_record[0]["id"],
        "total_chunks": len(chunks),
        "sample_embedding": embeddings[0][:5]
    }

# This part demonstrates how the process_document function might be called.
# For website integration, you would likely modify this to receive file uploads
# and parameters from a web request.
# Example usage (requires a PDF file named 'sample.pdf' and environment variables set):
# if __name__ == "__main__":
#     pdf_file_path_example = 'sample.pdf' # Replace with actual path or handle file upload
#     original_name_example = "sample_document"
#     supabase_table_example = "files" # Your Supabase table for file metadata
#     chunk_size_example = 1000
#     destination_example = "uploaded_docs" # Folder in GCP bucket
#     embedding_model_example = "models/text-embedding-004"
#
#     try:
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
#         print("Document processing successful:", processing_output)
#
#     except Exception as e:
#         print("Error during document processing:", e)

# This part demonstrates how the hybrid search and RAG pipeline might be called.
# For website integration, this would likely be triggered by a user query
# from the website interface.
# Example usage (requires the above process_document to have been run):
# if __name__ == "__main__":
#     user_query_example = "What is the main topic of the document?"
#     file_title_example = "sample_document" # The title used during processing
#     match_count_example = 10
#     full_text_weight_example = 1.0
#     semantic_weight_example = 1.0
#     rrf_k_example = 50
#
#     try:
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
#             system_prompt="You are a helpful assistant that answers questions based on documents.",
#             gemini_api_key=gemini_api_key
#         )
#         print("\n🧠 Answer:", answer_example)
#
#     except Exception as e:
#         print("\nError during search and answer generation:", e)
