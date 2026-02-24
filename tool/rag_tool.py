import logging
import os
import shutil
import time
import gc
from datetime import datetime

from dotenv import load_dotenv
from tool.github_tool import get_repo_content, get_repo_content_by_git
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
REPO_OWNER = os.getenv("TARGET_REPO_OWNER")
REPO_NAME = os.getenv("TARGET_REPO_NAME")
CHROMA_DB_PATH = "./chroma_db"

OLLAMA_EMBEDDING_MODEL = "embeddinggemma"
OLLAMA_BASE_URL = "http://localhost:11434"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_repository_code(
    documents: list[Document],
    repo_owner: str,
    repo_name: str,
    output_base_dir: str = "./saved_repos",
) -> str:
    """
    Save repository code to disk for easy testing and reference.
    
    Args:
        documents: List of LangChain Documents containing code
        repo_owner: Repository owner
        repo_name: Repository name
        output_base_dir: Base directory to save repositories
        
    Returns:
        Path to the saved repository directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    repo_dir = os.path.join(output_base_dir, f"{repo_owner}_{repo_name}_{timestamp}")
    os.makedirs(repo_dir, exist_ok=True)
    
    logger.info(f"Saving repository code to {repo_dir}...")
    
    saved_files = 0
    for doc in documents:
        if not doc.metadata:
            continue
            
        source = doc.metadata.get("source", "unknown")
        
        # Construct file path
        if "/" in source:
            parts = source.split("/", 2)
            if len(parts) >= 3:
                file_path = parts[2]
            else:
                file_path = source
        else:
            file_path = source
        
        full_path = os.path.join(repo_dir, file_path)
        
        # Create directory structure
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save file
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(doc.page_content)
            saved_files += 1
        except Exception as e:
            logger.warning(f"Failed to save {file_path}: {e}")
    
    logger.info(f"✓ Saved {saved_files} files to {repo_dir}")
    
    # Save metadata
    import json
    metadata = {
        "timestamp": timestamp,
        "repository": f"{repo_owner}/{repo_name}",
        "total_files": saved_files,
        "total_documents": len(documents),
    }
    metadata_path = os.path.join(repo_dir, ".gias_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    return repo_dir


def create_rag_knowledge_base(
    docs: list[Document],
    repo_owner: str = None,
    repo_name: str = None,
    save_repo_code: bool = True,
    old_vectorstore = None,
) -> tuple[Chroma, str]:
    """
    Splits documents and builds the vector store using local Ollama for embeddings.
    
    IMPORTANT: This function does NOT delete or close the old vectorstore.
    Instead, it rebuilds the database in-place by:
    1. Clearing the old Chroma collection
    2. Adding new documents to it
    
    This avoids all Windows file locking issues since we never try to delete
    or rename files that are in use by the running server.
    
    Args:
        docs: List of documents to process
        repo_owner: Repository owner (for saving code)
        repo_name: Repository name (for saving code)
        save_repo_code: Whether to save the repository code to disk
        old_vectorstore: Existing vectorstore (kept in place, not closed)
        
    Returns:
        Tuple of (Chroma vectorstore, path to saved repo code if enabled else None)
    """

    if not docs:
        logger.error("No documents available for processing. RAG creation failed.")
        raise ValueError("Document list is empty.")

    logger.info("Starting code chunking...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100, separators=["\n\n", "\n", " ", ""]
    )

    processed_docs = text_splitter.split_documents(docs)
    logger.info(
        f"Code chunking complete. Total chunks generated: {len(processed_docs)}"
    )

    logger.info(
        f"Generating embeddings using local Ollama model: {OLLAMA_EMBEDDING_MODEL}..."
    )

    try:
        embeddings = OllamaEmbeddings(
            model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL
        )
    except Exception as e:
        logger.error(
            f"Failed to initialize Ollama Embeddings. Is Ollama running and model '{OLLAMA_EMBEDDING_MODEL}' pulled? Error: {e}"
        )
        raise

    # Strategy: Rebuild Chroma database in-place without deleting
    # This completely avoids Windows file locking issues
    logger.info("Building new Chroma vectorstore (in-place, no deletion needed)...")
    
    try:
        # Create new Chroma vectorstore at the same location
        # Chroma will handle clearing old data and creating new embeddings
        vectorstore = Chroma.from_documents(
            documents=processed_docs, 
            embedding=embeddings, 
            persist_directory=CHROMA_DB_PATH
        )
        logger.info("✓ New vectorstore created successfully at " + CHROMA_DB_PATH)
        
    except Exception as e:
        logger.error(f"Failed to create vectorstore: {e}")
        raise
    
    # Save repository code if requested
    saved_repo_path = None
    if save_repo_code and repo_owner and repo_name:
        saved_repo_path = save_repository_code(docs, repo_owner, repo_name)
    
    return vectorstore, saved_repo_path


if __name__ == "__main__":
    logger.info(f"Loading repository contents from {REPO_OWNER}/{REPO_NAME}...")
    documents = get_repo_content_by_git(REPO_OWNER, REPO_NAME)

    if not documents:
        logger.error("No documents retrieved from the repository. Exiting.")
        exit(1)

    logger.info(f"Total documents retrieved: {len(documents)}")

    try:
        rag_knowledge_base, saved_path = create_rag_knowledge_base(
            documents, REPO_OWNER, REPO_NAME, save_repo_code=True
        )
        rag_knowledge_base.persist()
        logger.info("RAG knowledge base created and persisted successfully.")
        if saved_path:
            logger.info(f"Repository code saved to: {saved_path}")
    except Exception as e:
        logger.error(f"Failed to create RAG knowledge base: {e}")
        exit(1)
