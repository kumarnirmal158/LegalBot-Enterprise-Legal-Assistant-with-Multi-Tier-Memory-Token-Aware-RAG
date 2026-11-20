import os
import importlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legalbot-precedents")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "legal-documents-v1")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
CHUNK_SIZE_TOKENS = 350
CHUNK_OVERLAP_TOKENS = 70
UPSERT_BATCH_SIZE = 100 

class LegalVectorStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is missing in your .env file.")

        # 1. Connect to Pinecone Cloud
        self.pc = Pinecone(api_key=PINECONE_API_KEY)

        # 2. Embedding Model & Tokenizer
        sentence_transformers = importlib.import_module("sentence_transformers")
        self.embed_model = sentence_transformers.SentenceTransformer(EMBEDDING_MODEL)
        self.tokenizer = self.embed_model.tokenizer

        # 3. Create index if it doesn't exist
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        if INDEX_NAME not in existing_indexes:
            print(f"[Pinecone] Creating index '{INDEX_NAME}'...")
            self.pc.create_index(
                name=INDEX_NAME,
                dimension=EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

        self.index = self.pc.Index(INDEX_NAME)
        print(f"[Pinecone] Connected to index: {INDEX_NAME} | Namespace: {PINECONE_NAMESPACE}")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        token_ids = self.tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def extract_pdf_pages(self, file_path: Path) -> list:
        from pypdf import PdfReader
        pages = []
        reader = PdfReader(str(file_path))
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page_number": page_number, "text": text.strip()})
        return pages

    def load_documents(self) -> list:
        documents = []
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            return documents

        supported_extensions = {".pdf", ".txt", ".md"}

        for file_path in self.data_dir.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in supported_extensions:
                continue
   
            relative_path = file_path.relative_to(self.data_dir)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "general"
            document_type = file_path.stem.replace("_", " ").title()

            print(f"[Documents] Reading: {relative_path}")

            if file_path.suffix.lower() == ".pdf":
                for page in self.extract_pdf_pages(file_path):
                    documents.append({
                        "file_path": file_path,
                        "source": file_path.name,
                        "category": category,
                        "document_type": document_type,
                        "page_number": page["page_number"],
                        "text": page["text"]
                    })
            else:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if content.strip():
                    documents.append({
                        "file_path": file_path,
                        "source": file_path.name,
                        "category": category,
                        "document_type": document_type,
                        "page_number": "N/A",
                        "text": content.strip()
                    })
        return documents

    def create_chunks(self, documents: list) -> list:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE_TOKENS,
            chunk_overlap=CHUNK_OVERLAP_TOKENS,
            length_function=self.count_tokens,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""]
        )

        all_chunks = []
        total_tokens = 0

        for document in documents:
            chunks = splitter.split_text(document["text"])
            for chunk_number, chunk in enumerate(chunks, start=1):
                token_count = self.count_tokens(chunk)
                total_tokens += token_count
                all_chunks.append({
                    "source": document["source"],
                    "category": document["category"],
                    "document_type": document["document_type"],
                    "page_number": document["page_number"],
                    "chunk_number": chunk_number,
                    "text": chunk,
                    "token_count": token_count
                })

        print(f"[Chunking] Created {len(all_chunks)} chunks (Total tokens: {total_tokens}).")
        return all_chunks

    def ingest_external_files(self):
        print("\n" + "=" * 70)
        print("STARTING LEGAL DOCUMENT INGESTION")
        print("=" * 70)

        documents = self.load_documents()
        if not documents:
            print("[Ingestion] No supported documents found in data/.")
            return

        chunks = self.create_chunks(documents)
        vectors = []

        for index, item in enumerate(chunks, start=1):
            text = item["text"]
            embedding = self.embed_model.encode(text, normalize_embeddings=True).tolist()
            safe_source = item["source"].replace(" ", "_").replace(".", "_")
            page = str(item["page_number"]).replace(" ", "_")
            vector_id = f"{safe_source}_p{page}_c{item['chunk_number']}"

            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": text,
                    "source": item["source"],
                    "category": item["category"],
                    "document_type": item["document_type"],
                    "page_number": str(item["page_number"]),
                    "chunk_id": item["chunk_number"],
                    "token_count": item["token_count"],
                    "source_type": "external_document"
                }
            })

            if index % 50 == 0 or index == len(chunks):
                print(f"[Embedding] Processed {index}/{len(chunks)} chunks")

        # Upload in batches
        uploaded = 0
        for start in range(0, len(vectors), UPSERT_BATCH_SIZE):
            batch = vectors[start:start + UPSERT_BATCH_SIZE]
            self.index.upsert(vectors=batch, namespace=PINECONE_NAMESPACE)
            uploaded += len(batch)
            print(f"[Pinecone] Uploaded {uploaded}/{len(vectors)} records")

        print("=" * 70)
        print(f"INGESTION COMPLETED: {len(vectors)} records in namespace '{PINECONE_NAMESPACE}'")
        print("=" * 70 + "\n")

    def retrieve_relevant_contexts(self, query: str, top_k: int = 5) -> list:
        query_token_count = self.count_tokens(query)
        print(f"[Retrieval] Query: '{query}' | Query tokens: {query_token_count}")

        query_vector = self.embed_model.encode(query, normalize_embeddings=True).tolist()
        result = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE
        )

        retrieved = []
        for rank, match in enumerate(result.matches, start=1):
            meta = match.metadata or {}
            retrieved.append({
                "rank": rank,
                "score": float(match.score),
                "text": meta.get("text", ""),
                "source": meta.get("source", "unknown"),
                "category": meta.get("category", "unknown"),
                "document_type": meta.get("document_type", "unknown"),
                "page_number": meta.get("page_number", "N/A"),
                "chunk_id": meta.get("chunk_id", "N/A"),
                "token_count": meta.get("token_count", 0)
            })

        for item in retrieved:
            print(f"  #{item['rank']} | {item['source']} (Page: {item['page_number']}) | Score: {item['score']:.4f} | Tokens: {item['token_count']}")

        return retrieved

    def store_important_client_update(self, session_id: str, text: str, case_id: str = "general"):
        """
        Embeds ONLY critical court updates and important case facts into Pinecone.
        """
        embedding = self.embed_model.encode(text, normalize_embeddings=True).tolist()
        import uuid
        vector_id = f"critical_{session_id}_{uuid.uuid4().hex[:8]}"

        self.index.upsert(
            vectors=[{
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": text,
                    "session_id": session_id,
                    "case_id": case_id,
                    "type": "critical_court_update"
                }
            }],
            namespace="client-matters-v1"
        )
        print(f"[Pinecone] Upserted critical update for {session_id} into 'client-matters-v1'.")

    def retrieve_client_matter_memory(self, session_id: str, query: str, top_k: int = 2) -> list:
        """
        Searches previously saved critical court updates for this specific client.
        """
        query_vector = self.embed_model.encode(query, normalize_embeddings=True).tolist()
        try:
            result = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                namespace="client-matters-v1",
                filter={"session_id": {"$eq": session_id}}
            )
            return [m.metadata.get("text", "") for m in result.matches if m.score >= 0.70]
        except Exception:
            return []