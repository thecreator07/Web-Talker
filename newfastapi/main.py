from fastapi import FastAPI, HTTPException,Path
from pydantic import BaseModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from openai import OpenAI
from dotenv import load_dotenv
import tempfile, os, json, asyncio
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import hashlib
from helper import fanout
load_dotenv()

# Google Service Account Temp Save
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

tmp_path = os.path.join(tempfile.gettempdir(), "sa.json")
with open(tmp_path, "w") as f:
    json.dump(creds, f)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path

# App Setup
app = FastAPI()

# Allow all origins in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("DEV_MODE") == "true" else [
        "http://localhost:3000",
        "https://web-talker-liart.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Qdrant Client
qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_KEY")
)

# Embeddings
embedder = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.environ.get("GEMINI_API_KEY")
)

# Gemini Client
client = OpenAI(
    api_key=os.environ.get("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Data Models
class UrlRequest(BaseModel):
    url: str
    collection_name: Optional[str] = "rag"

class QueryRequest(BaseModel):
    query: str
    collection_name: Optional[str] = "rag"
    k: Optional[int] = 5

# Helper: Document Splitter
def docs_splitter(base_url):
    loader = WebBaseLoader(base_url)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return text_splitter.split_documents(docs)

# Inject Data into Qdrant
@app.post("/rag/url")
async def rag_injection(request: UrlRequest):
    try:
        # Get current collections
        collections = qdrant_client.get_collections().collections

        # If collection count > 8, prevent adding a new one
        if len(collections) > 8 and request.collection_name not in [c.name for c in collections]:
            raise HTTPException(
                status_code=400,
                detail="Collection limit exceeded. Delete an existing collection before adding a new one."
            )

        # Create unique ID for the URL
        url_hash = hashlib.md5(request.url.encode()).hexdigest()
        print(f"Processing URL:with hash: {url_hash}")
        # Create collection if it doesn't exist
        if request.collection_name not in [c.name for c in collections]:
            qdrant_client.create_collection(
                collection_name=request.collection_name,
                vectors_config={"size": 768, "distance": "Cosine"}
            )

        # Load and embed asynchronously
        split_docs = await asyncio.to_thread(docs_splitter, request.url)
        
        QdrantVectorStore.from_documents(
            documents=split_docs,
            embedding=embedder,
            url=os.environ.get("QDRANT_URL"),
            api_key=os.environ.get("QDRANT_KEY"),
            collection_name=request.collection_name,
        )

        return {
            "status": "success",
            "message": "URL processed and stored in vector DB",
            "url_hash": url_hash,
            "chunks": len(split_docs)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#  Query Data
@app.post("/rag/query")
async def rag_retrieval(request: QueryRequest):
    try:
        context_text=fanout(request.collection_name,request.query,embedder,request.k,client)
        
        SYSTEM_PROMPT = f"""
        You are a helpful assistant. Use ONLY this context:
        {context_text}
        Rules:
        1. Answer only from context.
        2. Provide code in markdown if applicable.        
        """

        chat =  client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.query}
            ]
        )

        return {"answer": chat.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#  Retrieve Collections
@app.get("/rag/collections")
async def list_collections():
    try:
        cols = qdrant_client.get_collections()
        
        return {"collections": [c.name for c in cols.collections]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/rag/collections/{collection_name}")
async def delete_collection(collection_name: str = Path(..., description="Name of the collection to delete")):
    try:
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        if collection_name not in [c.name for c in collections]:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")

        # Delete collection
        qdrant_client.delete_collection(collection_name=collection_name)
        return {"status": "success", "message": f"Collection '{collection_name}' deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))