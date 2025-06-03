from typing import List, Optional
from src.domain.entities.document import Document
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.external.ai_service import AIService
from src.infrastructure.external.storage_service import StorageService

class DocumentService:
    """Service for handling document processing and management."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        ai_service: AIService,
        storage_service: StorageService
    ):
        self.document_repository = document_repository
        self.ai_service = ai_service
        self.storage_service = storage_service
    
    async def process_document(self, file_content: bytes, title: str) -> Document:
        """Process a new document: extract text, create chunks, generate embeddings."""
        # 1. Upload to storage
        storage_url = await self.storage_service.upload(file_content, title)
        
        # 2. Extract text
        content = await self.ai_service.extract_text(file_content)
        
        # 3. Create chunks
        chunks = await self.ai_service.create_chunks(content)
        
        # 4. Generate embeddings
        embeddings = await self.ai_service.generate_embeddings(chunks)
        
        # 5. Create and save document
        document = Document.create(
            title=title,
            content=content,
            chunks=chunks,
            embeddings=embeddings,
            metadata={"storage_url": storage_url}
        )
        
        return await self.document_repository.save(document)
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Document]:
        """Search documents using hybrid search."""
        return await self.document_repository.search(query, limit)
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        return await self.document_repository.find_by_id(document_id) 