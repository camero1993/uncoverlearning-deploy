from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.document import Document

class DocumentRepository(ABC):
    """Abstract base class for document persistence."""
    
    @abstractmethod
    async def save(self, document: Document) -> Document:
        """Save a document to the repository."""
        pass
    
    @abstractmethod
    async def find_by_id(self, document_id: str) -> Optional[Document]:
        """Find a document by its ID."""
        pass
    
    @abstractmethod
    async def find_by_title(self, title: str) -> Optional[Document]:
        """Find a document by its title."""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Document]:
        """Search for documents using hybrid search."""
        pass
    
    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete a document by its ID."""
        pass 