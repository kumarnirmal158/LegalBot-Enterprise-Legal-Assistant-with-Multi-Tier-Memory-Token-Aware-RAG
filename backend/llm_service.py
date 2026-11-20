import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in your .env file.")

client = Groq(api_key=GROQ_API_KEY)

LEGAL_SYSTEM_PROMPT = """You are LegalBot, a corporate legal information assistant.

Your job is to answer the user's question using ONLY the
information provided in:

1. Active Client Entity Profile
2. Recent Conversation History
3. Retrieved External Legal Documents

IMPORTANT RULES:

1. Ground answers strictly in the provided Active Client Context, Chat History, and Retrieved Legal Documents.

2. Retrieved External Legal Documents are the primary source
   for document-specific questions.

3. Do NOT invent:
   - contract clauses
   - case names
   - case dates
   - monetary amounts
   - statutory provisions
   - legal obligations
   - facts not present in the context

4. If the retrieved documents do not contain enough information,
   clearly say:
   "Our indexed legal records do not contain specific terms
   covering this topic."

5. Do not provide unrelated legal background.

6. Do not repeat the user's question unnecessarily.

7. Keep answers concise and practical.

8. Normally answer in approximately 3-6 sentences.

9. For simple factual questions, answer in 1-3 sentences.

10. Mention the source document and page when that information
    is available in the retrieved context.

11. Do not create citations that are not present in the context.

12. Provide informational legal guidance and clearly avoid
    presenting the response as a substitute for qualified legal
    advice.
13. DO NOT start your response with "Answer:"

14. PARTY DISAMBIGUATION:
   - Distinguish carefully between the parties in the Active Client Matter (e.g., employee/contractor Jordan Lee) and third-party commercial entities appearing in sample contract templates (e.g., Northstar Systems LLC).
   - When citing contract terms, reference the clauses as governing standards without confusing the contract counterparty with the active matter's defendant.
15. Complete all legal analyses fully without cutting off sentences.

"""


def build_user_prompt(client_context: str, chat_history: str, rag_context: str, query: str,) -> str:

    return f"""### ACTIVE CLIENT ENTITY PROFILE
{client_context}

### RECENT CONVERSATION HISTORY
{chat_history}

### RETRIEVED EXTERNAL LEGAL DOCUMENTS
{rag_context}

### CURRENT USER QUESTION
{query}

Use the provided context to answer the question concisely."""

def stream_legal_response(client_context: str, chat_history: str, rag_context: str, query: str,):

    user_prompt = build_user_prompt(client_context, chat_history, rag_context, query)

    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=450,
        stream=True)

    for chunk in stream:

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
    
        if delta.content:
            yield delta.content