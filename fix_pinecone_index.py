"""
Script to recreate Pinecone index with correct dimension for text-embedding-004 (768 dimensions)
"""
import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX", "index0")

if not api_key:
    raise RuntimeError("PINECONE_API_KEY must be set in environment variables.")

print(f"Connecting to Pinecone...")
pc = Pinecone(api_key=api_key)

# Check if index exists
existing_indexes = [idx.name for idx in pc.list_indexes()]

if index_name in existing_indexes:
    print(f"WARNING: Index '{index_name}' already exists")
    print(f"Current embedding model (text-embedding-004) produces 768-dimensional vectors")
    print(f"Your existing index likely has 1536 dimensions (mismatch!)")
    print(f"\nOptions:")
    print(f"1. Delete existing index and create new one with 768 dimensions (RECOMMENDED)")
    print(f"2. Use a different index name")
    
    response = input(f"\nDelete '{index_name}' and recreate with 768 dimensions? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print(f"\nDeleting existing index '{index_name}'...")
        pc.delete_index(index_name)
        print(f"Index deleted successfully")
    else:
        new_name = input(f"Enter new index name (or press Enter to cancel): ").strip()
        if new_name:
            index_name = new_name
        else:
            print("Cancelled.")
            exit(0)

# Create index with correct dimension (768 for text-embedding-004)
print(f"\nCreating index '{index_name}' with dimension 768...")
pc.create_index(
    name=index_name,
    dimension=768,  # text-embedding-004 produces 768-dimensional vectors
    metric="cosine",
    spec={
        "serverless": {
            "cloud": "aws",
            "region": os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        }
    }
)

print(f"SUCCESS: Index '{index_name}' created successfully with dimension 768")
print(f"\nIMPORTANT: You'll need to re-ingest all your documents after recreating the index.")
print(f"All existing vectors in the old index will be lost.")

