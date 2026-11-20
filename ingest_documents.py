from backend.vector_store import LegalVectorStore


if __name__ == "__main__":

    print("=" * 70)
    print("LegalBot External Document Ingestion")
    print("=" * 70)

    vector_store = LegalVectorStore()

    vector_store.ingest_external_files()

    print("=" * 70)
    print("Document ingestion finished.")
    print("=" * 70)