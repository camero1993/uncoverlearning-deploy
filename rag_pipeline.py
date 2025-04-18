
# rag_pipeline.py

import io
import requests
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from tqdm import tqdm
from supabase import create_client
import openai

# --- Config (replace with env vars or config file in production) ---
BUCKET_FOLDER_PATH = "./uploads/"

def hybrid_pdf_to_text(pdf_path: str, text_threshold: int = 20) -> str:
    doc = fitz.open(pdf_path)
    print(f"📄 Total pages: {len(doc)}")

    full_text = ""
    for i in tqdm(range(len(doc)), desc="Extracting"):
        page = doc.load_page(i)
        text = page.get_text()

        if len(text.strip()) < text_threshold:
            pix = page.get_pixmap(dpi=300)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(image)
            print(f"🔁 Page {i+1}: used OCR fallback")
        else:
            print(f"✅ Page {i+1}: extracted text normally")

        full_text += text + "\n"

    print(f"\n🧾 Total characters extracted: {len(full_text)}")
    return full_text

def split_text(content: str, chunk_size: int) -> list:
    content = content.replace('\n', ' ')
    total_chars = len(content)
    chunks = [content[i:i+chunk_size] for i in range(0, total_chars, chunk_size)]

    print(f"💾 Total characters: {total_chars}")
    print(f"✂️  Created {len(chunks)} chunks\n")
    return chunks

def supabase_insert(table: str, rows: list, supabase_url: str, supabase_key: str):
    supabase = create_client(supabase_url, supabase_key)
    data, count = supabase.table(table).insert(rows).execute()
    return data

def process_and_upload_pdf(
    pdf_path: str,
    file_id: str,
    original_name: str,
    chunk_size: int,
    supabase_url: str,
    supabase_key: str
):
    text = hybrid_pdf_to_text(pdf_path)
    chunks = split_text(text, chunk_size)

    chunk_data = []
    for i, chunk in enumerate(chunks):
        chunk_data.append({
            "id": f"{file_id}-{i}",
            "fileId": file_id,
            "position": i,
            "originalName": original_name,
            "extractedText": chunk,
        })

    print("📤 Uploading chunks to Supabase...")
    supabase_insert("chunks", chunk_data, supabase_url, supabase_key)
    print("✅ Upload complete.")

def generate_embedding(content: str, model: str, api_key: str) -> list:
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": content,
        "model": model
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()['data'][0]['embedding']

def hybrid_search(
    supabase_url: str,
    supabase_key: str,
    query: str,
    query_embedding: list,
    match_count: int,
    full_text_weight: float,
    semantic_weight: float,
    rrf_k: int,
    file_title: str
):
    supabase = create_client(supabase_url, supabase_key)
    response = supabase.rpc("hybrid_search", {
        "query_text": query,
        "query_embedding": query_embedding,
        "match_count": match_count,
        "full_text_weight": full_text_weight,
        "semantic_weight": semantic_weight,
        "rrf_k": rrf_k,
        "file_title": file_title
    }).execute()
    return response.data

def format_prompt_with_context(search_results: list, user_query: str) -> str:
    context_sections = []
    for i, result in enumerate(search_results):
        content = result.get("extractedText", "")
        context_sections.append(f"Document {i+1}:\n{content.strip()}\n")
    context_text = "\n---\n".join(context_sections)
    prompt = f"""You are a helpful assistant answering questions based on the following context:

{context_text}

Based on the above documents, answer this question:
{user_query}
"""
    return prompt

def generate_response(user_prompt: str, system_prompt: str, model: str, api_key: str, max_tokens: int = 500, temperature: float = 0.7):
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response['choices'][0]['message']['content']
