from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from dotenv import load_dotenv
import tempfile, os, json

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

# # Point Google SDK at this file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path

# Init FastAPI
app = FastAPI()

# Models
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


# Embeddings
embedder = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
print(os.environ.get("DATABASE_URL"))
# Vector Store
vector_store = PGVector(
    embeddings=embedder,
    collection_name="docsUV",
    connection=os.environ.get("DATABASE_URL"),
    use_jsonb=True,
    create_extension=True
)

# Gemini Client
client = OpenAI(
    api_key=os.environ.get('GEMINI_API_KEY'),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

@app.post("/rag/url")
async def rag_injection(request: UrlRequest):
    try:
        # Step 1: Split and Embed Docs
        split_docs = docs_splitter(request.url)
        vector_store.add_documents(split_docs)

        return "INJESTION"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/query")
async def rag_retrieval(request:QueryRequest):
    try:
        relevant_chunks = vector_store.similarity_search(request.query, k=5)
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
        
        