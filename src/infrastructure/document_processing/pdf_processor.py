from typing import List, Optional, Union
from pathlib import Path
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LangChainDocumentProcessor:
    """Document processor using LangChain components."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        text_threshold: int = 20,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            text_threshold: Minimum text density for OCR fallback
            gemini_api_key: Google Gemini API key
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_threshold = text_threshold
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment variables")
        
        # Initialize LangChain components
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False
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
        
        # Load PDF using PyMuPDFLoader
        if pdf_url:
            loader = PyMuPDFLoader(pdf_url)
        else:
            loader = PyMuPDFLoader(str(pdf_path))
        
        # Get the raw PyMuPDF document for OCR fallback
        if pdf_url:
            import requests
            response = requests.get(pdf_url)
            response.raise_for_status()
            pdf_doc = fitz.open("pdf", response.content)
        else:
            pdf_doc = fitz.open(str(pdf_path))
        
        # Process each page
        documents = []
        for i, page in enumerate(pdf_doc):
            # Get text using LangChain's loader
            page_doc = loader.load_page(i)
            
            # If text density is low, use OCR
            if len(page_doc.page_content.strip()) < self.text_threshold:
                ocr_text = self._extract_text_with_ocr(page)
                if ocr_text:
                    page_doc.page_content = ocr_text
            
            documents.append(page_doc)
        
        # Split documents into chunks
        split_docs = self.text_splitter.split_documents(documents)
        
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