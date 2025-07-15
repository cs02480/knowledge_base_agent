### knowledge_base_agent


# Knowledge Base Agent: RAG Pipeline

This project implements a Retrieval-Augmented Generation (RAG) pipeline designed to answer questions based on a local knowledge base. It uses Qdrant as a vector database for efficient document retrieval and Ollama for local LLM inference.


## Module Explanation

This project is primarily driven by two core scripts: `main_ingestion.py` and `main_rag.py`, supported by various modules in the `src/` directory.

### `main_ingestion.py` (Data Ingestion Pipeline)

This script is responsible for building and maintaining your knowledge base in Qdrant. It automates the process of converting raw documents into a searchable format.

* **Purpose:**
    * Scans specified data directories (`data/pdfs`, `data/texts`) for new or modified documents.
    * Parses documents (e.g., extracts text from PDFs, reads text files).
    * Breaks down the extracted text into smaller, manageable `DocumentChunk`s.
    * Generates numerical vector embeddings for each chunk using a pre-trained embedding model (FastEmbed).
    * Uploads these chunks (along with their embeddings and metadata, including the full text of the chunk) to your Qdrant vector database.
    * Maintains a `FileTracker` to avoid re-processing already ingested or unchanged files.
    * Includes an option to clear all existing data in Qdrant before ingesting new data, useful for starting fresh or updating the entire knowledge base.

* **Key Components:**
    * `src/document_processors.py`: Contains logic for reading and chunking different document types (PDF, TXT).
    * `src/embedding_models.py`: Provides the interface to generate embeddings for text chunks.
    * `src/qdrant_manager.py`: Handles all interactions with the Qdrant database, including collection creation, upserting (uploading) points, and managing collection information. **Crucially, it ensures the chunk's text is stored in the Qdrant payload.**
    * `src/file_tracker.py`: Records the state of ingested files to enable incremental updates.

### `main_rag.py` (Retrieval-Augmented Generation Pipeline)

This script forms the interactive part of the RAG system, allowing you to ask questions and receive answers informed by your knowledge base.

* **Purpose:**
    * Takes a user query as input.
    * Embeds the user query into a vector representation.
    * Uses the `Retriever` to search the Qdrant vector database for document chunks whose embeddings are most similar to the query embedding.
    * Retrieves the actual text content of these relevant chunks from Qdrant's payload.
    * Constructs a prompt for the Large Language Model (LLM), providing the original query along with the retrieved document chunks as context.
    * Sends this contextualized prompt to the local LLM (Ollama).
    * Receives and displays the LLM's generated answer.

* **Key Components:**
    * `src/retriever.py`: Manages the similarity search operation in Qdrant. It embeds the query and fetches the top-k most relevant document chunks, *including their full text from the payload*.
    * `src/llm_integrator.py`: Provides an interface to interact with the local Ollama LLM, sending prompts and receiving responses.



## Step-by-Step Guide to Run the Project

Follow these steps to set up and run your RAG pipeline.

### Prerequisites

Before you start, ensure you have the following installed:

* **Python 3.9+**:
    ```bash
    sudo apt update
    sudo apt install python3.9 python3.9-venv
    ```
* **Ollama**:
    Install Ollama from its official website: [https://ollama.com/download](https://ollama.com/download)
    After installation, pull the required LLM model (e.g., `qwen:8b`).
    ```bash
    ollama pull qwen:8b
    ```
    You will also need to run the Ollama server in a separate terminal:
    ```bash
    ollama serve
    ```
* **Qdrant**:
    Run Qdrant using Docker. Ensure Docker is installed and running.
    ```bash
    docker run -p 6333:6333 -p 6334:6334 \
        -v $(pwd)/qdrant_data:/qdrant/storage \
        qdrant/qdrant
    ```
    This command will run Qdrant and store its data in a `qdrant_data` directory in your current working directory. Keep this terminal open.

### Setup

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone <your-repository-url> knowledge_base_agent
    cd knowledge_base_agent
    ```

2.  **Create and activate a Python Virtual Environment:**
    ```bash
    python3.9 -m venv .kbavenv
    source .kbavenv/bin/activate
    ```
    (Your terminal prompt should now show `(.kbavenv)`).

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Place your documents:**
    Put your PDF files in the `data/pdfs/` directory and plain text files in the `data/texts/` directory. Example dummy files are usually present.

### How to Run

Ensure both **Ollama server** (`ollama serve`) and **Qdrant container** are running in separate terminals before proceeding.

#### 1. Ingest Data

First, you need to process and upload your documents to Qdrant.

* **Important:** If this is your first time running ingestion, or if you've made changes to the `qdrant_manager.py` (especially to how payload is stored), it's highly recommended to clear existing data.
    Open `main_ingestion.py` and **uncomment** the line:
    ```python
    # ingestion_manager.clear_all_ingested_data()
    ```
    So it looks like:
    ```python
    ingestion_manager.clear_all_ingested_data()
    ```

* Run the ingestion script:
    ```bash
    /home/king/knowledge_base_agent/.kbavenv/bin/python main_ingestion.py
    ```
    This will process your documents, generate embeddings, and upload them to Qdrant. You will see logs indicating the progress.

#### 2. Run the RAG Pipeline

Once ingestion is complete, you can start querying your knowledge base.

* Run the RAG pipeline script:
    ```bash
    /home/king/knowledge_base_agent/.kbavenv/bin/python main_rag.py
    ```
* The application will prompt you to enter your query. Type your question and press Enter.
* The pipeline will retrieve relevant information from Qdrant and use it as context for the Ollama LLM to generate an answer.

---

### Configuration

You can adjust various settings like Qdrant host/port, Ollama model name, and collection name in `src/config.py`.
