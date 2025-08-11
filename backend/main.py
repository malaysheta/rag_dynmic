from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
import os
import shutil
import chat

load_dotenv()

app = FastAPI()

# Include the router from chat.py
app.include_router(chat.router)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Store list of uploaded files
uploaded_files = []

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Remove all previously uploaded files
        for old_file in UPLOAD_DIR.iterdir():
            if old_file.is_file():
                old_file.unlink()
        uploaded_files.clear()

        # Optionally: Clear Qdrant collection (requires Qdrant client)
        # from qdrant_client import QdrantClient
        # client = QdrantClient(url="http://localhost:6333")
        # client.delete_collection(collection_name='learn_vector')

        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load PDF
        loader = PyPDFLoader(file_path=str(file_path))
        docs = loader.load()

        # Chunk documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=500
        )
        split_docs = text_splitter.split_documents(documents=docs)

        # Create embeddings and store in Qdrant
        embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
        QdrantVectorStore.from_documents(
            documents=split_docs,
            url="http://localhost:6333",
            collection_name='learn_vector',
            embedding=embedding_model
        )

        # Add file to uploaded_files list
        uploaded_files.append(file.filename)
        return {"message": f"PDF {file.filename} processed successfully", "files": uploaded_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_uploaded_files/")
async def get_uploaded_files():
    return {"files": uploaded_files}

@app.post("/remove_file/")
async def remove_file(file_name: str):
    global uploaded_files
    if file_name in uploaded_files:
        file_path = UPLOAD_DIR / file_name
        if file_path.exists():
            file_path.unlink()  # Remove the file from disk
        uploaded_files.remove(file_name)
        return {"message": f"File {file_name} removed successfully", "files": uploaded_files}
    raise HTTPException(status_code=400, detail="File not found")