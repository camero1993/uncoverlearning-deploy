from fastapi import HTTPException, status

class DocumentProcessingError(HTTPException):
    """Raised when there's an error processing a document."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {detail}"
        )

class QueryProcessingError(HTTPException):
    """Raised when there's an error processing a query."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {detail}"
        )

class ConfigurationError(Exception):
    """Raised when there's a configuration error."""
    pass

class VectorStoreError(Exception):
    """Raised when there's an error with the vector store."""
    pass

class DocumentProcessorError(Exception):
    """Raised when there's an error with the document processor."""
    pass

class RAGChainError(Exception):
    """Raised when there's an error with the RAG chain."""
    pass 