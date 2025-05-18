from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import uuid

@dataclass
class Document:
    id: str
    title: str
    content: str
    chunks: List[str]
    embeddings: List[List[float]]
    created_at: datetime
    updated_at: datetime
    metadata: dict
    
    @classmethod
    def create(cls, title: str, content: str, chunks: List[str], embeddings: List[List[float]], metadata: dict = None) -> 'Document':
        """Factory method to create a new Document."""
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            chunks=chunks,
            embeddings=embeddings,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        ) 