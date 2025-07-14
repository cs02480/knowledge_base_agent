# main_rag.py

import os
import logging
from typing import List

from src.retriever import Retriever
from src.llm_integrator import LLMIntegrator
from src.models import DocumentChunk # For type hinting

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_rag_prompt(query: str, retrieved_chunks: List[DocumentChunk]) -> str:

     
    """
    Constructs the prompt for the LLM by combining the query and retrieved context.
    """
    context_texts = [f"Source: {chunk.metadata.get('source_file', 'Unknown')}" \
                     + (f", Page: {chunk.metadata['page_number']}" if 'page_number' in chunk.metadata else "") \
                     + f"\nContent: {chunk.text}" for chunk in retrieved_chunks]
    

    retrived_text = ["{chunk.text}" for chunk in retrieved_chunks]
    logging.info(context_texts)
    context_str = "\n\n".join(context_texts)
    
    if not context_str.strip():
        logging.warning("No relevant context retrieved. Generating response without context.")
        return f"Query: {query}\n\nNo relevant information was found in the knowledge base."

    prompt = f"""You are an AI assistant that answers questions based on the provided context.
If the answer is not available in the context, clearly state that you don't have enough information.

Context:
{context_str}

Query: {query}

Answer:"""
    
    logging.debug(f"Generated RAG prompt:\n{prompt}")
    return prompt

def main_rag_pipeline():
    """
    Runs the interactive RAG pipeline.
    """
    logging.info("Initializing RAG pipeline components...")
    retriever = Retriever(use_grpc=True)
    
    # Initialize LLMIntegrator for Ollama and Qwen3
    # IMPORTANT: Replace 'qwen:7b' with the exact tag of your Qwen3 model pulled in Ollama
    # (e.g., 'qwen:32b', 'qwen:72b-instruct-q4_K_M', etc. You can find this with 'ollama list')
    try:
        llm_integrator = LLMIntegrator(llm_provider="ollama", model_name="qwen3:8b") 
        # For Qwen3, a common tag might be 'qwen:7b' or 'qwen:32b' or 'qwen:72b-instruct'
        # Check `ollama list` in your terminal to find the exact tag
    except ValueError as e:
        logging.error(f"Failed to initialize LLM Integrator: {e}")
        logging.error("Please ensure Ollama is running and the specified model is pulled.")
        return

    logging.info("RAG pipeline ready. Type 'exit' or 'quit' to end the session.")

    while True:
        user_query = input("\nEnter your query (or 'exit' to quit): ").strip()
        if user_query.lower() in ["exit", "quit"]:
            break

        if not user_query:
            print("Please enter a query.")
            continue

        logging.info(f"User query received: '{user_query}'")

        # 1. Retrieve relevant chunks
        retrieved_chunks = retriever.retrieve(user_query, top_k=3)

        if not retrieved_chunks:
            print("\nAI Assistant: I couldn't find any relevant information in the knowledge base for your query.")
            # If no context, still try to get a general answer from LLM but warn user
            response = llm_integrator.generate_response(f"Answer the following query: {user_query}. If you don't have enough information, state so clearly.")
            if response:
                print(f"AI Assistant (General): {response}")
            continue

        # Log retrieved chunks for debugging
        logging.debug("Retrieved chunks:")
        for i, chunk in enumerate(retrieved_chunks):
            logging.debug(f"Chunk {i+1} (Source: {chunk.metadata.get('source_file')}, Page: {chunk.metadata.get('page_number') if 'page_number' in chunk.metadata else 'N/A'}): {chunk.text[:100]}...")


        # 2. Build augmented prompt
        rag_prompt = build_rag_prompt(user_query, retrieved_chunks)

        # 3. Generate response from LLM
        print("\nAI Assistant: Generating response...")
        llm_response = llm_integrator.generate_response(rag_prompt)

        if llm_response:
            print(f"\nAI Assistant: {llm_response}")
        else:
            print("\nAI Assistant: Sorry, I couldn't generate a response at this time.")

if __name__ == "__main__":
    # Ensure you've run main_ingestion.py at least once to populate Qdrant
    # Ensure Ollama server is running and the Qwen3 model is pulled.
    main_rag_pipeline()