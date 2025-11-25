"""
Script to fix Pinecone dimension mismatch.
Detects the embedding model being used and fixes the Pinecone index accordingly.
"""
import os
import sys
from dotenv import load_dotenv
from pinecone import Pinecone

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()

# Embedding model dimensions mapping
EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,  # Default dimension
    "text-embedding-3-large": 3072,  # Default dimension
    "text-embedding-ada-002": 1536,
    "text-embedding-004": 768,
}

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX", "index0")
embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
auto_delete = "--yes" in sys.argv or "-y" in sys.argv

if not api_key:
    raise RuntimeError("PINECONE_API_KEY must be set in environment variables.")

# Get expected dimension from embedding model
expected_dim = EMBEDDING_DIMENSIONS.get(embedding_model, 1536)  # Default to 1536 if unknown

print(f"Embedding model: {embedding_model}")
print(f"Expected dimension: {expected_dim}")
print(f"Pinecone index: {index_name}")
print(f"\nConnecting to Pinecone...")
pc = Pinecone(api_key=api_key)

# Check if index exists
existing_indexes = [idx.name for idx in pc.list_indexes()]

if index_name not in existing_indexes:
    print(f"\nIndex '{index_name}' does not exist. Creating it with dimension {expected_dim}...")
    try:
        pc.create_index(
            name=index_name,
            dimension=expected_dim,
            metric="cosine",
            spec={
                "serverless": {
                    "cloud": "aws",
                    "region": os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
                }
            }
        )
        print(f"[+] SUCCESS: Index '{index_name}' created with dimension {expected_dim}")
        sys.exit(0)
    except Exception as e:
        print(f"[-] ERROR creating index: {e}")
        sys.exit(1)

# Get current index dimension
try:
    index_info = pc.describe_index(index_name)
    current_dim = index_info.dimension
    print(f"\nCurrent index dimension: {current_dim}")
    print(f"Required dimension: {expected_dim}")
    
    if current_dim == expected_dim:
        print(f"\n[+] Index already has correct dimension ({expected_dim}). No action needed.")
        sys.exit(0)
    
    print(f"\n[!] DIMENSION MISMATCH DETECTED!")
    print(f"   Current: {current_dim}")
    print(f"   Required: {expected_dim}")
    print(f"\n[!] WARNING: Deleting and recreating the index will DELETE ALL existing vectors!")
    print(f"   You will need to re-ingest all your documents after this.")
    
    if auto_delete:
        print(f"\n[*] Deleting existing index '{index_name}'...")
        pc.delete_index(index_name)
        print(f"[+] Index deleted successfully")
        
        print(f"\n[*] Creating new index '{index_name}' with dimension {expected_dim}...")
        try:
            pc.create_index(
                name=index_name,
                dimension=expected_dim,
                metric="cosine",
                spec={
                    "serverless": {
                        "cloud": "aws",
                        "region": os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
                    }
                }
            )
            print(f"[+] SUCCESS: Index '{index_name}' created with dimension {expected_dim}")
            print(f"\n[*] NEXT STEPS:")
            print(f"   1. Re-ingest all your documents through the admin panel")
            print(f"   2. Or use the ingestion scripts to re-process your knowledge base")
            sys.exit(0)
        except Exception as e:
            print(f"[-] ERROR creating index: {e}")
            sys.exit(1)
    else:
        print(f"\nTo fix this automatically, run:")
        print(f"  python fix_pinecone_dimension_mismatch.py --yes")
        print(f"\nOr manually:")
        print(f"  1. Delete index '{index_name}' in Pinecone dashboard")
        print(f"  2. Create new index with dimension {expected_dim}")
        print(f"  3. Re-ingest all documents")
        sys.exit(1)
        
except Exception as e:
    print(f"[-] ERROR: Could not get index info: {e}")
    sys.exit(1)

