from dotenv import load_dotenv
import os
from src.infrastructure.document_processing.pdf_processor import LangChainDocumentProcessor
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore
from src.core.app_settings import settings
import uuid
import time
from pathlib import Path

def test_document_processing():
    print("\n=== Document Processing Pipeline Test ===")
    
    # Load environment variables
    load_dotenv()
    
    # Generate a proper UUID for the file
    file_uuid_for_test = str(uuid.uuid4())
    print(f"\nTest File ID (UUID for this run): {file_uuid_for_test}")
    
    try:
        # 1. Initialize Document Processor
        print("\n1. Initializing Document Processor:")
        document_processor = LangChainDocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            text_threshold=20,  # For OCR testing
            gemini_api_key=settings.GEMINI_API_KEY
        )
        print("   ✅ Document processor initialized")
        print(f"   Chunk size: {settings.CHUNK_SIZE}")
        print(f"   Chunk overlap: {settings.CHUNK_OVERLAP}")
        print(f"   OCR threshold: {document_processor.text_threshold}")
        
        # 2. Initialize Vector Store (for Supabase client, embeddings, and hybrid_search)
        print("\n2. Initializing Vector Store Wrapper:")
        # Note: We are not primarily using vector_store.add_documents() for chunk insertion due to metadata handling with older LangChain versions.
        vector_store_wrapper = LangChainVectorStore(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY,
            gemini_api_key=settings.GEMINI_API_KEY,
            table_name=settings.SUPABASE_TABLE # This is 'chunks'
        )
        print("   ✅ Vector store wrapper initialized")
        
        # 3. Process PDF to get documents (chunks)
        print("\n3. Processing PDF into documents (chunks):")
        test_pdf_filename = "attention_is_all_you_need.pdf"
        test_pdf_path = f"test_docs/{test_pdf_filename}"
        if not os.path.exists(test_pdf_path):
            raise FileNotFoundError(f"Test PDF not found: {test_pdf_path}")
        
        print(f"   Processing {test_pdf_path}...")
        processed_documents = document_processor.process_pdf(pdf_path=test_pdf_path)
        print(f"   ✅ Generated {len(processed_documents)} documents (chunks) from PDF.")
        
        if processed_documents:
            print("\n   Sample from first processed document:")
            print(f"   Content: {processed_documents[0].page_content[:200]}...")
            print(f"   Initial Metadata: {processed_documents[0].metadata}")
        
        # 4. Generate Embeddings for the documents
        print("\n4. Generating embeddings for documents:")
        document_embeddings = document_processor.generate_embeddings(processed_documents)
        print(f"   ✅ Generated {len(document_embeddings)} embeddings.")
        
        # 5. Upload PDF to GCP and prepare for Supabase insertion
        print("\n5. Uploading PDF to GCP and inserting file metadata into Supabase 'files' table:")
        start_gcp_file_meta_time = time.time()
        
        print("   Uploading PDF to GCP...")
        with open(test_pdf_path, 'rb') as f:
            file_content_bytes = f.read()
            gcp_url = vector_store_wrapper.upload_to_gcp(
                buffer=file_content_bytes,
                filename=f"{Path(test_pdf_filename).stem}_{file_uuid_for_test}.pdf",
                destination=settings.GCP_DESTINATION_FOLDER
            )
        print(f"   ✅ PDF uploaded to GCP: {gcp_url}")
        
        print("   Inserting file metadata into 'files' table...")
        # This uses the method from LangChainVectorStore to insert into the 'files' table
        db_file_id = vector_store_wrapper.insert_file_metadata(
            title=f"{Path(test_pdf_filename).stem} {file_uuid_for_test[:8]}",
            link=gcp_url
        )
        print(f"   ✅ File metadata inserted. DB File ID for 'chunks.fileId': {db_file_id}")
        gcp_file_meta_time = time.time() - start_gcp_file_meta_time
        print(f"   ✅ GCP upload and file metadata insertion took {gcp_file_meta_time:.2f}s")
        
        # 6. Manually Insert Chunks into Supabase 'chunks' table
        print(f"\n6. Manually inserting {len(processed_documents)} chunks into Supabase '{settings.SUPABASE_TABLE}' table:")
        start_chunk_insertion_time = time.time()
        for i, (doc, embedding_vector) in enumerate(zip(processed_documents, document_embeddings)):
            chunk_uuid = str(uuid.uuid4()) # Unique ID for each chunk
            chunk_data_to_insert = {
                "id": chunk_uuid,
                "fileId": db_file_id, # Foreign key from 'files' table
                "position": i,
                "originalName": test_pdf_filename,
                "content": doc.page_content, # Text content of the chunk
                "downloadUrl": gcp_url, # URL of the original PDF in GCP
                "embedding": embedding_vector # The generated embedding
                # 'fts' and 'created_at' columns are expected to be handled by Supabase (triggers/defaults)
            }
            try:
                vector_store_wrapper.supabase.table(settings.SUPABASE_TABLE).insert(chunk_data_to_insert).execute()
            except Exception as e_insert:
                print(f"ERROR inserting chunk {i} (ID: {chunk_uuid}): {e_insert}")
                raise # Re-raise after logging
            if (i + 1) % 10 == 0 or (i + 1) == len(processed_documents):
                print(f"   Stored chunk {i + 1}/{len(processed_documents)}")
        
        chunk_insertion_time = time.time() - start_chunk_insertion_time
        print(f"   ✅ All chunks inserted in {chunk_insertion_time:.2f}s")
        
        # 7. Test Retrieval from 'chunks' table using Hybrid Search
        print(f"\n7. Testing retrieval from '{settings.SUPABASE_TABLE}' table using Hybrid Search:")
        test_queries = [
            "What is self-attention and how does it work?",
            "Explain the architecture of the transformer model"
        ]
        
        for query_text in test_queries:
            print(f"\n   Query: {query_text}")
            start_retrieval_time = time.time()
            
            # Embed the query using the embedding model from the vector store wrapper
            query_embedding_vector = vector_store_wrapper.embeddings.embed_query(query_text)
            
            # Perform hybrid search using the method from the vector store wrapper
            search_results = vector_store_wrapper.hybrid_search(
                query=query_text,
                query_embedding=query_embedding_vector,
                match_count=settings.MATCH_COUNT,
                full_text_weight=settings.FULL_TEXT_WEIGHT,
                semantic_weight=settings.SEMANTIC_WEIGHT,
                rrf_k=settings.RRF_K,
                file_title=f"{Path(test_pdf_filename).stem} {file_uuid_for_test[:8]}" # Filter by the title in 'files' table
            )
            
            retrieval_time = time.time() - start_retrieval_time
            print(f"   Retrieved {len(search_results)} results in {retrieval_time:.2f}s.")
            
            if search_results:
                print("   Top result preview (from hybrid_search):")
                top_search_result = search_results[0]
                # Column names from hybrid_search RPC might be lowercase
                print(f"     Content: {top_search_result.get('content', 'N/A')[:200]}...")
                print(f"     Position: {top_search_result.get('position', 'N/A')}")
                print(f"     Chunk ID: {top_search_result.get('id', 'N/A')}")
                print(f"     File ID: {top_search_result.get('fileid', 'N/A')}")
            else:
                print("   No results returned from hybrid search for this query.")
            
            time.sleep(0.5) # Brief pause
        
        print("\n=== Document Processing and RAG Test (Manual Chunk Insertion) Completed Successfully ===")
        
    except Exception as e:
        print(f"\n❌ OVERALL ERROR during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_document_processing() 