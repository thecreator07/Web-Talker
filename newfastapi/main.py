from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from openai import OpenAI
from dotenv import load_dotenv
import tempfile, os, json
from fastapi.middleware.cors import CORSMiddleware
import requests

load_dotenv()

creds = {
    "type": "service_account",
    "project_id": os.getenv("GOOGLE_PROJECT_ID", "text-to-speech-467917"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY"),
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
    "universe_domain": "googleapis.com"
}

temp_dir = tempfile.gettempdir()
tmp_path = os.path.join(temp_dir, "sa.json")
with open(tmp_path, "w") as f:
    json.dump(creds, f)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://your-deployed-frontend.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UrlRequest(BaseModel):
    url: str

class QueryRequest(BaseModel):
    query: str

def docs_splitter(base_url):
    loader = WebBaseLoader(base_url)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = text_splitter.split_documents(docs)
    return split_docs

embedder = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.environ.get("GEMINI_API_KEY")
)

client = OpenAI(
    api_key=os.environ.get('GEMINI_API_KEY'),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

@app.post("/rag/url")
async def rag_injection(request: UrlRequest):
    try:
        split_docs = docs_splitter(request.url)
        print(f"[INFO] Splitting done: {len(split_docs)} chunks")

        qdrant_url = "https://web-talker-1.onrender.com"
        print(f"[DEBUG] Connecting to Qdrant at: {qdrant_url}")

        # Check if the Qdrant service is reachable
        try:
            response = requests.get(f"{qdrant_url}/dashboard", timeout=10)
            print(f"[DEBUG] Qdrant health check response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Failed to connect to Qdrant: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to Qdrant service")

        store = QdrantVectorStore.from_documents(
            documents=split_docs,
            url=qdrant_url,
            collection_name="newrag",
            embedding=embedder,
            timeout=30  # Increase timeout to 30 seconds
        )
        print(store)

        return "INJECTION"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/query")
async def rag_retrieval(request: QueryRequest):
    try:
        qdrant_url = "https://web-talker-1.onrender.com"
        print(f"[DEBUG] Connecting to Qdrant at: {qdrant_url}")

        # Check if the Qdrant service is reachable
        try:
            response = requests.get(f"{qdrant_url}/dashboard", timeout=10)
            print(f"[DEBUG] Qdrant health check response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Failed to connect to Qdrant: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to Qdrant service")

        retriever = QdrantVectorStore.from_existing_collection(
            url=qdrant_url,
            collection_name='newrag',
            embedding=embedder,
            timeout=30  # Increase timeout to 30 seconds
        )
        relevant_chunks = retriever.similarity_search(request.query, k=5)
        context_text = "\n".join([doc.page_content for doc in relevant_chunks])
        SYSTEM_PROMPT = f"""You are a helpful assistant that answers questions based on the available context:\n{context_text}\n\nrules:\n1. answer the question based on the context provided.\n2. don't include the 'context' word in your answer.\n3. if code then provide the code in markdown format.\n4.make the output in readable for human"""
        chat = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.query}
            ]
        )

        return chat.choices[0].message.content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
