import os
import sys

# Add the current directory to sys.path to ensure we can import if needed, 
# though for this script mainly library imports are needed.
sys.path.append(os.getcwd())

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
except ImportError as e:
    print(f"Error importing libraries: {e}")
    print("Please ensure you have installed requirements.txt")
    sys.exit(1)

def inspect_vector_store():
    index_path = "faiss_index"
    
    if not os.path.exists(index_path):
        print(f"Index folder '{index_path}' not found.")
        print("Please run 'python rag_graph.py' first to generate the index.")
        return

    print(f"Loading vector store from '{index_path}'...")
    try:
        # Initialize Embeddings (Must match the one used to create the index in rag_graph.py)
        embeddings = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
        
        # Load the index
        # allow_dangerous_deserialization is required for loading local pickle files in newer langchain versions
        vector_store = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        
        # 1. Check total count
        # The underlying faiss index is accessible via vector_store.index
        count = vector_store.index.ntotal
        print(f"\n✅ Success! Index loaded correctly.")
        print(f"📊 Total Data Points (Vectors): {count}")
        
        # 2. Interactive Test Mode
        print("\n--- Interactive Search Test (Type 'exit' to quit) ---")
        while True:
            query = input("\nEnter search query to test data quality: ")
            if query.lower() in ['exit', 'quit']:
                break
            
            if not query.strip():
                continue
                
            results = vector_store.similarity_search(query, k=3)
            
            if not results:
                print("No results found.")
            else:
                print(f"\nTop 3 results for '{query}':")
                for i, doc in enumerate(results, 1):
                    source = doc.metadata.get('source', 'Unknown Source')
                    # Show first 200 chars of content
                    content = doc.page_content.replace('\n', ' ')[:200]
                    print(f"\n[Result {i}] From: {source}")
                    print(f"Content: {content}...")
                    
    except Exception as e:
        print(f"\n❌ Error inspecting index: {e}")

if __name__ == "__main__":
    inspect_vector_store()
