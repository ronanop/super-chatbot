"""
Script to recreate Pinecone index with correct dimension for text-embedding-004 (768 dimensions)
Run this script to fix the dimension mismatch error.
"""
import os
import sys
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX", "index0")
auto_delete = "--yes" in sys.argv or "-y" in sys.argv

if not api_key:
    raise RuntimeError("PINECONE_API_KEY must be set in environment variables.")

print(f"Connecting to Pinecone...")
pc = Pinecone(api_key=api_key)

# Check if index exists
existing_indexes = [idx.name for idx in pc.list_indexes()]

if index_name in existing_indexes:
    print(f"WARNING: Index '{index_name}' already exists")
    
    # Get index info to check dimension
    try:
        index_info = pc.describe_index(index_name)
        current_dim = index_info.dimension
        print(f"Current index dimension: {current_dim}")
        print(f"Required dimension for text-embedding-004: 768")
        
        if current_dim == 768:
            print(f"Index already has correct dimension (768). No action needed.")
            sys.exit(0)
    except Exception as e:
        print(f"Could not get index info: {e}")
        print(f"Assuming dimension mismatch...")
    
    if auto_delete:
        print(f"\nDeleting existing index '{index_name}'...")
        pc.delete_index(index_name)
        print(f"Index deleted successfully")
    else:
        print(f"\nTo fix this, run:")
        print(f"  python fix_pinecone_index_auto.py --yes")
        print(f"\nOr manually delete the index '{index_name}' in Pinecone dashboard")
        print(f"and recreate it with dimension 768.")
        sys.exit(1)

# Create index with correct dimension (768 for text-embedding-004)
print(f"\nCreating index '{index_name}' with dimension 768...")
try:
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
    print(f"\nIMPORTANT: You'll need to re-ingest all your documents.")
    print(f"All existing vectors in the old index are lost.")
except Exception as e:
    print(f"ERROR creating index: {e}")
    sys.exit(1)

