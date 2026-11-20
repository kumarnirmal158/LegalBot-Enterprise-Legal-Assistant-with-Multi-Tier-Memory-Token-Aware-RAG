
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
client = MongoClient(MONGO_URI)
db = client["legalbot_db"]
ist_timezone = ZoneInfo("Asia/Kolkata")

# ------------------------------------------------------------------
# 1. Chat History Operations
# ------------------------------------------------------------------
def save_message_to_db(session_id: str, role: str, content: str, is_important: bool = False):
    """
    Saves all messages to MongoDB. Flags important updates.
    """
    message_doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "is_important": is_important,
        "timestamp": datetime.now(tz=ist_timezone).isoformat()
    }
    db.chat_history.insert_one(message_doc)

def get_session_history_from_db(session_id: str, limit: int = 6):
    messages = list(
        db.chat_history.find({"session_id": session_id})
        .sort("timestamp", -1)
        .limit(limit)
    )
    messages.reverse()
    for m in messages:
        m["_id"] = str(m["_id"])
    return messages

# ------------------------------------------------------------------
# 2. Dynamic Client Profile Operations
# ------------------------------------------------------------------
def get_client_profile_from_db(session_id: str):
    return db.client_profiles.find_one({"_id": session_id})

def close_case_in_db(session_id: str, case_id: str, final_outcome: str):
    """
    Marks an ongoing case as closed and appends final outcome.
    """
    db.client_profiles.update_one(
        {"_id": session_id, "cases.case_id": case_id},
        {
            "$set": {"cases.$.status": "closed"},
            "$push": {"cases.$.court_updates": f"Case Closed: {final_outcome}"}
        }
    )

def add_new_case_to_db(session_id: str, case_id: str, title: str, summary: str):
    """
    Adds a new ongoing case to an existing client record.
    """
    new_case = {
        "case_id": case_id,
        "title": title,
        "status": "ongoing",
        "summary": summary,
        "court_updates": []
    }
    db.client_profiles.update_one(
        {"_id": session_id},
        {"$push": {"cases": new_case}}
    )

def add_court_update_to_db(session_id: str, case_id: str, update_text: str):
    """
    Appends a critical court update to a specific case.
    """
    db.client_profiles.update_one(
        {"_id": session_id, "cases.case_id": case_id},
        {"$push": {"cases.$.court_updates": update_text}}
    )

def get_all_client_ids():
    """Fetch all registered client IDs dynamically from MongoDB."""
    clients = list(db.client_profiles.find({}, {"_id": 1}))
    return [c["_id"] for c in clients] if clients else ["case_1", "case_2"]

def register_new_client(client_id: str, client_name: str, jurisdiction: str):
    """Create a new client profile in MongoDB."""
    doc = {
        "_id": client_id,
        "client_name": client_name,
        "jurisdiction": jurisdiction,
        "status": "active",
        "cases": []
    }
    db.client_profiles.update_one({"_id": client_id}, {"$set": doc}, upsert=True)

def update_client_status(client_id: str, status: str):
    """Mark a client as active or inactive (e.g., 'no current dealings')."""
    db.client_profiles.update_one({"_id": client_id}, {"$set": {"status": status}})