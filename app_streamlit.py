import json
import requests
import streamlit as st

API_URL = "http://localhost:8000"

st.set_page_config(page_title="LegalBot", page_icon="⚖️", layout="centered")

st.markdown("""
<style>
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse;
        text-align: right;
        background-color: rgba(0, 102, 204, 0.08);
        border-radius: 12px;
        padding: 8px 12px;
        margin-left: auto;
        max-width: 85%;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        background-color: rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 8px 12px;
        margin-right: auto;
        max-width: 85%;
    }
    .source-tag {
        font-size: 0.82rem;
        color: #7d8590;
        margin-top: 6px;
        font-style: italic;
    }
    .critical-badge {
        font-size: 0.78rem;
        background-color: #ffebe9;
        color: #cf222e;
        border: 1px solid #ff8182;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        margin-bottom: 4px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = "case_1"
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("⚖️ LegalBot")
    st.caption("Enterprise Portfolio Manager")
    st.divider()

    # 1. Dynamically fetch clients from MongoDB
    try:
        client_res = requests.get(f"{API_URL}/clients", timeout=3)
        available_clients = client_res.json().get("clients", ["case_1", "case_2"])
    except requests.RequestException:
        available_clients = ["case_1", "case_2"]

    selected_client = st.selectbox(
        "Active Client File:",
        options=available_clients,
        index=0 if st.session_state.current_session_id not in available_clients 
              else available_clients.index(st.session_state.current_session_id)
    )

    if selected_client != st.session_state.current_session_id:
        st.session_state.current_session_id = selected_client
        st.session_state.messages = []
        try:
            res = requests.get(f"{API_URL}/history/{selected_client}", timeout=5)
            if res.status_code == 200:
                st.session_state.messages = res.json().get("history", [])
        except requests.RequestException:
            pass
        st.rerun()

    st.divider()

    # 2. Portfolio Management Tools
    with st.expander("🛠️ Manage Client & Case Lifecycle"):
        st.markdown("#### Register New Client")
        new_cid = st.text_input("New Client ID (e.g. client_03)").strip()
        new_cname = st.text_input("Company / Client Name").strip()
        new_jurisdiction = st.text_input("Jurisdiction", value="Delaware Corporate Law").strip()
        if st.button("➕ Add Client", use_container_width=True) and new_cid and new_cname:
            requests.post(f"{API_URL}/clients/new", json={
                "client_id": new_cid, "client_name": new_cname, "jurisdiction": new_jurisdiction
            })
            st.success(f"Added client '{new_cname}'!")
            st.rerun()

        st.divider()
        st.markdown("#### Add New Case to Current Client")
        add_case_id = st.text_input("Case Code (e.g. APX-2026-03)").strip()
        add_case_title = st.text_input("Case Title").strip()
        add_case_summary = st.text_area("Case Summary").strip()
        if st.button("📂 Open Case", use_container_width=True) and add_case_id and add_case_title:
            requests.post(f"{API_URL}/cases/add", json={
                "client_id": selected_client,
                "case_id": add_case_id,
                "title": add_case_title,
                "summary": add_case_summary
            })
            st.success("New ongoing case registered!")
            st.rerun()

        st.divider()
        st.markdown("#### Close an Ongoing Case")
        close_cid = st.text_input("Case Code to Close (e.g. APX-2026-01)").strip()
        close_outcome = st.text_input("Final Disposition / Outcome").strip()
        if st.button("🔒 Mark Case as Closed", use_container_width=True) and close_cid:
            requests.post(f"{API_URL}/cases/close", json={
                "client_id": selected_client,
                "case_id": close_cid,
                "outcome": close_outcome or "Settled / Closed"
            })
            st.success(f"Case {close_cid} moved to closed history!")
            st.rerun()

    st.divider()
    mark_as_critical = st.checkbox("📌 Flag as Critical Court Update / Ruling", help="Persists to MongoDB and indexes into client-specific vector memory.")

st.title("⚖️ LegalBot Consultation")
st.caption(f"Active Client File: **{st.session_state.current_session_id.upper()}**")

# Load existing chat messages
if not st.session_state.messages:
    try:
        res = requests.get(f"{API_URL}/history/{st.session_state.current_session_id}", timeout=5)
        if res.status_code == 200:
            st.session_state.messages = res.json().get("history", [])
    except requests.RequestException:
        pass

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Chat Input
if prompt := st.chat_input("Enter legal inquiry or case update..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        if mark_as_critical:
            st.markdown('<div class="critical-badge">CRITICAL COURT RECORD</div>', unsafe_allow_html=True)
        st.markdown(prompt)

    with st.chat_message("assistant"):
        source_documents = []

        def stream_response():
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "session_id": st.session_state.current_session_id,
                        "message": prompt,
                        "mark_important": mark_as_critical
                    },
                    stream=True,
                    timeout=(10, 180)
                )
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue

                    payload = json.loads(line[6:])
                    event_type = payload.get("type")

                    if event_type == "sources":
                        source_documents.extend(payload.get("sources", []))
                    elif event_type == "token":
                        yield payload.get("content", "")
                    elif event_type == "error":
                        yield f"\n\nError: {payload.get('message', 'Unknown error')}"
            except requests.RequestException as e:
                yield f"\n\nBackend error: {e}"

        answer = st.write_stream(stream_response())

        source_line = ""
        if source_documents:
            top_doc = source_documents[0]
            source_file = top_doc.get("source", "Legal Precedent")
            page_num = top_doc.get("page_number", "1")
            source_line = f"\n\n*Source: {source_file} | Page {page_num}*"
            st.markdown(f'<div class="source-tag">Source: {source_file} | Page {page_num}</div>', unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": f"{answer}{source_line}"
    })