# LangGraph RAG Example

This project demonstrates a simple Retrieval-Augmented Generation (RAG) workflow using LangChain and LangGraph.

## Prerequisites

- **Python 3.9 or higher** is required.
- DeepSeek API Key.

## Setup

1.  **Create a Virtual Environment** (if you haven't already):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**:
    - Open `.env` file.
    - Add your DeepSeek API Key and Base URL:
      ```ini
      DEEPSEEK_API_KEY=sk-...
      DEEPSEEK_BASE_URL=https://api.deepseek.com
      ```

## Running the Script

Run the python script:

```bash
python rag_graph.py
```

## How it Works

1.  **Vector Store**: Initializes a FAISS vector store with some dummy documents, using local **HuggingFace Embeddings** (`all-MiniLM-L6-v2`) to avoid extra API costs.
2.  **Graph State**: Maintains the conversation history (`messages`) and retrieved context (`context`).
3.  **Nodes**:
    - `retrieve`: Searches the vector store for relevant information based on the user's query.
    - `generate`: Uses **DeepSeek** model to answer the question using the retrieved context.
4.  **Workflow**: The graph defines the flow: Start -> Retrieve -> Generate -> End.