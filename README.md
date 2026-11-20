# ⚖️ LegalBot: Multi-Tenant Corporate Legal Assistant (RAG)

An enterprise-grade Retrieval-Augmented Generation (RAG) assistant built for corporate legal consulting firms. LegalBot enables legal advisors to conduct grounded statutory research, track client-specific litigation lifecycles, and analyze judicial precedents with complete tenant isolation and zero hallucination.

---

## 📌 Core Capabilities

1. **Personal Interactions & Multi-Turn Context:**
   - Retains conversational context across multi-turn dialogs without repetitive prompts.
   - Automatically injects active client entities and ongoing dispute facts into the prompt context.

2. **Past Cases & Matter Lifecycle:**
   - Tracks historical case records, prior settlements, and judicial dispositions from MongoDB.
   - Dynamic tools to register new corporate clients, add ongoing litigation matters, and update case statuses to closed/settled.

3. **Similar Cases & Comparative Precedents:**
   - Semantic retrieval across contracts, corporate policies, and court precedent records.
   - Compares current matter facts against historical jurisprudence (e.g., *Waymo v. Uber*, *Apex v. Nexa Systems*) to recommend actionable legal strategies.

4. **Transparent Attribution & Guardrails:**
   - Direct inline citations citing source files and page numbers (e.g., `Source: case_law_and_precedents.pdf | Page 1`).
   - Strict negative prompting prevents the fabrication of non-existent liquidated damages, notice periods, or statutory clauses.

---

## 🏛️ System Architecture

- **Backend Gateway:** FastAPI (Asynchronous endpoints, Server-Sent Events for real-time token streaming).
- **Persistent Data Store:** MongoDB (Client portfolio records, case lifecycle statuses, and full chat session transcripts).
- **Vector Database:** Pinecone Serverless (`all-MiniLM-L6-v2` 384-dimensional dense embeddings, token-aware chunking).
- **Inference Engine:** Groq Cloud (`openai/gpt-oss-120b` running at low temperature for deterministic grounding).
- **Frontend UI:** Streamlit (Chat bubble alignment, dynamic client switcher, inline citation rendering).

---

## 📂 Project Structure

```text
legalbot/
├── backend/
│   ├── database.py             # MongoDB connection, session history, and client lifecycle CRUD
│   ├── init_mongo_clients.py   # Seeding script for dynamic client records (case_1, case_2)
│   ├── llm_service.py          # Groq streaming client and system prompt guardrails
│   ├── main.py                 # FastAPI routing, SSE streaming, and memory synthesis
│   ├── memory.py               # Multi-tier memory manager (Active profile + sliding window)
│   └── vector_store.py         # Pinecone index querying and selective matter vectorization
├── data/                       # Ground truth legal documents
│   ├── contract_law/           # Employment, NDA, Service, and Software License agreements
│   ├── corporate_law/          # Corporate compliance, merger, and shareholder agreements
│   └── intellectual_property/  # Copyright guidelines, patent agreements, trade secret policy
├── .env.example                # Sample environment variables template
├── app_streamlit.py            # Streamlit user interface
├── ingest_documents.py         # Token-aware PDF extraction and Pinecone vector upsert
├── README.md                   # Project documentation
└── requirements.txt            # Project dependencies

```

---

## 🛠️ Step-by-Step Setup & Usage Guide

Follow these steps to set up and run the repository on another machine from scratch.

### 1. Prerequisites

Ensure the following are installed:

* **Python 3.10+** (Python 3.11 or 3.12 recommended)
* **MongoDB** (Local instance running at `mongodb://localhost:27017` or MongoDB Atlas URI)
* **Pinecone Cloud Account** (Free tier index with 384 dimensions and `cosine` similarity metric)
* **Groq Cloud API Key**

---

### 2. Clone the Repository & Navigate to Directory

```bash
git clone [https://gitlab.siamcomputing.com/siamcomputing-training/cet/machine-learning/ml-interns/2026/nirmal-kumar/internship-tasks.git](https://gitlab.siamcomputing.com/siamcomputing-training/cet/machine-learning/ml-interns/2026/nirmal-kumar/internship-tasks.git)
cd internship-tasks/legalbot

```

---

### 3. Create and Activate Virtual Environment

* **On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

```


* **On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate

```



---

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

---

### 5. Configure Environment Variables (`.env`)

Create a `.env` file in the `legalbot/` root directory by copying the sample template:

```bash
cp .env.example .env

```

Populate `.env` with your actual credentials:

```ini
# Groq API Configuration
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL= openai/gpt-oss-120b

# Pinecone Vector Database
PINECONE_API_KEY=pcsk_your_actual_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=legalbot-precedents
PINECONE_NAMESPACE=legal-documents-v1

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=legalbot_db

```

---

### 6. Ingest Legal Documents into Vector Database

Extract text from the legal PDF corpus, perform token-aware chunking (350 tokens, 70 overlap), compute dense embeddings, and upload to Pinecone:

```bash
python ingest_documents.py

```

*Expected output: Vector upsert confirmation for ~740 chunks into namespace `legal-documents-v1`.*

---

### 7. Seed MongoDB Client Portfolios

Populate MongoDB with default client matters (`case_1` for Apex Innovations, `case_2` for Northstar Systems):

```bash
python backend/init_mongo_clients.py

```

---

### 8. Run the Application

You will need **two terminal tabs** running concurrently:

#### Terminal 1: Launch FastAPI Backend Gateway

```bash
# Ensure virtual environment is activated
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

```

*API docs available at: `http://127.0.0.1:8000/docs*`

#### Terminal 2: Launch Streamlit Frontend Client

```bash
# Open a new terminal tab and activate virtual environment
streamlit run app_streamlit.py

```

*Web application opens automatically at: `http://localhost:8501*`

---

## 🧪 Testing the Test Scenarios in UI

1. **Test Multi-Turn Continuity & Active Matters:**
* Select `case_1` (Apex Innovations) from the sidebar.
* Ask: `"Summarize our active ongoing matter concerning the software licensing dispute."`
* Follow up with: `"Based on that, what restrictive covenants apply to Jordan Lee?"`


2. **Test Judicial Precedents (Similar Cases):**
* Ask: `"Search indexed precedents for cases involving bulk data downloads prior to employee departure."`
* Verify: The model retrieves *Waymo v. Uber* and *Apex v. Nexa Systems* with inline page citations.


3. **Test Multi-Tenant Isolation:**
* Switch sidebar to `case_2` (Northstar Systems).
* Ask: `"What is our current dispute status?"`
* Verify: Zero context or leakage from Apex Innovations appears.
