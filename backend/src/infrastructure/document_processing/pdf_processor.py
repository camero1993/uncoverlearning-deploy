from typing import List, Optional, Union
from pathlib import Path
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv
import requests
import tiktoken
from tqdm import tqdm

# Load environment variables
load_dotenv()

class LangChainDocumentProcessor:
    """Document processor using LangChain components."""
    
    def __init__(
        self,
        chunk_size: int = 2000,  # Default to 2000 tokens (~1200 words)
        chunk_overlap: int = 200,  # Default to 200 tokens overlap
        text_threshold: int = 20,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks in tokens (not characters)
            chunk_overlap: Overlap between chunks in tokens
            text_threshold: Minimum text density for OCR fallback
            gemini_api_key: Google Gemini API key
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_threshold = text_threshold
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment variables")
        
        # Initialize token counter
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Using OpenAI's tokenizer as approximation
        
        # Initialize text splitter with token-based approach
        self.text_splitter = TokenTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            encoding_name="cl100k_base",  # Using OpenAI's tokenizer as approximation
        )
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.gemini_api_key
        )
    
    def _extract_text_with_ocr(self, page: fitz.Page) -> str:
        """Extract text from a page using OCR if needed."""
        text = page.get_text()
        
        # If text density is low, use OCR
        if len(text.strip()) < self.text_threshold:
            try:
                pix = page.get_pixmap(dpi=300)
                img_buffer = io.BytesIO(pix.tobytes("png"))
                image = Image.open(img_buffer)
                text = pytesseract.image_to_string(image)
            except Exception as e:
                print(f"OCR failed: {e}")
                text = ""
        
        return text
    
    def process_pdf(
        self,
        pdf_path: Optional[Union[str, Path]] = None,
        pdf_url: Optional[str] = None
    ) -> List[Document]:
        """
        Process a PDF file using LangChain's PyMuPDFLoader with OCR fallback.
        
        Args:
            pdf_path: Path to local PDF file
            pdf_url: URL of PDF file
            
        Returns:
            List of LangChain Document objects
        """
        if not pdf_path and not pdf_url:
            raise ValueError("Either pdf_path or pdf_url must be provided")

        # Initialize LangChain's PyMuPDFLoader
        if pdf_url:
            loader = PyMuPDFLoader(pdf_url)
        else:
            loader = PyMuPDFLoader(str(pdf_path))
        
        # Load all pages using LangChain's loader
        try:
            print("Loading PDF pages...")
            initial_langchain_docs = loader.load()
            print(f"Loaded {len(initial_langchain_docs)} pages from PDF")
        except Exception as e:
            print(f"Error loading PDF with PyMuPDFLoader: {e}")
            return [] 

        if not initial_langchain_docs:
            return []

        # Prepare for potential OCR fallback by opening the PDF with fitz
        fitz_actual_doc = None
        fitz_pages_for_ocr: List[fitz.Page] = []

        # Check if OCR might be needed
        ocr_potentially_needed = any(
            len(doc.page_content.strip()) < self.text_threshold for doc in initial_langchain_docs
        )

        if ocr_potentially_needed:
            try:
                if pdf_url:
                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()
                    fitz_actual_doc = fitz.open(stream=response.content, filetype="pdf")
                else:
                    fitz_actual_doc = fitz.open(str(pdf_path))
                
                if fitz_actual_doc:
                    print("Loading pages for potential OCR...")
                    for i in tqdm(range(len(fitz_actual_doc)), desc="Loading pages"):
                        fitz_pages_for_ocr.append(fitz_actual_doc.load_page(i))
            except Exception as e:
                print(f"Could not open PDF with fitz for OCR fallback: {e}")

        # Process each document (page) from LangChain loader, with OCR fallback
        print("Processing pages...")
        final_documents_for_splitting = []
        for i, lc_doc in enumerate(tqdm(initial_langchain_docs, desc="Processing pages")):
            page_content_to_use = lc_doc.page_content
            
            if len(lc_doc.page_content.strip()) < self.text_threshold and fitz_pages_for_ocr:
                page_index = lc_doc.metadata.get('page')

                if page_index is not None and 0 <= page_index < len(fitz_pages_for_ocr):
                    fitz_page_for_ocr = fitz_pages_for_ocr[page_index]
                    try:
                        ocr_text = self._extract_text_with_ocr(fitz_page_for_ocr)
                        if ocr_text.strip():
                            page_content_to_use = ocr_text
                    except Exception as e:
                        print(f"Error during OCR for page {page_index}: {e}")
                elif page_index is None:
                    print(f"Warning: 'page' metadata not found in LangChain Document (source: {lc_doc.metadata.get('source')})")
                else:
                    print(f"Warning: Page index {page_index} out of bounds for OCR pages list")
            
            lc_doc.page_content = page_content_to_use
            final_documents_for_splitting.append(lc_doc)
        
        # Split documents into chunks using token-based splitting
        if not final_documents_for_splitting:
            return []
            
        print("Splitting documents into chunks...")
        split_docs = self.text_splitter.split_documents(final_documents_for_splitting)
        
        # Clean up fitz document if it was opened
        if fitz_actual_doc:
            try:
                fitz_actual_doc.close()
            except Exception as e:
                print(f"Error closing fitz_actual_doc: {e}")

        # Verify token counts in chunks
        print("Verifying token counts...")
        for i, doc in enumerate(tqdm(split_docs, desc="Verifying chunks")):
            token_count = len(self.tokenizer.encode(doc.page_content))
            if token_count > 8000:  # Gemini's embedding model limit
                print(f"Warning: Chunk {i} has {token_count} tokens, which exceeds Gemini's limit")

        print(f"Successfully processed PDF into {len(split_docs)} chunks")
        return split_docs
    
    def generate_embeddings(self, documents: List[Document]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.
        
        Args:
            documents: List of LangChain Document objects
            
        Returns:
            List of embedding vectors
        """
        texts = [doc.page_content for doc in documents]
        embeddings = self.embeddings.embed_documents(texts)
        return embeddings 