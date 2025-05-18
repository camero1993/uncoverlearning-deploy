from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore
import os
from dotenv import load_dotenv
from langchain.schema import BaseMessage
from langchain.chains.conversational_retrieval.base import _get_chat_history

# Load environment variables
load_dotenv()

class LangChainRAGChain:
    """RAG pipeline implementation using LangChain's chains."""
    
    def __init__(
        self,
        vector_store: LangChainVectorStore,
        gemini_api_key: Optional[str] = None,
        model_name: str = "models/gemini-1.5-pro-latest"
    ):
        """
        Initialize the RAG chain.
        
        Args:
            vector_store: LangChainVectorStore instance
            gemini_api_key: Google Gemini API key
            model_name: Name of the Gemini model to use
        """
        self.vector_store = vector_store
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment variables")
        
        # Initialize the LLM
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.gemini_api_key,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create the RAG chain
        self.chain = self._create_rag_chain()
    
    def _create_rag_chain(self) -> ConversationalRetrievalChain:
        """Create the RAG chain with conversation memory."""
        # Create the prompt template
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a kind, peer-to-peer chat bot tutor for college students, focused on helping them understand the provided document.
Your primary goal is to guide the student's learning based *only* on the information found in the document excerpts and the conversation history.
Do not provide information from outside the document.

When answering:
- Explain concepts clearly and break down complex ideas.
- Provide examples from the document or create simple illustrative examples when helpful.
- Craft answers that guide the student's understanding, rather than just giving direct answers.
- If the information needed to answer the question is not present in the excerpts or history, state that you cannot answer based on the provided context.
- If the user's question is unclear or could refer to multiple concepts in the document/history, ask a clarifying question to understand exactly what they are asking about.
- Maintain a friendly, approachable, peer-to-peer tone throughout.
- Break up your answers into clear paragraphs (including a full blank line in between each one) and use bullets for lists to maximize readability."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
            ("human", "Context: {context}")
        ])
        
        # Create the chain
        # Note: Use chain_type="stuff" with our custom prompt instead of passing combine_docs_chain directly
        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 10}
            ),
            memory=self.memory,
            combine_docs_chain_kwargs={
                "prompt": qa_prompt
            },
            return_source_documents=True,
            return_generated_question=False
        )
        
        return chain
    
    def query(
        self,
        question: str,
        file_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG chain with a question.
        
        Args:
            question: The question to ask
            file_title: Optional file title to filter results
            
        Returns:
            Dictionary containing the answer and source documents
        """
        # 1. Perform hybrid search to get documents
        query_embedding = self.vector_store.embeddings.embed_query(question)
        
        search_results = self.vector_store.hybrid_search(
            query=question,
            query_embedding=query_embedding,
            match_count=10,
            full_text_weight=1.0,
            semantic_weight=1.0,
            rrf_k=50,
            file_title=file_title or ""
        )
        
        if not search_results:
            return {
                "answer": "Could not find relevant information in the specified document.",
                "source_documents": []
            }
        
        documents = [
            Document(
                page_content=result["content"],
                metadata={
                    "id": result.get("id"),
                    "fileId": result.get("fileId"),
                    "position": result.get("position"),
                    "originalName": result.get("originalName"),
                    "downloadUrl": result.get("downloadUrl")
                }
            )
            for result in search_results
        ]
        
        # 2. Get current chat history
        current_chat_history_messages: List[BaseMessage] = self.memory.chat_memory.messages

        # 3. Generate standalone question if history exists
        new_question = question
        if current_chat_history_messages:
            chat_history_str = _get_chat_history(current_chat_history_messages)
            # The question_generator is an LLMChain, its output_key is typically 'text'
            question_generator_output = self.chain.question_generator.invoke({
                "question": question,
                "chat_history": chat_history_str
            })
            new_question = question_generator_output[self.chain.question_generator.output_key]

        # 4. Invoke combine_docs_chain with our documents and the (new) question
        # The combine_docs_chain (e.g., StuffDocumentsChain) takes "input_documents", 
        # "question", and any other variables from its prompt (e.g., "chat_history").
        # Our qa_prompt (used by combine_docs_chain) expects "chat_history" as MessagesPlaceholder.
        combine_docs_input = {
            "input_documents": documents,
            "question": new_question,
            "chat_history": current_chat_history_messages # Pass List[BaseMessage] for MessagesPlaceholder
        }
        
        # The output is a dict, typically with a key like 'output_text'.
        # ConversationalRetrievalChain maps this to "answer".
        # We use combine_docs_chain.output_key to be robust.
        generated_response = self.chain.combine_docs_chain.invoke(combine_docs_input)
        final_answer = generated_response[self.chain.combine_docs_chain.output_key]
        
        # 5. Manually update memory
        # Use the original question and the final answer for memory.
        self.memory.save_context(
            {"question": question}, # Inputs to the chain for this turn
            {"answer": final_answer}  # Outputs from the chain for this turn
        )
        
        # Return the answer and the source documents we fetched and used
        return {
            "answer": final_answer,
            "source_documents": documents
        } 