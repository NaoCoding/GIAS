import logging
import os
import shutil

from dotenv import load_dotenv
from github_tool import get_repo_content, get_repo_content_by_git
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


def create_rag_knowledge_base(docs: list[Document]) -> Chroma:
    """Splits documents and builds the vector store using local Ollama for embeddings."""

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

    # Clean up previous database to ensure fresh analysis
    if os.path.exists(CHROMA_DB_PATH):
        logger.warning(f"Removing existing vector store at {CHROMA_DB_PATH}.")
        shutil.rmtree(CHROMA_DB_PATH)

    # Build Chroma database
    vectorstore = Chroma.from_documents(
        documents=processed_docs, embedding=embeddings, persist_directory=CHROMA_DB_PATH
    )
    logger.info("Vector store creation complete.")
    return vectorstore


if __name__ == "__main__":
    logger.info(f"Loading repository contents from {REPO_OWNER}/{REPO_NAME}...")
    # documents = get_repo_content(REPO_OWNER, REPO_NAME)
    # The reason we switch to Git method is to handle large repositories more efficiently
    documents = get_repo_content_by_git(REPO_OWNER, REPO_NAME)

    if not documents:
        logger.error("No documents retrieved from the repository. Exiting.")
        exit(1)

    logger.info(f"Total documents retrieved: {len(documents)}")

    try:
        rag_knowledge_base = create_rag_knowledge_base(documents)
        rag_knowledge_base.persist()
        logger.info("RAG knowledge base created and persisted successfully.")
    except Exception as e:
        logger.error(f"Failed to create RAG knowledge base: {e}")
        exit(1)
