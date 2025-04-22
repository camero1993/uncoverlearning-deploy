from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from rag_pipeline import (
    generate_embedding,
    hybrid_search,
    format_prompt_with_context,
    generate_response,
)

app = FastAPI()

# CORS setup for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
async def ask_question(request: Request):
    data = await request.json()
    query = data.get("query", "")
    file_title = data.get("file_title", "default")  # Optional: allow client to choose

    # Step 1: Embed query
    embedding = generate_embedding(
        query=query,
        model="text-embedding-ada-002",
        openai_key="your-openai-api-key"  # replace with secure env var in prod
    )

    # Step 2: Search in Supabase
    results = hybrid_search(
        supabase_url="https://your-project.supabase.co",
        supabase_key="your-supabase-service-role-key",  # secure in production
        query=query,
        query_embedding=embedding,
        match_count=10,
        full_text_weight=1.0,
        file_title=file_title
    )

    # Step 3: Format the prompt
    prompt = format_prompt_with_context(query, results)

    # Step 4: Get model response
    answer = generate_response(prompt, model="gpt-3.5-turbo", openai_key="your-openai-api-key")

    return {
        "answer": answer,
        "context_used": [r['content'] for r in results]  # optional: return source context
    }
