from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from rag_pipeline import generate_response  # adjust to match your actual function

app = FastAPI()

# Allow JS frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to Vercel domain
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
async def ask_question(request: Request):
    data = await request.json()
    query = data.get("query", "")
    answer = generate_response(query)
    return {"answer": answer}
