import os
import json
from dotenv import load_dotenv
import requests
from pathlib import Path
import time

# Load environment variables
load_dotenv()

def test_document_processing():
    """Test the complete RAG pipeline with the Attention paper"""
    
    # Configuration
    API_BASE_URL = "http://localhost:8001"  # Adjust if needed
    PDF_PATH = "test_docs/attention_is_all_you_need.pdf"
    
    print("\n1. Testing Document Upload and Processing")
    print("-----------------------------------------")
    
    # Read PDF file
    with open(PDF_PATH, "rb") as f:
        files = {"file": ("attention_is_all_you_need.pdf", f, "application/pdf")}
        data = {"original_name": "attention_is_all_you_need.pdf"}
        
        # Upload document
        print("Uploading document...")
        response = requests.post(
            f"{API_BASE_URL}/upload_document/",
            files=files,
            data=data
        )
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.text}")
            return
        
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   - File ID: {result.get('file_id')}")
        print(f"   - Total chunks: {result.get('total_chunks')}")
        print(f"   - GCP URL: {result.get('file_url')}")
        
        # Wait for processing to complete
        time.sleep(2)
        
        print("\n2. Testing Document Querying")
        print("---------------------------")
        
        # Test queries
        test_queries = [
            "What is self-attention and how does it work?",
            "Explain the architecture of the transformer model",
            "What are the advantages of transformers over RNNs?",
            "How does positional encoding work in the transformer?",
            "What is the complexity of the attention mechanism?",
            "Describe the multi-head attention mechanism"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: {query}")
            response = requests.post(
                f"{API_BASE_URL}/query_document/",
                json={"query": query}
            )
            
            if response.status_code != 200:
                print(f"❌ Query failed: {response.text}")
                continue
            
            result = response.json()
            print("✅ Query successful!")
            print(f"Answer: {result.get('answer')[:200]}...")
            print(f"Number of source chunks: {len(result.get('chunks', []))}")
            
            # Print first source chunk for verification
            if result.get('chunks'):
                first_chunk = result['chunks'][0]
                print("\nFirst source chunk:")
                print(f"Position: {first_chunk.get('position')}")
                print(f"Text: {first_chunk.get('extractedText')[:100]}...")
            
            time.sleep(1)  # Avoid rate limiting

if __name__ == "__main__":
    test_document_processing() 