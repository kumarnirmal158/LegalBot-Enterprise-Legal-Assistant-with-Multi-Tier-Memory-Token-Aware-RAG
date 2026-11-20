from backend.database import get_client_profile_from_db, get_session_history_from_db

class LegalMemoryManager:
    def get_entity_context(self, session_id: str) -> str:
        profile = get_client_profile_from_db(session_id)
        if not profile:
            return f"Client Identifier: {session_id}\nNo profile registered in MongoDB."

        client_name = profile.get("client_name", session_id)
        jurisdiction = profile.get("jurisdiction", "General Corporate Law")
        cases = profile.get("cases", [])

        ongoing = [c for c in cases if c.get("status") == "ongoing"]
        closed = [c for c in cases if c.get("status") == "closed"]

        lines = [
            f"Client Name: {client_name}",
            f"Jurisdiction: {jurisdiction}",
            "",
            "--- ACTIVE ONGOING MATTERS ---"
        ]

        if ongoing:
            for c in ongoing:
                lines.append(f"• Case [{c.get('case_id')}]: {c.get('title')}")
                lines.append(f"  Summary: {c.get('summary')}")
                if c.get("court_updates"):
                    lines.append(f"  Recent Court Updates: {' | '.join(c.get('court_updates'))}")
        else:
            lines.append("• No active ongoing cases currently pending.")

        lines.append("")
        lines.append("--- CLOSED HISTORICAL MATTERS ---")
        if closed:
            for c in closed:
                lines.append(f"• Resolved Case [{c.get('case_id')}]: {c.get('title')}")
                lines.append(f"  Disposition: {c.get('summary')}")
        else:
            lines.append("• No prior closed cases on file.")

        return "\n".join(lines)

    def get_recent_chat_history(self, session_id: str) -> str:
        messages = get_session_history_from_db(session_id)
        if not messages:
            return "No previous conversation history for this matter."

        formatted = []
        for msg in messages:
            formatted.append(f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}")
        return "\n".join(formatted)