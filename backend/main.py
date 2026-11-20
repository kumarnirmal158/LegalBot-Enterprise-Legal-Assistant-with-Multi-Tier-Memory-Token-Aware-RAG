import json
import re
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.database import (
    get_session_history_from_db,
    save_message_to_db,
    add_court_update_to_db,
    add_new_case_to_db,
    close_case_in_db,
    get_all_client_ids,
    register_new_client,
    update_client_status
)
from backend.llm_service import stream_legal_response
from backend.memory import LegalMemoryManager
from backend.vector_store import LegalVectorStore

app = FastAPI(title="LegalBot Dynamic Enterprise Backend")

vector_store = LegalVectorStore()
memory_manager = LegalMemoryManager()

class ChatRequest(BaseModel):
    session_id: str
    message: str
    mark_important: bool = False  # Allows manual or automated critical flagging

# Heuristic keywords indicating critical court developments
IMPORTANT_TRIGGERS = [
    "court update", "judge ruled", "injunction granted", "order issued",
    "subpoena", "settlement agreed", "hearing scheduled", "verdict"
]

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    # 1. Determine if message is critical
    is_critical = request.mark_important or any(
        re.search(rf"\b{k}\b", request.message, re.IGNORECASE) for k in IMPORTANT_TRIGGERS
    )

    # 2. Retrieve shared legal documents (from legal-documents-v1)
    retrieved_docs = vector_store.retrieve_relevant_contexts(request.message, top_k=5)
    rag_parts = [
        f"Source: {doc['source']} | Page: {doc['page_number']}\nContent: {doc['text']}"
        for doc in retrieved_docs
    ]

    # 3. Retrieve client's past critical memory (from client-matters-v1)
    client_critical_memory = vector_store.retrieve_client_matter_memory(
        session_id=request.session_id,
        query=request.message,
        top_k=2
    )
    if client_critical_memory:
        rag_parts.append("### CLIENT-SPECIFIC COURT & CASE UPDATES:\n" + "\n---\n".join(client_critical_memory))

    rag_context_str = "\n\n".join(rag_parts) if rag_parts else "No relevant legal context."

    # 4. Dynamic Client Context & History from MongoDB
    entity_context_str = memory_manager.get_entity_context(request.session_id)
    chat_history_str = memory_manager.get_recent_chat_history(request.session_id)

    # 5. Persist user message to MongoDB (tagged with is_important flag)
    save_message_to_db(request.session_id, "user", request.message, is_important=is_critical)

    # If critical, store in Pinecone matter memory
    if is_critical:
        vector_store.store_important_client_update(
            session_id=request.session_id,
            text=f"Client critical update: {request.message}"
        )

    # 6. Stream response
    def event_stream():
        yield f"data: {json.dumps({'type': 'sources', 'sources': retrieved_docs, 'is_critical': is_critical})}\n\n"

        full_bot_reply = ""
        try:
            for token in stream_legal_response(
                client_context=entity_context_str,
                chat_history=chat_history_str,
                rag_context=rag_context_str,
                query=request.message
            ):
                full_bot_reply += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Save assistant response to MongoDB
            save_message_to_db(request.session_id, "assistant", full_bot_reply, is_important=False)
            yield 'data: {"type": "done"}\n\n'
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/history/{session_id}")
def get_history_endpoint(session_id: str):
    return {"session_id": session_id, "history": get_session_history_from_db(session_id)}

@app.get("/clients")
def list_clients():
    return {"clients": get_all_client_ids()}

class NewClientRequest(BaseModel):
    client_id: str
    client_name: str
    jurisdiction: str

@app.post("/clients/new")
def create_client(req: NewClientRequest):
    register_new_client(req.client_id, req.client_name, req.jurisdiction)
    return {"status": "created"}

class CloseCaseRequest(BaseModel):
    client_id: str
    case_id: str
    outcome: str

@app.post("/cases/close")
def close_case_route(req: CloseCaseRequest):
    close_case_in_db(req.client_id, req.case_id, req.outcome)
    return {"status": "case closed"}

class AddCaseRequest(BaseModel):
    client_id: str
    case_id: str
    title: str
    summary: str

@app.post("/cases/add")
def add_case_route(req: AddCaseRequest):
    add_new_case_to_db(req.client_id, req.case_id, req.title, req.summary)
    return {"status": "case added"}