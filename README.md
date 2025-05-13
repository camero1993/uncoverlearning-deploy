# UncoverLearning RAG Pipeline

A RAG (Retrieval-Augmented Generation) pipeline for educational content using LangChain, FastAPI, and Google's Gemini model.

## Project Structure

```
uncoverlearning-deploy/
├── src/
│   ├── api/                    # FastAPI application and routes
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app initialization
│   │   └── routes/            # API route handlers
│   │       ├── __init__.py
│   │       ├── document_upload.py   # Document upload endpoints
│   │       └── document_query.py    # Query endpoints
│   │
│   ├── core/                  # Core business logic
│   │   ├── __init__.py
│   │   ├── app_settings.py    # Configuration management
│   │   └── error_handlers.py  # Custom exceptions
│   │
│   ├── domain/               # Domain models and interfaces
│   │   ├── __init__.py
│   │   ├── models/          # Domain models
│   │   └── interfaces/      # Abstract interfaces
│   │
│   └── infrastructure/       # Infrastructure implementations
│       ├── __init__.py
│       ├── document_processing/  # Document processing
│       │   ├── __init__.py
│       │   └── pdf_processor.py
│       ├── rag/              # RAG implementation
│       │   ├── __init__.py
│       │   └── query_processor.py
│       └── vector_store/     # Vector store implementation
│           ├── __init__.py
│           └── supabase_store.py
│
├── tests/                    # Test files
│   ├── __init__.py
│   ├── unit/
│   └── integration/
│
├── docs/                     # Documentation
│   ├── langchain/           # LangChain documentation
│   └── api/                 # API documentation
│
├── scripts/                  # Utility scripts
│   ├── setup.sh
│   └── deploy.sh
│
├── .env.example             # Example environment variables
├── .gitignore
├── requirements.txt         # Python dependencies
├── render.yaml             # Render deployment configuration
└── README.md               # This file
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

3. Run the application locally:
   ```bash
   uvicorn src.main:app --reload
   ```

## Deployment to Render

1. Create a new Web Service on Render:
   - Connect your GitHub repository
   - Select "Python" as the runtime
   - The build command and start command are configured in `render.yaml`

2. Set up environment variables in Render:
   - Go to your service's "Environment" tab
   - Add all required environment variables from `.env.example`
   - Make sure to set `sync: false` for sensitive variables

3. Deploy:
   - Render will automatically deploy when you push to your main branch
   - You can also manually deploy from the Render dashboard

## API Endpoints

- `POST /api/documents/upload/`: Upload and process a document
- `POST /api/queries/query_document/`: Query the RAG pipeline
- `GET /`: Health check endpoint

## Development

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation as needed
- Use type hints throughout the codebase 