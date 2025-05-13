# LangChain Documentation References

This directory contains references to key LangChain documentation that we'll use for the migration.

## Key Documentation Links

1. **Document Loaders**
   - [PDF Loaders](https://python.langchain.com/docs/modules/data_connection/document_loaders/pdf)
   - [Text Loaders](https://python.langchain.com/docs/modules/data_connection/document_loaders/text)

2. **Text Splitting**
   - [Text Splitters](https://python.langchain.com/docs/modules/data_connection/text_splitter)

3. **Embeddings**
   - [Google Vertex AI Embeddings](https://python.langchain.com/docs/modules/model_io/embeddings/google_vertex_ai)
   - [Google Generative AI Embeddings](https://python.langchain.com/docs/modules/model_io/embeddings/google_generative_ai)

4. **Vector Stores**
   - [Supabase Vector Store](https://python.langchain.com/docs/modules/data_connection/vectorstores/integrations/supabase)

5. **Chains**
   - [RAG Chain](https://python.langchain.com/docs/modules/chains/popular/retrieval_qa)
   - [Conversation Chain](https://python.langchain.com/docs/modules/chains/popular/chat_conversation)

6. **Memory**
   - [Conversation Memory](https://python.langchain.com/docs/modules/memory)

## Migration Notes

1. We'll be using the following LangChain components:
   - `PyMuPDFLoader` for PDF processing
   - `RecursiveCharacterTextSplitter` for text chunking
   - `GoogleGenerativeAIEmbeddings` for embeddings
   - `SupabaseVectorStore` for vector storage
   - `RetrievalQA` chain for RAG implementation

2. Key differences from current implementation:
   - LangChain provides more standardized interfaces
   - Built-in support for various document formats
   - More flexible text splitting strategies
   - Integrated memory management for conversations 