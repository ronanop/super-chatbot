from app.ingestion.text_loader import ingest_text_file
from app.vectorstore.pinecone_store import upsert_chunks


def main() -> None:
    document = ingest_text_file("kb.txt")
    chunks = document.chunks
    total = len(chunks)
    print(f"Total chunks to upload: {total}")

    batch_size = 100
    for start in range(0, total, batch_size):
        batch = chunks[start:start + batch_size]
        upsert_chunks(batch)
        done = min(start + batch_size, total)
        print(f"Uploaded {done}/{total} chunks")

    print("Done.")


if __name__ == "__main__":
    main()